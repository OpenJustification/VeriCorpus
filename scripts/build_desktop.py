# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import argparse
import os
from pathlib import Path
import sys


def build_args(flavor: str) -> list[str]:
    flavor = flavor.strip().lower()
    if flavor not in {"lite", "full"}:
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

    if flavor == "full":
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
        choices=("lite", "full"),
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
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
