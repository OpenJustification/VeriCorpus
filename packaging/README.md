# Desktop packaging — VeriCorpus 0.2.0 (experimental alpha)

Build three PyInstaller onedir bundles with `python scripts/build_desktop.py --flavor lite`,
`--flavor standard`, or `--flavor verified`. The executable always has the name
`VeriCorpus.exe` on Windows; ZIP artifacts have distinct profile names.

- **Lite:** native digital PDF extraction and Document Structure Engine.
- **Standard:** Lite plus the PaddleOCR-VL and Docling Python packages. Model weights are not bundled.
- **Verified:** Standard plus separately packaged Tesseract (Windows Actions builds only).
  GLM-OCR and olmOCR are optional external local services, not bundled.

The authoritative workflow is `.github/workflows/windows-exe.yml` (three automatic Windows
jobs). Advanced model startup may need additional downloads and runtime setup.
The existing `packaging/vericorpus.spec` is a developer fallback; the workflow uses
`scripts/build_desktop.py` with PyInstaller command-line options.

Tesseract and downloaded model assets keep their upstream licenses. The Windows Verified workflow refuses to package a Tesseract installation if it cannot find license notice files.
