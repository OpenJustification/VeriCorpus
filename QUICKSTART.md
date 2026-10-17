# VeriCorpus 0.2.0-alpha — Quick start

## Native Windows EXE / Linux binary (GitHub Actions builds)

Commit this source tree to GitHub; the included workflows under
`.github/workflows/` build portable GUI bundles on native Windows and Linux
runners. Download your chosen `VeriCorpus-0.2.0-alpha-Windows-x64-lite.zip` or
`VeriCorpus-0.2.0-alpha-Linux-x86_64-lite.tar.gz` from the successful build
artifacts. Those packages are **not inside this source archive**; they must be
built and tested on the target OS.

## Run from the source ZIP right away

On Windows with Python 3.11+ installed, double-click `START_WINDOWS.cmd`.
On Linux with Python and venv available, run `./START_LINUX.sh`.
The launchers create a project-local `.venv`, install package dependencies,
and start the Tk desktop GUI. Installation may require internet access;
Lite PDF processing itself does not.

CLI usage:

```sh
python -m pip install -e .
python -m vericorpus.cli prepare paper.pdf --profile lite --out result
python -m vericorpus.cli prepare book.epub --profile lite --out epub-result
python -m vericorpus.cli verify-output result
```

**Inspect data**: Open `result/review_dashboard.html` locally in a normal
browser, examine the original PDF beside the extracted text, and export local
corrections. Read `result/DATASET_CARD.md` and `result/validation_report.json`.

**For trainers**: `pretraining.jsonl` is one `text` field per admitted record;
`training.jsonl` has richer provenance, page/readiness and confidence labels.

**Limitations**: The scores are heuristic and not calibrated to a published
human-labeled OCR/layout accuracy benchmark. Standard/Verified performance
depends on additional local OCR models and runtime hardware. Qwen3.5-4B and
Nemotron 3 Nano 4B are not yet integrated into the released runtime.
