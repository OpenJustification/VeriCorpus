# GitHub setup guide

The repository is prepared for GitHub, but a few settings can only be enabled after the repository exists.

## 1. Create the repository

Create an empty GitHub repository named `vericorpus` (or your preferred name). Do not initialize it with another README/license because those files already exist here.

From this project directory:

```bash
git init
git add .
git commit -s -m "VeriCorpus 0.2.0-alpha training-readiness architecture"
git branch -M main
git remote add origin <YOUR-GITHUB-REPOSITORY-URL>
git push -u origin main
```

## 2. Recommended repository settings

Under GitHub repository settings:

- enable Issues;
- enable Discussions if you want community design conversations;
- enable Private vulnerability reporting / Security Advisories;
- allow GitHub Actions;
- keep Actions permissions at the minimum required by each workflow;
- enable Dependabot alerts and security updates;
- require the included **DCO** workflow as a branch-protection status check so pull requests enforce `Signed-off-by` commits;
- add a `CODEOWNERS` file after the maintainer GitHub handles are known.

## 3. Branch protection

For `main`, consider requiring:

- pull requests before merge;
- the CI workflow to pass;
- branches to be up to date before merge;
- conversation resolution before merge.

For a single-maintainer early alpha, you may start less strictly and tighten this before accepting outside contributions.

## 4. Create the first release

After the initial push passes CI:

```bash
git tag -a v0.2.0a1 -m "VeriCorpus 0.2.0-alpha.1"
git push origin v0.2.0a1
```

The tagged release workflow builds/tests Windows and Linux desktop bundles (Lite, Standard, Verified) and creates SHA-256 checksums, scan them, and attach the artifacts to a GitHub **pre-release** while VeriCorpus remains alpha.

## 5. Repository URL

The package metadata points to `https://github.com/OpenJustification/VeriCorpus`. Update those URLs only if the canonical repository changes.

## License verification

Before public publication, GitHub should detect the repository license as AGPL-3.0. The project metadata intentionally uses the SPDX expression `AGPL-3.0-or-later`.


For a normal GitHub Desktop push to `main`/`master`, the primary workflow is **Windows EXE - Lite Standard Verified** (`.github/workflows/windows-exe.yml`). It builds three Windows artifacts without a tag. See `BUILD_ALL_THREE_WINDOWS.md`.
