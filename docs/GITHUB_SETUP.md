# GitHub setup guide

The repository is prepared for GitHub, but a few settings can only be enabled after the repository exists.

## 1. Create the repository

Create an empty GitHub repository named `vericorpus` (or your preferred name). Do not initialize it with another README/license because those files already exist here.

From this project directory:

```bash
git init
git add .
git commit -s -m "Initial VeriCorpus 0.1.0 release"
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
git tag -a v0.1.0 -m "VeriCorpus 0.1.0"
git push origin v0.1.0
```

The release workflow will run tests, build the wheel and source distribution, create SHA-256 checksums, build/smoke-test Windows and Linux desktop bundles (Lite and Full), scan them, and attach the artifacts to a GitHub **pre-release** while VeriCorpus remains alpha.

## 5. Repository URL placeholders

Because the final GitHub owner/repository URL was not known when this package was prepared, add the final project URLs to `pyproject.toml` and `CITATION.cff` after the repository exists. This is optional for GitHub operation but recommended before publishing to PyPI or citing the project.

## License verification

Before public publication, GitHub should detect the repository license as AGPL-3.0. The project metadata intentionally uses the SPDX expression `AGPL-3.0-or-later`.
