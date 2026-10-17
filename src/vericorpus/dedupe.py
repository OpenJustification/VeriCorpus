# SPDX-License-Identifier: AGPL-3.0-or-later
"""Exact, auditable, indexed near-duplicate detection over text shingles."""
from __future__ import annotations

from collections import defaultdict
import re
from .util import sha256_text


def _canonical(text: str) -> str:
    return re.sub(r"\s+", " ", text.casefold()).strip()


def exact_dedupe(records):
    seen = set()
    output = []
    for r in records:
        h = sha256_text(_canonical(r["text"]))
        if h in seen:
            continue
        seen.add(h)
        output.append(r)
    return output


def _word_ngrams(text: str, n: int = 5):
    words = re.findall(r"\w+", text.casefold())
    if len(words) < n:
        return set(words)
    return {tuple(words[i:i+n]) for i in range(len(words)-n+1)}


def near_duplicate(a: str, b: str, threshold: float = 0.92) -> bool:
    A, B = _word_ngrams(a), _word_ngrams(b)
    if not A or not B:
        return False
    return len(A & B) / len(A | B) >= threshold


def dedupe_with_report(records, threshold: float = 0.95):
    """Indexed recall-preserving Jaccard check (candidate retrieval via shared shingles).

    All pairs above a nonzero Jaccard threshold share at least one shingle,
    so the inverted index cannot miss a true near duplicate. Very common
    shingles can cost memory/time on massive corpora; this is a batch reference
    implementation rather than a distributed trillion-token deduper.
    """
    kept = []
    dropped = []
    index = defaultdict(list)
    fingerprints = {}
    shingled = []
    for record in records:
        text = record["text"]
        digest = sha256_text(_canonical(text))
        duplicate_of = fingerprints.get(digest)
        sim = 1.0
        kind = "exact"
        grams = _word_ngrams(text)
        if duplicate_of is None and grams:
            # Candidates must share a shingle; choose comparisons in admission order.
            candidate_indices = sorted({idx for gram in grams for idx in index.get(gram, ())})
            for i in candidate_indices:
                other = shingled[i]
                # Jaccard bound from sizes alone.
                if min(len(other), len(grams)) / max(len(other), len(grams)) < threshold:
                    continue
                score = len(grams & other) / len(grams | other)
                if score >= threshold:
                    duplicate_of = kept[i]
                    sim = score
                    kind = "near"
                    break
        if duplicate_of is not None:
            dropped.append({
                "removed_record_id": record.get("record_id"),
                "kept_record_id": duplicate_of.get("record_id"),
                "removed_document_id": record.get("document_id"),
                "removed_page_number": record.get("page_number"),
                "kept_document_id": duplicate_of.get("document_id"),
                "kept_page_number": duplicate_of.get("page_number"),
                "similarity": round(sim, 6), "type": kind,
            })
            continue
        index_id = len(kept)
        kept.append(record)
        shingled.append(grams)
        fingerprints[digest] = record
        for gram in grams:
            index[gram].append(index_id)
    return kept, dropped


def near_dedupe(records, threshold: float = 0.92):
    return dedupe_with_report(records, threshold)[0]
