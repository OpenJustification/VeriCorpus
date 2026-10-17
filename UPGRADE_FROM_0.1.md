# Upgrade from VeriCorpus 0.1 to 0.2.0-alpha.1

This release changes the core acceptance model. Native PDF text is no longer treated as training-ready merely because it is extractable. The Document Structure Engine identifies layout and semantic objects before training text is flattened.

## Recommended GitHub Desktop update

1. Back up any local changes.
2. Extract this package.
3. Copy the package contents into the root of the local `VeriCorpus` repository, preserving `.github/`.
4. Allow replacement of existing project files.
5. In GitHub Desktop review the diff, commit `VeriCorpus 0.2.0-alpha training-readiness architecture`, and **Push origin**.
6. Confirm the normal **CI** workflow passes.
7. Run **Desktop bundles** manually and require all Windows/Linux Lite/Standard/Verified jobs to pass before tagging a release.
8. Test the extracted Windows bundle with a real PDF and Microsoft Defender before creating `v0.2.0a1`.

Do not copy downloaded model weights into Git. The repository tracks small model-registry/lock metadata but ignores common large weight formats.

## Output changes

Schema 2.0 adds document structure, object bounding boxes, routing decisions, multidimensional quality scores, training-readiness state, structured blocks, pretty JSON, and a Markdown training review. Consumers written only for the 0.1 schema should be updated before using 0.2 output.
