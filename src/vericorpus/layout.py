# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from dataclasses import dataclass
import math
import re
import statistics
from typing import Iterable

import fitz

from .models import BBox, Candidate, DocumentObject, PageStructure, SpanEvidence
from .util import contains_high_risk, normalize_block_text, normalize_text, stable_id, text_quality, union_bbox


_HEADING_RE = re.compile(
    r"^(?:\d+(?:\.\d+)*\.?\s+\S|abstract\b|introduction\b|materials? and methods?\b|results?(?: and discussion)?\b|discussion\b|conclusions?\b|acknowledg(?:e)?ments?\b|data availability\b|references\b|credit authorship\b|declaration of competing interest\b)",
    re.I,
)
_TABLE_CAPTION_RE = re.compile(r"^(?:table)\s+[A-Za-z0-9IVX]+\b", re.I)
_FIGURE_CAPTION_RE = re.compile(r"^(?:fig\.?|figure|scheme)\s*[A-Za-z0-9IVX]+\b", re.I)
_REFERENCE_ENTRY_RE = re.compile(r"^\s*\[\d+\]\s+")
_EQUATION_NUMBER_RE = re.compile(r"^\(\d+[A-Za-z]?\)$")
_MATH_SYMBOL_RE = re.compile(r"[=±×÷∑∫√∞≤≥↔→←μσλβαγδΔθπ^]|(?:\b(?:sin|cos|tan|log|ln)\b)")


@dataclass
class _RawBlock:
    idx: int
    bbox: BBox
    text: str
    block_type: int
    max_font: float = 0.0
    median_font: float = 0.0
    bold_fraction: float = 0.0
    line_count: int = 0

    @property
    def width(self) -> float:
        return self.bbox.width

    @property
    def height(self) -> float:
        return self.bbox.height


def _bbox_from_tuple(v) -> BBox:
    return BBox(x0=float(v[0]), y0=float(v[1]), x1=float(v[2]), y1=float(v[3]))


def _extract_raw_blocks(page: fitz.Page) -> list[_RawBlock]:
    d = page.get_text("dict", sort=False)
    out: list[_RawBlock] = []
    for idx, block in enumerate(d.get("blocks", [])):
        bbox = _bbox_from_tuple(block.get("bbox", (0, 0, 0, 0)))
        btype = int(block.get("type", 0))
        if btype == 1:
            out.append(_RawBlock(idx=idx, bbox=bbox, text="", block_type=1))
            continue
        lines = block.get("lines", [])
        parts: list[str] = []
        fonts: list[float] = []
        bold = 0
        total_spans = 0
        for line in lines:
            line_parts: list[str] = []
            for span in line.get("spans", []):
                txt = str(span.get("text", ""))
                if txt:
                    line_parts.append(txt)
                size = float(span.get("size", 0.0) or 0.0)
                if size > 0:
                    fonts.append(size)
                font_name = str(span.get("font", "")).lower()
                flags = int(span.get("flags", 0) or 0)
                total_spans += 1
                if "bold" in font_name or (flags & 16):
                    bold += 1
            if line_parts:
                parts.append("".join(line_parts))
        raw = "\n".join(parts)
        out.append(
            _RawBlock(
                idx=idx,
                bbox=bbox,
                text=normalize_block_text(raw),
                block_type=0,
                max_font=max(fonts) if fonts else 0.0,
                median_font=statistics.median(fonts) if fonts else 0.0,
                bold_fraction=(bold / total_spans) if total_spans else 0.0,
                line_count=len(parts),
            )
        )
    return out


def _body_font(blocks: list[_RawBlock]) -> float:
    vals = [b.median_font for b in blocks if b.block_type == 0 and len(b.text) >= 40 and b.median_font > 0]
    return statistics.median(vals) if vals else 9.0


def _math_density(text: str) -> float:
    if not text:
        return 0.0
    math_chars = len(_MATH_SYMBOL_RE.findall(text))
    digits = sum(c.isdigit() for c in text)
    alpha = sum(c.isalpha() for c in text)
    return min(1.0, (math_chars * 2 + min(digits, 6)) / max(alpha + digits, 8))


