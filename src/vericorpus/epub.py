# SPDX-License-Identifier: AGPL-3.0-or-later
"""Source-faithful EPUB 2/3 XHTML spine extractor (no remote content)."""
from __future__ import annotations

from pathlib import PurePosixPath, Path
import posixpath
import re
import xml.etree.ElementTree as ET
import zipfile

from .models import BBox, DocumentObject, PageStructure, Candidate, SpanEvidence
from .layout import structure_to_text
from .util import normalize_text, stable_id, text_quality

_MAX_ITEMS = 6000
_MAX_TOTAL_BYTES = 600 * 1024 * 1024
_MAX_ENTRY_BYTES = 60 * 1024 * 1024
_BLOCK_TAGS = {"p", "li", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "blockquote", "dt", "dd", "figcaption", "caption", "table", "math", "img"}


def _tag(node) -> str:
    return node.tag.rsplit("}", 1)[-1].lower() if isinstance(node.tag, str) else ""


def _read_xml(data: bytes) -> ET.Element:
    if b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("EPUB XML DTD/entities are not accepted")
    return ET.fromstring(data)


def _norm_inner(node) -> str:
    return normalize_text("".join(node.itertext())).strip()


def _path(base: str, href: str) -> str:
    # No external resources, rooted paths, parent traversal or percent-encoded
    # traversal; all ZIP member lookups remain within the archive.
    if href.startswith(("/", "\\")) or re.match(r"^[A-Za-z]+:", href):
        raise ValueError("EPUB spine path must be archive-relative")
    clean = posixpath.normpath(posixpath.join(posixpath.dirname(base), href.split("#")[0]))
    if clean in {"..", "."} or clean.startswith("../"):
        raise ValueError("EPUB spine path escapes the archive")
    return clean


def _objects(xhtml: ET.Element, spine_name: str, page_no: int):
    objects: list[DocumentObject] = []
    issues = []

    def emit(kind: str, text: str, node, metadata: dict | None = None):
        if not text and kind != "figure":
            return
        idx = len(objects)
        objects.append(DocumentObject(
            object_id=stable_id(spine_name, str(page_no), str(idx), kind),
            page_number=page_no, object_type=kind,
            bbox=BBox(x0=0, y0=float(idx), x1=0, y1=float(idx)),
            text=text, confidence=0.96 if kind not in {"math", "equation", "figure"} else 0.84,
            column_index=0, reading_order=idx + 1,
            source="epub_xhtml_dom",
            metadata={"source_chapter": spine_name, "geometry": "not_applicable", **(metadata or {})},
        ))

    def walk(node):
        name = _tag(node)
        if name in {"script", "style", "nav", "head", "noscript"}:
            return
        if name == "img":
            emit("figure", "", node, {"image_href": node.attrib.get("src", ""), "alt": node.attrib.get("alt", "")})
            issues.append("image_requires_visual_interpretation")
            return
        if name == "table":
            lines = []
            for row in node.iter():
                if _tag(row) != "tr":
                    continue
                cells = [_norm_inner(cell) for cell in row if _tag(cell) in {"th", "td"}]
                if cells:
                    lines.append(" | ".join(cells))
            caption = next((_norm_inner(child) for child in node if _tag(child) == "caption"), "")
            body = "\n".join(([caption] if caption else []) + lines)
            emit("table", body, node, {"rows": len(lines), "format": "source_html_table"})
            return
        if name == "math":
            # Retain exact source MathML markup. Do not guess a LaTeX equation.
            serialized = ET.tostring(node, encoding="unicode")
            emit("equation", serialized, node, {"format": "source_mathml"})
            return
        mapping = {"figcaption": "figure_caption", "caption": "table_caption", "pre": "code"}
        if name in _BLOCK_TAGS:
            kind = mapping.get(name, "heading" if re.fullmatch(r"h[1-6]", name) else "list" if name == "li" else "paragraph")
            emit(kind, _norm_inner(node), node)
            return
        if node.text and node.text.strip() and name in {"body", "div", "section", "article"}:
            emit("paragraph", normalize_text(node.text).strip(), node)
        for child in node:
            walk(child)
            # Free-floating tail text is source content, but usually whitespace.
            if child.tail and child.tail.strip():
                emit("paragraph", normalize_text(child.tail).strip(), child)

    walk(xhtml)
    return objects, sorted(set(issues))


