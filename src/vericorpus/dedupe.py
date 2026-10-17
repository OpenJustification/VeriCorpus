# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import re
from .util import sha256_text


def exact_dedupe(records):
    seen = set()
    output = []
    for r in records:
        h = sha256_text(r["text"].strip().lower())
        if h in seen:
            continue
        seen.add(h)
        output.append(r)
    return output


def _word_ngrams(text: str, n: int = 5):
    words = re.findall(r"\w+", text.lower())
    if len(words) < n:
        return set(words)
    return {tuple(words[i:i+n]) for i in range(len(words)-n+1)}


def near_duplicate(a: str, b: str, threshold: float = 0.92) -> bool:
    A, B = _word_ngrams(a), _word_ngrams(b)
    if not A or not B:
        return False
    return len(A & B) / len(A | B) >= threshold


def near_dedupe(records, threshold: float = 0.92):
    # MVP O(n^2): fine for small batches; replace with MinHash/LSH for production.
    kept = []
    for r in records:
        if any(near_duplicate(r["text"], k["text"], threshold) for k in kept):
            continue
        kept.append(r)
    return kept
