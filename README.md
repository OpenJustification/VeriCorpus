# VeriCorpus

**Local, evidence-first preparation of messy PDFs for auditable LLM training data.**

> **Status: experimental alpha.** VeriCorpus 0.1.0 is designed to abstain when source evidence is insufficient. It is not a guarantee of perfectly reconstructed text, and no automated system can recover information absent from the source.

## Desktop release: unpack and use

The public release publishes graphical desktop bundles for both Windows and Linux:

- `VeriCorpus-0.1.0-Windows-x64-full.zip`
- `VeriCorpus-0.1.0-Windows-x64-lite.zip`
- `VeriCorpus-0.1.0-Linux-x86_64-full.tar.gz`
- `VeriCorpus-0.1.0-Linux-x86_64-lite.tar.gz`

**Windows:** extract the ZIP and double-click `VeriCorpus.exe`.

**Linux:** extract the archive and run `./VeriCorpus`.

These are conventional PyInstaller **onedir** bundles. They do not install Python, run pip, or self-extract when the user launches the application. See [`docs/DESKTOP_RELEASES.md`](docs/DESKTOP_RELEASES.md).

## Profiles

- **Lite** — native PDF text only. Smallest footprint; appropriate for clean born-digital PDFs.
- **Standard** — PyMuPDF + PaddleOCR-VL 1.6 + Docling when the Full bundle and local model assets are available.
- **Verified** — attempts every separately installed independent reference parser (including Tesseract, GLM-OCR, and olmOCR). Missing optional engines are recorded rather than silently substituted.

Qwen3.5-4B and NVIDIA Nemotron 3 Nano 4B remain **staged optional adjudicator targets**. They are not allowed to affect output in 0.1.0 until their constrained local runtimes pass the same integration-test bar as the parser stack.

## Why VeriCorpus exists

Most document pipelines optimize for extraction. VeriCorpus optimizes for **admissible training data**: source-derived text, cross-family evidence, provenance, reproducibility, and explicit rejection when evidence is weak. No proprietary API is required by the reference application.

## Tool selection

VeriCorpus does not claim that one parser is universally best. The project tracks current independent document-parsing benchmarks, but a public default must also satisfy local/offline execution, clear licensing, reproducibility, mature integration, and packaged-platform tests. See [`docs/TOOL_SELECTION.md`](docs/TOOL_SELECTION.md).

## Safety contract

1. Original inputs are immutable and SHA-256 hashed.
2. Permanent engine-reputation bonuses are not used.
3. Local disagreement consensus must span at least two evidence families, not merely two engine names.
4. High-risk text is never repaired from linguistic plausibility alone.
5. The reference pipeline does not generate replacement text.
6. Unresolved content is removed from training output or the page is rejected.
7. Every localized decision is written to `evidence_ledger.jsonl`.
8. Network access is off by default after local models are cached.

## Developer installation

```bash
python -m pip install -e .
vericorpus-desktop
```

CLI use:

```bash
vericorpus prepare paper.pdf --out output --profile standard --online
# after model assets are cached:
vericorpus prepare paper.pdf --out output --profile standard
```

## Outputs

`training.jsonl`, `rejected.jsonl`, `audit.jsonl`, `evidence_ledger.jsonl`, `structured_blocks.jsonl`, `engine_status.json`, `manifest.json`, and `SHA256SUMS.json`. All JSONL records are stamped with the VeriCorpus schema and generator version.

## Reproducibility

Each run records input hashes, settings/hash, VeriCorpus/schema versions, Python/OS/architecture, installed package versions, deterministic seed/settings, model-lock information, engine availability, plugins, model/cache fingerprints, and output hashes. Desktop release archives include build inventories, checksums, and GitHub build-provenance attestations.

Exact GPU floating-point identity is not promised across different hardware/drivers. For strict experiments, use the same release artifact, cached model files/hashes, hardware class, and run settings. See [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md).

## Licensing

VeriCorpus is **GNU AGPL v3 or later (`AGPL-3.0-or-later`)**. Third-party software and model weights retain their own licenses. The official clean reference registry excludes proprietary APIs and models with non-approved custom licenses; optional integrations are clearly labeled and model weights are not redistributed by the project. See [`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md) and [`docs/LEGAL_AND_MODEL_POLICY.md`](docs/LEGAL_AND_MODEL_POLICY.md).

This repository is not legal advice and cannot make downstream document/model use legally risk-free. Users remain responsible for copyright, privacy, data-protection, export-control, and upstream model-license obligations.

## Release verification

The tagged release workflow blocks publication unless source tests pass and the packaged Windows/Linux desktop binaries pass their own PDF-to-training-data self-test. Windows artifacts are additionally scanned with Microsoft Defender and Linux artifacts with ClamAV. SHA-256 checksums and GitHub provenance are published alongside the archives.

## Development

```bash
python -m pip install -e ".[dev]"
python -m ruff check src tests scripts packaging
python -m pytest -q
python scripts/release_check.py
python scripts/license_check.py
python -m vericorpus.desktop --self-test
```

Contributions use the [Developer Certificate of Origin](DCO.md). See [CONTRIBUTING.md](CONTRIBUTING.md), [GOVERNANCE.md](GOVERNANCE.md), and [AI_POLICY.md](AI_POLICY.md).
