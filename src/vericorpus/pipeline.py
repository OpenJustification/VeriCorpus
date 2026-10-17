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
from .dedupe import dedupe_with_report
from .corpus import stable_record_id, create_training_exports, validate_run
from .epub import epub_structures, epub_candidate
from .dashboard import write_review_dashboard
from .evidence import (
    detect_disagreements,
    drop_unresolved_sentences,
    page_agreement,
    reconstruct_anchor,
    resolve_disagreement,
)
from .extractors import tesseract_candidate
from .layout import analyze_page, native_layout_candidate, structure_to_text
from .model_registry import load_model_lock, load_registry, validate_registry
from .models import Candidate, PageRecord, PageStructure
from .optional_adapters import (
    availability,
    docling_candidate,
    glmocr_candidate,
    olmocr_candidate,
    paddle_candidate,
)
from .plugins import discover_extractor_plugins
from .quality import quality_vector, training_readiness
from .repro import canonical_json_hash, model_cache_fingerprints, runtime_fingerprint, verify_cache_fingerprints
from .routing import route_page
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
        for key in keys:
            os.environ.pop(key, None)


def _collect_candidates(
    page: fitz.Page,
    page_no: int,
    structure: PageStructure,
    route: dict,
    settings: Settings,
    avail: dict[str, bool],
    plugins: dict | None = None,
) -> list[Candidate]:
    out = [native_layout_candidate(structure)]
    requested = set(route.get("requested_engines", []))

    if "tesseract" in requested:
        try:
            out.append(tesseract_candidate(page, page_no, dpi=settings.render_dpi))
        except Exception as exc:
            out.append(_error_candidate("tesseract", exc))
    if "paddleocr_vl_1_6" in requested:
        if avail.get("paddleocr_vl_1_6"):
            try:
                out.append(paddle_candidate(page, page_no, dpi=settings.render_dpi))
            except Exception as exc:
                out.append(_error_candidate("paddleocr_vl_1_6", exc))
        else:
            out.append(_error_candidate("paddleocr_vl_1_6", "not installed or model unavailable"))
    if "docling" in requested:
        if avail.get("docling"):
            try:
                out.append(docling_candidate(page, page_no))
            except Exception as exc:
                out.append(_error_candidate("docling", exc))
        else:
            out.append(_error_candidate("docling", "not installed"))
    if "glmocr" in requested:
        if avail.get("glmocr"):
            try:
                out.append(glmocr_candidate(page, page_no, dpi=settings.render_dpi))
            except Exception as exc:
                out.append(_error_candidate("glmocr", exc))
        else:
            out.append(_error_candidate("glmocr", "not installed/self-hosted backend unavailable"))
    if "olmocr2" in requested:
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


