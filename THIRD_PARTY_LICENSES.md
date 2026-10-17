# Third-party licensing notes

VeriCorpus is licensed under **AGPL-3.0-or-later**. Third-party software and model weights retain their own licenses. VeriCorpus does not redistribute the listed model weights.

This inventory was reviewed for the 0.2.0-alpha reference/desktop profile on **2026-10-17**. It is informational, not legal advice. The Windows and Linux desktop releases also ship machine-generated package/build inventories so users can audit the exact artifact they received.

| Component/model | Role | Upstream license documented by upstream | 0.1 status |
|---|---|---|---|
| PyMuPDF / MuPDF | PDF extraction/rendering | AGPL or upstream commercial license | Core |
| PaddlePaddle / PaddleOCR | local inference / document pipeline | Apache-2.0 | Full desktop Standard |
| PaddleOCR-VL 1.6 | primary document VLM | Apache-2.0 | Full desktop Standard; weights downloaded upstream, not redistributed |
| OvisOCR2 | tracked compact document-parser candidate | Apache-2.0 | Tracked only; not active or redistributed in 0.2.0-alpha |
| TeleOCR | tracked benchmark-leading document-parser candidate | Apache-2.0 | Tracked only; not active or redistributed; upstream custom-code path requires review before activation |
| Docling | structured document conversion | MIT | Full desktop Standard |
| Tesseract OCR | classical OCR | Apache-2.0 | Optional Verified witness; system tool, not bundled in desktop archives |
| pytesseract | Tesseract wrapper | Apache-2.0 | Core Python dependency |
| GLM-OCR code | optional independent OCR | Apache-2.0 | Implemented optional Verified adapter |
| GLM-OCR weights | optional independent OCR model | MIT | Not redistributed |
| olmOCR | optional PDF linearization | Apache-2.0 | Implemented optional Verified adapter; not redistributed |
| Qwen3.5-4B | staged local visual adjudicator target | Apache-2.0 | Catalogued only; not active/bundled in 0.2.0-alpha |
| NVIDIA Nemotron 3 Nano 4B | staged text second-opinion target | NVIDIA Nemotron Open Model License | Outside clean reference profile; not active/bundled in 0.2.0-alpha |
| huggingface-hub | model/cache transport | Apache-2.0 | Full desktop model/cache support |
| Pillow | image handling | Pillow license | Core |
| Pydantic | validation | MIT | Core |
| Typer | CLI | MIT | Core |
| Rich | CLI display | MIT | Core |

## Deliberately excluded from the clean reference distribution

The official clean reference extras do **not** install proprietary model APIs or parser/model families with unreviewed/custom terms. Optional third-party plugins are allowed, but they are outside the reference license inventory. Nemotron remains separately catalogued because the user requested it be retained, but it is not bundled, active by default, or counted as a clean-reference model.

## Data rights are separate

A software/model license does not grant rights to copyrighted PDFs, personal data, medical records, trade secrets, or other input content. Dataset builders are responsible for establishing their own lawful basis and permissions.
