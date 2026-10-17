# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from vericorpus import __schema_version__, __version__


def main() -> int:
    errors: list[str] = []

    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    match = re.search(r"^version:\s*([^\s]+)\s*$", citation, flags=re.MULTILINE)
    citation_version = match.group(1).strip('"\'') if match else None
    if citation_version != __version__:
        errors.append(f"CITATION.cff version {citation_version!r} != package version {__version__!r}")

    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    if f"## {__version__}" not in changelog and f"## [{__version__}]" not in changelog:
        errors.append(f"CHANGELOG.md has no section for {__version__}")

    required = [
        "README.md", "UPGRADE_FROM_0.1.md", "LICENSE", "NOTICE", "SECURITY.md", "CONTRIBUTING.md", "GOVERNANCE.md",
        "DCO.md", "AI_POLICY.md", "THIRD_PARTY_LICENSES.md", "docs/SCHEMA.md", "docs/PLUGINS.md",
        "docs/RELEASING.md", "docs/REPRODUCIBILITY.md", "docs/LEGAL_AND_MODEL_POLICY.md",
        "docs/TOOL_SELECTION.md", "docs/DESKTOP_RELEASES.md", "docs/OBJECT_IDENTIFICATION.md", "models/benchmark-snapshot.json",
        "RELEASE_NOTES_v0.2.0-alpha.md", "models/reference-open.json", "models/model-lock.example.json",
        ".github/workflows/ci.yml", ".github/workflows/release.yml", ".github/workflows/dco.yml",
        ".github/workflows/desktop-build.yml", ".github/workflows/windows-exe.yml", "packaging/stage_tesseract_windows.ps1", "packaging/vericorpus.spec", "packaging/desktop_entry.py",
        "packaging/requirements-bundle-lite.txt", "packaging/requirements-bundle-full.txt",
        "src/vericorpus/desktop.py",
    ]
    for rel in required:
        if not (ROOT / rel).exists():
            errors.append(f"missing required release file: {rel}")

    pyproject_path = ROOT / "pyproject.toml"
    pyproject_text = pyproject_path.read_text(encoding="utf-8")
    if 'license = "AGPL-3.0-or-later"' not in pyproject_text:
        errors.append("pyproject.toml is not licensed as AGPL-3.0-or-later")
    project = tomllib.loads(pyproject_text)["project"]
    if project.get("gui-scripts", {}).get("vericorpus-desktop") != "vericorpus.desktop:main":
        errors.append("desktop GUI entry point is missing or incorrect")

    schema_doc = (ROOT / "docs/SCHEMA.md").read_text(encoding="utf-8")
    if f"Current schema version: **{__schema_version__}**" not in schema_doc:
        errors.append("docs/SCHEMA.md does not match package schema version")

    lower_pyproject = pyproject_text.lower()
    for token in ["openai", "anthropic", "mineru"]:
        if token in lower_pyproject:
            errors.append(f"excluded official dependency token present in pyproject: {token}")

    for removed in ["portable_ui.py", "portable/VeriCorpus.cmd", ".github/workflows/portable-windows.yml"]:
        if (ROOT / removed).exists():
            errors.append(f"legacy bootstrap file should not be in the desktop release: {removed}")

    if errors:
        for error in errors:
            print(f"ERROR: {error}")
        return 1

    print(f"Release metadata is consistent for VeriCorpus {__version__} desktop/public release.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
