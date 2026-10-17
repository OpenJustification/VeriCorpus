# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import os
import runpy
import sys
from pathlib import Path


def test_desktop_entry_repairs_missing_console_streams(monkeypatch):
    entry = Path(__file__).resolve().parents[1] / "packaging" / "desktop_entry.py"

    monkeypatch.setattr(sys, "stdout", None)
    monkeypatch.setattr(sys, "stderr", None)
    monkeypatch.setattr(sys, "stdin", None)

    # Do not execute the UI/main function; execute the entry module with a
    # non-__main__ run name so we only test its early runtime setup.
    runpy.run_path(str(entry), run_name="vericorpus_packaging_test")

    assert sys.stdout is not None
    assert sys.stderr is not None
    assert sys.stdin is not None
