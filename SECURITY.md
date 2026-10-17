# Security policy

## Supported versions

The latest tagged **0.2.x** alpha release is the supported development line.

## Reporting vulnerabilities

Please do not publish exploitable security issues in a public issue. Use GitHub's private vulnerability reporting/security advisory mechanism when available.

## Document threat model

Documents are untrusted input. Parsers may encounter malformed PDFs, decompression bombs, huge images, malicious embedded content, or prompt-like text. Run high-risk corpora in containers/sandboxes with filesystem, CPU, memory, GPU, and network limits.

The official reference profile is **offline by default**. Built-in GLM-OCR integration forces its model endpoint to localhost; olmOCR is invoked without a remote `--server`; VeriCorpus does not ship proprietary hosted-model adapters.

Third-party plugins execute Python code in the VeriCorpus process and therefore have the same privileges as the user. Install plugins only from sources you trust.

Never commit API keys, private documents, model credentials, or confidential output datasets to the repository.
