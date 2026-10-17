# Changelog

## 0.2.0a1 — consolidated three-profile build (experimental alpha)

- Preserved scientific document-structure detection, equation/table routing, and source-only extraction.
- Included corpus-integrity exports (source-only pretraining, structured evidence ledgers, review queues, deterministic document-disjoint splits, hash checks and an offline HTML review dashboard).
- Added three distinct Windows x64 PyInstaller onedir artifacts: Lite, Standard, Verified.
- Bundles now have a profile marker; desktop GUI defaults to the matching profile and disables unsupported selections.
- Windows Verified builds stage an independent Tesseract OCR witness and English language data; other optional OCR engines still require separate installation.
- Added per-artifact EXE smoke testing, bundled-profile verification, Windows Defender scans and SHA-256 checksums in the push-triggered GitHub Actions workflow.
- This release retains output schema **3.0** to preserve the richer structured training-export fields.

## 0.1.0 — first public alpha

- Added conservative PDF extraction and evidence/provenance ledgers.
- Introduced source verification, local profiles, desktop packaging and AGPL licensing.
