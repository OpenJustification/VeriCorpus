See **QUICKSTART.md** for source launchers and instructions on producing Windows/Linux binaries.

# VeriCorpus

**Autonomous, evidence-first preparation of PDFs for reproducible LLM training data.**

> **Status: experimental alpha (Python package version `0.2.0a1`, corpus schema `3.0`).** VeriCorpus 0.2.0-alpha is designed to detect document structure, route difficult pages to stronger parsers when available, verify source-derived candidates, and abstain when evidence is insufficient. It is not a guarantee of perfectly reconstructed text, and no automated system can recover information absent from the source.

## Processing architecture

The central rule is now:

**Identify structure → extract → verify → score training readiness → accept/reprocess/abstain.**

A native PDF text layer is no longer treated as proof that a page is training-ready.

The new **Document Structure Engine (DSE)** detects 1/2/3-column and mixed layouts and identifies objects such as figures, captions, tables, equations, headings, references, headers, and footers before text is flattened. See [`docs/OBJECT_IDENTIFICATION.md`](docs/OBJECT_IDENTIFICATION.md).

## Desktop bundles

The workflows produce the following artifacts after a successful GitHub Actions build (no compiled EXE is inside this source ZIP):

- `VeriCorpus-0.2.0-Windows-x64-lite.zip`
- `VeriCorpus-0.2.0-Windows-x64-standard.zip`
- `VeriCorpus-0.2.0-Windows-x64-verified.zip`
- `VeriCorpus-0.2.0-Linux-x86_64-lite.tar.gz`
- `VeriCorpus-0.2.0-Linux-x86_64-standard.tar.gz`
- `VeriCorpus-0.2.0-Linux-x86_64-verified.tar.gz`

**GitHub Desktop users:** see [BUILD_ALL_THREE_WINDOWS.md](BUILD_ALL_THREE_WINDOWS.md). The push-to-main workflow generates three downloadable Windows EXE ZIP artifacts.

Windows users extract the ZIP and launch `VeriCorpus.exe`. Linux users extract the archive and run `./VeriCorpus`. The bundles are conventional PyInstaller **onedir** applications; they do not install Python or self-extract at launch.

## Profiles

- **Lite** — PyMuPDF native source evidence + DSE object/layout reconstruction. Fastest and fully offline.
- **Standard** — autonomous routing plus PaddleOCR-VL 1.6 and Docling when installed/cached; Tesseract can be invoked automatically on complex pages when available.
- **Verified** — attempts all separately installed independent reference parsers, including Tesseract, local GLM-OCR, and local olmOCR, and records cross-family verification.

Qwen3.5-4B and NVIDIA Nemotron 3 Nano 4B remain staged optional adjudicator targets until their constrained runtimes pass the same integration-test bar as the parser stack.

## Core reliability contract

1. Original inputs are immutable and SHA-256 hashed.
2. Page structure is identified before training text is flattened.
3. Permanent engine-reputation bonuses are not used.
4. Consensus must span independent evidence families.
5. High-risk scientific content is never repaired from linguistic plausibility alone.
6. The reference pipeline does not generate replacement text.
7. Unresolved high-risk content blocks training acceptance.
8. Every localized decision is preserved in the evidence ledger.
9. Quality is multidimensional: text, layout, reading order, tables, equations, Unicode, numeric fidelity, and structure are scored separately.
10. Network access is off by default after local model assets are cached.

## CLI

```bash
python -m pip install -e .

vericorpus prepare paper.pdf --out output --profile lite
vericorpus prepare paper.pdf --out output --profile standard --online
vericorpus inspect-layout paper.pdf --page 5
vericorpus groundtruth manuscript.tex rendered.pdf --out labels.jsonl
```

## Outputs

Interactive (local-only):

- `review_dashboard.html` — open in a browser to inspect extracted pages and objects, flag numeric/table/equation problems, and export traceable `vericorpus_feedback.json` suggestions without silently modifying training data.

Machine-oriented:

- `training.jsonl`
- `rejected.jsonl`
- `unresolved.jsonl`
- `audit.jsonl`
- `evidence_ledger.jsonl`
- `structured_blocks.jsonl`
- `document_structure.jsonl`
- `routing.jsonl`
- `manifest.json`
- `SHA256SUMS.json`

Human-oriented:

- `training.pretty.json`
- `training_review.md`

## Why this architecture

A two-column scientific PDF can have nearly perfect character extraction but the wrong reading order. A table can contain correct tokens but incorrect row/column associations. An equation can be flattened into surrounding prose. VeriCorpus therefore treats **training readiness** as a separate problem from OCR/text extraction.

## Structured-submission benchmark path

VeriCorpus can derive object labels from LaTeX, JATS XML, and DOCX sources and align text anchors to a rendered PDF. This makes structured journal submission packages useful for building object/layout datasets for column detection, figures, tables, equations, and reading-order evaluation.

## Reproducibility

Each run records source hashes, settings/hash, VeriCorpus/schema versions, Python/OS/architecture, installed package versions, deterministic seed/settings, model-lock information, engine availability, plugins, model/cache fingerprints, and output hashes. Exact GPU floating-point identity is not promised across different hardware/drivers.

## Licensing

VeriCorpus is **GNU AGPL v3 or later (`AGPL-3.0-or-later`)**. Third-party software and model weights retain their own licenses. Model weights are not redistributed by the reference release.

## Development

```bash
python -m pip install -e ".[dev]"
python -m ruff check src tests scripts packaging
python -m pytest -q
python scripts/release_check.py
python scripts/license_check.py
python -m vericorpus.desktop --self-test
```

Contributions use the [Developer Certificate of Origin](DCO.md).

## v0.3 strict corpus exports

`training.jsonl` retains page-level source provenance; `pretraining.jsonl` contains
only `{"text": "..."}` records for direct trainer loading. Uncertain **partial** pages
are kept in `review_queue.jsonl` and **never** silently included in training.
`duplicates.jsonl` explains removals and their matching source records.
`corpus_report.json` and `DATASET_CARD.md` document statistics and limitations.
The `splits/` directory contains deterministic document-disjoint JSONL splits.
Runs with fewer than 10 accepted documents use the train split only.

Verify the resulting data (including checksums and record IDs) before uploading:

```bash
vericorpus verify-output path/to/output
```

Note: the ordinary `training.jsonl` is **not** instruction-tuning Q&A. No generated
answers are presented as factual evidence; only original source-derived text is admitted.

## EPUB import

Local EPUB 2/3 documents are processed in original XHTML spine order. Section
numbers replace physical PDF page numbers; EPUB has no inherent physical page
coordinates. HTML tables and source MathML are preserved as structured objects;
images are recorded as figures but **not** hallucinated into visual descriptions.
Unsafe/malformed EPUBs are rejected rather than silently guessed.

```bash
vericorpus prepare book.epub --out epub-output --profile lite
```
