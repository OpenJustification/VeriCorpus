# VeriCorpus 0.1.0-alpha — First Public Release

VeriCorpus 0.1.0 is the first public alpha of a local, evidence-first pipeline for preparing digital and scanned PDFs for auditable LLM-training datasets while preferring abstention over unsupported reconstruction.

## Desktop applications

The release workflow builds four graphical artifacts from the tagged source:

- Windows x64 Lite
- Windows x64 Full
- Linux x86_64 Lite
- Linux x86_64 Full

Windows users extract the release ZIP and launch `VeriCorpus.exe`. Linux users extract the tarball and launch `./VeriCorpus`.

The desktop applications are PyInstaller **onedir** bundles, not self-installing or self-extracting bootstraps. The application does not download Python or execute pip at startup.

## Processing profiles

- **Lite:** PyMuPDF native text for clean born-digital PDFs.
- **Standard:** PyMuPDF + PaddleOCR-VL 1.6 + Docling when the Full bundle/model assets are available.
- **Verified:** Standard plus separately available independent witnesses such as Tesseract, locally self-hosted GLM-OCR, and local olmOCR.

Qwen3.5-4B and NVIDIA Nemotron 3 Nano 4B remain staged adjudicator targets; they cannot influence output in this release.

## Reliability principles

- strong native PDF text is accepted as direct source evidence;
- OCR consensus must span independent evidence families;
- high-risk values are never reconstructed from linguistic plausibility alone;
- the reference pipeline does not author replacement text;
- unresolved material is rejected rather than guessed;
- every run records provenance, settings, environment/model-lock information, and output hashes.

## Release security and provenance

Desktop release jobs execute the packaged binary's `--self-test` before archiving. Windows bundles must pass a Microsoft Defender scan, Linux bundles must pass a ClamAV scan, and every archive receives a SHA-256 checksum and GitHub build-provenance attestation. The alpha is not code-signed unless the maintainer separately configures a trusted signing certificate.

## Licensing

VeriCorpus is released under **AGPL-3.0-or-later**. Third-party software and model weights retain their own licenses and are not relicensed by VeriCorpus. Model weights are not redistributed by the reference release.

## Maturity

This is an alpha release, not a claim of production-stable OCR accuracy. A public human-verified benchmark/calibration suite remains required before 1.0.
