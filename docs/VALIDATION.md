# VeriCorpus 0.2.0-alpha validation snapshot

Validation prepared on **2026-10-17** for the training-readiness architecture.

## Local validation

The source tree is checked for:

- Python compilation;
- the full pytest suite;
- synthetic PDF → Lite pipeline → `training.jsonl` self-test;
- preservation of scientific quantities such as `0.05 mg/mL` and `30 min`;
- two-column and three-column detection plus deterministic reading-order reconstruction;
- object bounding-box output;
- LaTeX structured-source object extraction/alignment;
- human-readable `training.pretty.json` and `training_review.md` generation;
- numeric conflict abstention and cross-family consensus;
- model/cache lock verification;
- release metadata and license-policy checks;
- wheel construction with local build isolation disabled when the test environment is offline.

The current local suite contains **40 passing tests** in the prepared source tree. The object/quality scores are still heuristic and require benchmark calibration before stable 1.0.

## Real scientific-PDF regression

A 9-page two-column materials-science paper was used as a regression input. The 0.1 native flattening interleaved columns and flattened adjacent tables/equations. The 0.2 DSE identifies the paper as multi-column/mixed, reconstructs column flow, preserves tables and equations as explicit objects, normalizes detached accents such as `Gonz´alez → González`, and produces human-readable review output.

This regression is a development validation case, not a claim that every scientific PDF is solved.

## Desktop release design

Release binaries remain conventional PyInstaller **onedir** applications. Four artifacts are built from the same tag: Windows x64 Lite/Standard/Verified and Linux x86_64 Lite/Standard/Verified. Native GitHub-hosted runners execute the packaged `--self-test`; Windows additionally passes Microsoft Defender and Linux passes ClamAV before release creation.

## Maturity

This remains an alpha. A public human-verified benchmark covering reading order, object detection, tables, equations, numeric fidelity, Unicode fidelity, hallucination/abstention, and training-ready precision is required before 1.0.

## v0.3 additions

EPUB spine/table and image abstention tests, record-level dedupe lineage, deterministic document-disjoint splits, tamper-detecting checksums, and offline interactive review dashboard export.
