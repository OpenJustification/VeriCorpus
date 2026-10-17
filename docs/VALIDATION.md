# VeriCorpus 0.1.0 validation snapshot

Validation prepared on **2026-10-17** for the first public alpha release candidate.

## Local source validation

The release source tree is checked for:

- Python compilation;
- the full pytest suite;
- a real synthetic scientific PDF → Lite pipeline → `training.jsonl` self-test;
- preservation of `0.05 mg/mL` and `30 min` in the self-test;
- Lite clean-born-digital acceptance;
- numeric conflict abstention;
- cross-family consensus and same-family false-consensus rejection;
- reversible offline/online model policy;
- cache fingerprint/model-lock verification;
- release metadata and reference-license policy;
- YAML parsing for all GitHub workflows;
- wheel/source-distribution construction and metadata inspection.

## Desktop release design

The old browser/embedded-runtime bootstrap has been removed from the public desktop path. Release binaries are conventional PyInstaller **onedir** applications with a Tk desktop UI.

Four release artifacts are built from the same tag:

- Windows x64 Lite
- Windows x64 Full
- Linux x86_64 Lite
- Linux x86_64 Full

The Lite package is the smallest fully offline born-digital PDF path. The Full package additionally contains the Python software dependencies required for PaddleOCR and Docling. Third-party model weights are not redistributed.

## GitHub release gates

The Windows/Linux binaries themselves cannot both be executed in this preparation container, so GitHub-hosted native runners are mandatory publication gates. Each platform job must:

1. install the pinned direct bundle dependencies;
2. build the onedir desktop application using PyInstaller 6.22.3;
3. execute the packaged application with `--self-test`;
4. verify that the packaged binary produces a successful real PDF-to-JSONL result;
5. include package/install/build inventories and the project licenses;
6. scan Windows output with Microsoft Defender or Linux output with ClamAV;
7. generate a SHA-256 checksum for the final archive;
8. generate GitHub build-provenance attestation.

The GitHub Release job depends on every desktop matrix job. A failed Windows, Linux, Lite, Full, self-test, or malware scan prevents the release from being created.

## Packaging/security rationale

VeriCorpus deliberately avoids a self-downloading/self-extracting custom bootstrap executable. This reduces antivirus heuristics and makes the shipped runtime files inspectable. The first alpha may remain unsigned unless the maintainer configures a trusted Windows code-signing certificate; users should download release assets only from the official GitHub release and verify checksum/provenance.

## Reproducibility

Every VeriCorpus data-processing run records source hashes, settings, package/runtime versions, model/cache fingerprints, engine availability, and output hashes. Desktop builds additionally include `BUILD_INFO.json`, `python-freeze.txt`, `pip-install-report.json`, and a third-party license inventory.

A model-locked run is not considered locked merely because a lock file exists: local cache hashes must match while offline before and after processing.

## Maturity

This is an **alpha validation snapshot**, not a claim of corpus-wide OCR accuracy, bit-identical GPU execution across hardware, or universal parser superiority. A public human-verified benchmark/calibration study remains required before 1.0.
