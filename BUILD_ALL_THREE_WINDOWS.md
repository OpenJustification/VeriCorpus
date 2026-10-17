# VeriCorpus 0.2.0 — build Lite, Standard, and Verified Windows EXE files

**This ZIP contains source code, not prebuilt EXEs.** GitHub Actions builds three separate onedir EXE packages when you commit and push the repository using GitHub Desktop.

## Upload/update using GitHub Desktop

1. Extract this entire ZIP. It contains hidden `.github` and `.gitignore` files. Do not copy the ZIP itself into the repository; copy its **contents**, preserving subfolders.
2. In GitHub Desktop, select your existing VeriCorpus repository. Open **Repository → Show in Explorer**.
3. Back up local changes. Copy/merge the extracted folder's **contents** into the repository root, replacing matching project files. Keep the repository's existing hidden `.git` directory intact; **never** replace/delete `.git`.
4. Return to GitHub Desktop, review **Changes**, commit (e.g. `Build VeriCorpus 0.2.0 in three profiles`), then **Push origin**.
5. On GitHub, open **Actions → Windows EXE - Lite Standard Verified**. A push to `main`/`master` triggers it automatically. Or choose **Run workflow**.
6. After each of the three build jobs passes, open that run's **Artifacts** and download the named Lite, Standard, and Verified ZIP artifacts.
7. GitHub artifact downloads are a ZIP containing the distributable ZIP and its `.sha256` file. Extract the outer ZIP first, then extract the inner `VeriCorpus-0.2.0-Windows-x64-<profile>.zip` into a writable folder. Run `VeriCorpus.exe` there. Preserve the entire directory, not only the EXE.

## What each package contains

| Profile | Bundled software | External requirements | Default GUI profile |
| --- | --- | --- | --- |
| Lite | PyMuPDF, Document Structure Engine, base Python dependencies | None for digital PDFs | Lite |
| Standard | Lite + PaddleOCR-VL/Docling Python dependencies | OCR model weights may need one-time downloading | Standard |
| Verified | Standard + independent Tesseract executable and English traineddata | GLM-OCR/olmOCR are optional local services and **not** bundled; model weights may need downloading | Verified |

**Model weights are not included** in the three GitHub artifacts. Standard and Verified depend on upstream asset availability, disk/RAM, and runtime compatibility. They are not guaranteed to process every PDF.

Verified starts with the independent Tesseract witness packaged from the Windows runner. It does *not* mean every verification model is installed or that all outputs have been independently cross-checked: see the per-page evidence ledger and system status. An automatically verified output can still contain errors.

## Release checks and limitations

Each Windows job installs profile dependencies, runs source tests, builds the GUI via PyInstaller, executes the compiled EXE's PDF smoke test, confirms the correct bundled profile, scans with Microsoft Defender, and uploads a ZIP + SHA-256 checksum. Verified additionally checks that packaged Tesseract launches and is discoverable by the EXE. Binary packaging and OCR inference have **not** been tested in this chat's Linux environment; check the GitHub run before distributing.

The `desktop-build.yml` workflow also provides manual Linux and Windows builds for all three profiles. The `release.yml` workflow is reserved for tagged pre-releases, not ordinary GitHub Desktop pushes.
