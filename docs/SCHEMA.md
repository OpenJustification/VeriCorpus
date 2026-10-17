# VeriCorpus output schema

Current schema version: **3.0**

Every JSONL row is stamped with:

```json
{
  "vericorpus_schema": "2.0",
  "generator": "vericorpus",
  "generator_version": "0.2.0a1"
}
```

## Training rows

`training.jsonl` keeps a simple `text` field for model-training compatibility while adding structured quality and provenance:

```json
{
  "document_id": "sha256...",
  "source_file": "paper.pdf",
  "page_number": 5,
  "text": "...",
  "quality": 0.94,
  "quality_dimensions": {
    "text_fidelity": 0.99,
    "reading_order": 0.96,
    "layout": 0.95,
    "tables": 0.91,
    "equations": 0.90,
    "unicode": 1.0,
    "numeric_fidelity": 0.90,
    "structure": 0.95,
    "overall": 0.94,
    "calibration": "heuristic"
  },
  "training_readiness": {
    "status": "accepted",
    "score": 0.94,
    "blocking_issues": [],
    "warnings": ["quality_scores_are_heuristic_not_benchmark_calibrated"],
    "verification_grade": "source_plus_layout"
  },
  "layout": {
    "layout_type": "multi_column",
    "column_count": 2,
    "complexity_score": 0.63,
    "complexity_reasons": ["2_column_layout", "tables:2", "equations:1"]
  },
  "provenance": {}
}
```

## Structure outputs

- `document_structure.jsonl`: page object graph, bounding boxes, object types, columns, and reading order.
- `structured_blocks.jsonl`: source-derived tables, equations, figures/captions, and other special objects.
- `routing.jsonl`: autonomous page-routing decisions.
- `evidence_ledger.jsonl`: localized disagreement decisions.
- `unresolved.jsonl`: unresolved evidence that must not silently enter training output.
- `training.pretty.json`: indented human-readable form of accepted training rows.
- `training_review.md`: human-readable page review.

`manifest.json` records source hashes, settings, runtime/package fingerprint, deterministic settings, model/cache fingerprints, engine availability, and output hashes.

Schema 2.0 intentionally separates **extraction quality**, **document structure**, and **training readiness**.

### v3 corpus exports

- `training.jsonl`: accepted, deduplicated source text, stable `record_id`, `text_sha256`, quality and provenance.
- `pretraining.jsonl`: source text only (`text` field).
- `review_queue.jsonl`: partially ready units, excluded from strict training.
- `duplicates.jsonl`: exact/near removal with kept and removed IDs.
- `corpus_report.json`: layout/object/quality statistics.
- `splits/*.jsonl`: document-hash-based train/validation/test; at least 10 accepted documents required for holdouts.
- `validation_report.json`: after-run integrity findings. Generated after checksums, so is not itself included in `SHA256SUMS.json`.

For EPUB, `page_number` denotes XHTML spine sequence, not a physical page.
EPUB objects report `geometry: not_applicable`, and no PDF-layout coordinates
are fabricated. Feedback exported by `review_dashboard.html` is proposed
annotation data and must be reviewed before use, never auto-merged.
