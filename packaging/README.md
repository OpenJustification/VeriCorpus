# Desktop packaging

VeriCorpus publishes **onedir** desktop bundles rather than self-extracting one-file executables.
This reduces antivirus heuristics and makes every bundled file inspectable.

Release artifacts:

- `VeriCorpus-0.1.0-Windows-x64-Lite.zip`
- `VeriCorpus-0.1.0-Windows-x64-Full.zip`
- `VeriCorpus-0.1.0-Linux-x86_64-Lite.tar.gz`
- `VeriCorpus-0.1.0-Linux-x86_64-Full.tar.gz`

Each archive contains a graphical `VeriCorpus` application. Windows uses `VeriCorpus.exe`.
Linux uses `VeriCorpus`.

The **Lite** build contains the deterministic born-digital PDF path and is the smallest release.
The **Full** build additionally bundles the Python packages required by the Standard profile
(PaddleOCR-VL and Docling). Model weights are not redistributed; users may allow a one-time
upstream model download, after which processing can remain offline.

Qwen and Nemotron remain catalogued/staged model packs. They are not allowed to affect output
until their constrained local adjudicator implementations pass the release integration suite.
