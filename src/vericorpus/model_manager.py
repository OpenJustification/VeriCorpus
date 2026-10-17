# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from importlib.resources import files
import hashlib
import json
import os
from pathlib import Path


def load_local_catalog() -> dict:
    return json.loads(files("vericorpus.data").joinpath("local-models.json").read_text(encoding="utf-8"))


def model_home() -> Path:
    raw = os.environ.get("VERICORPUS_MODEL_HOME")
    path = Path(raw) if raw else Path.home() / ".vericorpus" / "models"
    path.mkdir(parents=True, exist_ok=True)
    return path


def model_entry(key: str) -> dict:
    for item in load_local_catalog().get("models", []):
        if item.get("key") == key:
            return item
    raise KeyError(key)


def model_path(key: str) -> Path:
    return model_home() / key


def model_status() -> list[dict]:
    rows=[]
    for item in load_local_catalog().get("models", []):
        path=model_path(item["key"])
        rows.append({**item, "installed": path.exists() and any(path.iterdir()), "path": str(path)})
    return rows


def _sha256(path: Path) -> str:
    h=hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda:f.read(1024*1024),b""):
            h.update(chunk)
    return h.hexdigest()


def download_model(key: str, *, acknowledge_license: bool=False) -> dict:
    item=model_entry(key)
    if not item.get("downloadable", True):
        raise RuntimeError(
            f"{key} is catalogued but is not a directly downloadable active VeriCorpus model pack in this release"
        )
    if item.get("requires_license_acknowledgement") and not acknowledge_license:
        raise PermissionError(f"{key} requires explicit acknowledgement of its upstream model license")
    try:
        from huggingface_hub import hf_hub_download, snapshot_download
    except Exception as exc:
        raise RuntimeError("Install VeriCorpus Standard/Verified model support (huggingface-hub) first") from exc
    target=model_path(key); target.mkdir(parents=True,exist_ok=True)
    common=dict(repo_id=item["id"],revision=item["revision"],local_dir=str(target))
    if item.get("filename"):
        path=Path(hf_hub_download(filename=item["filename"],**common))
        files_out=[path]
    else:
        snapshot_download(**common)
        files_out=[p for p in target.rglob("*") if p.is_file()]
    manifest={
        "format":"vericorpus-downloaded-model-v1",
        "key":key,"id":item["id"],"revision":item["revision"],"license":item["license"],
        "files":[{"path":str(p.relative_to(target)),"bytes":p.stat().st_size,"sha256":_sha256(p)} for p in sorted(files_out)],
    }
    (target/"VERICORPUS_MODEL_MANIFEST.json").write_text(json.dumps(manifest,indent=2),encoding="utf-8")
    return manifest
