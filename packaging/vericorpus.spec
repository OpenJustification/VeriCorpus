# -*- mode: python ; coding: utf-8 -*-
# SPDX-License-Identifier: AGPL-3.0-or-later
import os
from PyInstaller.utils.hooks import collect_all, copy_metadata

bundle = os.environ.get("VERICORPUS_BUNDLE", "lite").strip().lower()
if bundle not in {"lite", "standard", "verified"}:
    raise SystemExit(f"Unsupported VERICORPUS_BUNDLE={bundle}")

pathex = [os.path.abspath("src"), os.path.abspath("packaging")]
datas = []
binaries = []
hiddenimports = []

# Preserve package metadata used by importlib.metadata and license/version reporting.
for dist in ["vericorpus", "PyMuPDF", "Pillow", "pytesseract", "pydantic", "typer", "rich"]:
    try:
        datas += copy_metadata(dist)
    except Exception:
        pass

# VeriCorpus JSON registries are package data but collect explicitly as a packaging guard.
try:
    d, b, h = collect_all("vericorpus")
    datas += d; binaries += b; hiddenimports += h
except Exception:
    pass

if bundle in {"standard", "verified"}:
    for pkg, dist in [
        ("paddle", "paddlepaddle"),
        ("paddleocr", "paddleocr"),
        ("paddlex", "paddlex"),
        ("docling", "docling"),
        ("huggingface_hub", "huggingface-hub"),
        ("transformers", "transformers"),
    ]:
        try:
            d, b, h = collect_all(pkg)
            datas += d; binaries += b; hiddenimports += h
        except Exception:
            pass
        try:
            datas += copy_metadata(dist)
        except Exception:
            pass

# Stable deduplication keeps spec output manageable.
def uniq(items):
    seen = set(); out = []
    for item in items:
        key = repr(item)
        if key not in seen:
            seen.add(key); out.append(item)
    return out

datas = uniq(datas)
binaries = uniq(binaries)
hiddenimports = sorted(set(hiddenimports))

analysis = Analysis(
    ["packaging/desktop_entry.py"],
    pathex=pathex,
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(analysis.pure)
exe = EXE(
    pyz,
    analysis.scripts,
    [],
    exclude_binaries=True,
    name="VeriCorpus",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
coll = COLLECT(
    exe,
    analysis.binaries,
    analysis.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="VeriCorpus",
)
