# SPDX-License-Identifier: AGPL-3.0-or-later
"""Deterministic training exports, document-disjoint splits and integrity checks.

The official pretraining export contains only source-derived text. Audit metadata
stays in training.jsonl so trainers never accidentally learn provenance headers.
"""
from __future__ import annotations

from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
from typing import Any

from .util import sha256_text


def stable_record_id(record: dict) -> str:
    material = "\x1f".join((
        str(record["document_id"]), str(record["page_number"]), record["text"]
    ))
    return "vc_" + hashlib.sha256(material.encode("utf-8")).hexdigest()[:24]


def split_for_document(document_id: str, validation_percent: int = 10, test_percent: int = 10) -> str:
    """Hash-based split: all pages from the same document always stay together."""
    if not 0 <= validation_percent <= 50 or not 0 <= test_percent <= 50:
        raise ValueError("Split percentages must be 0..50")
    if validation_percent + test_percent >= 100:
        raise ValueError("Train split cannot be empty")
    bucket = int(hashlib.sha256(document_id.encode("utf-8")).hexdigest()[:15], 16) % 10000
    if bucket < 100 * test_percent:
        return "test"
    if bucket < 100 * (test_percent + validation_percent):
        return "validation"
    return "train"


def _jsonl(path: Path, data: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as fp:
        for row in data:
            fp.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def create_training_exports(out_dir: Path, records: list[dict], audits: list[dict],
                            structures: list[dict], duplicates: list[dict],
                            rejected: list[dict], partial: list[dict]) -> dict:
    """Return report. Does not modify source documents or validated records."""
    for record in records:
        record.setdefault("record_id", stable_record_id(record))
        record.setdefault("text_sha256", sha256_text(record["text"]))
    raw = [{"text": r["text"]} for r in records]
    _jsonl(out_dir / "pretraining.jsonl", raw)

    documents = {r["document_id"] for r in records}
    # A single PDF never yields accidental empty training data because its hash
    # happens to be in a holdout bucket. For small runs, use all-train and say so.
    use_holdouts = len(documents) >= 10
    assigned: dict[str, str] = {
        document_id: split_for_document(document_id) if use_holdouts else "train"
        for document_id in sorted(documents)
    }
    split_rows = {s: [] for s in ("train", "validation", "test")}
    for r in records:
        split_rows[assigned[r["document_id"]]].append({"text": r["text"]})
    for split, rows in split_rows.items():
        _jsonl(out_dir / "splits" / f"{split}.jsonl", rows)
    mapping = [{"document_id": d, "split": s} for d, s in sorted(assigned.items())]
    _jsonl(out_dir / "splits" / "document_assignments.jsonl", mapping)

    layout_counts = Counter(s.get("layout_type", "unknown") for s in structures)
    object_counts = Counter(
        obj.get("object_type", "unknown")
        for s in structures for obj in s.get("objects", [])
        if not obj.get("metadata", {}).get("suppressed", False)
    )
    issue_counts = Counter(
        reason
        for a in audits
        for reason in (a.get("readiness") or {}).get("blocking_issues", [])
    )
    warn_counts = Counter(
        w for a in audits for w in (a.get("readiness") or {}).get("warnings", [])
    )
    report = {
        "documents_total": len({a["document_id"] for a in audits}),
        "documents_in_training": len(documents),
        "units_processed": len(audits),
        "training_records": len(records),
        "training_characters": sum(len(r["text"]) for r in records),
        "training_utf8_bytes": sum(len(r["text"].encode("utf-8")) for r in records),
        "accepted_exact_or_near_duplicates_removed": len(duplicates),
        "rejected_units": len(rejected),
        "partial_units_held_for_review": len(partial),
        "layout_types": dict(sorted(layout_counts.items())),
        "structure_object_counts": dict(sorted(object_counts.items())),
        "blocking_issues": dict(sorted(issue_counts.items())),
        "warnings": dict(sorted(warn_counts.items())),
        "split_strategy": "document_hash_80_10_10" if use_holdouts else "all_train_small_corpus",
        "split_document_counts": dict(sorted(Counter(assigned.values()).items())),
        "split_record_counts": {s: len(rows) for s, rows in split_rows.items()},
        "limitations": [
            "No benchmark-calibrated claim about scientific correctness is made.",
            "A source-native extraction is not independent verification of the source's scientific claims.",
            "Figures lacking textual descriptions are not hallucinated into text.",
            "Holdout splits are deterministic and document-disjoint, not balanced by topic or publisher.",
        ],
    }
    (out_dir / "corpus_report.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8"
    )
    lines = [
        "# VeriCorpus dataset card", "", "## Scope", "",
        f"- Documents: {report['documents_total']}",
        f"- Processed document units: {report['units_processed']}",
        f"- Training records: {report['training_records']}",
        f"- Excluded duplicates: {len(duplicates)}",
        f"- Held for review: {len(partial)}",
        f"- Rejected/reprocess: {len(rejected)}", "",
        "## Ready-to-load file", "",
        "`pretraining.jsonl` is UTF-8 JSON Lines with a single `text` field. Each record is source-derived; it is not synthetic question-answer training data.",
        "", "## Splits", "",
        f"Strategy: `{report['split_strategy']}`. Documents are never split across train/validation/test. ",
        "For fewer than ten admitted documents, all training text stays in the training split.", "",
        "## Human review", "",
        "Use `training_review.md`, `document_structure.jsonl`, `review_queue.jsonl`, `evidence_ledger.jsonl`, and `unresolved.jsonl`. ",
        "Partial or unresolved records are held out of the strict training export by default.", "",
        "## Limitations", "",
    ]
    lines.extend("- " + v for v in report["limitations"])
    (out_dir / "DATASET_CARD.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return report


def validate_run(out_dir: Path) -> dict:
    """Check a completed run using disk outputs; never blindly trust manifest scores."""
    errors: list[str] = []
    out_dir = Path(out_dir)

    def get_jsonl(filename: str) -> list[dict]:
        path = out_dir / filename
        if not path.exists():
            errors.append(f"missing:{filename}")
            return []
        rows = []
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except (ValueError, TypeError):
                errors.append(f"invalid_json:{filename}:{line_number}")
                continue
            if not isinstance(row, dict):
                errors.append(f"invalid_row_type:{filename}:{line_number}")
                continue
            rows.append(row)
        return rows

    training = get_jsonl("training.jsonl")
    audits = get_jsonl("audit.jsonl")
    pretrain = get_jsonl("pretraining.jsonl")
    train = get_jsonl("splits/train.jsonl")
    validation = get_jsonl("splits/validation.jsonl")
    test = get_jsonl("splits/test.jsonl")
    assignments = get_jsonl("splits/document_assignments.jsonl")
    audit_keys = {(x.get("document_id"), x.get("page_number")) for x in audits}
    seen = set()
    for index, row in enumerate(training):
        reference = (row.get("document_id"), row.get("page_number"))
        if reference not in audit_keys:
            errors.append(f"orphan_training:{index}")
        if not row.get("text", "").strip():
            errors.append(f"empty_training:{index}")
        if row.get("record_id") != stable_record_id(row):
            errors.append(f"record_id_mismatch:{index}")
        if row.get("text_sha256") != sha256_text(row.get("text", "")):
            errors.append(f"text_hash_mismatch:{index}")
        if row.get("training_readiness", {}).get("status") != "accepted":
            errors.append(f"nonaccepted_in_strict_training:{index}")
        if row.get("record_id") in seen:
            errors.append(f"duplicate_record_id:{index}")
        seen.add(row.get("record_id"))
    if pretrain != [{"text": r["text"]} for r in training]:
        errors.append("pretraining_disagrees_with_training")
    if len(train) + len(validation) + len(test) != len(training):
        errors.append("split_record_count_mismatch")
    mapping = {r.get("document_id"): r.get("split") for r in assignments}
    expected = {s: [] for s in ("train", "validation", "test")}
    for r in training:
        which = mapping.get(r["document_id"])
        if which not in expected:
            errors.append(f"missing_split_assignment:{r['document_id']}")
        else:
            expected[which].append({"text": r["text"]})
    for key, rows in (("train", train), ("validation", validation), ("test", test)):
        if expected[key] != rows:
            errors.append(f"split_mismatch:{key}")
    sums_path = out_dir / "SHA256SUMS.json"
    if sums_path.exists():
        try:
            checksums = json.loads(sums_path.read_text(encoding="utf-8"))
            for name, wanted in checksums.items():
                if name == "manifest_pre_hash_sha256":
                    name = "manifest.json"
                path = out_dir / name
                if not path.exists():
                    errors.append(f"missing_hashed_file:{name}")
                elif hashlib.sha256(path.read_bytes()).hexdigest() != wanted:
                    errors.append(f"checksum_mismatch:{name}")
        except (ValueError, OSError):
            errors.append("invalid_checksums")
    else:
        errors.append("missing:SHA256SUMS.json")
    return {"status": "PASS" if not errors else "FAIL", "errors": errors,
            "training_records": len(training), "processed_units": len(audits)}