def _classify_block(block: _RawBlock, page_w: float, page_h: float, body_font: float) -> tuple[str, float]:
    if block.block_type == 1:
        area = block.bbox.width * block.bbox.height
        if area < page_w * page_h * 0.015:
            return "unknown", 0.82
        return "figure", 0.94
    text = block.text.strip()
    if not text:
        return "unknown", 0.4
    low = text.lower()
    rel_y0 = block.bbox.y0 / max(page_h, 1)
    rel_y1 = block.bbox.y1 / max(page_h, 1)

    if rel_y0 < 0.16 and re.search(r"contents lists available|journal homepage|materials today communications", low):
        return "header", 0.98
    if rel_y1 < 0.065:
        return "header", 0.95
    if rel_y0 > 0.86 and re.search(r"doi\.org|received |available online|all rights are reserved|©", low):
        return "footer", 0.96
    if rel_y0 > 0.94:
        if re.fullmatch(r"\s*\d+\s*", text):
            return "page_number", 0.99
        return "footer", 0.92
    if _TABLE_CAPTION_RE.match(text):
        return "table_caption", 0.99
    if _FIGURE_CAPTION_RE.match(text):
        return "figure_caption", 0.99
    if _REFERENCE_ENTRY_RE.match(text):
        return "reference_entry", 0.98
    if low.strip() == "references":
        return "reference_header", 0.99
    if _EQUATION_NUMBER_RE.fullmatch(text):
        return "equation_number", 0.98
    if _HEADING_RE.match(text) and len(text) <= 180:
        return "heading", 0.97
    if len(text) <= 220 and block.max_font >= max(body_font * 1.35, 12.0) and block.bold_fraction >= 0.2:
        if rel_y0 < 0.45:
            return "title", 0.91
        return "heading", 0.88
    if rel_y0 < 0.36 and re.search(r"\b(?:university|universidad|institute|department|facult|center|centre)\b", low):
        return "affiliation", 0.88
    if rel_y0 < 0.35 and ("abstract" in low[:40] or low == "a b s t r a c t"):
        return "abstract", 0.9
    if rel_y0 < 0.42 and (low.startswith("keywords") or low == "a r t i c l e i n f o"):
        return "keywords", 0.88
    if _math_density(text) >= 0.30 and len(text) <= 180:
        return "equation", 0.84
    if re.match(r"^(?:[-•▪◦]|\d+[.)])\s+", text) and len(text) < 1000:
        return "list", 0.85
    if re.match(r"^(?:algorithm|pseudo-?code)\b", low):
        return "algorithm", 0.85
    if len(text) < 180 and re.search(r"\b(?:def|class|import|return|SELECT|function)\b", text):
        return "code", 0.8
    return "paragraph", 0.86


def _greedy_clusters(values: list[float], tolerance: float) -> list[list[float]]:
    if not values:
        return []
    clusters: list[list[float]] = []
    for x in sorted(values):
        if not clusters:
            clusters.append([x])
            continue
        center = statistics.median(clusters[-1])
        if abs(x - center) <= tolerance:
            clusters[-1].append(x)
        else:
            clusters.append([x])
    return clusters


def _infer_columns(objects: list[DocumentObject], page_w: float, page_h: float) -> tuple[int, list[float], float]:
    eligible = [
        o for o in objects
        if o.object_type in {"paragraph", "heading", "reference_entry", "abstract", "keywords", "affiliation", "list"}
        and o.bbox.width <= page_w * 0.55
        and o.bbox.y0 >= page_h * 0.07
        and o.bbox.y1 <= page_h * 0.94
        and len(o.text) >= 8
    ]
    if len(eligible) < 2:
        return 1, [page_w * 0.08], 0.7
    xs = [o.bbox.x0 for o in eligible]
    raw_clusters = _greedy_clusters(xs, tolerance=max(18.0, page_w * 0.045))
    clusters = []
    for c in raw_clusters:
        center = statistics.median(c)
        members = [o for o in eligible if abs(o.bbox.x0 - center) <= max(18.0, page_w * 0.045)]
        text_chars = sum(len(o.text) for o in members)
        if len(c) >= 2 or text_chars >= 40:
            clusters.append(c)
    if not clusters:
        return 1, [statistics.median(xs)], 0.72
    # Merge near-neighbor clusters caused by indentation / subsection headings.
    centers = [statistics.median(c) for c in clusters]
    merged: list[list[float]] = []
    for c in centers:
        if merged and abs(c - statistics.median(merged[-1])) < page_w * 0.16:
            merged[-1].append(c)
        else:
            merged.append([c])
    centers = [statistics.median(c) for c in merged]
    if len(centers) > 3:
        # Keep the three strongest x-origin modes.
        support = []
        for center in centers:
            n = sum(abs(x - center) <= page_w * 0.08 for x in xs)
            support.append((n, center))
        centers = sorted(c for _, c in sorted(support, reverse=True)[:3])
    count = max(1, min(3, len(centers)))
    if count == 1:
        return 1, centers, 0.78
    gaps = [b - a for a, b in zip(centers, centers[1:])]
    sep = min(gaps) / max(page_w, 1)
    conf = max(0.65, min(0.99, 0.62 + sep))
    return count, centers, conf


