# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from importlib.resources import files
import json
from pathlib import Path

ALLOWED_REFERENCE_LICENSES = {"Apache-2.0", "MIT", "AGPL-3.0-or-later"}


def load_registry(path: Path | None = None) -> dict:
    if path is not None:
        return json.loads(path.read_text(encoding="utf-8"))
    payload = files("vericorpus.data").joinpath("reference-open.json").read_text(encoding="utf-8")
    return json.loads(payload)


def validate_registry(registry: dict) -> list[str]:
    errors: list[str] = []
    for item in registry.get("models", []):
        if item.get("license") not in ALLOWED_REFERENCE_LICENSES:
            errors.append(f"{item.get('id')}: non-reference license {item.get('license')}")
        if not item.get("revision_policy"):
            errors.append(f"{item.get('id')}: missing revision_policy")
    return errors


def load_model_lock(path: Path | None) -> dict:
    if path is None:
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    if data.get("format") != "vericorpus-model-lock-v1":
        raise ValueError("Unsupported model lock format")
    return data