def epub_structures(path: Path):
    """Yield a pseudo-page per XHTML spine item; EPUB has no physical PDF pages."""
    with zipfile.ZipFile(path) as zf:
        infos = zf.infolist()
        if len(infos) > _MAX_ITEMS or sum(i.file_size for i in infos) > _MAX_TOTAL_BYTES:
            raise ValueError("EPUB archive exceeds safe entry/uncompressed size limits")
        if any(i.file_size > _MAX_ENTRY_BYTES for i in infos):
            raise ValueError("EPUB archive member exceeds per-file safe size limit")
        files = {i.filename for i in infos}
        if "META-INF/container.xml" not in files:
            raise ValueError("EPUB missing META-INF/container.xml")
        container = _read_xml(zf.read("META-INF/container.xml"))
        rf = next((n for n in container.iter() if _tag(n) == "rootfile"), None)
        if rf is None or "full-path" not in rf.attrib:
            raise ValueError("EPUB container lacks OPF package path")
        opf_name = _path("", rf.attrib["full-path"])
        if opf_name not in files:
            raise ValueError("EPUB OPF package not found")
        opf = _read_xml(zf.read(opf_name))
        items = {n.attrib["id"]: n.attrib["href"]
                 for n in opf.iter() if _tag(n) == "item" and "id" in n.attrib and "href" in n.attrib}
        spine = [n.attrib["idref"] for n in opf.iter()
                 if _tag(n) == "itemref" and "idref" in n.attrib and n.attrib.get("linear", "yes") != "no"]
        if not spine:
            raise ValueError("EPUB lacks linear XHTML spine items")
        for number, item_id in enumerate(spine, 1):
            if item_id not in items:
                raise ValueError(f"EPUB spine references undefined manifest ID: {item_id}")
            chapter = _path(opf_name, items[item_id])
            if chapter not in files:
                raise ValueError(f"EPUB missing declared spine item: {chapter}")
            tree = _read_xml(zf.read(chapter))
            body = next((e for e in tree.iter() if _tag(e) == "body"), None)
            if body is None:
                raise ValueError(f"EPUB chapter missing body: {chapter}")
            objects, issues = _objects(body, chapter, number)
            ids = [o.object_id for o in objects]
            has_text = bool(structure_to_text(PageStructure(page_number=number, width=0, height=0, objects=objects, reading_order=ids)).strip())
            structure = PageStructure(
                page_number=number, width=0, height=0,
                layout_type="single_column" if has_text else "image_only",
                column_count=1, objects=objects, reading_order=ids,
                confidence=0.95 if has_text else 0.2,
                reading_order_confidence=0.99 if has_text else 0.0,
                complexity_score=min(1.0, 0.08 + 0.06 * sum(o.object_type == "table" for o in objects)
                                     + 0.10 * sum(o.object_type == "equation" for o in objects)),
                complexity_reasons=issues + ["epub_source_semantic_layout"],
                diagnostics={"chapter": chapter, "geometry": "not_applicable", "source_format": "epub",
                             "figures": sum(o.object_type == "figure" for o in objects),
                             "tables": sum(o.object_type == "table" for o in objects),
                             "equations": sum(o.object_type == "equation" for o in objects),
                             "high_risk_objects": sum(o.object_type in {"table", "equation"} for o in objects)},
            )
            yield structure


def epub_candidate(structure: PageStructure) -> Candidate:
    text = structure_to_text(structure)
    spans = [SpanEvidence(engine="epub_xhtml", text=o.text, confidence=o.confidence,
                          page_number=structure.page_number, bbox=None, content_type=o.object_type,
                          metadata={"object_id": o.object_id, "source_chapter": o.metadata.get("source_chapter")})
             for o in structure.objects if o.text and o.object_type != "figure"]
    return Candidate(engine="epub_xhtml", text=text,
                     confidence=0.55 * text_quality(text) + 0.45 * structure.confidence,
                     spans=spans, metadata={"evidence_family": "epub_xhtml_source", "format": "epub", "local_only": True})