def _structure_rows(document_id: str, source_file: str, structure: PageStructure) -> list[dict]:
    rows = []
    for o in structure.objects:
        if o.metadata.get("suppressed"):
            continue
        if o.object_type not in {
            "table",
            "equation",
            "figure",
            "figure_caption",
            "code",
            "algorithm",
            "identifier",
        }:
            continue
        rows.append(
            {
                "document_id": document_id,
                "source_file": source_file,
                "page_number": structure.page_number,
                "object_id": o.object_id,
                "content_type": o.object_type,
                "text": o.text,
                "engine": o.source,
                "confidence": o.confidence,
                "bbox": o.bbox.model_dump(),
                "reading_order": o.reading_order,
                "column_index": o.column_index,
                "status": "source_derived_object",
                "child_ids": o.child_ids,
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


def _write_pretty_json(path: Path, rows: list[dict]) -> None:
    stamped = []
    for row in rows:
        x = dict(row)
        x.setdefault("vericorpus_schema", __schema_version__)
        x.setdefault("generator", "vericorpus")
        x.setdefault("generator_version", __version__)
        stamped.append(x)
    path.write_text(json.dumps(stamped, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _write_review(path: Path, rows: list[dict]) -> None:
    chunks = [f"# VeriCorpus training review\n\nGenerator: VeriCorpus {__version__}\n"]
    for r in rows:
        q = r.get("quality_dimensions", {})
        ready = r.get("training_readiness", {})
        layout = r.get("layout", {})
        chunks.append(
            "\n".join(
                [
                    f"## {r.get('source_file')} — page {r.get('page_number')}",
                    "",
                    f"- Status: **{ready.get('status', 'unknown')}**",
                    f"- Overall quality: **{q.get('overall', r.get('quality', 0)):.3f}**",
                    f"- Verification: `{ready.get('verification_grade', 'unknown')}`",
                    f"- Layout: `{layout.get('layout_type', 'unknown')}`; columns: {layout.get('column_count', '?')}",
                    f"- Reading-order confidence: {q.get('reading_order', 0):.3f}",
                    f"- Table confidence: {q.get('tables', 1):.3f}",
                    f"- Equation confidence: {q.get('equations', 1):.3f}",
                    f"- Numeric fidelity: {q.get('numeric_fidelity', 1):.3f}",
                    "",
                    "### Training text",
                    "",
                    r.get("text", ""),
                    "",
                ]
            )
        )
    path.write_text("\n".join(chunks).rstrip() + "\n", encoding="utf-8")


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
        files = [p for p in sorted(input_path.rglob("*")) if p.suffix.lower() in {".pdf", ".epub"}]
    elif input_path.suffix.lower() in {".pdf", ".epub"}:
        files = [input_path]
    else:
        raise ValueError("VeriCorpus accepts PDF/EPUB files or folders containing them.")
    if not files:
        raise ValueError("No PDF/EPUB files were found in the requested input.")

    avail = availability()
    plugins = discover_extractor_plugins()
    audits: list[dict] = []
    ledger_rows: list[dict] = []
    accepted: list[dict] = []
    rejected: list[dict] = []
    partial: list[dict] = []
    unresolved_rows: list[dict] = []
    structured: list[dict] = []
    structures: list[dict] = []
    routing_rows: list[dict] = []
    inputs = []

    for pdf_path in files:
        source_file = str(pdf_path.relative_to(input_path)) if input_path.is_dir() else pdf_path.name
        doc_hash = sha256_file(pdf_path)
        inputs.append({"source_file": source_file, "sha256": doc_hash, "bytes": pdf_path.stat().st_size})
        def iter_source_units():
            if pdf_path.suffix.lower() == ".epub":
                for item in epub_structures(pdf_path):
                    yield None, item
            else:
                with fitz.open(pdf_path) as source_doc:
                    for page_idx in range(len(source_doc)):
                        page = source_doc[page_idx]
                        yield page, analyze_page(page, page_idx + 1)

        for page, structure in iter_source_units():
                page_no = structure.page_number
                route = route_page(structure, settings, avail) if page is not None else {
                    "profile": settings.profile, "requested_engines": ["epub_xhtml"], "complex": bool(structure.complexity_score > 0.38),
                    "complexity_score": structure.complexity_score, "reasons": ["epub_dom_extraction_no_ocr"],
                }
                route_row = {"document_id": doc_hash, "source_file": source_file, "page_number": page_no, **route}
                routing_rows.append(route_row)
                structures.append({"document_id": doc_hash, "source_file": source_file, **structure.model_dump()})
                structured.extend(_structure_rows(doc_hash, source_file, structure))

                candidates = _collect_candidates(page, page_no, structure, route, settings, avail, plugins) if page is not None else [epub_candidate(structure)]
                useful = [
                    c
                    for c in candidates
                    if c.text.strip() and not c.engine.endswith("_error") and c.confidence >= settings.min_engine_confidence
                ]

                if useful:
                    anchor, disagreements = detect_disagreements(useful, page_no, settings.disagreement_context_chars)
                else:
                    anchor = Candidate(engine="none", text="", confidence=0.0)
                    disagreements = []

                ledger = []
                for d in disagreements:
                    entry = resolve_disagreement(doc_hash, source_file, d, useful, [], 1.0)
                    ledger.append(entry)
                    ledger_rows.append(entry.model_dump())
                    if entry.decision == "unresolved":
                        unresolved_rows.append(
                            {
                                "document_id": doc_hash,
                                "source_file": source_file,
                                "page_number": page_no,
                                "disagreement_id": d.disagreement_id,
                                "content_type": d.content_type,
                                "high_risk": d.high_risk,
                                "bbox": d.bbox.model_dump() if d.bbox else None,
                                "alternatives": d.alternatives,
                                "reason": entry.reason,
                            }
                        )

                agreement = page_agreement(useful)
                if not useful:
                    reconstructed = structure_to_text(structure)
                    clean = ""
                    unresolved = 1
                    high_unresolved = 1 if structure.diagnostics.get("high_risk_objects", 0) else 0
                elif len(useful) == 1:
                    # One source family can still be technically training-ready when
                    # it is born-digital and the Document Structure Engine validates
                    # object layout / reading order. The verification grade remains
                    # source_plus_layout, never cross-family.
                    reconstructed = anchor.text
                    clean = anchor.text
                    unresolved = 0
                    high_unresolved = 0
                else:
                    reconstructed, unresolved, high_unresolved = reconstruct_anchor(anchor, disagreements, ledger)
                    clean = drop_unresolved_sentences(reconstructed)

                q = quality_vector(
                    clean if clean else reconstructed,
                    structure,
                    useful,
                    len(disagreements),
                    unresolved,
                    high_unresolved,
                )
                ready = training_readiness(
                    q,
                    structure,
                    useful,
                    unresolved,
                    high_unresolved,
                    settings.page_accept_quality,
                )

                if ready.status == "accepted" and clean.strip():
                    decision = "accepted"
                    reason = "training_readiness_pass"
                elif ready.status == "partial" and clean.strip():
                    decision = "partial"
                    reason = "training_readiness_partial"
                elif ready.status == "reprocess":
                    decision = "reprocess"
                    reason = "training_readiness_reprocess"
                else:
                    decision = "rejected"
                    reason = "training_readiness_reject"

                page_record = PageRecord(
                    document_id=doc_hash,
                    source_file=source_file,
                    page_number=page_no,
                    candidates=candidates,
                    structure=structure,
                    quality=q,
                    readiness=ready,
                    routing=route,
                    disagreements=disagreements,
                    ledger_entries=ledger,
                    selected_text=clean if clean else reconstructed,
                    agreement=agreement,
                    selected_quality=q.overall,
                    unresolved_spans=unresolved,
                    decision=decision,
                    decision_reason=reason,
                )
                audits.append(page_record.model_dump())

                rec = {
                    "document_id": doc_hash,
                    "source_file": source_file,
                    "source_format": pdf_path.suffix.lower().lstrip("."),
                    "page_number": page_no,
                    "text": clean if clean else reconstructed,
                    "quality": q.overall,
                    "quality_dimensions": q.model_dump(),
                    "training_readiness": ready.model_dump(),
                    "layout": {
                        "layout_type": structure.layout_type,
                        "column_count": structure.column_count,
                        "complexity_score": structure.complexity_score,
                        "complexity_reasons": structure.complexity_reasons,
                    },
                    "provenance": {
                        "decision": decision,
                        "decision_reason": reason,
                        "page_agreement": agreement,
                        "unresolved_spans": unresolved,
                        "high_risk_unresolved_spans": high_unresolved,
                        "engines": [c.engine for c in useful],
                        "evidence_families": sorted({c.metadata.get("evidence_family", c.engine) for c in useful}),
                        "ledger_ids": [e.ledger_id for e in ledger],
                        "route": route,
                    },
                }
                if rec["text"].strip():
                    rec["record_id"] = stable_record_id(rec)
                if decision == "accepted" and rec["text"].strip():
                    accepted.append(rec)
                elif decision == "partial" and rec["text"].strip():
                    partial.append(rec)
                else:
                    rejected.append(rec)

    before = len(accepted)
    accepted, duplicate_rows = dedupe_with_report(accepted, threshold=0.95)
    after = len(accepted)
    corpus_report = create_training_exports(out_dir, accepted, audits, structures, duplicate_rows, rejected, partial)

    write_review_dashboard(out_dir / "review_dashboard.html", audits, structured, __version__)
    _write_jsonl(out_dir / "audit.jsonl", audits)
    _write_jsonl(out_dir / "evidence_ledger.jsonl", ledger_rows)
    _write_jsonl(out_dir / "training.jsonl", accepted)
    _write_jsonl(out_dir / "rejected.jsonl", rejected)
    _write_jsonl(out_dir / "review_queue.jsonl", partial)
    _write_jsonl(out_dir / "duplicates.jsonl", duplicate_rows)
    _write_jsonl(out_dir / "unresolved.jsonl", unresolved_rows)
    _write_jsonl(out_dir / "structured_blocks.jsonl", structured)
    _write_jsonl(out_dir / "document_structure.jsonl", structures)
    _write_jsonl(out_dir / "routing.jsonl", routing_rows)
    if settings.write_pretty_json:
        _write_pretty_json(out_dir / "training.pretty.json", accepted)
    if settings.write_review_markdown:
        _write_review(out_dir / "training_review.md", accepted)
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
        "pages_rejected_or_reprocess": len(rejected),
        "pages_partial_held_for_review": len(partial),
        "duplicates_excluded": len(duplicate_rows),
        "corpus_report": corpus_report,
        "ledger_entries": len(ledger_rows),
        "unresolved_items": len(unresolved_rows),
        "structured_blocks": len(structured),
        "engine_availability": avail,
        "extractor_plugins": sorted(plugins),
        "acceptance_rate": after / max(len(audits), 1),
        "architecture": {
            "document_structure_engine": True,
            "object_identification": True,
            "column_detection": "1/2/3-column plus mixed-layout heuristic",
            "dynamic_routing": True,
            "multidimensional_quality": True,
            "human_readable_exports": True,
        },
        "safety_contract": [
            "Reference build never invents replacement text.",
            "Layout is identified before page text is flattened.",
            "High-risk disagreements require independent source-derived evidence when multiple families are available.",
            "Unresolved high-risk content blocks training acceptance.",
            "All localized decisions are preserved in evidence_ledger.jsonl.",
            "Network access is disabled for official reference runs unless the user explicitly changes settings.",
        ],
        "limitations": [
            "Object and quality confidence values are heuristic until calibrated on a human-verified layout benchmark.",
            "Exact GPU floating-point reproducibility can vary across hardware/runtime versions even with deterministic decoding.",
            "Complex image-only equations/tables may require a configured visual parser in Standard or Verified profiles.",
        ],
    }
    manifest_path = out_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2, ensure_ascii=False, sort_keys=True) + "\n", encoding="utf-8")

    output_files = [
        "review_dashboard.html",
        "audit.jsonl",
        "evidence_ledger.jsonl",
        "training.jsonl",
        "rejected.jsonl",
        "review_queue.jsonl",
        "duplicates.jsonl",
        "pretraining.jsonl",
        "corpus_report.json",
        "DATASET_CARD.md",
        "splits/train.jsonl",
        "splits/validation.jsonl",
        "splits/test.jsonl",
        "splits/document_assignments.jsonl",
        "unresolved.jsonl",
        "structured_blocks.jsonl",
        "document_structure.jsonl",
        "routing.jsonl",
        "engine_status.json",
    ]
    if settings.write_pretty_json:
        output_files.append("training.pretty.json")
    if settings.write_review_markdown:
        output_files.append("training_review.md")
    outputs = {name: _sha256_path(out_dir / name) for name in output_files}
    outputs["manifest_pre_hash_sha256"] = _sha256_path(manifest_path)
    (out_dir / "SHA256SUMS.json").write_text(json.dumps(outputs, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    integrity = validate_run(out_dir)
    (out_dir / "validation_report.json").write_text(
        json.dumps(integrity, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    if integrity["status"] != "PASS":
        raise RuntimeError("Dataset integrity validation failed: " + "; ".join(integrity["errors"]))
    return manifest
