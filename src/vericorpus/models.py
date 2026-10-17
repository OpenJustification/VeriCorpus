# SPDX-License-Identifier: AGPL-3.0-or-later
from __future__ import annotations

from pydantic import BaseModel, Field
from typing import Literal


class BBox(BaseModel):
    x0: float
    y0: float
    x1: float
    y1: float

    @property
    def width(self) -> float:
        return max(0.0, self.x1 - self.x0)

    @property
    def height(self) -> float:
        return max(0.0, self.y1 - self.y0)


ContentType = Literal[
    "text",
    "title",
    "author",
    "affiliation",
    "abstract",
    "keywords",
    "heading",
    "paragraph",
    "list",
    "figure",
    "figure_caption",
    "table",
    "table_caption",
    "table_footnote",
    "equation",
    "equation_number",
    "code",
    "algorithm",
    "identifier",
    "header",
    "footer",
    "page_number",
    "footnote",
    "reference_header",
    "reference_entry",
    "unknown",
]


class SpanEvidence(BaseModel):
    engine: str
    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: BBox | None = None
    page_number: int
    content_type: ContentType = "text"
    metadata: dict = Field(default_factory=dict)


class Candidate(BaseModel):
    engine: str
    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    spans: list[SpanEvidence] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class DocumentObject(BaseModel):
    object_id: str
    page_number: int
    object_type: ContentType
    bbox: BBox
    text: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    column_index: int | None = None
    reading_order: int | None = None
    source: str = "pymupdf_layout"
    child_ids: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


class PageStructure(BaseModel):
    page_number: int
    width: float
    height: float
    column_count: int = Field(default=1, ge=1, le=8)
    layout_type: Literal["single_column", "multi_column", "mixed", "image_only", "unknown"] = "unknown"
    objects: list[DocumentObject] = Field(default_factory=list)
    reading_order: list[str] = Field(default_factory=list)
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    reading_order_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    complexity_score: float = Field(default=0.0, ge=0.0, le=1.0)
    complexity_reasons: list[str] = Field(default_factory=list)
    diagnostics: dict = Field(default_factory=dict)


class QualityVector(BaseModel):
    text_fidelity: float = Field(default=0.0, ge=0.0, le=1.0)
    reading_order: float = Field(default=0.0, ge=0.0, le=1.0)
    layout: float = Field(default=0.0, ge=0.0, le=1.0)
    tables: float = Field(default=1.0, ge=0.0, le=1.0)
    equations: float = Field(default=1.0, ge=0.0, le=1.0)
    unicode: float = Field(default=1.0, ge=0.0, le=1.0)
    numeric_fidelity: float = Field(default=1.0, ge=0.0, le=1.0)
    structure: float = Field(default=0.0, ge=0.0, le=1.0)
    overall: float = Field(default=0.0, ge=0.0, le=1.0)
    calibration: Literal["heuristic", "benchmark_calibrated"] = "heuristic"


class TrainingReadiness(BaseModel):
    status: Literal["accepted", "partial", "reprocess", "rejected"] = "rejected"
    score: float = Field(default=0.0, ge=0.0, le=1.0)
    blocking_issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    verification_grade: Literal[
        "source_only",
        "source_plus_layout",
        "cross_family",
        "cross_family_high_risk_verified",
    ] = "source_only"


class Disagreement(BaseModel):
    disagreement_id: str
    page_number: int
    anchor_engine: str = ""
    anchor_start: int = 0
    anchor_end: int = 0
    bbox: BBox | None = None
    left_context: str = ""
    right_context: str = ""
    alternatives: dict[str, str] = Field(default_factory=dict)
    content_type: ContentType = "text"
    high_risk: bool = False
    severity: float = Field(default=0.0, ge=0.0, le=1.0)


class AIJudgment(BaseModel):
    provider: str
    status: Literal["supported", "unresolved", "reject"]
    text: str = ""
    confidence: float = 0.0
    rationale_code: str = ""
    disagreement_id: str = ""


class LedgerEntry(BaseModel):
    ledger_id: str
    document_id: str
    source_file: str
    page_number: int
    bbox: BBox | None = None
    content_type: str
    original_alternatives: dict[str, str] = Field(default_factory=dict)
    selected_text: str = ""
    evidence_engines: list[str] = Field(default_factory=list)
    ai_judgments: list[AIJudgment] = Field(default_factory=list)
    decision: Literal["accepted", "rejected", "unresolved"]
    reason: str
    confidence: float = 0.0
    high_risk: bool = False


class PageRecord(BaseModel):
    document_id: str
    source_file: str
    page_number: int
    candidates: list[Candidate]
    structure: PageStructure | None = None
    quality: QualityVector | None = None
    readiness: TrainingReadiness | None = None
    routing: dict = Field(default_factory=dict)
    disagreements: list[Disagreement] = Field(default_factory=list)
    ledger_entries: list[LedgerEntry] = Field(default_factory=list)
    selected_text: str = ""
    agreement: float = 0.0
    selected_quality: float = 0.0
    unresolved_spans: int = 0
    decision: Literal["accepted", "partial", "reprocess", "rejected"] = "rejected"
    decision_reason: str = ""


class TrainingRecord(BaseModel):
    document_id: str
    source_file: str
    page_number: int
    text: str
    quality: float
    quality_dimensions: QualityVector | None = None
    training_readiness: TrainingReadiness | None = None
    provenance: dict


class SourceObjectLabel(BaseModel):
    source_type: Literal["latex", "jats", "docx", "unknown"]
    object_type: ContentType
    label: str = ""
    caption: str = ""
    anchor_text: str = ""
    source_location: str = ""
    page_number: int | None = None
    bbox: BBox | None = None
    aligned: bool = False
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    metadata: dict = Field(default_factory=dict)
