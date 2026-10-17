# Tool selection policy

Snapshot date: **2026-10-17**.

VeriCorpus does **not** claim that a single parser is universally best. The first public release chooses tools using five criteria together: independent benchmark quality, local/offline execution, license clarity, deterministic/reproducible operation, and practical Windows portability.

## Current document-parsing benchmark snapshot

The OmniDocBench maintainers currently report, on `v1.6_full`, TeleOCR at 96.91 overall, OvisOCR2 at 96.47, PaddleOCR-VL 1.6 at 96.34, and GLM-OCR at 95.22. The machine-readable snapshot is in `models/benchmark-snapshot.json`.

Source: <https://github.com/opendatalab/OmniDocBench>

The leaderboard is a useful external benchmark, not an oracle. An independent September 2026 reproduction issue reported 95.25 for its PaddleOCR-VL-1.6 orchestration versus the maintainer table's 96.34 and documented a formula-score discrepancy. VeriCorpus therefore treats benchmark rank as one input and intends to maintain its own frozen, reproducible torture corpus before 1.0.

## Why PaddleOCR-VL 1.6 is the desktop default

TeleOCR has the highest current score in that benchmark, but its current upstream inference path relies on custom model code and a runtime stack that is less suitable for a unpack-and-use Windows desktop release. OvisOCR2 is a particularly attractive compact candidate and is tracked for a future integration pass.

PaddleOCR-VL 1.6 remains in the top tier while providing a mature, license-clear Apache-2.0 pipeline that can cache its models locally and integrate cleanly with the desktop application. It is therefore the current default **for this release**, not a claim that it is permanently the highest-scoring model.

## Other selected tools

- **PyMuPDF**: direct source text and geometry for born-digital PDFs. Direct embedded text should outrank visual reconstruction when it is clean.
- **Docling**: structured document conversion/representation and an independent implementation path.
- **Tesseract**: classical OCR witness with very different failure modes from modern VLMs.
- **GLM-OCR**: optional local independent neural OCR family.
- **olmOCR**: optional PDF linearization specifically oriented toward LLM-corpus preparation.
- **Qwen3.5-4B**: retained as the planned local multimodal adjudicator, but it is not allowed to author replacement text and is not advertised as active until its constrained runtime passes integration tests.
- **NVIDIA Nemotron 3 Nano 4B**: retained as an optional future text-side second opinion. It is outside the clean reference profile because its model uses NVIDIA's separate model license.

## Release rule

A newly released model does not become a VeriCorpus default solely because it wins one leaderboard. Before activation it must pass: license review, pinned-revision verification, offline inference tests, reproducibility tests, adversarial extraction tests, and the packaged desktop build smoke test.