def _nearest_column(obj: DocumentObject, centers: list[float]) -> int | None:
    if not centers:
        return None
    return min(range(len(centers)), key=lambda i: abs(obj.bbox.x0 - centers[i]))


def _merge_intervals(intervals: Iterable[tuple[float, float]]) -> list[tuple[float, float]]:
    vals = sorted((a, b) for a, b in intervals if b >= a)
    if not vals:
        return []
    merged = [list(vals[0])]
    for a, b in vals[1:]:
        if a <= merged[-1][1] + 2.0:
            merged[-1][1] = max(merged[-1][1], b)
        else:
            merged.append([a, b])
    return [(float(a), float(b)) for a, b in merged]


def _vertical_bands(objects: list[DocumentObject], page_h: float) -> list[tuple[float, float]]:
    usable = [o for o in objects if o.object_type not in {"header", "footer", "page_number"}]
    if not usable:
        return []
    merged = _merge_intervals((o.bbox.y0, o.bbox.y1) for o in usable)
    if len(merged) <= 1:
        return merged
    gap_threshold = max(16.0, page_h * 0.022)
    bands: list[list[float]] = [[merged[0][0], merged[0][1]]]
    for a, b in merged[1:]:
        if a - bands[-1][1] >= gap_threshold:
            bands.append([a, b])
        else:
            bands[-1][1] = max(bands[-1][1], b)
    return [(a, b) for a, b in bands]


def _bbox_union(objs: list[DocumentObject]) -> BBox:
    box = union_bbox([o.bbox for o in objs])
    assert box is not None
    return box


def _table_like(o: DocumentObject) -> bool:
    t = o.text
    if o.object_type in {"table_caption", "table"}:
        return True
    tokens = re.findall(r"\S+", t)
    if not tokens:
        return False
    num = sum(bool(re.search(r"\d", x)) for x in tokens)
    short = sum(len(x) <= 12 for x in tokens)
    units = bool(re.search(r"\b(?:wt%|GPa|MPa|nm|µm|mm|N|mN|%|cm−?1|cm-1)\b", t, re.I))
    return (num / len(tokens) >= 0.22 and short / len(tokens) >= 0.65) or units


def _table_text_from_words(page: fitz.Page, bbox: BBox, caption: DocumentObject) -> str:
    words = page.get_text("words", clip=fitz.Rect(bbox.x0, bbox.y0, bbox.x1, bbox.y1), sort=False)
    data = []
    for w in words:
        x0, y0, x1, y1, txt = w[:5]
        if y1 <= caption.bbox.y1 + 1.5:
            continue
        txt = normalize_text(str(txt))
        if txt:
            data.append((float(x0), float(y0), float(x1), float(y1), txt))
    if not data:
        return caption.text
    rows: list[list[tuple[float,float,float,float,str]]] = []
    for word in sorted(data, key=lambda x: ((x[1] + x[3]) / 2, x[0])):
        cy = (word[1] + word[3]) / 2
        target = None
        for row in rows:
            rcy = statistics.mean((x[1] + x[3]) / 2 for x in row)
            if abs(cy - rcy) <= 3.6:
                target = row
                break
        if target is None:
            rows.append([word])
        else:
            target.append(word)
    rows.sort(key=lambda r: min(x[1] for x in r))
    row_cells: list[list[str]] = []
    for row in rows:
        row = sorted(row, key=lambda x: x[0])
        if not row:
            continue
        widths = [(x[2]-x[0]) / max(len(x[4]),1) for x in row if x[2] > x[0]]
        char_w = statistics.median(widths) if widths else 4.0
        gap_threshold = max(9.5, char_w * 2.5)
        cells: list[str] = []
        cur = [row[0][4]]
        prev_x1 = row[0][2]
        for w in row[1:]:
            gap = w[0] - prev_x1
            if gap >= gap_threshold:
                cells.append(" ".join(cur))
                cur = [w[4]]
            else:
                cur.append(w[4])
            prev_x1 = w[2]
        cells.append(" ".join(cur))
        row_cells.append(cells)

    # Merge visual line wraps inside table cells without guessing values.
    merged_rows: list[list[str]] = []
    i = 0
    while i < len(row_cells):
        cur = row_cells[i]
        if i + 1 < len(row_cells):
            nxt = row_cells[i + 1]
            cur_numeric = sum(bool(re.search(r"(?<![A-Za-z])\d+(?:\.\d+)?", c)) for c in cur)
            nxt_numeric = sum(bool(re.search(r"(?<![A-Za-z])\d+(?:\.\d+)?", c)) for c in nxt)
            if len(cur) >= 2 and len(nxt) == len(cur) and cur_numeric == 0 and nxt_numeric == 0:
                cur = [f"{a} {b}".strip() for a, b in zip(cur, nxt)]
                i += 1
            elif len(cur) >= 2 and len(nxt) == 1 and nxt[0].startswith("(") and not re.search(r"\d", nxt[0]):
                cur = list(cur)
                cur[0] = f"{cur[0]} {nxt[0]}".strip()
                i += 1
        merged_rows.append(cur)
        i += 1

    lines = [caption.text] + [" | ".join(cells) for cells in merged_rows]
    return "\n".join(lines)


