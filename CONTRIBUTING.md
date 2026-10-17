# Contributing to VeriCorpus

Thank you for contributing. VeriCorpus is an evidence-first data-quality project, so changes that increase extraction recall must not silently reduce provenance or safety guarantees.

All commits contributed for inclusion must carry a Developer Certificate of Origin sign-off. Use `git commit -s`. By signing off, you certify the contribution under the terms in [DCO.md](DCO.md).

## Development setup

```bash
python -m venv .venv
python -m pip install -U pip
python -m pip install -e ".[dev]"
```

Tesseract is required for the integration test. Optional engines are not required for the core unit suite.

## Before opening a pull request

Run:

```bash
python -m compileall -q src
python -m ruff check src tests
python -m pytest -q
```

For packaging changes, also run:

```bash
python -m build
python -m twine check dist/*
```

## Pull request expectations

- Explain the failure mode or capability being changed.
- Add or update tests for behavior changes.
- Preserve provenance for any transformed text.
- Do not allow generative models to introduce unsupported high-risk content.
- Keep optional heavy dependencies behind extras/adapters.
- Update `CHANGELOG.md` for user-visible changes.
- Sign every contributed commit with `Signed-off-by:` (`git commit -s`).
- Use an RFC for public-schema, plugin-API, evidence-policy, licensing, or other major architectural changes.
- Follow [AI_POLICY.md](AI_POLICY.md) for AI-assisted contributions.

## Adding an extraction engine

Third-party packages should prefer the public `vericorpus.plugins.ExtractorPlugin` interface and the `vericorpus.extractors` Python entry-point group. Built-in adapters may live in the core repository when justified.

An engine adapter should:

1. identify itself with a stable engine name;
2. return text plus confidence when available;
3. preserve page coordinates when available;
4. expose structured content labels where possible;
5. fail locally without terminating the entire document pipeline;
6. never overwrite another engine's evidence.

## Tests

Unit tests should be deterministic and should not require network access or API keys. Provider and heavy-engine integrations should be isolated and skipped when unavailable.
