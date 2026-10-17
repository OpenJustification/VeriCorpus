# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_OFFICIAL_TOKENS = {"openai", "anthropic", "mineru"}
ALLOWED_MODEL_LICENSES = {"Apache-2.0", "MIT", "AGPL-3.0-or-later"}


def main() -> int:
    errors: list[str] = []
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    extras = json.dumps(pyproject["project"].get("optional-dependencies", {})).lower()
    for token in FORBIDDEN_OFFICIAL_TOKENS:
        if token in extras:
            errors.append(f"official optional dependencies contain excluded integration: {token}")
    registry = json.loads((ROOT / "models/reference-open.json").read_text(encoding="utf-8"))
    for model in registry.get("models", []):
        if model.get("license") not in ALLOWED_MODEL_LICENSES:
            errors.append(f"reference model has non-approved license: {model.get('id')} -> {model.get('license')}")
    if errors:
        for e in errors:
            print("ERROR:", e)
        return 1
    print("Reference dependency/model policy check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
