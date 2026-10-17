# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import os
import sys

# PyInstaller windowed/noconsole applications on Windows intentionally have no
# standard console streams. Some application/library code still expects these
# objects to exist, so provide harmless sinks before importing VeriCorpus.
# This preserves a GUI-only application while preventing NoneType stream errors.
if sys.stdout is None:
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
if sys.stderr is None:
    sys.stderr = open(os.devnull, "w", encoding="utf-8")
if sys.stdin is None:
    sys.stdin = open(os.devnull, "r", encoding="utf-8")

from vericorpus.desktop import main

if __name__ == "__main__":
    raise SystemExit(main())
