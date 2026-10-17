# VeriCorpus architecture

## Core principle

The unit of trust is not a page and not a model response. It is an **evidence-backed localized span**.

## Processing stages

1. Source hash and immutable provenance
2. Page rendering
3. Parallel extraction engines
4. Word/span normalization
5. Anchor selection
6. Cross-engine sequence alignment
7. Local disagreement localization
8. Risk classification
9. Extractor consensus
10. Optional visual adjudication on a bounding-box crop
11. Evidence-ledger write
12. Local reconstruction or abstention
13. Removal of unresolved sentences from training output
14. Structured-block preservation
15. Deduplication
16. Manifest and audit export

## Trust policy

### Low-risk prose
Two extractors agreeing is sufficient. If extractors disagree, one high-confidence visual AI can select an *existing* alternative.

### High-risk spans
Numbers, equations, identifiers, code, scientific quantities and biological sequences receive stricter handling. Generative completion is forbidden. If there is no extractor consensus, two independent visual AI judges must agree on an existing extraction alternative.

### Abstention
`[UNRESOLVED]` is an internal marker. Sentences containing it are removed before training export. If too much of the page is unresolved, the page is rejected.

## Production expansion path

Future releases should introduce a Universal Document Representation (UDR) with typed blocks and normalized coordinates, then specialist validators for math, tables, code, chemistry, citations and sequences.
