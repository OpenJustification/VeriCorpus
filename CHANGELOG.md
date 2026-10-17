# Changelog

## 0.1.0 — first public alpha

- First public VeriCorpus release.
- Added graphical **Windows x64 and Linux x86_64 desktop bundles** in Lite and Full variants.
- Replaced the earlier self-installing/browser bootstrap design with conventional PyInstaller **onedir** desktop applications; the shipped app does not install Python, run pip, or self-extract at launch.
- Added `lite`, `standard`, and `verified` processing profiles.
- Fixed Lite mode so strong born-digital PDF text can be accepted as direct source evidence without requiring a redundant OCR engine.
- Standard Full desktop stack uses the actually integrated PyMuPDF, PaddleOCR-VL 1.6, and Docling paths.
- Verified profile can add Tesseract, locally self-hosted GLM-OCR, and local olmOCR when separately installed.
- Added cross-family extraction consensus so correlated wrappers do not count as independent witnesses.
- Added relocatable local caches/models/data under `VeriCorpusData` beside packaged desktop binaries.
- Added staged catalog entries for Qwen3.5-4B and NVIDIA Nemotron 3 Nano 4B without presenting untested adjudicator runtimes as active.
- Added a dated OmniDocBench tool-selection snapshot; TeleOCR and OvisOCR2 are tracked but not active because public-release defaults also require reproducibility, security review, maintainability, and packaged-platform integration tests.
- Added immutable input/output hashes, model-lock support, deterministic settings, engine status, and reproducibility manifests.
- Added AGPL-3.0-or-later licensing, DCO contribution policy, governance, AI contribution policy, and third-party license inventory.
- Added release-gated packaged-binary self-tests, Microsoft Defender/ClamAV scans, SHA-256 checksums, package/build inventories, and GitHub build-provenance attestations.
- Public output schema starts at **1.0**.
