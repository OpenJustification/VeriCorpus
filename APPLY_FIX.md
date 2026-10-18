# VeriCorpus 0.2.0 — dependency pin fix

## Confirmed cause
The uploaded GitHub Actions ZIP from commit `b3953ab41f2565f75e5dfce6567dc45d83a1f8e3` contains six desktop jobs, all failing during pip dependency installation because `pytesseract==0.2.13` does not exist on PyPI. The logs explicitly list `0.3.13` among available versions. No PyInstaller step was reached.

## Fix
- `packaging/requirements-bundle-lite.txt`: pin `pytesseract==0.3.13`.
- `packaging/requirements-bundle-full.txt`: pin `pytesseract==0.3.13`.

GitHub `main` already appeared to have the corrected Lite file when checked; the Full file still had the incorrect version. Both files are included to ensure local copies agree. No unrelated pins or workflow files have been changed.

## GitHub Desktop
1. Extract this archive.
2. Copy its `packaging` folder **contents** into your cloned VeriCorpus repository's `packaging` folder. Replace files as requested.
3. In GitHub Desktop, confirm the expected changes. The Lite file may show no change if already corrected; the Full file should show the version correction.
4. Commit: `Fix pytesseract dependency pin in desktop bundles`.
5. Click `Push origin`.
6. Open GitHub → Actions → Desktop bundles → Run workflow (`main`). Run a **new workflow** after pushing, not simply re-run old jobs on an older commit.
7. Check which new stages pass. This fixes the known missing-package error, but later issues could still be exposed after dependency installation.

The Node.js 20 deprecation warnings in the uploaded logs were **not** the source of this failure.
