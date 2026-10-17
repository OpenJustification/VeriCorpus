# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path

import fitz

from . import __schema_version__, __version__
from .config import Settings
from .dedupe import exact_dedupe, near_dedupe
from .evidence import (
    detect_disagreements,
    drop_unresolved_sentences,
    page_agreement,
    reconstruct_anchor,
    resolve_disagreement,
)
from .extractors import native_candidate, tesseract_candidate
from .model_registry import load_model_lock, load_registry, validate_registry
from .models import Candidate, PageRecord
from .optional_adapters import (
    availability,
    docling_candidate,
    glmocr_candidate,
    olmocr_candidate,
    paddle_candidate,
)
from .plugins import discover_extractor_plugins
from .repro import canonical_json_hash, model_cache_fingerprints, runtime_fingerprint, verify_cache_fingerprints
from .util import sha256_file, text_quality


def _error_candidate(engine: str, exc: Exception | str) -> Candidate:
    return Candidate(engine=f"{engine}_error", text="", confidence=0.0, metadata={"error": str(exc)[:1000]})


def _settings_dict(settings: Settings) -> dict:
    d = asdict(settings)
    if d.get("model_lock_path") is not None:
        d["model_lock_path"] = str(d["model_lock_path"])
    return d


def _set_offline(settings: Settings) -> None:
    keys = ("HF_HUB_OFFLINE", "TRANSFORMERS_OFFLINE", "HF_DATASETS_OFFLINE")
    if settings.offline:
        for key in keys:
            os.environ[key] = "1"
    else:
        # Desktop sessions are long-lived: a previous offline run must not permanently
        # block an explicitly online first-run model download in the same process.
        for key in keys:
            os.environ.pop(key, None)


def _collect_candidates(
    page: fitz.Page,
    page_no: int,
    settings: Settings,
    avail: dict[str, bool],
    plugins: dict | None = None,
) -> list[Candidate]:
    out = [native_candidate(page, page_no)]
    if settings.use_tesseract:
        try:
            out.append(tesseract_candidate(page, page_no, dpi=settings.render_dpi))
        except Exception as exc:
            out.append(_error_candidate("tesseract", exc))
    if settings.use_paddleocr:
        if avail.get("paddleocr_vl_1_6"):
            try:
                out.append(paddle_candidate(page, page_no, dpi=settings.render_dpi))
            except Exception as exc:
                out.append(_error_candidate("paddleocr_vl_1_6", exc))
        else:
            out.append(_error_candidate("paddleocr_vl_1_6", "not installed or model unavailable"))
    if settings.use_docling:
        if avail.get("docling"):
            try:
                out.append(docling_candidate(page, page_no))
            except Exception as exc:
                out.append(_error_candidate("docling", exc))
        else:
            out.append(_error_candidate("docling", "not installed"))
    if settings.use_glmocr:
        if avail.get("glmocr"):
            try:
                out.append(glmocr_candidate(page, page_no, dpi=settings.render_dpi))
            except Exception as exc:
                out.append(_error_candidate("glmocr", exc))
        else:
            out.append(_error_candidate("glmocr", "not installed/self-hosted backend unavailable"))
    if settings.use_olmocr:
        if avail.get("olmocr"):
            try:
                out.append(olmocr_candidate(page, page_no))
            except Exception as exc:
                out.append(_error_candidate("olmocr2", exc))
        else:
            out.append(_error_candidate("olmocr2", "not installed"))

    for plugin_name, plugin in (plugins or {}).items():
        try:
            candidate = plugin.extract(page, page_no, dpi=settings.render_dpi)
            if not isinstance(candidate, Candidate):
                raise TypeError("extractor plugin must return vericorpus.models.Candidate")
            out.append(candidate)
        except Exception as exc:
            out.append(_error_candidate(f"plugin:{plugin_name}", exc))
    return out


def _special_blocks(document_id: str, source_file: str, page_no: int, candidates: list[Candidate]):
    rows = []
    seen = set()
    for c in candidates:
        for s in c.spans:
            if s.content_type not in {"table", "equation", "code", "identifier"}:
                continue
            key = (s.content_type, s.text.strip().lower(), page_no)
            if not s.text.strip() or key in seen:
                continue
            seen.add(key)
            rows.append(
                {
                    "document_id": document_id,
                    "source_file": source_file,
                    "page_number": page_no,
                    "content_type": s.content_type,
                    "text": s.text,
                    "engine": s.engine,
                    "confidence": s.confidence,
                    "bbox": s.bbox.model_dump() if s.bbox else None,
                    "status": "evidence_only",
                    "note": "High-risk structured blocks require independent source evidence; VeriCorpus does not generatively repair them.",
                }
            )
    return rows


