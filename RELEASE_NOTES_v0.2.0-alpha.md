# VeriCorpus 0.2.0-alpha — Training-Readiness Architecture

VeriCorpus 0.2.0-alpha changes the core pipeline from **extract-first** to **structure-first** document processing.

## Major changes

- Added the **Document Structure Engine (DSE)**. Each page is analyzed before text is flattened.
- Detects 1-, 2-, and 3-column layouts plus mixed full-width/column layouts.
- Identifies semantic page objects including headings, paragraphs, figures, figure captions, tables, equations, references, headers, footers, and page numbers.
- Reconstructs reading order from page geometry before creating training text.
- Adds deterministic Unicode/diacritic and soft-hyphen cleanup for born-digital PDFs.
- Adds source-derived table grouping and row/cell reconstruction from PDF word geometry.
- Adds equation-region grouping so mathematical fragments are isolated from surrounding prose.
- Adds autonomous page routing: simple pages stay on the native path; complex pages can escalate to the layout/OCR engines allowed by the selected profile.
- Adds multidimensional quality scoring for text fidelity, reading order, layout, tables, equations, Unicode, numeric fidelity, and structure.
- Adds explicit `training_readiness` status and verification grade rather than equating a native text layer with training quality.
- Adds `document_structure.jsonl`, `routing.jsonl`, `unresolved.jsonl`, `training.pretty.json`, and `training_review.md`.
- Adds `vericorpus inspect-layout` for page-level object inspection.
- Adds `vericorpus groundtruth` to derive object labels from LaTeX, JATS XML, or DOCX submissions and align text anchors to a corresponding PDF. This supports building layout/object datasets from structured journal submissions such as MDPI-style source packages.

## Reliability principles

VeriCorpus never uses linguistic plausibility alone to invent high-risk scientific values. Complex pages can be escalated to independent parsers. When evidence is insufficient, the training-readiness layer can request reprocessing or abstain.

Quality scores in this alpha are **heuristic**, not yet benchmark-calibrated. A human-verified object/layout benchmark remains required before stable 1.0.

## Desktop bundles

The workflows build Windows x64 and Linux x86_64 Lite/Standard/Verified PyInstaller `onedir` bundles. Windows packaged self-tests use synchronous GUI-process waiting, and release jobs retain Defender/ClamAV gates and build provenance.


## Additional corpus integrity features included in this source snapshot


Adds a strict admission policy (accepted only), deterministic source-derived text exports,
document-disjoint train/validation/test splits, scalable indexed near-duplicate detection,
traceable duplicate removals, integrity verification, an automated corpus report,
a human-readable dataset card, EPUB XHTML source import, and an offline
interactive review dashboard exporting separate human feedback. Existing PDF layout/object identification, local
OCR adapters, Tk desktop UI and Windows/Linux build workflows are preserved.

**Maturity:** Experimental. Scientific correctness, OCR accuracy and object fidelity
require domain-specific gold-standard benchmarks. Qwen3.5-4B and Nemotron 3 Nano
4B remain optional staged adjudicator targets, not integrated into this release.
Windows/Linux binaries are created by native CI runners; source archive is not a binary.
Rights notices are not technical quality rejection criteria.
