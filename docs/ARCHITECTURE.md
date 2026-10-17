# VeriCorpus architecture

## Core principle

The unit of trust is an **evidence-backed document object or localized span**, not a flattened page string and not a model response.

## Processing stages

1. Source hash and immutable provenance
2. Page rendering / native PDF object inspection
3. **Document Structure Engine**
   - 1/2/3-column and mixed-layout detection
   - object identification (paragraphs, headings, figures, captions, tables, equations, references, headers/footers)
   - geometric reading-order graph
4. Complexity-aware routing
5. Parallel source-derived extraction families
6. Object/span normalization
7. Cross-engine sequence alignment and localized disagreement detection
8. Scientific-risk classification
9. Cross-family extractor consensus
10. Optional constrained visual adjudication that may select only existing source-derived candidates
11. Evidence-ledger write
12. Reconstruction or abstention
13. Multidimensional quality scoring
14. Training-readiness decision: accept / partial / reprocess / reject
15. Exact + near deduplication
16. Machine and human-readable exports
17. Manifest, hashes, and audit export

## Document Structure Engine

VeriCorpus identifies structure **before** flattening text. A page becomes a graph of typed objects with bounding boxes, column membership, confidence, and reading order. Tables and equations remain explicit objects instead of being silently merged into prose.

This is designed to prevent a common PDF failure mode: characters are extracted correctly while two- or three-column reading order is wrong.

## Trust policy

### Source-only pages
A strong born-digital source can be admitted when the DSE establishes coherent structure and reading order. The verification grade remains `source_plus_layout`; it is not mislabeled as cross-family verification.

### Cross-family pages
When multiple independent parser families are available, agreement is measured across families rather than engine names.

### High-risk spans
Numbers, equations, identifiers, code, scientific quantities, and biological sequences receive stricter handling. Generative completion is forbidden. Unresolved high-risk content blocks training acceptance.

### Abstention
`[UNRESOLVED]` is an internal marker. Unresolved content is excluded from training output, or the page is routed for reprocessing/rejected.

## Structured-source supervision

LaTeX, JATS XML, and DOCX submissions can be converted into object labels and aligned to a corresponding PDF. This provides a path to train/calibrate object detectors using journal submission packages rather than relying only on manual bounding-box annotation.
