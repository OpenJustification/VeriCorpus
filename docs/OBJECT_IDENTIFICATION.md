# Document Structure Engine (DSE)

VeriCorpus 0.3 analyzes page structure before producing training text.

## Objects

The DSE can identify or represent:

- title, author, affiliation, abstract, keywords
- heading, paragraph, list
- figure, subfigure region, figure caption
- table, table caption, table footnote
- display equation and equation number
- code / algorithm regions
- headers, footers, page numbers, footnotes
- reference headings and reference entries
- unknown objects when classification is uncertain

Every object has a page number, bounding box, confidence, column assignment when applicable, source, and reading-order position.

## Column/layout identification

The native structure engine estimates 1-, 2-, and 3-column layouts and identifies mixed pages that contain full-width objects plus columns. Reading order is reconstructed by vertical bands and column flow instead of relying on the PDF's flattened text order.

## Structured-submission ground truth

`vericorpus groundtruth` can extract semantic labels from:

- LaTeX (`figure`, `table`, `equation`, `align`, `algorithm`, section headings)
- JATS XML (`fig`, `table-wrap`, `disp-formula`, titles)
- DOCX/OOXML (tables, drawings, Office Math, figure/table captions)

Text anchors are aligned to a corresponding PDF when possible. This allows journal submission packages—including structured publisher submissions such as MDPI-style LaTeX/DOCX packages—to seed a human-verifiable object/layout benchmark without hand-labeling every object from scratch.

Source labels are evidence, not unquestioned truth: alignment confidence and failures remain explicit.
