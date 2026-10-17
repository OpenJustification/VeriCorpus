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
from .layout import analyze_page
from .groundtruth import write_groundtruth
from .plugins import discover_extractor_plugins
from .corpus import validate_run

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
    """Prepare PDFs or EPUBs using a named local profile. The Standard bundle provides the optional OCR Python dependencies."""
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


@app.command("verify-output")
def verify_output_command(out: Path = typer.Argument(..., exists=True, file_okay=False)) -> None:
    """Validate checksums, provenance, training readiness and document-disjoint splits."""
    result = validate_run(out)
    console.print_json(data=result)
    if result["status"] != "PASS":
        raise typer.Exit(1)


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


@app.command("inspect-layout")
def inspect_layout_command(
    pdf: Path = typer.Argument(..., exists=True, readable=True),
    page: int = typer.Option(1, "--page", "-p", min=1),
) -> None:
    """Inspect VeriCorpus Document Structure Engine output for one PDF page."""
    import fitz

    doc = fitz.open(pdf)
    try:
        if page > len(doc):
            raise typer.BadParameter(f"PDF has only {len(doc)} page(s)")
        structure = analyze_page(doc[page - 1], page)
        console.print_json(data=structure.model_dump())
    finally:
        doc.close()


@app.command("groundtruth")
def groundtruth_command(
    source: Path = typer.Argument(..., exists=True, readable=True, help="LaTeX, JATS XML, or DOCX source manuscript"),
    pdf: Path = typer.Argument(..., exists=True, readable=True, help="Rendered/published PDF to align against"),
    out: Path = typer.Option(Path("vericorpus_groundtruth.jsonl"), "--out", "-o"),
) -> None:
    """Create object labels from structured submission files and align text anchors to the PDF."""
    result = write_groundtruth(source, pdf, out)
    console.print_json(data=result)


if __name__ == "__main__":
    app()
