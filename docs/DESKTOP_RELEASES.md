# VeriCorpus 0.2.0 — three desktop profiles

The GitHub Desktop upload workflow is explained in [`BUILD_ALL_THREE_WINDOWS.md`](../BUILD_ALL_THREE_WINDOWS.md).

Automatic Windows artifacts after pushing `main`/`master`:

- `VeriCorpus-0.2.0-Windows-x64-lite.zip`
- `VeriCorpus-0.2.0-Windows-x64-standard.zip`
- `VeriCorpus-0.2.0-Windows-x64-verified.zip`

The `Desktop bundles` workflow can additionally produce Linux x86_64 profiles with
matching `-lite`, `-standard`, and `-verified` names. On Linux, Tesseract must be installed separately.

**All deliverables are PyInstaller `onedir` packages.** Extract the entire archive;
run `VeriCorpus.exe` on Windows or `VeriCorpus` on Linux. Do not move the executable
away from its accompanying `_internal` directory. GUI defaults to the profile for
that bundle. Model weights are not redistributed.

Verified Windows bundles include Tesseract installed on the GitHub runner and
packaged with its adjacent `tessdata` and license files. Additional independent
OCR models remain optional separately hosted tools. System status reports actual
availability; Verified does not assert unanimous agreement or infallible OCR.

The Windows packaged smoke test is deliberately narrow: it tests a small born-digital
PDF in Lite processing mode, even for Standard and Verified binaries. Successful
builds do not prove advanced OCR correctness or benchmark coverage.
