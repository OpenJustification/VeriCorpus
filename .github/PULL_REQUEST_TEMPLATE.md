## Summary

What does this change do?

## Why

What failure mode or capability does it address?

## Verification

- [ ] `python -m compileall -q src`
- [ ] `python -m ruff check src tests`
- [ ] `python -m pytest -q`
- [ ] User-visible changes documented in `CHANGELOG.md`

## Evidence/safety impact

- [ ] Provenance is preserved.
- [ ] No new path allows generative models to silently introduce unsupported high-risk content.
- [ ] Optional heavy dependencies fail locally and do not break the core pipeline.
