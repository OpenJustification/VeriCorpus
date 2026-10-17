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


class SpanEvidence(BaseModel):
    engine: str
    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    bbox: BBox | None = None
    page_number: int
    content_type: Literal["text", "table", "equation", "code", "identifier", "unknown"] = "text"
    metadata: dict = Field(default_factory=dict)


class Candidate(BaseModel):
    engine: str
    text: str
    confidence: float = Field(ge=0.0, le=1.0)
    spans: list[SpanEvidence] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


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
    content_type: Literal["text", "table", "equation", "code", "identifier", "unknown"] = "text"
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
    disagreements: list[Disagreement] = Field(default_factory=list)
    ledger_entries: list[LedgerEntry] = Field(default_factory=list)
    selected_text: str = ""
    agreement: float = 0.0
    selected_quality: float = 0.0
    unresolved_spans: int = 0
    decision: Literal["accepted", "partial", "rejected"] = "rejected"
    decision_reason: str = ""


class TrainingRecord(BaseModel):
    document_id: str
    source_file: str
    page_number: int
    text: str
    quality: float
    provenance: dict
