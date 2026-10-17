# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

import fitz

from .extractors import render_page
from .models import Candidate
from .util import normalize_text, text_quality

_DOC_CONVERTER = None
_PADDLE_VL = None


def _plain_parser_text(text: str) -> str:
    text = re.sub(r"```.*?```", lambda m: m.group(0).replace("```", ""), text or "", flags=re.S)
    text = re.sub(r"^#{1,6}\s+", "", text, flags=re.M)
    text = re.sub(r"[*_]{1,3}", "", text)
    text = re.sub(r"\[(.*?)\]\([^)]*\)", r"\1", text)
    return normalize_text(text)


def availability() -> dict[str, bool]:
    out = {
        "tesseract": bool(shutil.which("tesseract")),
        "docling": False,
        "paddleocr_vl_1_6": False,
        "glmocr": bool(shutil.which("glmocr")),
        "olmocr": bool(shutil.which("olmocr")),
    }
    try:
        from paddleocr import PaddleOCRVL  # noqa: F401
        out["paddleocr_vl_1_6"] = True
    except Exception:
        pass
    try:
        import docling  # noqa: F401
        out["docling"] = True
    except Exception:
        pass
    return out


def _single_page_pdf(page: fitz.Page, out: Path) -> None:
    doc = fitz.open()
    doc.insert_pdf(page.parent, from_page=page.number, to_page=page.number)
    doc.save(out)
    doc.close()


def _obj_to_dict(obj: Any) -> dict:
    if isinstance(obj, dict):
        return obj
    for attr in ("json_result", "json", "res"):
        if hasattr(obj, attr):
            value = getattr(obj, attr)
            try:
                value = value() if callable(value) else value
            except Exception:
                continue
            if isinstance(value, str):
                try:
                    return json.loads(value)
                except Exception:
                    return {"text": value}
            if isinstance(value, dict):
                return value
    if hasattr(obj, "to_dict"):
        try:
            value = obj.to_dict()
            if isinstance(value, dict):
                return value
        except Exception:
            pass
    if hasattr(obj, "__dict__"):
        return dict(obj.__dict__)
    return {}


def _extract_text_recursive(obj: Any) -> list[str]:
    out: list[str] = []
    if isinstance(obj, str):
        if obj.strip():
            out.append(obj)
    elif isinstance(obj, dict):
        for k, v in obj.items():
            if k.lower() in {"text", "markdown", "content", "rec_text", "rec_texts"}:
                out.extend(_extract_text_recursive(v))
            elif isinstance(v, (dict, list)):
                out.extend(_extract_text_recursive(v))
    elif isinstance(obj, list):
        for x in obj:
            out.extend(_extract_text_recursive(x))
    return out


def paddle_candidate(page: fitz.Page, page_number: int, dpi: int = 300) -> Candidate:
    """Official PaddleOCR-VL 1.6 local pipeline. No cloud API is used."""
    global _PADDLE_VL
    from paddleocr import PaddleOCRVL

    if _PADDLE_VL is None:
        _PADDLE_VL = PaddleOCRVL(pipeline_version="v1.6")
    image = render_page(page, dpi=dpi)
    with tempfile.TemporaryDirectory(prefix="vericorpus_paddlevl_") as td:
        img_path = Path(td) / "page.png"
        image.save(img_path)
        results = list(_PADDLE_VL.predict(str(img_path)))
    chunks: list[str] = []
    for item in results:
        d = _obj_to_dict(item)
        chunks.extend(_extract_text_recursive(d))
    text = _plain_parser_text("\n".join(chunks))
    return Candidate(
        engine="paddleocr_vl_1_6",
        text=text,
        confidence=text_quality(text),
        spans=[],
        metadata={"dpi": dpi, "pipeline_version": "v1.6", "local_only": True, "evidence_family": "paddle_vlm"},
    )


