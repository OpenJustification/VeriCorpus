# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path
import json
import zipfile
import pytest

from vericorpus.corpus import split_for_document, validate_run
from vericorpus.dedupe import dedupe_with_report, near_duplicate
from vericorpus.config import settings_for_profile
from vericorpus.pipeline import prepare


def build_epub(path: Path):
    container = '''<?xml version="1.0"?>
<container xmlns="urn:oasis:names:tc:opendocument:xmlns:container" version="1.0"><rootfiles><rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/></rootfiles></container>'''
    opf = '''<?xml version="1.0"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="id"><manifest><item id="part1" href="one.xhtml" media-type="application/xhtml+xml"/></manifest><spine><itemref idref="part1"/></spine></package>'''
    xhtml = '''<?xml version="1.0"?>
<html xmlns="http://www.w3.org/1999/xhtml"><body><h1>Biomedical Materials</h1><p>Titanium composite improves adhesion and surface roughness by changing processing parameters in controlled experiments.</p><table><tr><th>Sample</th><th>Hardness GPa</th></tr><tr><td>Untreated</td><td>2.15 ± 0.07</td></tr></table><p>Other text relevant for downstream training applications and reproducible source reconstruction.</p><img src="micrograph.png" alt="Microscopy image"/></body></html>'''
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr("META-INF/container.xml", container)
        z.writestr("OEBPS/content.opf", opf)
        z.writestr("OEBPS/one.xhtml", xhtml)


def test_epub_structure_and_exports(tmp_path: Path):
    path = tmp_path / "book.epub"
    build_epub(path)
    out = tmp_path / "output"
    manifest = prepare(path, out, settings_for_profile("lite"))
    assert manifest["documents"] == 1
    assert manifest["pages_accepted_after_dedupe"] == 1
    text = json.loads((out / "pretraining.jsonl").read_text(encoding="utf-8").splitlines()[0])["text"]
    assert "Biomedical Materials" in text
    assert "2.15 ± 0.07" in text
    assert "[TABLE]" in text
    assert "Microscopy image" not in text  # Never invent visual interpretation from image alt.
    structures = json.loads((out / "document_structure.jsonl").read_text(encoding="utf-8").splitlines()[0])
    assert "figure" in [x["object_type"] for x in structures["objects"]]
    assert structures["diagnostics"]["geometry"] == "not_applicable"
    assert validate_run(out)["status"] == "PASS"


def test_epub_rejects_unsafe_archive_path(tmp_path: Path):
    path = tmp_path / "bad.epub"
    build_epub(path)
    # Update the container to point outside the archive.
    with zipfile.ZipFile(path, "a") as z:
        z.writestr("META-INF/container.xml", '''<container><rootfile full-path="../../unsafe"/></container>''')
    with pytest.raises(ValueError, match="escapes the archive"):
        prepare(path, tmp_path / "out", settings_for_profile("lite"))


def test_dedupe_keeps_lineage_and_uses_near_threshold():
    text = " ".join(f"scientificword{i}" for i in range(120))
    a = {"text": text, "record_id": "one", "document_id": "A", "page_number": 1}
    b = {"text": "  " + text.upper() + "\n", "record_id": "two", "document_id": "B", "page_number": 5}
    c = {"text": text.replace("scientificword60", "replacementword"), "record_id": "three", "document_id": "C", "page_number": 1}
    assert near_duplicate(text, c["text"], threshold=0.90)
    kept, dropped = dedupe_with_report([a, b, c], threshold=0.90)
    assert len(kept) == 1
    assert [d["type"] for d in dropped] == ["exact", "near"]
    assert all(d["kept_record_id"] == "one" for d in dropped)


def test_doc_disjoint_splits_and_tamper_detection(tmp_path: Path):
    from vericorpus.corpus import create_training_exports
    records = []
    for i in range(24):
        for p in range(3):
            records.append({"document_id": f"doc:{i}", "page_number": p,
                            "text": f"document {i} page {p}",
                            "training_readiness": {"status": "accepted"}})
    audits = [{"document_id": x["document_id"], "page_number": x["page_number"]} for x in records]
    create_training_exports(tmp_path, records, audits, [], [], [], [])
    assert len({split_for_document(f"doc:{i}") for i in range(100)}) == 3
    assigned = {}
    for file in (tmp_path / "splits" / "document_assignments.jsonl").read_text().splitlines():
        item = json.loads(file)
        assigned[item["document_id"]] = item["split"]
    assert len(assigned) == 24
    assert all(assigned[f"doc:{i}"] == split_for_document(f"doc:{i}") for i in range(24))


def test_original_pdf_like_output_fails_tampered_checksum(tmp_path: Path):
    import fitz
    pdf = tmp_path / "input.pdf"
    with fitz.open() as doc:
        page = doc.new_page()
        page.insert_text((72,72), "This is a substantial materials science paragraph with a numeric result 2.15 GPa.")
        doc.save(pdf)
    out = tmp_path / "out"
    prepare(pdf, out, settings_for_profile("lite"))
    assert validate_run(out)["status"] == "PASS"
    with (out / "pretraining.jsonl").open("a", encoding="utf-8") as f:
        f.write('{"text": "fabricated 99.5"}\n')
    finding = validate_run(out)
    assert finding["status"] == "FAIL"
    assert "pretraining_disagrees_with_training" in finding["errors"]
    assert "checksum_mismatch:pretraining.jsonl" in finding["errors"]
