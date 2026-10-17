# SPDX-License-Identifier: AGPL-3.0-or-later
from dataclasses import dataclass, field, replace
from pathlib import Path


@dataclass
class Settings:
    # Reference profile is local/open only. Missing optional engines are recorded and skipped.
    profile: str = "standard"
    deterministic: bool = True
    seed: int = 20261016
    offline: bool = True
    model_lock_path: Path | None = None

    use_tesseract: bool = True
    use_paddleocr: bool = True
    use_docling: bool = True
    use_glmocr: bool = False
    use_olmocr: bool = False
    use_qwen_judge: bool = False
    use_nemotron_judge: bool = False

    native_good_threshold: float = 0.88
    min_engine_confidence: float = 0.50
    span_agreement_threshold: float = 0.93
    page_accept_quality: float = 0.80
    render_dpi: int = 300
    disagreement_context_chars: int = 220
    reject_page_if_unresolved_fraction_gt: float = 0.15

    # Fixed decoding settings for local generative adjudicators.
    temperature: float = 0.0
    do_sample: bool = False
    enabled_engines: list[str] = field(default_factory=list)


def settings_for_profile(profile: str, **overrides) -> Settings:
    """Return conservative desktop defaults for a named local profile."""
    name = profile.lower().strip()
    if name == "lite":
        base = Settings(
            profile="lite",
            use_tesseract=False,
            use_paddleocr=False,
            use_docling=False,
            use_glmocr=False,
            use_olmocr=False,
        )
    elif name == "standard":
        base = Settings(
            profile="standard",
            use_tesseract=False,
            use_paddleocr=True,
            use_docling=True,
            use_glmocr=False,
            use_olmocr=False,
        )
    elif name == "verified":
        base = Settings(
            profile="verified",
            use_tesseract=True,
            use_paddleocr=True,
            use_docling=True,
            use_glmocr=True,
            use_olmocr=True,
            # Qwen/Nemotron remain optional adjudicator packs until their local
            # runtimes pass the same integration-test bar as the parser stack.
            use_qwen_judge=False,
            use_nemotron_judge=False,
        )
    else:
        raise ValueError(f"Unknown profile: {profile}")
    valid = set(Settings.__dataclass_fields__)
    bad = set(overrides) - valid
    if bad:
        raise TypeError(f"Unknown Settings field(s): {', '.join(sorted(bad))}")
    return replace(base, **overrides)
