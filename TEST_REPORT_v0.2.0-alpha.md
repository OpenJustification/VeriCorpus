# VeriCorpus 0.2.0-alpha — validation summary

Date: 2026-10-17

## Completed locally

- **40/40 pytest tests passed** (one harmless warning in a test that intentionally overwrites a ZIP member).
- Python source compilation and the desktop source self-test passed (reported version `0.2.0a1`, schema `3.0`).
- Source release metadata consistency check passed.
- Wheel `vericorpus-0.2.0a1-py3-none-any.whl` built and imported from a separate installation directory.
- Dataset checksums/record ID/reproducible split checks passed on a real 9-page scientific materials-science PDF.
- Native PDF regression: **9 pages processed; 9 admitted; 0 held for review; 0 rejected** in Lite mode. Two-column, table and equation objects appear on page 5.
- Synthetic two- and three-column detection tests passed; EPUB XHTML spine reading, semantic HTML tables, image interpretation abstention and unsafe archive path tests passed.
- Offline HTML dashboard JavaScript **syntax** passed `node --check`.

## Not validated here

- Windows `.exe` and Linux portable PyInstaller binaries are **not** built in this environment. GitHub Actions workflows target native OS runners and include packaged self-tests and security scans.
- The HTML dashboard's interactive behavior was **not** browser-executed in this environment, because local Chromium navigation is administratively blocked; the source JavaScript passed syntax checking.
- PaddleOCR-VL, Docling, GLM-OCR, olmOCR and optional model backends were not downloaded and benchmarked as part of this update.
- Qwen3.5-4B and Nemotron 3 Nano 4B are intentionally **not** described as active adjudicators.
- Heuristic quality scores are not benchmark-calibrated estimates of scientific truth, and admitted native PDF text is not independent fact-checking.
- EPUB images are identified and source alt text is recorded as metadata, but visual contents are not interpreted by the XHTML extractor.

## Recommended next release gate

Validate 100+ heterogeneous gold-labeled scientific documents, including scanned PDFs, complex vector figures, scientific multi-row tables, MathML/display equations, complex 3-column layouts, missing glyphs, and publisher XML submissions. Measure precision, recall, reading-order accuracy, exact numeric fidelity, abstention calibration, and generated training-set contamination before declaring 1.0 stable.
