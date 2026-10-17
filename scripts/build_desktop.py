# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


def build_args(flavor: str) -> list[str]:
    flavor = flavor.strip().lower()
    if flavor not in {"lite", "standard", "verified"}:
        raise ValueError(f"Unsupported bundle flavor: {flavor}")

    args = [
        "--noconfirm",
        "--clean",
        "--log-level",
        "INFO",
        "--onedir",
        "--windowed",
        "--name",
        "VeriCorpus",
        "--paths",
        "src",
        "--collect-all",
        "vericorpus",
        "--collect-all",
        "pymupdf",
        "--hidden-import",
        "fitz",
        "--copy-metadata",
        "vericorpus",
        "--copy-metadata",
        "PyMuPDF",
        "--copy-metadata",
        "Pillow",
        "--copy-metadata",
        "pydantic",
        "packaging/desktop_entry.py",
    ]

    if flavor in {"standard", "verified"}:
        for package in [
            "paddle",
            "paddleocr",
            "paddlex",
            "docling",
            "huggingface_hub",
            "transformers",
        ]:
            args += ["--collect-all", package]

        for distribution in [
            "paddlepaddle",
            "paddleocr",
            "paddlex",
            "docling",
            "huggingface-hub",
            "transformers",
        ]:
            args += ["--copy-metadata", distribution]

    return args


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--flavor",
        choices=("lite", "standard", "verified"),
        default=os.environ.get("VERICORPUS_BUNDLE", "lite"),
    )
    parser.add_argument("--print-only", action="store_true")
    ns = parser.parse_args(argv)

    args = build_args(ns.flavor)
    print("VeriCorpus PyInstaller build")
    print("Flavor:", ns.flavor)
    print("Python:", sys.version)
    print("Working directory:", Path.cwd())
    print("PyInstaller arguments:")
    for item in args:
        print(" ", item)

    if ns.print_only:
        return 0

    from PyInstaller.__main__ import run as pyinstaller_run
    pyinstaller_run(args)

    expected = Path("dist") / "VeriCorpus"
    if not expected.exists():
        raise RuntimeError(f"PyInstaller completed but {expected} was not created")
    # Explicit runtime capability marker. Used by desktop app to restrict its profile selector.
    from vericorpus import __version__
    import json
    from vericorpus.desktop import supported_profiles
    profile_file = expected / "BUNDLE_PROFILE.json"
    profile_file.write_text(json.dumps({"version": __version__, "bundle_profile": ns.flavor,
        "supported_profiles": supported_profiles(ns.flavor),
        "note": "Model weights and independent external OCR tools are not necessarily bundled."},
        indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
