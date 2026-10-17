# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from pathlib import Path
import json

import fitz

from vericorpus.layout import analyze_page, structure_to_text
from vericorpus.groundtruth import extract_source_labels, align_labels_to_pdf


def _two_column_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)
    page.insert_text((50, 60), "Two-column test document", fontsize=16)
    page.insert_textbox(fitz.Rect(50, 120, 280, 360), "1. Introduction\nLeft column paragraph one.\nLeft column paragraph two.", fontsize=11)
    page.insert_textbox(fitz.Rect(320, 120, 550, 360), "Right column paragraph one.\nRight column paragraph two.", fontsize=11)
    doc.save(path)
    doc.close()


def test_two_column_detection_and_reading_order(tmp_path: Path):
    pdf = tmp_path / "two.pdf"
    _two_column_pdf(pdf)
    doc = fitz.open(pdf)
    try:
        s = analyze_page(doc[0], 1)
        text = structure_to_text(s)
    finally:
        doc.close()
    assert s.column_count == 2
    assert s.layout_type in {"multi_column", "mixed"}
    assert text.index("Left column paragraph one") < text.index("Right column paragraph one")
    assert s.reading_order_confidence >= 0.8


def test_structure_output_has_bboxes(tmp_path: Path):
    pdf = tmp_path / "two.pdf"
    _two_column_pdf(pdf)
    doc = fitz.open(pdf)
    try:
        s = analyze_page(doc[0], 1)
    finally:
        doc.close()
    assert s.objects
    assert all(o.bbox.x1 >= o.bbox.x0 for o in s.objects)
    assert any(o.object_type in {"title", "heading", "paragraph"} for o in s.objects)


def test_latex_groundtruth_extract_and_align(tmp_path: Path):
    tex = tmp_path / "paper.tex"
    tex.write_text(
        r"""\section{Methods}
\begin{figure}\caption{Microscopy image of the coating}\label{fig:micro}\end{figure}
\begin{table}\caption{Mechanical properties}\label{tab:mech}\end{table}
\begin{equation}E = mc^2\end{equation}
""",
        encoding="utf-8",
    )
    labels = extract_source_labels(tex)
    assert {x.object_type for x in labels} >= {"heading", "figure", "table", "equation"}

    pdf = tmp_path / "paper.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "Methods")
    page.insert_text((72, 120), "Microscopy image of the coating")
    page.insert_text((72, 160), "Mechanical properties")
    doc.save(pdf)
    doc.close()
    aligned = align_labels_to_pdf(labels, pdf)
    assert any(x.aligned for x in aligned if x.object_type == "figure")
    assert any(x.aligned for x in aligned if x.object_type == "table")


def test_pipeline_writes_human_readable_and_structure_outputs(tmp_path: Path):
    from vericorpus.config import settings_for_profile
    from vericorpus.pipeline import prepare

    pdf = tmp_path / "two.pdf"
    _two_column_pdf(pdf)
    out = tmp_path / "out"
    prepare(pdf, out, settings_for_profile("lite"))
    for name in [
        "training.jsonl",
        "training.pretty.json",
        "training_review.md",
        "document_structure.jsonl",
        "routing.jsonl",
        "unresolved.jsonl",
    ]:
        assert (out / name).exists(), name
    rows = [json.loads(x) for x in (out / "training.jsonl").read_text(encoding="utf-8").splitlines() if x]
    assert rows
    assert "quality_dimensions" in rows[0]
    assert "training_readiness" in rows[0]
    assert rows[0]["layout"]["column_count"] == 2


def test_three_column_detection(tmp_path: Path):
    pdf = tmp_path / "three.pdf"
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)
    cols = [
        (35, "Column one has enough text to be detected as the first column of this document."),
        (220, "Column two has enough text to be detected as the second column of this document."),
        (405, "Column three has enough text to be detected as the third column of this document."),
    ]
    for x, text in cols:
        page.insert_textbox(fitz.Rect(x, 100, x + 155, 500), text, fontsize=10)
    doc.save(pdf)
    doc.close()

    doc = fitz.open(pdf)
    try:
        s = analyze_page(doc[0], 1)
        text = structure_to_text(s)
    finally:
        doc.close()
    assert s.column_count == 3
    assert text.index("Column one") < text.index("Column two") < text.index("Column three")
