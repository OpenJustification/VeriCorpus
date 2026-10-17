from __future__ import annotations

import json
from pathlib import Path
import pytest

from vericorpus.config import settings_for_profile
from vericorpus.desktop import _bundle_profile, supported_profiles


def test_profile_matrix():
    assert supported_profiles("lite") == ["lite"]
    assert supported_profiles("standard") == ["lite", "standard"]
    assert supported_profiles("verified") == ["lite", "standard", "verified"]
    assert settings_for_profile("lite").use_docling is False
    assert settings_for_profile("standard").use_docling is True
    assert settings_for_profile("verified").use_tesseract is True


def test_build_pyinstaller_profile_options():
    import sys
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
    from build_desktop import build_args
    for profile in ("lite", "standard", "verified"):
        args = build_args(profile)
        assert "--windowed" in args
        assert "--onedir" in args
        assert ("paddleocr" in args) is (profile != "lite")
    with pytest.raises(ValueError):
        build_args("full")


def test_developer_profile_can_be_selected(monkeypatch):
    monkeypatch.setenv("VERICORPUS_BUNDLE_PROFILE", "standard")
    assert _bundle_profile() == "standard"
