# VeriCorpus v0.2.0-alpha — Corpus integrity and reproducible training exports

Adds a strict admission policy (accepted only), deterministic source-derived text exports,
document-disjoint train/validation/test splits, scalable indexed near-duplicate detection,
traceable duplicate removals, integrity verification, an automated corpus report,
a human-readable dataset card, EPUB XHTML source import, and an offline
interactive review dashboard exporting separate human feedback. Existing PDF layout/object identification, local
OCR adapters, Tk desktop UI and Windows/Linux build workflows are preserved.

**Maturity:** Experimental. Scientific correctness, OCR accuracy and object fidelity
require domain-specific gold-standard benchmarks. Qwen3.5-4B and Nemotron 3 Nano
4B remain optional staged adjudicator targets, not integrated into this release.
Windows/Linux binaries are created by native CI runners; source archive is not a binary.
Rights notices are not technical quality rejection criteria.
