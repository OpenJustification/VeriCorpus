# Reproducibility

VeriCorpus distinguishes **auditable reproducibility** from impossible promises of universal bit-for-bit GPU identity.

## Every run

The manifest records source hashes, VeriCorpus/schema versions, settings/hash, deterministic seed/settings, runtime/package versions, engine availability, and **content fingerprints of configured local model/cache roots**. This lets another run verify which local model bytes were present even when an upstream framework manages its own cache.

## Strict locked run

A `vericorpus-model-lock-v1` file may contain expected `cache_fingerprints`. When a lock is supplied, VeriCorpus now:

1. requires offline mode;
2. hashes the configured local cache/model roots before processing;
3. refuses to start if they do not match the lock;
4. hashes them again after processing; and
5. refuses the run if those bytes changed.

Only a run that passes those checks receives the `locked-cache-verified` reproducibility grade. Merely supplying a lock filename is not sufficient.

To create a lock, first perform an ordinary offline/cached run, copy the desired SHA-256 values from `manifest.json` → `model_cache_fingerprints`, and place them into a copy of `models/model-lock.example.json`. Preserve the release ZIP and model/cache directory alongside the dataset for strongest reproducibility.

## Deterministic settings

VeriCorpus seeds Python, NumPy (if installed), and PyTorch (if installed), requests deterministic PyTorch algorithms, disables cuDNN benchmarking, and uses non-sampling decoding settings for compatible plugins.

Exact floating-point outputs can still differ across GPUs, kernels, quantizations, drivers, or libraries. For strict comparisons use the same desktop release artifact, model/cache bytes, hardware class, driver/runtime, and settings.
