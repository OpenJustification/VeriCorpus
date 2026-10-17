# SPDX-License-Identifier: AGPL-3.0-or-later
from pathlib import Path
import json

from vericorpus.repro import canonical_json_hash, runtime_fingerprint, tree_fingerprint, verify_cache_fingerprints
from vericorpus.model_registry import load_model_lock


def test_canonical_hash_is_order_independent():
    assert canonical_json_hash({"b": 2, "a": 1}) == canonical_json_hash({"a": 1, "b": 2})


def test_model_lock_validation(tmp_path: Path):
    p = tmp_path / "lock.json"
    p.write_text(json.dumps({"format":"vericorpus-model-lock-v1","models":{}}), encoding="utf-8")
    assert load_model_lock(p)["format"] == "vericorpus-model-lock-v1"


def test_runtime_fingerprint_has_core_fields():
    fp = runtime_fingerprint(123, {})
    assert fp["determinism"]["seed"] == 123
    assert "packages" in fp and "tesseract" in fp


def test_tree_fingerprint_changes_with_content(tmp_path: Path):
    root = tmp_path / "cache"
    root.mkdir()
    (root / "model.bin").write_bytes(b"abc")
    a = tree_fingerprint(root)
    (root / "model.bin").write_bytes(b"abd")
    b = tree_fingerprint(root)
    assert a["sha256"] != b["sha256"]
    assert a["files"] == b["files"] == 1


def test_cache_lock_verification_detects_mismatch():
    expected = {"paddlex": {"sha256": "a" * 64}}
    actual = {"paddlex": {"sha256": "b" * 64}}
    assert verify_cache_fingerprints(expected, actual)


def _make_native_pdf(path: Path) -> None:
    import fitz
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((72, 72), "A clean native PDF with sufficient direct source text for reproducibility lock testing.")
    doc.save(path)
    doc.close()


def test_pipeline_refuses_mismatched_cache_lock(tmp_path: Path, monkeypatch):
    import pytest
    from vericorpus.config import settings_for_profile
    from vericorpus.pipeline import prepare

    cache = tmp_path / "models"
    cache.mkdir()
    (cache / "weights.bin").write_bytes(b"actual")
    monkeypatch.setenv("VERICORPUS_MODEL_HOME", str(cache))
    lock = tmp_path / "lock.json"
    lock.write_text(json.dumps({
        "format": "vericorpus-model-lock-v1",
        "models": {},
        "cache_fingerprints": {"vericorpus_models": {"sha256": "0" * 64}},
    }), encoding="utf-8")
    source = tmp_path / "source.pdf"
    _make_native_pdf(source)
    with pytest.raises(ValueError, match="Model lock verification failed"):
        prepare(source, tmp_path / "out", settings_for_profile("lite", model_lock_path=lock))


def test_pipeline_accepts_matching_cache_lock_and_marks_verified(tmp_path: Path, monkeypatch):
    from vericorpus.config import settings_for_profile
    from vericorpus.pipeline import prepare

    cache = tmp_path / "models"
    cache.mkdir()
    (cache / "weights.bin").write_bytes(b"actual")
    monkeypatch.setenv("VERICORPUS_MODEL_HOME", str(cache))
    digest = tree_fingerprint(cache)["sha256"]
    lock = tmp_path / "lock.json"
    lock.write_text(json.dumps({
        "format": "vericorpus-model-lock-v1",
        "models": {},
        "cache_fingerprints": {"vericorpus_models": {"sha256": digest}},
    }), encoding="utf-8")
    source = tmp_path / "source.pdf"
    _make_native_pdf(source)
    manifest = prepare(source, tmp_path / "out", settings_for_profile("lite", model_lock_path=lock))
    assert manifest["reproducibility_grade"] == "locked-cache-verified"
    assert manifest["model_cache_fingerprints"]["vericorpus_models"]["sha256"] == digest
