# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from pathlib import Path
import json
import tomllib

from vericorpus import __schema_version__, __version__
from vericorpus.model_registry import load_registry, validate_registry

ROOT = Path(__file__).resolve().parents[1]


def test_release_files_exist() -> None:
    for rel in [
        "LICENSE", "README.md", "CHANGELOG.md", "CITATION.cff", "SECURITY.md",
        "CONTRIBUTING.md", "GOVERNANCE.md", "DCO.md", "AI_POLICY.md",
        "THIRD_PARTY_LICENSES.md", "docs/SCHEMA.md", "docs/PLUGINS.md",
        "docs/REPRODUCIBILITY.md", "docs/LEGAL_AND_MODEL_POLICY.md", "docs/TOOL_SELECTION.md",
        "models/reference-open.json", "models/model-lock.example.json", "models/benchmark-snapshot.json", "RELEASE_NOTES_v0.2.0-alpha.md", "docs/DESKTOP_RELEASES.md",
        ".github/workflows/ci.yml", ".github/workflows/release.yml", ".github/workflows/dco.yml", ".github/workflows/desktop-build.yml",
        "packaging/vericorpus.spec", "src/vericorpus/desktop.py",
    ]:
        assert (ROOT / rel).exists(), rel


def test_readme_does_not_claim_foolproof() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    assert "not a guarantee" in readme
    assert __version__ in (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")


def test_license_metadata_is_agpl_or_later() -> None:
    pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    notice = (ROOT / "NOTICE").read_text(encoding="utf-8")
    assert 'license = "AGPL-3.0-or-later"' in pyproject
    assert "license: AGPL-3.0-or-later" in citation
    assert "either version 3" in notice and "any later version" in notice


def test_schema_version_is_documented() -> None:
    schema = (ROOT / "docs/SCHEMA.md").read_text(encoding="utf-8")
    assert f"Current schema version: **{__schema_version__}**" in schema


def test_official_extras_exclude_proprietary_and_custom_license_components() -> None:
    data = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    deps = json.dumps(data["project"]["optional-dependencies"]).lower()
    for forbidden in ["openai", "anthropic", "mineru"]:
        assert forbidden not in deps


def test_reference_model_registry_is_license_clean() -> None:
    registry = load_registry(ROOT / "models" / "reference-open.json")
    assert not validate_registry(registry)
    assert all(m["license"] in {"Apache-2.0", "MIT", "AGPL-3.0-or-later"} for m in registry["models"])


def test_public_plugin_interface_imports() -> None:
    from vericorpus.plugins import ENTRY_POINT_GROUP, discover_extractor_plugins
    assert ENTRY_POINT_GROUP == "vericorpus.extractors"
    assert isinstance(discover_extractor_plugins(), dict)


def test_license_file_is_agpl_v3_text() -> None:
    text = (ROOT / "LICENSE").read_text(encoding="utf-8")
    assert "GNU AFFERO GENERAL PUBLIC LICENSE" in text
    assert "Version 3, 19 November 2007" in text


def test_public_release_version_and_schema() -> None:
    assert __version__ == "0.2.0a1"
    assert __schema_version__ == "3.0"


def test_tracked_benchmark_leaders_are_not_active_or_downloadable() -> None:
    catalog = json.loads((ROOT / "src/vericorpus/data/local-models.json").read_text(encoding="utf-8"))
    by_key = {m["key"]: m for m in catalog["models"]}
    for key in ["ovisocr2", "teleocr"]:
        assert by_key[key]["default"] is False
        assert by_key[key]["downloadable"] is False
        assert by_key[key]["integration_status"] == "tracked-not-active"


def test_benchmark_snapshot_has_current_selected_rows() -> None:
    snap = json.loads((ROOT / "models/benchmark-snapshot.json").read_text(encoding="utf-8"))
    assert snap["snapshot_date"] == "2026-10-17"
    scores = {r["model"]: r["overall"] for r in snap["selected_rows"]}
    assert scores["TeleOCR"] == 96.91
    assert scores["OvisOCR2"] == 96.47
    assert scores["PaddleOCR-VL-1.6"] == 96.34