def _sha256_path(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _write_jsonl(path: Path, rows):
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            stamped = dict(row)
            stamped.setdefault("vericorpus_schema", __schema_version__)
            stamped.setdefault("generator", "vericorpus")
            stamped.setdefault("generator_version", __version__)
            f.write(json.dumps(stamped, ensure_ascii=False, sort_keys=True) + "\n")


def prepare(input_path: Path, out_dir: Path, settings: Settings):
    input_path = input_path.resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    _set_offline(settings)

    registry = load_registry()
    registry_errors = validate_registry(registry)
    if registry_errors:
        raise RuntimeError("Invalid reference model registry: " + "; ".join(registry_errors))
    model_lock = load_model_lock(settings.model_lock_path)
    if model_lock and not settings.offline:
        raise ValueError("A model-locked run must be offline so model/cache bytes cannot change during processing")
    cache_before = model_cache_fingerprints() if model_lock else {}
    if model_lock:
        expected_cache = model_lock.get("cache_fingerprints", {})
        if not expected_cache:
            raise ValueError("Model lock is missing cache_fingerprints; it cannot prove local model bytes")
        lock_errors = verify_cache_fingerprints(expected_cache, cache_before)
        if lock_errors:
            raise ValueError("Model lock verification failed before processing: " + "; ".join(lock_errors))
    runtime = runtime_fingerprint(settings.seed, model_lock)

    if input_path.is_dir():
        files = [p for p in sorted(input_path.rglob("*")) if p.suffix.lower() == ".pdf"]
    elif input_path.suffix.lower() == ".pdf":
        files = [input_path]
    else:
        raise ValueError("VeriCorpus 0.1 currently accepts PDF files or folders containing PDFs.")
    if not files:
        raise ValueError("No PDF files were found in the requested input.")

    avail = availability()
    plugins = discover_extractor_plugins()
    audits = []
    ledger_rows = []
    accepted = []
    rejected = []
    structured = []
    inputs = []

    for pdf_path in files:
        source_file = str(pdf_path.relative_to(input_path)) if input_path.is_dir() else pdf_path.name
        doc_hash = sha256_file(pdf_path)
        inputs.append({"source_file": source_file, "sha256": doc_hash, "bytes": pdf_path.stat().st_size})
        doc = fitz.open(pdf_path)
        try:
            for page_idx in range(len(doc)):
                page_no = page_idx + 1
                page = doc[page_idx]
                candidates = _collect_candidates(page, page_no, settings, avail, plugins)
                useful = [
                    c
                    for c in candidates
                    if c.text.strip() and not c.engine.endswith("_error") and c.confidence >= settings.min_engine_confidence
                ]
                structured.extend(_special_blocks(doc_hash, source_file, page_no, useful))

                anchor, disagreements = detect_disagreements(useful, page_no, settings.disagreement_context_chars)
                ledger = []
                for d in disagreements:
                    # Reference build settles text only from independent extraction evidence.
                    # Local visual-judge plugins may be added later, but cannot author replacement text.
                    entry = resolve_disagreement(doc_hash, source_file, d, useful, [], 1.0)
                    ledger.append(entry)
                    ledger_rows.append(entry.model_dump())

                agreement = page_agreement(useful)
                if len(useful) < 2:
                    # A clean born-digital PDF text layer is source evidence, not a
                    # language-model reconstruction. Lite mode may therefore admit it
                    # when the native extraction itself is strong. Scans/weak text
                    # still require independent extraction evidence.
                    native_only = (
                        len(useful) == 1
                        and useful[0].engine == "pymupdf_native"
                        and useful[0].confidence >= max(0.95, settings.page_accept_quality)
                        and len(useful[0].text.strip()) >= 40
                    )
                    reconstructed = anchor.text
                    if native_only:
                        unresolved = 0
                        high_unresolved = 0
                        clean = anchor.text
                        decision = "accepted"
                        reason = "high_quality_native_pdf_text_layer"
                    else:
                        unresolved = max(1, len(disagreements))
                        high_unresolved = max(1, sum(1 for d in disagreements if d.high_risk))
                        clean = ""
                        decision = "rejected"
                        reason = "fewer_than_two_independent_extractions"
                else:
                    reconstructed, unresolved, high_unresolved = reconstruct_anchor(anchor, disagreements, ledger)
                    clean = drop_unresolved_sentences(reconstructed)
                    if not disagreements and agreement >= settings.span_agreement_threshold and anchor.confidence >= settings.page_accept_quality:
                        decision = "accepted"
                        reason = "page_level_independent_agreement"
                    elif unresolved == 0 and clean.strip():
                        decision = "accepted"
                        reason = "all_localized_disagreements_resolved"
                    else:
                        frac = unresolved / max(len(disagreements), 1)
                        if clean.strip() and frac <= settings.reject_page_if_unresolved_fraction_gt:
                            decision = "partial"
                            reason = "unresolved_sentences_removed"
                        else:
                            decision = "rejected"
                            reason = "too_much_unresolved_content"

                page_record = PageRecord(
                    document_id=doc_hash,
                    source_file=source_file,
                    page_number=page_no,
                    candidates=candidates,
                    disagreements=disagreements,
                    ledger_entries=ledger,
                    selected_text=clean if decision != "rejected" else reconstructed,
                    agreement=agreement,
                    selected_quality=text_quality(clean if clean else reconstructed),
                    unresolved_spans=unresolved,
                    decision=decision,
                    decision_reason=reason,
                )
                audits.append(page_record.model_dump())
                rec = {
                    "document_id": doc_hash,
                    "source_file": source_file,
                    "page_number": page_no,
                    "text": clean,
                    "quality": text_quality(clean),
                    "provenance": {
                        "decision": decision,
                        "decision_reason": reason,
                        "page_agreement": agreement,
                        "unresolved_spans": unresolved,
                        "high_risk_unresolved_spans": high_unresolved,
                        "engines": [c.engine for c in useful],
                        "ledger_ids": [e.ledger_id for e in ledger],
                    },
                }
                if decision in {"accepted", "partial"} and clean.strip():
                    accepted.append(rec)
                else:
                    rec["text"] = reconstructed
                    rejected.append(rec)
        finally:
            doc.close()

    before = len(accepted)
    accepted = exact_dedupe(accepted)
    accepted = near_dedupe(accepted, threshold=0.95)
    after = len(accepted)

    _write_jsonl(out_dir / "audit.jsonl", audits)
    _write_jsonl(out_dir / "evidence_ledger.jsonl", ledger_rows)
    _write_jsonl(out_dir / "training.jsonl", accepted)
    _write_jsonl(out_dir / "rejected.jsonl", rejected)
    _write_jsonl(out_dir / "structured_blocks.jsonl", structured)
    (out_dir / "engine_status.json").write_text(json.dumps(avail, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    settings_obj = _settings_dict(settings)
    generative_model_engines_requested = any([settings.use_paddleocr, settings.use_glmocr, settings.use_olmocr, settings.use_docling])
    cache_after = model_cache_fingerprints()
    if model_lock:
        lock_errors = verify_cache_fingerprints(model_lock.get("cache_fingerprints", {}), cache_after)
        if lock_errors:
            raise RuntimeError("Model/cache bytes changed during locked processing: " + "; ".join(lock_errors))
        reproducibility_grade = "locked-cache-verified"
    elif not generative_model_engines_requested:
        reproducibility_grade = "deterministic-no-model-assets"
    elif any(v.get("files", 0) for v in cache_after.values()):
        reproducibility_grade = "cache-fingerprinted-unlocked"
    else:
        reproducibility_grade = "unlocked-model-assets"
    manifest = {
        "vericorpus_schema": __schema_version__,
        "generator": "vericorpus",
        "generator_version": __version__,
        "profile": settings.profile,
        "offline": settings.offline,
        "reproducibility_grade": reproducibility_grade,
        "settings": settings_obj,
        "settings_sha256": canonical_json_hash(settings_obj),
        "reference_registry": registry,
        "runtime": runtime,
        "model_cache_fingerprints": cache_after,
        "inputs": inputs,
        "documents": len(files),
        "pages_total": len(audits),
        "pages_accepted_before_dedupe": before,
        "pages_accepted_after_dedupe": after,
        "pages_rejected": len(rejected),
        "ledger_entries": len(ledger_rows),
        "structured_blocks": len(structured),
        "engine_availability": avail,
        "extractor_plugins": sorted(plugins),
        "acceptance_rate": after / max(len(audits), 1),
        "safety_contract": [
            "Reference build never invents replacement text.",
            "High-risk disagreements require independent source-derived evidence.",
            "Unresolved sentences are removed from training output or the page is rejected.",
            "All localized decisions are preserved in evidence_ledger.jsonl.",
            "Network access is disabled for official reference runs unless the user explicitly changes settings.",
        ],
        "limitations": [
            "Exact GPU floating-point reproducibility can vary across hardware/runtime versions even with deterministic decoding.",
            "Confidence values are heuristic until calibrated on a human-verified benchmark.",
        ],
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

    output_files = [
        "audit.jsonl",
        "evidence_ledger.jsonl",
        "training.jsonl",
        "rejected.jsonl",
        "structured_blocks.jsonl",
        "engine_status.json",
    ]
    outputs = {name: _sha256_path(out_dir / name) for name in output_files}
    outputs["manifest_pre_hash_sha256"] = _sha256_path(manifest_path)
    (out_dir / "SHA256SUMS.json").write_text(json.dumps(outputs, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest
