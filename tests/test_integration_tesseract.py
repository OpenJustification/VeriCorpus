# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
import shutil
from pathlib import Path

import fitz
import pytest

from vericorpus.config import Settings
from vericorpus.pipeline import prepare



def _make_pdf(path: Path) -> None:
    doc = fitz.open()
    page = doc.new_page(width=612, height=792)
    page.insert_text(
        (72, 100),
        "The concentration was 0.05 mg/mL. The samples were incubated for 30 min at 37 C.",
        fontsize=14,
    )
    doc.save(path)
    doc.close()


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract executable not installed")
def test_end_to_end_pdf_with_tesseract(tmp_path: Path) -> None:
    source = tmp_path / "sample.pdf"
    output = tmp_path / "output"
    _make_pdf(source)

    manifest = prepare(
        source,
        output,
        Settings(
            use_tesseract=True,
            use_paddleocr=False,
            use_docling=False,
            use_glmocr=False,
            use_olmocr=False,
            render_dpi=300,
        ),
    )

    assert manifest["pages_total"] == 1
    rows = [json.loads(line) for line in (output / "training.jsonl").read_text(encoding="utf-8").splitlines() if line]
    assert rows, "Expected the synthetic page to be admitted to training output"
    text = rows[0]["text"]
    assert "0.05 mg/mL" in text
    assert "30 min" in text
    assert rows[0]["source_file"] == "sample.pdf"


@pytest.mark.skipif(shutil.which("tesseract") is None, reason="Tesseract executable not installed")
def test_manifest_and_training_records_are_schema_stamped(tmp_path):
    import json
    import fitz

    from vericorpus.config import Settings
    from vericorpus.pipeline import prepare

    src = tmp_path / "schema_sample.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "The concentration was 0.05 mg/mL and incubation time was 30 min.")
    doc.save(src)
    doc.close()

    out = tmp_path / "out"
    manifest = prepare(
        src,
        out,
        Settings(
            use_tesseract=True,
            use_paddleocr=False,
            use_docling=False,
            use_glmocr=False,
            use_olmocr=False,
        ),
    )
    assert manifest["vericorpus_schema"] == "3.0"
    assert manifest["generator"] == "vericorpus"
    assert manifest["generator_version"] == "0.2.0a1"

    rows = [json.loads(line) for line in (out / "training.jsonl").read_text(encoding="utf-8").splitlines()]
    assert rows
    assert all(row["vericorpus_schema"] == "3.0" for row in rows)
    assert all(row["generator_version"] == "0.2.0a1" for row in rows)


def test_lite_profile_accepts_clean_native_pdf(tmp_path):
    import json
    import fitz

    from vericorpus.config import settings_for_profile
    from vericorpus.pipeline import prepare

    src = tmp_path / "clean_native.pdf"
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (72, 72),
        "This is a clean born-digital PDF page with enough source text to validate the native extraction path.",
        fontsize=12,
    )
    doc.save(src)
    doc.close()

    out = tmp_path / "out_lite"
    manifest = prepare(src, out, settings_for_profile("lite"))
    rows = [json.loads(line) for line in (out / "training.jsonl").read_text(encoding="utf-8").splitlines() if line]
    assert rows
    assert rows[0]["provenance"]["decision_reason"] == "training_readiness_pass"