def _group_tables(page: fitz.Page, objects: list[DocumentObject], page_w: float) -> tuple[list[DocumentObject], set[str]]:
    additions: list[DocumentObject] = []
    suppressed: set[str] = set()
    for cap in [o for o in objects if o.object_type == "table_caption"]:
        cap_col = cap.column_index
        candidates = []
        for o in objects:
            if o.object_id == cap.object_id or o.object_type in {"header", "footer", "page_number", "figure", "figure_caption"}:
                continue
            if o.bbox.y0 < cap.bbox.y1 - 2 or o.bbox.y0 > cap.bbox.y1 + 68:
                continue
            if cap_col is not None and o.column_index is not None and o.column_index != cap_col:
                continue
            overlap_x = max(0.0, min(cap.bbox.x1 + page_w * 0.1, o.bbox.x1) - max(cap.bbox.x0 - page_w * 0.03, o.bbox.x0))
            if overlap_x <= 0:
                continue
            immediate_header = o.bbox.y0 <= cap.bbox.y1 + 28 and len(o.text) <= 280
            if _table_like(o) or immediate_header:
                candidates.append(o)
        if not candidates:
            continue
        data_members = sorted(candidates, key=lambda x: (x.bbox.y0, x.bbox.x0))
        members = [cap] + data_members
        # Reconstruct visual table rows by y alignment, then sort cells left-to-right.
        row_groups: list[list[DocumentObject]] = []
        for m in data_members:
            cy = (m.bbox.y0 + m.bbox.y1) / 2
            placed = False
            for row in row_groups:
                row_cy = statistics.mean((x.bbox.y0 + x.bbox.y1) / 2 for x in row)
                if abs(cy - row_cy) <= 6.0:
                    row.append(m)
                    placed = True
                    break
            if not placed:
                row_groups.append([m])
        row_groups.sort(key=lambda row: min(x.bbox.y0 for x in row))
        text_lines = [cap.text]
        for row in row_groups:
            cells = []
            for m in sorted(row, key=lambda x: x.bbox.x0):
                cells.append(re.sub(r"\s*\n\s*", " | ", m.text.strip()))
            text_lines.append(" | ".join(cells))
        table_text = _table_text_from_words(page, _bbox_union(members), cap)
        obj = DocumentObject(
            object_id=stable_id(str(cap.page_number), cap.object_id, "table_group"),
            page_number=cap.page_number,
            object_type="table",
            bbox=_bbox_union(members),
            text=table_text,
            confidence=min(0.94, 0.78 + 0.03 * len(members)),
            column_index=cap_col,
            source="pymupdf_layout",
            child_ids=[m.object_id for m in members],
            metadata={"grouping": "caption_plus_aligned_table_like_blocks"},
        )
        additions.append(obj)
        suppressed.update(m.object_id for m in members)
    return additions, suppressed


