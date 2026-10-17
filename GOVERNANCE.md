# VeriCorpus governance

VeriCorpus is an open-source project. Its technical direction should remain transparent,
reviewable, and driven by evidence rather than by a single vendor integration.

## Roles

- **Maintainer:** has merge and release authority and is responsible for security and release quality.
- **Core contributor:** a recurring contributor trusted to review one or more project areas.
- **Contributor:** anyone submitting issues, tests, documentation, benchmarks, code, or design proposals.

The repository owner acts as the initial maintainer. Additional maintainers may be added publicly as the
project grows.

## Decision making

Routine bug fixes and small features are decided through pull-request review. Significant changes to the
evidence model, public schemas, plugin APIs, licensing, security boundaries, or acceptance policy should
be proposed through an RFC in `rfcs/` and discussed publicly before merge.

Maintainers should prefer documented technical evidence, benchmark results, reproducibility, and backward
compatibility over vendor preference.

## Releases

Releases require passing CI, package-build validation, release metadata checks, and the documented release
checklist. Security fixes may use an expedited process when disclosure would create risk.

## Conflicts of interest

Maintainers should disclose material conflicts of interest when reviewing changes that substantially favor
a commercial service, model provider, or integration they control.

## License changes

A project-wide license change is considered a major governance action and should not be made silently. Rights already granted under previous releases are not withdrawn by a later release. Once outside contributions are accepted, changing to an unrelated license may also require permission from the relevant copyright holders unless another valid licensing mechanism applies.
