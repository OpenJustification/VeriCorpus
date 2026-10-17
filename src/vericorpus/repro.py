# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import hashlib
import importlib.metadata
import json
import os
import platform
import random
import subprocess
import sys
from pathlib import Path
from typing import Iterable


def canonical_json_hash(obj: object) -> str:
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def installed_versions(names: Iterable[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for name in names:
        try:
            out[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            out[name] = "not-installed"
    return out


def executable_version(name: str, args: list[str] | None = None) -> str:
    try:
        cp = subprocess.run([name] + (args or ["--version"]), capture_output=True, text=True, timeout=10, check=False)
        text = (cp.stdout or cp.stderr).strip().splitlines()
        return text[0][:500] if text else f"exit={cp.returncode}"
    except Exception:
        return "not-available"


def set_deterministic(seed: int) -> dict[str, object]:
    random.seed(seed)
    os.environ.setdefault("CUBLAS_WORKSPACE_CONFIG", ":4096:8")
    report: dict[str, object] = {"seed": seed, "python_random": True}
    try:
        import numpy as np
        np.random.seed(seed)
        report["numpy"] = True
    except Exception:
        report["numpy"] = False
    try:
        import torch
        torch.manual_seed(seed)
        if torch.cuda.is_available():
            torch.cuda.manual_seed_all(seed)
        try:
            torch.use_deterministic_algorithms(True, warn_only=True)
            report["torch_deterministic_algorithms"] = True
        except Exception:
            report["torch_deterministic_algorithms"] = False
        if hasattr(torch.backends, "cudnn"):
            torch.backends.cudnn.benchmark = False
            torch.backends.cudnn.deterministic = True
        report["torch"] = getattr(torch, "__version__", "unknown")
    except Exception:
        report["torch"] = "not-installed"
    return report



def _sha256_file(path: Path, digest_cache: dict[str, str] | None = None) -> str:
    key = str(path.resolve())
    if digest_cache is not None and key in digest_cache:
        return digest_cache[key]
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    value = h.hexdigest()
    if digest_cache is not None:
        digest_cache[key] = value
    return value


def tree_fingerprint(path: Path) -> dict[str, object]:
    """Content fingerprint a model/cache tree using relative paths and file SHA-256 values."""
    if not path.exists():
        return {"exists": False, "files": 0, "bytes": 0, "sha256": None}
    h = hashlib.sha256()
    total = 0
    count = 0
    digest_cache: dict[str, str] = {}
    for item in sorted((x for x in path.rglob("*") if x.is_file()), key=lambda x: x.as_posix()):
        # Lock/temp files are transport state, not model content.
        if item.name.endswith((".lock", ".tmp", ".incomplete")):
            continue
        rel = item.relative_to(path).as_posix()
        try:
            size = item.stat().st_size
            digest = _sha256_file(item, digest_cache)
        except (OSError, FileNotFoundError):
            continue
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(str(size).encode("ascii"))
        h.update(b"\0")
        h.update(digest.encode("ascii"))
        h.update(b"\n")
        total += size
        count += 1
    return {"exists": True, "files": count, "bytes": total, "sha256": h.hexdigest()}


def model_cache_fingerprints() -> dict[str, dict[str, object]]:
    """Fingerprint configured local model/cache roots without sending data anywhere."""
    roots = {
        "vericorpus_models": os.environ.get("VERICORPUS_MODEL_HOME"),
        "paddlex": os.environ.get("PADDLE_PDX_CACHE_HOME"),
        "huggingface": os.environ.get("HF_HOME"),
        "torch": os.environ.get("TORCH_HOME"),
    }
    out: dict[str, dict[str, object]] = {}
    for label, raw in roots.items():
        if raw:
            fp = tree_fingerprint(Path(raw))
            fp["path"] = str(Path(raw))
            out[label] = fp
    return out


def verify_cache_fingerprints(expected: dict, actual: dict) -> list[str]:
    errors: list[str] = []
    for label, spec in expected.items():
        want = spec.get("sha256") if isinstance(spec, dict) else spec
        got = actual.get(label, {}).get("sha256")
        if not want or str(want).startswith("REPLACE_"):
            errors.append(f"{label}: lock has no concrete cache SHA-256")
        elif got != want:
            errors.append(f"{label}: cache SHA-256 mismatch (expected {want}, got {got})")
    return errors

def git_commit(repo: Path) -> str:
    try:
        cp = subprocess.run(["git", "-C", str(repo), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=5, check=False)
        return cp.stdout.strip() if cp.returncode == 0 else "unknown"
    except Exception:
        return "unknown"


def runtime_fingerprint(seed: int, model_lock: dict | None = None) -> dict:
    packages = installed_versions([
        "vericorpus", "PyMuPDF", "pytesseract", "Pillow", "pydantic", "typer", "rich",
        "paddleocr", "paddlepaddle", "docling", "huggingface-hub", "glmocr", "olmocr", "transformers", "torch", "huggingface-hub",
    ])
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "machine": platform.machine(),
        "packages": packages,
        "tesseract": executable_version("tesseract"),
        "determinism": set_deterministic(seed),
        "model_lock": model_lock or {},
        "model_lock_sha256": canonical_json_hash(model_lock or {}),
    }
