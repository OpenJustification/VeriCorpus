# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> int:
    if len(sys.argv) != 2:
        raise SystemExit("usage: verify_bundle.py PATH_TO_EXECUTABLE")
    exe = Path(sys.argv[1]).resolve()
    if not exe.exists():
        raise SystemExit(f"missing executable: {exe}")
    cp = subprocess.run([str(exe), "--self-test"], capture_output=True, text=True, timeout=180)
    if cp.returncode != 0:
        print(cp.stdout)
        print(cp.stderr, file=sys.stderr)
        raise SystemExit("desktop binary self-test failed")
    last = (cp.stdout.strip().splitlines() or [""])[-1]
    data = json.loads(last)
    if data.get("status") != "PASS" or data.get("version") != "0.2.0a1":
        raise SystemExit(f"unexpected self-test result: {data}")
    print(json.dumps({"binary": str(exe), "sha256": sha256(exe), "self_test": data}, indent=2, sort_keys=True))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
