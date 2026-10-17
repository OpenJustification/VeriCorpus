# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import json
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel

from . import __schema_version__, __version__
from .benchmark import evaluate_jsonl
from .config import Settings, settings_for_profile
from .model_registry import load_registry, validate_registry
from .optional_adapters import availability
from .pipeline import prepare as run_prepare
from .plugins import discover_extractor_plugins

app = typer.Typer(add_completion=False, no_args_is_help=True)
console = Console()


@app.callback()
def main() -> None:
    """VeriCorpus: reproducible, evidence-first document preparation for LLM training."""


@app.command("prepare")
def prepare_command(
    input_path: Path = typer.Argument(..., exists=True, readable=True),
    out: Path = typer.Option(Path("vericorpus_output"), "--out", "-o"),
    profile: str = typer.Option("standard", "--profile", help="lite, standard, or verified"),
    model_lock: Path | None = typer.Option(None, "--model-lock", exists=True, readable=True),
    online: bool = typer.Option(False, "--online", help="Allow model frameworks to download missing local model assets."),
    seed: int = typer.Option(20261016, "--seed"),
    dpi: int = typer.Option(300, "--dpi", min=150, max=600),
) -> None:
    """Prepare PDFs using a named local profile. Standard is the full desktop-app profile."""
    settings = settings_for_profile(
        profile,
        seed=seed,
        offline=not online,
        model_lock_path=model_lock,
        render_dpi=dpi,
    )
    manifest = run_prepare(input_path, out, settings)
    console.print(Panel.fit(json.dumps(manifest, indent=2, default=str), title=f"VeriCorpus {__version__} complete"))


@app.command("engines")
def engines_command() -> None:
    """Show local parser availability."""
    status = availability()
    status["pymupdf_native"] = True
    status["third_party_plugins"] = sorted(discover_extractor_plugins())
    console.print_json(data=status)


@app.command("models")
def models_command() -> None:
    """Show the license-reviewed open reference model registry."""
    registry = load_registry()
    registry["validation_errors"] = validate_registry(registry)
    console.print_json(data=registry)


@app.command("doctor")
def doctor_command() -> None:
    """Show release, engine, model-policy, and reproducibility diagnostics."""
    registry = load_registry()
    report = {
        "vericorpus_version": __version__,
        "schema_version": __schema_version__,
        "reference_profile": "reference-open",
        "default_network_policy": "offline",
        "engines": {**availability(), "pymupdf_native": True},
        "third_party_extractor_plugins": sorted(discover_extractor_plugins()),
        "reference_registry_valid": not validate_registry(registry),
        "reference_models": [x["id"] for x in registry.get("models", [])],
        "note": "Reference VeriCorpus uses no proprietary API. Model weights are not redistributed by VeriCorpus.",
    }
    console.print_json(data=report)


@app.command("version")
def version_command() -> None:
    """Print the VeriCorpus version."""
    console.print(__version__)


@app.command("benchmark")
def benchmark_command(
    predicted: Path = typer.Argument(..., exists=True, readable=True),
    gold: Path = typer.Argument(..., exists=True, readable=True),
) -> None:
    """Compare training JSONL with a gold-standard JSONL."""
    console.print_json(data=evaluate_jsonl(predicted, gold))


if __name__ == "__main__":
    app()
