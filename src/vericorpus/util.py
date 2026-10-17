# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import hashlib
import re
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path
from .models import BBox


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", errors="replace")).hexdigest()


def stable_id(*parts: str, n: int = 20) -> str:
    return hashlib.sha256("\x1f".join(parts).encode("utf-8", errors="replace")).hexdigest()[:n]


def normalize_text(text: str) -> str:
    text = unicodedata.normalize("NFKC", text or "")
    text = text.replace("\u00ad", "")
    text = re.sub(r"-\n(?=[a-z])", "", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def comparison_text(text: str) -> str:
    text = normalize_text(text).lower()
    text = re.sub(r"\s+", " ", text)
    return text


def similarity(a: str, b: str) -> float:
    a, b = comparison_text(a), comparison_text(b)
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    return SequenceMatcher(None, a, b).ratio()


def text_quality(text: str) -> float:
    if not text or len(text.strip()) < 20:
        return 0.0
    n = max(len(text), 1)
    replacement = text.count("\ufffd") / n
    controls = sum(1 for c in text if ord(c) < 32 and c not in "\n\t\r") / n
    printable = sum(1 for c in text if c.isprintable() or c in "\n\t\r") / n
    alnum = sum(1 for c in text if c.isalnum()) / n
    weird_tokens = len(re.findall(r"\b[^\W\d_]*[|~^`]{1,}[^\W\d_]*\b", text))
    token_count = max(len(re.findall(r"\S+", text)), 1)
    weird_rate = weird_tokens / token_count
    score = (
        0.45 * printable
        + 0.25 * min(alnum / 0.55, 1.0)
        + 0.30 * (1.0 - min(replacement * 20 + controls * 20 + weird_rate * 5, 1.0))
    )
    return max(0.0, min(score, 1.0))


_HIGH_RISK_PATTERNS = [
    r"\b\d+(?:\.\d+)?\b",
    r"\b\d+(?:\.\d+)?(?:e[+-]?\d+)?\s*(?:%|mg|g|kg|µg|ug|ng|mL|ml|L|M|mM|µM|uM|nM|mg/kg|mg/mL|µg/mL)\b",
    r"\b(?:doi:?\s*)?10\.\d{4,9}/\S+\b",
    r"\b(?:GSE|SRR|SRX|PRJNA|PMID|ISBN|NCT)\w*\d+\b",
    r"\bp\s*[<=>]\s*0?\.\d+\b",
    r"\b[ACGTUN]{12,}\b",
    r"\b[A-Z]{15,}\b",
    r"(?:[A-Za-z0-9]\s*[=+\-*/^]\s*){2,}[A-Za-z0-9]",
]


def contains_high_risk(text: str) -> bool:
    return any(re.search(pat, text or "", re.IGNORECASE) for pat in _HIGH_RISK_PATTERNS)


def content_type(text: str, label: str | None = None) -> str:
    label_l = (label or "").lower()
    if "table" in label_l:
        return "table"
    if any(k in label_l for k in ["formula", "equation", "math"]):
        return "equation"
    if "code" in label_l:
        return "code"
    t = text or ""
    if re.search(r"(?:[A-Za-z0-9]\s*[=+\-*/^]\s*){2,}[A-Za-z0-9]", t):
        return "equation"
    if re.search(r"\b(?:doi:|GSE|SRR|SRX|PRJNA|PMID|ISBN|NCT)\w*", t, re.I):
        return "identifier"
    if re.search(r"\b(?:def |class |import |SELECT |function\(|console\.|public static)\b", t):
        return "code"
    return "text"


def repair_fraction(original: str, revised: str) -> float:
    if not original:
        return 1.0 if revised else 0.0
    sm = SequenceMatcher(None, original, revised)
    matched = sum(block.size for block in sm.get_matching_blocks())
    return max(0.0, min(1.0, 1.0 - matched / max(len(original), 1)))


def union_bbox(boxes: list[BBox | None]) -> BBox | None:
    b = [x for x in boxes if x is not None]
    if not b:
        return None
    return BBox(x0=min(x.x0 for x in b), y0=min(x.y0 for x in b), x1=max(x.x1 for x in b), y1=max(x.y1 for x in b))


def bbox_iou(a: BBox | None, b: BBox | None) -> float:
    if a is None or b is None:
        return 0.0
    ix0, iy0 = max(a.x0,b.x0), max(a.y0,b.y0)
    ix1, iy1 = min(a.x1,b.x1), min(a.y1,b.y1)
    iw, ih = max(0, ix1-ix0), max(0, iy1-iy0)
    inter = iw*ih
    area_a = max(0,a.x1-a.x0)*max(0,a.y1-a.y0)
    area_b = max(0,b.x1-b.x0)*max(0,b.y1-b.y0)
    denom = area_a+area_b-inter
    return inter/denom if denom else 0.0