def _group_equations(objects: list[DocumentObject], page_w: float) -> tuple[list[DocumentObject], set[str]]:
    additions: list[DocumentObject] = []
    suppressed: set[str] = set()
    seeds = [o for o in objects if o.object_type == "equation"]
    used: set[str] = set()
    for seed in seeds:
        if seed.object_id in used:
            continue
        cy = (seed.bbox.y0 + seed.bbox.y1) / 2
        nearby_numbers = [
            o for o in objects
            if o.object_type == "equation_number"
            and abs(((o.bbox.y0 + o.bbox.y1) / 2) - cy) <= 14.0
        ]
        right_edge = max([o.bbox.x1 for o in nearby_numbers], default=seed.bbox.x1 + page_w * 0.12)
        left_edge = min(seed.bbox.x0, min([o.bbox.x0 for o in nearby_numbers], default=seed.bbox.x0))
        same_band = []
        for o in objects:
            if o.object_id in used or o.object_type in {"header", "footer", "page_number", "figure", "figure_caption", "table", "table_caption"}:
                continue
            ocy = (o.bbox.y0 + o.bbox.y1) / 2
            if abs(ocy - cy) > 14.0:
                continue
            within_formula_span = o.bbox.x0 >= left_edge - 4 and o.bbox.x1 <= right_edge + 4
            short_fragment = len(o.text.strip()) <= 40 and o.bbox.width <= page_w * 0.45
            if o.object_type in {"equation", "equation_number"} or _math_density(o.text) >= 0.10 or (within_formula_span and short_fragment):
                same_band.append(o)
        same_band = sorted({o.object_id: o for o in same_band}.values(), key=lambda x: x.bbox.x0)
        if not same_band:
            same_band = [seed]
        # Preserve geometry. For a simple fraction layout, reconstruct the
        # fraction deterministically from upper/lower source fragments; otherwise
        # keep the fragments in left-to-right source order without invention.
        eq_number = next((o for o in same_band if o.object_type == "equation_number"), None)
        core_seed = next((o for o in same_band if o.object_id == seed.object_id), seed)
        middle = [o for o in same_band if o.object_id not in {core_seed.object_id, eq_number.object_id if eq_number else ""}]
        seed_cy = (core_seed.bbox.y0 + core_seed.bbox.y1) / 2
        upper = [o for o in middle if ((o.bbox.y0 + o.bbox.y1) / 2) < seed_cy - 1.0]
        lower = [o for o in middle if ((o.bbox.y0 + o.bbox.y1) / 2) > seed_cy + 1.0]
        fraction_reconstructed = False
        if "=" in core_seed.text and upper and lower:
            up = " ".join(o.text for o in sorted(upper, key=lambda x: x.bbox.x0)).strip()
            lo = " ".join(o.text for o in sorted(lower, key=lambda x: x.bbox.x0)).strip()
            if up and lo:
                eq_text = f"{core_seed.text} ({up})/({lo})"
                if eq_number:
                    eq_text += f" {eq_number.text}"
                fraction_reconstructed = True
            else:
                eq_text = " ".join(o.text for o in same_band if o.text).strip()
        else:
            eq_text = " ".join(o.text for o in same_band if o.text).strip()
        if not eq_text:
            continue
        obj = DocumentObject(
            object_id=stable_id(str(seed.page_number), seed.object_id, "equation_group"),
            page_number=seed.page_number,
            object_type="equation",
            bbox=_bbox_union(same_band),
            text=normalize_text(eq_text),
            confidence=0.90 if nearby_numbers and len(same_band) > 2 else (0.86 if len(same_band) > 1 else 0.80),
            column_index=seed.column_index,
            source="pymupdf_layout",
            child_ids=[o.object_id for o in same_band],
            metadata={"grouping": "same_baseline_math_fragments", "fraction_reconstructed_from_geometry": fraction_reconstructed},
        )
        additions.append(obj)
        used.update(o.object_id for o in same_band)
        suppressed.update(o.object_id for o in same_band)
    return additions, suppressed


