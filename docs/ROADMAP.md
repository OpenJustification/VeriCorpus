# Roadmap

## 0.2 — Broader inputs and parser qualification

- EPUB, DOCX, HTML, TXT, and image ingestion
- canonical document/page/block/span representation
- normalized coordinate systems across engines
- qualification harness for tracked parsers such as OvisOCR2 and TeleOCR
- exact immutable model/runtime pins before an engine can become active
- better resumability and cache keys

## 0.3 — Specialist validators

- table-cell consensus
- mathematical OCR + symbolic equivalence checks
- identifier/DOI validation
- code parsing/linting where applicable
- scientific units and numerical consistency checks
- constrained local adjudicator qualification for Qwen/Nemotron targets

## 0.4 — Corpus-scale curation

- MinHash/LSH near-duplicate detection
- semantic deduplication
- PII policy modules
- benchmark-contamination checks
- scalable Parquet/Hugging Face exports

## 0.5 — Calibration and adversarial evaluation

- human gold-standard torture corpus
- false-accepted reconstruction rate
- reliability/calibration curves
- adversarial document and prompt-injection test suite
- engine-ablation benchmarks

## 1.0 criteria

VeriCorpus should not be called production-stable until confidence thresholds are benchmark-calibrated, high-risk false acceptance is quantified, active optional-engine integrations are continuously tested, and the universal representation supports the intended core document formats.
