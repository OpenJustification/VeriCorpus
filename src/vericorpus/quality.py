# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

import math
import re

from .evidence import evidence_family
from .models import Candidate, PageStructure, QualityVector, TrainingReadiness
from .util import text_quality, unicode_quality


def _weighted_geometric(values: list[tuple[float, float]]) -> float:
    vals = [(max(1e-6, min(1.0, v)), w) for v, w in values if w > 0]
    if not vals:
        return 0.0
    total = sum(w for _, w in vals)
    return math.exp(sum(w * math.log(v) for v, w in vals) / total)


def _object_score(structure: PageStructure, object_type: str) -> float:
    objs = [o for o in structure.objects if o.object_type == object_type and not o.metadata.get("suppressed")]
    if not objs:
        return 1.0
    return sum(o.confidence for o in objs) / len(objs)


def quality_vector(
    text: str,
    structure: PageStructure,
    useful_candidates: list[Candidate],
    disagreement_count: int,
    unresolved: int,
    high_unresolved: int,
) -> QualityVector:
    text_fid = text_quality(text)
    uquality = unicode_quality(text)
    table_score = _object_score(structure, "table")
    equation_score = _object_score(structure, "equation")
    families = {evidence_family(c.engine, useful_candidates) for c in useful_candidates if c.text.strip()}

    # Numeric fidelity is not claimed as perfect from one parser family. Native
    # source geometry is still strong evidence, but cross-family corroboration is
    # rewarded. Any unresolved high-risk content is a hard penalty.
    if high_unresolved:
        numeric = 0.0
    elif len(families) >= 2:
        numeric = max(0.88, 1.0 - unresolved / max(disagreement_count, 1) * 0.25)
    else:
        numeric = 0.90 if re.search(r"\d", text) else 1.0

    structure_score = max(0.0, min(1.0, 0.55 * structure.confidence + 0.45 * structure.reading_order_confidence))
    overall = _weighted_geometric([
        (text_fid, 0.18),
        (structure.reading_order_confidence, 0.20),
        (structure.confidence, 0.14),
        (table_score, 0.12),
        (equation_score, 0.12),
        (uquality, 0.08),
        (numeric, 0.10),
        (structure_score, 0.06),
    ])
    if unresolved:
        overall *= max(0.4, 1.0 - min(0.45, unresolved * 0.06))
    return QualityVector(
        text_fidelity=text_fid,
        reading_order=structure.reading_order_confidence,
        layout=structure.confidence,
        tables=table_score,
        equations=equation_score,
        unicode=uquality,
        numeric_fidelity=max(0.0, min(1.0, numeric)),
        structure=structure_score,
        overall=max(0.0, min(1.0, overall)),
        calibration="heuristic",
    )


def training_readiness(
    q: QualityVector,
    structure: PageStructure,
    useful_candidates: list[Candidate],
    unresolved: int,
    high_unresolved: int,
    min_score: float,
) -> TrainingReadiness:
    blockers: list[str] = []
    warnings: list[str] = []
    if q.reading_order < 0.72:
        blockers.append("low_reading_order_confidence")
    if q.layout < 0.70:
        blockers.append("low_layout_confidence")
    if high_unresolved > 0:
        blockers.append("unresolved_high_risk_content")
    if q.unicode < 0.85:
        blockers.append("unicode_corruption")
    if q.text_fidelity < 0.72:
        blockers.append("low_text_fidelity")
    if q.tables < 0.72:
        blockers.append("low_table_confidence")
    if q.equations < 0.72:
        blockers.append("low_equation_confidence")

    families = {evidence_family(c.engine, useful_candidates) for c in useful_candidates if c.text.strip()}
    high_risk_present = structure.diagnostics.get("high_risk_objects", 0) > 0
    if len(families) >= 2 and high_risk_present and high_unresolved == 0:
        grade = "cross_family_high_risk_verified"
    elif len(families) >= 2:
        grade = "cross_family"
    elif structure.reading_order_confidence >= 0.8:
        grade = "source_plus_layout"
    else:
        grade = "source_only"

    if len(families) < 2 and structure.complexity_score >= 0.45:
        warnings.append("complex_page_has_single_evidence_family")
    if unresolved:
        warnings.append(f"unresolved_spans:{unresolved}")
    if q.calibration == "heuristic":
        warnings.append("quality_scores_are_heuristic_not_benchmark_calibrated")

    if blockers:
        status = "reprocess" if q.text_fidelity >= 0.5 else "rejected"
    elif q.overall >= min_score:
        status = "accepted"
    elif q.overall >= max(0.65, min_score - 0.12):
        status = "partial"
    else:
        status = "reprocess"

    return TrainingReadiness(
        status=status,
        score=q.overall,
        blocking_issues=blockers,
        warnings=warnings,
        verification_grade=grade,
    )