def _reading_order(objects: list[DocumentObject], column_centers: list[float], page_h: float) -> tuple[list[str], float]:
    live = [o for o in objects if not o.metadata.get("suppressed")]
    bands = _vertical_bands(live, page_h)
    ordered: list[DocumentObject] = []
    for y0, y1 in bands:
        band = [o for o in live if o.bbox.y1 >= y0 - 1 and o.bbox.y0 <= y1 + 1 and o.object_type not in {"header", "footer", "page_number"}]
        if not band:
            continue
        # A wide object gets its own visual position. Narrow content follows column flow.
        wide = [o for o in band if o.bbox.width >= 0.72 * max((x.bbox.x1 for x in live), default=1)]
        narrow = [o for o in band if o not in wide]
        if wide and len(wide) == len(band):
            ordered.extend(sorted(wide, key=lambda x: (x.bbox.y0, x.bbox.x0)))
            continue
        if wide:
            # Preserve vertical placement of full-width objects by splitting around them.
            for w in sorted(wide, key=lambda x: x.bbox.y0):
                before = [o for o in narrow if o.bbox.y1 <= w.bbox.y0 + 1]
                narrow = [o for o in narrow if o not in before]
                for ci in range(max(1, len(column_centers))):
                    ordered.extend(sorted([o for o in before if (o.column_index or 0) == ci], key=lambda x: (x.bbox.y0, x.bbox.x0)))
                ordered.append(w)
            for ci in range(max(1, len(column_centers))):
                ordered.extend(sorted([o for o in narrow if (o.column_index or 0) == ci], key=lambda x: (x.bbox.y0, x.bbox.x0)))
        else:
            if len(column_centers) <= 1:
                ordered.extend(sorted(narrow, key=lambda x: (x.bbox.y0, x.bbox.x0)))
            else:
                for ci in range(len(column_centers)):
                    ordered.extend(sorted([o for o in narrow if (o.column_index or 0) == ci], key=lambda x: (x.bbox.y0, x.bbox.x0)))
    # Add any object not captured above, excluding headers/footers/page numbers from training order.
    seen = {o.object_id for o in ordered}
    leftovers = [o for o in live if o.object_id not in seen and o.object_type not in {"header", "footer", "page_number"}]
    ordered.extend(sorted(leftovers, key=lambda x: (x.bbox.y0, x.bbox.x0)))
    # De-duplicate while preserving order.
    ids = []
    seen_ids = set()
    for o in ordered:
        if o.object_id not in seen_ids:
            ids.append(o.object_id)
            seen_ids.add(o.object_id)
    conf = 0.96 if ids else 0.0
    if len(column_centers) > 1:
        conf -= 0.03
    if leftovers:
        conf -= min(0.12, 0.02 * len(leftovers))
    return ids, max(0.0, min(1.0, conf))


def analyze_page(page: fitz.Page, page_number: int) -> PageStructure:
    width = float(page.rect.width)
    height = float(page.rect.height)
    raw = _extract_raw_blocks(page)
    body_font = _body_font(raw)
    objects: list[DocumentObject] = []
    for rb in raw:
        obj_type, conf = _classify_block(rb, width, height, body_font)
        objects.append(
            DocumentObject(
                object_id=stable_id(str(page_number), str(rb.idx), obj_type, rb.text[:120]),
                page_number=page_number,
                object_type=obj_type,
                bbox=rb.bbox,
                text=rb.text,
                confidence=conf,
                source="pymupdf_layout",
                metadata={
                    "raw_block_index": rb.idx,
                    "max_font": rb.max_font,
                    "median_font": rb.median_font,
                    "bold_fraction": rb.bold_fraction,
                    "line_count": rb.line_count,
                },
            )
        )

    column_count, centers, column_conf = _infer_columns(objects, width, height)
    for o in objects:
        if o.bbox.width <= width * 0.72 and o.object_type not in {"header", "footer", "page_number"}:
            o.column_index = _nearest_column(o, centers)

    # Combine table/equation fragments into semantic objects before deciding reading order.
    table_add, table_suppressed = _group_tables(page, objects, width)
    eq_add, eq_suppressed = _group_equations(objects, width)
    suppressed = table_suppressed | eq_suppressed
    for o in objects:
        if o.object_id in suppressed:
            o.metadata["suppressed"] = True
    for o in table_add + eq_add:
        if o.column_index is None and o.bbox.width <= width * 0.72:
            o.column_index = _nearest_column(o, centers)
    objects.extend(table_add)
    objects.extend(eq_add)

    reading_order, order_conf = _reading_order(objects, centers, height)
    by_id = {o.object_id: o for o in objects}
    for i, oid in enumerate(reading_order, start=1):
        if oid in by_id:
            by_id[oid].reading_order = i

    active = [o for o in objects if not o.metadata.get("suppressed") and o.object_type not in {"header", "footer", "page_number"}]
    wide_count = sum(o.bbox.width >= width * 0.72 for o in active)
    image_count = sum(o.object_type == "figure" for o in active)
    table_count = sum(o.object_type == "table" for o in active)
    equation_count = sum(o.object_type == "equation" for o in active)
    high_risk_count = sum(contains_high_risk(o.text) for o in active if o.text)

    if not any(o.text for o in active) and image_count:
        layout_type = "image_only"
    elif column_count == 1:
        layout_type = "single_column"
    elif wide_count:
        layout_type = "mixed"
    else:
        layout_type = "multi_column"

    reasons = []
    if column_count > 1:
        reasons.append(f"{column_count}_column_layout")
    if wide_count and column_count > 1:
        reasons.append("mixed_full_width_and_columns")
    if table_count:
        reasons.append(f"tables:{table_count}")
    if equation_count:
        reasons.append(f"equations:{equation_count}")
    if image_count:
        reasons.append(f"figures:{image_count}")
    if high_risk_count:
        reasons.append(f"high_risk_objects:{high_risk_count}")

    complexity = 0.08
    complexity += 0.16 * max(0, column_count - 1)
    complexity += 0.14 if wide_count and column_count > 1 else 0.0
    complexity += min(0.24, 0.08 * table_count)
    complexity += min(0.18, 0.06 * equation_count)
    complexity += min(0.12, 0.03 * image_count)
    complexity += min(0.12, 0.01 * high_risk_count)
    complexity = max(0.0, min(1.0, complexity))

    avg_obj_conf = statistics.mean([o.confidence for o in active]) if active else 0.0
    structure_conf = max(0.0, min(1.0, 0.55 * avg_obj_conf + 0.25 * column_conf + 0.20 * order_conf))

    return PageStructure(
        page_number=page_number,
        width=width,
        height=height,
        column_count=column_count,
        layout_type=layout_type,
        objects=objects,
        reading_order=reading_order,
        confidence=structure_conf,
        reading_order_confidence=order_conf,
        complexity_score=complexity,
        complexity_reasons=reasons,
        diagnostics={
            "body_font": body_font,
            "column_centers": centers,
            "column_detection_confidence": column_conf,
            "wide_objects": wide_count,
            "active_objects": len(active),
            "tables": table_count,
            "equations": equation_count,
            "figures": image_count,
            "high_risk_objects": high_risk_count,
        },
    )


