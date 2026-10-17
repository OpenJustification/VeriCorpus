# SPDX-License-Identifier: AGPL-3.0-or-later
"""Public plugin interfaces for third-party VeriCorpus integrations.

The API is intentionally small in the 0.x alpha line. Plugins are discovered via
Python entry points in the ``vericorpus.extractors`` group. A plugin must expose
an object with a stable ``name`` attribute and an ``extract`` method returning a
:class:`vericorpus.models.Candidate`.
"""
from __future__ import annotations

from importlib.metadata import entry_points
from typing import Protocol, runtime_checkable

import fitz

from .models import Candidate


ENTRY_POINT_GROUP = "vericorpus.extractors"


@runtime_checkable
class ExtractorPlugin(Protocol):
    """Minimal public interface for third-party extraction engines."""

    name: str

    def extract(self, page: fitz.Page, page_number: int, *, dpi: int = 300) -> Candidate:
        """Extract evidence from one PDF page without mutating the page."""
        ...


def discover_extractor_plugins() -> dict[str, ExtractorPlugin]:
    """Load installed extractor plugins registered through package entry points.

    Broken plugins are skipped so a third-party integration cannot prevent the core
    application from starting. Plugin failures during extraction should likewise be
    represented as local evidence failures rather than process-wide failures.
    """
    found: dict[str, ExtractorPlugin] = {}
    try:
        eps = entry_points(group=ENTRY_POINT_GROUP)
    except TypeError:  # compatibility with older importlib.metadata APIs
        eps = entry_points().get(ENTRY_POINT_GROUP, [])
    for ep in eps:
        try:
            plugin = ep.load()
            if isinstance(plugin, type):
                plugin = plugin()
            name = str(getattr(plugin, "name", ep.name)).strip() or ep.name
            if hasattr(plugin, "extract"):
                found[name] = plugin
        except Exception:
            continue
    return found
