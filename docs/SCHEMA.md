# VeriCorpus output schema

Current schema version: **1.0**

Every JSONL row includes:

```json
{
  "vericorpus_schema": "1.0",
  "generator": "vericorpus",
  "generator_version": "0.1.0"
}
```

`manifest.json` additionally records the reference profile, settings hash, source hashes, runtime/package fingerprint, deterministic settings, model lock/hash, engine availability, and reproducibility grade.

Schema changes that remove or reinterpret existing fields require a documented migration path before 1.0.