def structure_to_text(structure: PageStructure, include_figure_captions: bool = True) -> str:
    by_id = {o.object_id: o for o in structure.objects}
    parts: list[str] = []
    for oid in structure.reading_order:
        o = by_id.get(oid)
        if not o or o.metadata.get("suppressed"):
            continue
        if o.object_type in {"header", "footer", "page_number", "figure"}:
            continue
        if o.object_type == "figure_caption" and not include_figure_captions:
            continue
        text = o.text.strip()
        if not text:
            continue
        if o.object_type == "table":
            parts.append(f"[TABLE]\n{text}\n[/TABLE]")
        elif o.object_type == "equation":
            parts.append(f"[EQUATION] {text} [/EQUATION]")
        elif o.object_type == "figure_caption":
            parts.append(f"[FIGURE_CAPTION] {text} [/FIGURE_CAPTION]")
        else:
            parts.append(text)
    return normalize_text("\n\n".join(parts))


def native_layout_candidate(structure: PageStructure) -> Candidate:
    by_id = {o.object_id: o for o in structure.objects}
    spans: list[SpanEvidence] = []
    for oid in structure.reading_order:
        o = by_id.get(oid)
        if not o or o.metadata.get("suppressed") or o.object_type in {"header", "footer", "page_number", "figure"}:
            continue
        if not o.text.strip():
            continue
        spans.append(
            SpanEvidence(
                engine="pymupdf_native",
                text=o.text,
                confidence=o.confidence,
                bbox=o.bbox,
                page_number=structure.page_number,
                content_type=o.object_type,
                metadata={"unit": "layout_object", "object_id": o.object_id},
            )
        )
    text = structure_to_text(structure)
    confidence = max(0.0, min(1.0, 0.55 * text_quality(text) + 0.45 * structure.confidence))
    return Candidate(
        engine="pymupdf_native",
        text=text,
        confidence=confidence,
        spans=spans,
        metadata={
            "mode": "native_pdf_layout_reconstruction",
            "evidence_family": "native_pdf",
            "layout_type": structure.layout_type,
            "column_count": structure.column_count,
            "reading_order_confidence": structure.reading_order_confidence,
            "complexity_score": structure.complexity_score,
        },
    )
