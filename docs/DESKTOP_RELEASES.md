# Desktop releases

VeriCorpus 0.1.0 publishes prebuilt graphical bundles for **Windows x64** and **Linux x86_64**.
The bundles are produced on GitHub-hosted runners from the tagged source and are release-gated by packaged-binary self-tests.

## Assets

- `VeriCorpus-0.1.0-Windows-x64-lite.zip`
- `VeriCorpus-0.1.0-Windows-x64-full.zip`
- `VeriCorpus-0.1.0-Linux-x86_64-lite.tar.gz`
- `VeriCorpus-0.1.0-Linux-x86_64-full.tar.gz`

### Lite

The Lite desktop build contains the graphical application and the born-digital PDF path. It is intended for clean PDFs with a usable embedded text layer and does not require model downloads.

### Full

The Full desktop build additionally bundles the Python software dependencies needed by the Standard profile, including PaddleOCR and Docling. **Model weights are not redistributed.** A user may permit a one-time upstream model download; after assets are cached in the extracted application directory, subsequent processing can run offline.

## Unpack and run

Windows:

1. Download the Windows ZIP.
2. Extract it to a writable folder.
3. Double-click `VeriCorpus.exe`.

Linux:

```bash
tar -xzf VeriCorpus-0.1.0-Linux-x86_64-full.tar.gz
cd VeriCorpus
./VeriCorpus
```

The bundles use PyInstaller **onedir** mode rather than a self-extracting one-file executable. The application does not bootstrap Python, run pip, or install itself after launch.

## Release gates

Before a desktop artifact is attached to a GitHub release, CI must:

1. run the source test suite;
2. build the desktop application from the tagged source;
3. execute the packaged binary with `--self-test` and verify a real PDF-to-JSONL Lite run;
4. include a build-info file, pip installation report, `pip freeze`, and third-party license inventory;
5. scan the Windows bundle with Microsoft Defender;
6. scan the Linux bundle with ClamAV;
7. generate SHA-256 checksums;
8. create GitHub build-provenance attestations.

## Antivirus and signing

The first public alpha is not code-signed unless the project maintainer configures a trusted signing certificate in the release workflow. Users should prefer artifacts attached by the official GitHub release workflow and verify the published SHA-256 checksum and GitHub provenance. The project does not ask users to disable antivirus or create Defender exclusions.

## Local data

Packaged builds keep `VeriCorpusData/` beside the executable after extraction. This contains local model/cache files and outputs. No proprietary API is required by the reference application.
