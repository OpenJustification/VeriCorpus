from pathlib import Path
import os
import subprocess
import sys


def test_desktop_self_test_from_source(tmp_path: Path):
    env = os.environ.copy()
    env["PYTHONPATH"] = str(Path(__file__).resolve().parents[1] / "src")
    env["VERICORPUS_SELFTEST_OUTPUT"] = str(tmp_path / "result.json")
    cp = subprocess.run(
        [sys.executable, "-m", "vericorpus.desktop", "--self-test"],
        cwd=Path(__file__).resolve().parents[1],
        env=env,
        capture_output=True,
        text=True,
        timeout=60,
    )
    assert cp.returncode == 0, cp.stderr
    text = (tmp_path / "result.json").read_text(encoding="utf-8")
    assert '"status": "PASS"' in text
    assert '"version": "0.2.0a1"' in text


def test_desktop_packaging_files_present():
    root = Path(__file__).resolve().parents[1]
    for rel in [
        "packaging/vericorpus.spec",
        "packaging/desktop_entry.py",
        "packaging/requirements-bundle-lite.txt",
        "packaging/requirements-bundle-full.txt",
        ".github/workflows/desktop-build.yml",
        "docs/DESKTOP_RELEASES.md",
    ]:
        assert (root / rel).exists(), rel


def test_no_legacy_self_installing_bootstrap():
    root = Path(__file__).resolve().parents[1]
    for rel in [
        "portable_ui.py",
        "portable/VeriCorpus.cmd",
        ".github/workflows/portable-windows.yml",
    ]:
        assert not (root / rel).exists(), rel
