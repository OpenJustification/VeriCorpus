# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from .config import Settings
from .models import PageStructure


def route_page(structure: PageStructure, settings: Settings, availability: dict[str, bool]) -> dict:
    """Choose extraction families from observed page complexity.

    Profiles are capability ceilings, not static engine lists. A complex page can
    automatically invoke more of the engines allowed by the selected profile.
    """
    reasons = list(structure.complexity_reasons)
    requested = ["pymupdf_native"]
    detected_types = {o.object_type for o in structure.objects if not o.metadata.get("suppressed")}
    complex_layout = structure.column_count > 1 or structure.layout_type == "mixed"
    structured = bool(detected_types & {"table", "equation", "figure", "figure_caption"})
    high_complexity = structure.complexity_score >= settings.complex_page_threshold

    if settings.profile in {"standard", "verified"} and (complex_layout or structured or high_complexity):
        if settings.use_docling and availability.get("docling"):
            requested.append("docling")
        if settings.use_paddleocr and availability.get("paddleocr_vl_1_6"):
            requested.append("paddleocr_vl_1_6")
        if settings.auto_use_tesseract_on_complex and availability.get("tesseract"):
            requested.append("tesseract")

    if settings.profile == "standard" and len(requested) == 1:
        # Standard still uses configured structure parsers on ordinary pages when
        # available, but avoids unnecessary classical OCR.
        if settings.use_docling and availability.get("docling"):
            requested.append("docling")
        if settings.use_paddleocr and availability.get("paddleocr_vl_1_6"):
            requested.append("paddleocr_vl_1_6")

    if settings.profile == "verified":
        for engine, enabled, key in [
            ("tesseract", settings.use_tesseract, "tesseract"),
            ("docling", settings.use_docling, "docling"),
            ("paddleocr_vl_1_6", settings.use_paddleocr, "paddleocr_vl_1_6"),
            ("glmocr", settings.use_glmocr, "glmocr"),
            ("olmocr2", settings.use_olmocr, "olmocr"),
        ]:
            if enabled and availability.get(key) and engine not in requested:
                requested.append(engine)

    if complex_layout:
        reasons.append("route:layout_aware")
    if "table" in detected_types:
        reasons.append("route:table_aware")
    if "equation" in detected_types:
        reasons.append("route:equation_aware")
    if settings.profile == "lite" and (complex_layout or structured):
        reasons.append("lite:native_layout_reconstruction")

    return {
        "profile": settings.profile,
        "requested_engines": requested,
        "complex": bool(complex_layout or structured or high_complexity),
        "complexity_score": structure.complexity_score,
        "reasons": sorted(set(reasons)),
    }