def docling_candidate(page: fitz.Page, page_number: int) -> Candidate:
    global _DOC_CONVERTER
    from docling.document_converter import DocumentConverter

    if _DOC_CONVERTER is None:
        _DOC_CONVERTER = DocumentConverter()
    with tempfile.TemporaryDirectory(prefix="vericorpus_docling_") as td:
        pdf = Path(td) / "page.pdf"
        _single_page_pdf(page, pdf)
        result = _DOC_CONVERTER.convert(pdf)
        doc = result.document
        try:
            text = _plain_parser_text(doc.export_to_text())
        except Exception:
            text = _plain_parser_text(doc.export_to_markdown())
    return Candidate(
        engine="docling",
        text=text,
        confidence=text_quality(text),
        spans=[],
        metadata={"structured": True, "single_page_conversion": True, "local_only": True, "evidence_family": "docling"},
    )


def glmocr_candidate(page: fitz.Page, page_number: int, dpi: int = 300) -> Candidate:
    """Use GLM-OCR only against a self-hosted localhost model endpoint."""
    exe = shutil.which("glmocr")
    if not exe:
        raise RuntimeError("glmocr executable not found")
    image = render_page(page, dpi=dpi)
    with tempfile.TemporaryDirectory(prefix="vericorpus_glmocr_") as td_raw:
        td = Path(td_raw)
        img = td / "page.png"
        out = td / "out"
        cfg = td / "config.yaml"
        image.save(img)
        # Deliberately override MaaS/cloud mode. The only supported built-in target is localhost.
        cfg.write_text(
            "pipeline:\n"
            "  maas:\n"
            "    enabled: false\n"
            "  ocr_api:\n"
            "    api_host: 127.0.0.1\n"
            "    api_port: 8080\n",
            encoding="utf-8",
        )
        cmd = [exe, "parse", str(img), "--output", str(out), "--config", str(cfg)]
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=1200, check=False)
        if cp.returncode != 0:
            raise RuntimeError(f"GLM-OCR local parse failed: {cp.stderr[-1000:]}")
        candidates = list(out.rglob("*.md")) + list(out.rglob("*.json"))
        chunks: list[str] = []
        for candidate in candidates:
            raw = candidate.read_text(encoding="utf-8", errors="replace")
            if candidate.suffix == ".json":
                try:
                    chunks.extend(_extract_text_recursive(json.loads(raw)))
                except Exception:
                    continue
            else:
                chunks.append(raw)
        text = _plain_parser_text("\n".join(chunks))
    return Candidate(
        engine="glmocr",
        text=text,
        confidence=text_quality(text),
        spans=[],
        metadata={"dpi": dpi, "local_only": True, "endpoint": "127.0.0.1:8080", "evidence_family": "glm_ocr"},
    )


def olmocr_candidate(page: fitz.Page, page_number: int) -> Candidate:
    """Run the installed olmOCR CLI locally on a single-page PDF.

    This adapter intentionally supplies no --server argument, so olmOCR uses its local inference path.
    """
    exe = shutil.which("olmocr")
    if not exe:
        raise RuntimeError("olmocr executable not found")
    with tempfile.TemporaryDirectory(prefix="vericorpus_olmocr_") as td_raw:
        td = Path(td_raw)
        pdf = td / "page.pdf"
        workspace = td / "workspace"
        _single_page_pdf(page, pdf)
        cmd = [exe, str(workspace), "--markdown", "--workers", "1", "--pdfs", str(pdf)]
        cp = subprocess.run(cmd, capture_output=True, text=True, timeout=1200, check=False)
        if cp.returncode != 0:
            raise RuntimeError(f"olmOCR failed: {cp.stderr[-1000:]}")
        md_files = list(workspace.rglob("*.md"))
        if not md_files:
            raise RuntimeError("olmOCR produced no markdown output")
        md = max(md_files, key=lambda p: p.stat().st_size)
        text = _plain_parser_text(md.read_text(encoding="utf-8", errors="replace"))
    return Candidate(
        engine="olmocr2",
        text=text,
        confidence=text_quality(text),
        spans=[],
        metadata={"local_only": True, "evidence_family": "olmocr"},
    )
