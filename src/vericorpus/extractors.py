# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import io
import os
from pathlib import Path
import fitz
from PIL import Image

from .models import BBox, Candidate, SpanEvidence
from .util import normalize_text, text_quality, content_type


def render_page(page: fitz.Page, dpi: int = 300) -> Image.Image:
    scale = dpi / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
    return Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")


def crop_page_region(page: fitz.Page, bbox: BBox | None, dpi: int = 300, pad: float = 12.0) -> Image.Image:
    if bbox is None:
        return render_page(page, dpi=dpi)
    rect = fitz.Rect(max(0,bbox.x0-pad), max(0,bbox.y0-pad), min(page.rect.width,bbox.x1+pad), min(page.rect.height,bbox.y1+pad))
    scale = dpi / 72.0
    pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), clip=rect, alpha=False)
    return Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")


def native_candidate(page: fitz.Page, page_number: int) -> Candidate:
    words = page.get_text("words", sort=True)
    spans = []
    texts = []
    for w in words:
        x0,y0,x1,y1,txt = w[:5]
        txt = normalize_text(str(txt))
        if not txt:
            continue
        texts.append(txt)
        spans.append(SpanEvidence(
            engine="pymupdf_native",
            text=txt,
            confidence=1.0,
            bbox=BBox(x0=float(x0),y0=float(y0),x1=float(x1),y1=float(y1)),
            page_number=page_number,
            content_type=content_type(txt),
            metadata={"unit":"word"},
        ))
    text = normalize_text(page.get_text("text", sort=True))
    return Candidate(engine="pymupdf_native", text=text, confidence=text_quality(text), spans=spans, metadata={"mode":"native_text_layer","evidence_family":"native_pdf"})


def tesseract_candidate(page: fitz.Page, page_number: int, dpi: int = 300) -> Candidate:
    import pytesseract
    from pytesseract import Output
    cmd = os.getenv("TESSERACT_CMD")
    if cmd:
        pytesseract.pytesseract.tesseract_cmd = cmd
    image = render_page(page, dpi=dpi)
    data = pytesseract.image_to_data(image, output_type=Output.DICT, config="--psm 3")
    sx = page.rect.width / image.width
    sy = page.rect.height / image.height
    spans=[]; words=[]; confs=[]
    for i, raw in enumerate(data.get("text", [])):
        txt=(raw or "").strip()
        try: c=float(data["conf"][i])/100.0
        except Exception: c=0.0
        if not txt: continue
        x=float(data["left"][i])*sx; y=float(data["top"][i])*sy
        w=float(data["width"][i])*sx; h=float(data["height"][i])*sy
        spans.append(SpanEvidence(engine="tesseract", text=txt, confidence=max(0,min(c,1)), bbox=BBox(x0=x,y0=y,x1=x+w,y1=y+h), page_number=page_number, content_type=content_type(txt), metadata={"unit":"word","dpi":dpi}))
        words.append(txt)
        if c>=0: confs.append(c)
    text=normalize_text(" ".join(words))
    mean=sum(confs)/len(confs) if confs else 0.0
    q=text_quality(text)
    return Candidate(engine="tesseract", text=text, confidence=max(0,min(0.65*mean+0.35*q,1)), spans=spans, metadata={"dpi":dpi,"ocr_mean_confidence":mean,"evidence_family":"classical_ocr"})
