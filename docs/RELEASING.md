# Release process

VeriCorpus uses semantic version tags such as `v0.1.0`.

## Pre-release checklist

1. Update `src/vericorpus/__init__.py`.
2. Update `CHANGELOG.md`.
3. Update `CITATION.cff` version and release date.
4. Confirm `pyproject.toml`, `CITATION.cff`, `NOTICE`, and `LICENSE` remain consistent with `AGPL-3.0-or-later`.
5. Confirm `docs/SCHEMA.md` matches `__schema_version__`.
6. Run the local checks:

```bash
python -m compileall -q src scripts packaging
python -m ruff check src tests scripts packaging
python -m pytest -q
python -m vericorpus.desktop --self-test
python scripts/release_check.py
python scripts/license_check.py
python -m build
python -m twine check dist/*
```

7. Commit and push.
8. Create and push the tag:

```bash
git tag -a v0.1.0 -m "VeriCorpus 0.1.0"
git push origin v0.1.0
```

The GitHub release workflow builds a wheel/source distribution plus Windows x64 and Linux x86_64 Lite/Full desktop bundles, executes packaged self-tests, runs antivirus release gates, generates SHA-256 checksums and GitHub provenance attestations, and creates a GitHub **pre-release** using `RELEASE_NOTES_v0.1.0.md` while VeriCorpus remains alpha. Remove the `--prerelease` flag only when the project is ready for stable releases.

## PyPI

The included GitHub workflow intentionally creates GitHub Release artifacts only. Publishing to PyPI should be enabled separately after the package name, ownership, and trusted-publishing configuration are confirmed.
