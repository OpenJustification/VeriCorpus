# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
import re
import zipfile
from pathlib import Path
import xml.etree.ElementTree as ET

import fitz

from .models import BBox, SourceObjectLabel
from .util import normalize_text


def _strip_tex(text: str) -> str:
    text = re.sub(r"%.*$", "", text, flags=re.M)
    text = re.sub(r"\\(?:textbf|textit|emph|mathrm|mathbf|section|subsection|subsubsection)\*?\{([^{}]*)\}", r"\1", text)
    text = re.sub(r"\\[A-Za-z]+\*?(?:\[[^\]]*\])?", " ", text)
    text = text.replace("{", " ").replace("}", " ")
    return normalize_text(text)


def latex_labels(path: Path) -> list[SourceObjectLabel]:
    raw = path.read_text(encoding="utf-8", errors="replace")
    labels: list[SourceObjectLabel] = []
    for level, typ in [("section", "heading"), ("subsection", "heading"), ("subsubsection", "heading")]:
        for m in re.finditer(rf"\\{level}\*?\{{([^{{}}]+)\}}", raw, flags=re.S):
            title = _strip_tex(m.group(1))
            labels.append(SourceObjectLabel(source_type="latex", object_type=typ, anchor_text=title, source_location=str(path)))
    for env, typ in [("figure", "figure"), ("table", "table"), ("equation", "equation"), ("align", "equation"), ("algorithm", "algorithm")]:
        pat = re.compile(rf"\\begin\{{{env}\*?\}}(.*?)\\end\{{{env}\*?\}}", re.S)
        for m in pat.finditer(raw):
            body = m.group(1)
            cap = re.search(r"\\caption(?:\[[^\]]*\])?\{(.*?)\}", body, flags=re.S)
            lab = re.search(r"\\label\{([^}]+)\}", body)
            caption = _strip_tex(cap.group(1)) if cap else ""
            anchor = caption or _strip_tex(body)[:160]
            labels.append(
                SourceObjectLabel(
                    source_type="latex",
                    object_type=typ,
                    label=lab.group(1) if lab else "",
                    caption=caption,
                    anchor_text=anchor,
                    source_location=str(path),
                )
            )
    return labels


def jats_labels(path: Path) -> list[SourceObjectLabel]:
    root = ET.parse(path).getroot()
    labels: list[SourceObjectLabel] = []
    mapping = {
        "fig": "figure",
        "table-wrap": "table",
        "disp-formula": "equation",
        "title": "heading",
    }
    for elem in root.iter():
        tag = elem.tag.split("}")[-1]
        if tag not in mapping:
            continue
        text = normalize_text(" ".join(t for t in elem.itertext()))
        caption = ""
        for child in elem.iter():
            if child.tag.split("}")[-1] == "caption":
                caption = normalize_text(" ".join(t for t in child.itertext()))
                break
        labels.append(
            SourceObjectLabel(
                source_type="jats",
                object_type=mapping[tag],
                label=elem.attrib.get("id", ""),
                caption=caption,
                anchor_text=caption or text[:180],
                source_location=str(path),
            )
        )
    return labels


def docx_labels(path: Path) -> list[SourceObjectLabel]:
    ns = {
        "w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main",
        "m": "http://schemas.openxmlformats.org/officeDocument/2006/math",
        "a": "http://schemas.openxmlformats.org/drawingml/2006/main",
    }
    with zipfile.ZipFile(path) as z:
        root = ET.fromstring(z.read("word/document.xml"))
    labels: list[SourceObjectLabel] = []
    for elem in root.iter():
        tag = elem.tag.split("}")[-1]
        if tag == "tbl":
            text = normalize_text(" ".join(t.text or "" for t in elem.findall(".//w:t", ns)))
            labels.append(SourceObjectLabel(source_type="docx", object_type="table", anchor_text=text[:180], source_location=str(path)))
        elif tag in {"oMath", "oMathPara"}:
            text = normalize_text(" ".join(t.text or "" for t in elem.findall(".//m:t", ns)))
            labels.append(SourceObjectLabel(source_type="docx", object_type="equation", anchor_text=text[:180], source_location=str(path)))
        elif tag == "drawing":
            labels.append(SourceObjectLabel(source_type="docx", object_type="figure", source_location=str(path)))
        elif tag == "p":
            text = normalize_text(" ".join(t.text or "" for t in elem.findall(".//w:t", ns)))
            if re.match(r"^(?:Figure|Fig\.|Table)\s+\d+", text, re.I):
                typ = "figure_caption" if re.match(r"^(?:Figure|Fig\.)", text, re.I) else "table_caption"
                labels.append(SourceObjectLabel(source_type="docx", object_type=typ, caption=text, anchor_text=text, source_location=str(path)))
    # De-duplicate nested OMML hits.
    unique = {}
    for x in labels:
        key = (x.object_type, x.anchor_text, x.caption)
        unique[key] = x
    return list(unique.values())


def extract_source_labels(path: Path) -> list[SourceObjectLabel]:
    suffix = path.suffix.lower()
    if suffix in {".tex", ".ltx"}:
        return latex_labels(path)
    if suffix in {".xml", ".nxml"}:
        return jats_labels(path)
    if suffix == ".docx":
        return docx_labels(path)
    raise ValueError("Supported structured sources are .tex/.ltx, JATS .xml/.nxml, and .docx")


def _anchor_candidates(text: str) -> list[str]:
    words = re.findall(r"\S+", normalize_text(text))
    candidates = []
    for n in (12, 9, 6, 4):
        if len(words) >= n:
            candidates.append(" ".join(words[:n]))
    if text.strip():
        candidates.append(normalize_text(text)[:120])
    return list(dict.fromkeys(candidates))


def align_labels_to_pdf(labels: list[SourceObjectLabel], pdf_path: Path) -> list[SourceObjectLabel]:
    doc = fitz.open(pdf_path)
    try:
        for label in labels:
            if not label.anchor_text:
                continue
            found = False
            for anchor in _anchor_candidates(label.anchor_text):
                for page_idx, page in enumerate(doc):
                    rects = page.search_for(anchor)
                    if rects:
                        rect = rects[0]
                        label.page_number = page_idx + 1
                        label.bbox = BBox(x0=rect.x0, y0=rect.y0, x1=rect.x1, y1=rect.y1)
                        label.aligned = True
                        label.confidence = min(0.99, 0.72 + 0.02 * len(anchor.split()))
                        label.metadata["matched_anchor"] = anchor
                        found = True
                        break
                if found:
                    break
        return labels
    finally:
        doc.close()


def write_groundtruth(source_path: Path, pdf_path: Path, out_path: Path) -> dict:
    labels = align_labels_to_pdf(extract_source_labels(source_path), pdf_path)
    with out_path.open("w", encoding="utf-8", newline="\n") as f:
        for label in labels:
            f.write(json.dumps(label.model_dump(), ensure_ascii=False, sort_keys=True) + "\n")
    aligned = sum(x.aligned for x in labels)
    return {"objects": len(labels), "aligned": aligned, "alignment_rate": aligned / max(len(labels), 1), "output": str(out_path)}
