"""Runtime output contract (Sections 20, 22, 26, 30, 53 and Patch 10).

Tension status values are OUTPUT/EVALUATION labels. They are not ontology relations and are
never stored in the knowledge state.
"""
from __future__ import annotations

import re
from enum import Enum
from typing import List, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from src.ids import PAPER_ID_PATTERN

INSUFFICIENT_MESSAGE = "Insufficient evidence in the indexed corpus."

# System-authored text must never claim novelty of the proposal (Section 20).
NOVELTY_CLAIM_RE = re.compile(
    r"\b(?:this|your|the)\s+(?:proposal|research|idea|work)\s+(?:is|appears|seems)\s+(?:\w+\s+)?novel\b"
    r"|\bno prior work (?:exists|has been)\b",
    re.IGNORECASE,
)


class PositioningLabel(str, Enum):
    WELL_EXPLORED = "WELL_EXPLORED"
    PARTIALLY_EXPLORED = "PARTIALLY_EXPLORED"
    UNDERREPRESENTED = "UNDERREPRESENTED"
    UNKNOWN = "UNKNOWN"          # a positioning CLASS; distinct from the ABSTAIN decision


class EvidenceSufficiency(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INSUFFICIENT = "INSUFFICIENT"


class ClaimBasis(str, Enum):
    """Section 53: every output claim falls into exactly one of these."""

    DIRECTLY_SUPPORTED = "DIRECTLY_SUPPORTED"
    RULE_DERIVED = "RULE_DERIVED"
    AGGREGATED_FROM_EVIDENCE = "AGGREGATED_FROM_EVIDENCE"
    USER_PROVIDED = "USER_PROVIDED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


class TensionStatus(str, Enum):
    CONFLICTING = "CONFLICTING"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"


_TRACEABLE = {ClaimBasis.DIRECTLY_SUPPORTED, ClaimBasis.RULE_DERIVED, ClaimBasis.AGGREGATED_FROM_EVIDENCE}


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceItem(_Frozen):
    basis: ClaimBasis
    edge_id: Optional[str] = None
    paper_id: Optional[str] = Field(default=None, pattern=PAPER_ID_PATTERN)
    source_field: Optional[str] = None
    fragment: Optional[str] = None
    rule_id: Optional[str] = None

    @model_validator(mode="after")
    def _traceable(self) -> "EvidenceItem":
        if self.basis in _TRACEABLE and not (self.edge_id or self.paper_id):
            raise ValueError(f"evidence with basis {self.basis.value} must reference an edge_id or paper_id")
        return self


class AmbiguousTerm(_Frozen):
    input: str = Field(min_length=1)
    status: str = Field(default="AMBIGUOUS", pattern=r"^AMBIGUOUS$")
    candidates: Tuple[str, ...] = Field(min_length=2)


class Facet(_Frozen):
    facet_id: str = Field(min_length=1)
    facet_text: str = Field(min_length=1)
    grounded_concepts: Tuple[str, ...] = ()
    ambiguous_terms: Tuple[AmbiguousTerm, ...] = ()
    unknown_terms: Tuple[str, ...] = ()


class ProposalGrounding(_Frozen):
    raw_text: str
    facets: Tuple[Facet, ...] = ()
    matched_concepts: Tuple[str, ...] = ()
    ambiguous_concepts: Tuple[AmbiguousTerm, ...] = ()
    unknown_concepts: Tuple[str, ...] = ()

    @model_validator(mode="after")
    def _unique_facets(self) -> "ProposalGrounding":
        ids = [f.facet_id for f in self.facets]
        if len(ids) != len(set(ids)):
            raise ValueError("facet_id values must be unique")
        return self


class PriorWorkItem(_Frozen):
    paper_id: str = Field(pattern=PAPER_ID_PATTERN)
    score: float = Field(ge=0.0, le=1.0)
    shared_concepts: Tuple[str, ...] = ()
    shared_methods: Tuple[str, ...] = ()
    evidence: Tuple[EvidenceItem, ...] = ()
    confidence: EvidenceSufficiency


class ReadingPathItem(_Frozen):
    rank: int = Field(ge=1)
    paper_id: str = Field(pattern=PAPER_ID_PATTERN)
    reason: str = Field(min_length=1)
    concepts_learned: Tuple[str, ...] = ()
    prerequisites: Tuple[str, ...] = ()
    relationship_to_proposal: str = Field(min_length=1)


class FacetPositioning(_Frozen):
    facet_id: str = Field(min_length=1)
    facet_text: str = Field(min_length=1)
    label: PositioningLabel
    abstain: bool                                   # ABSTAIN is a system decision, not a class
    confidence_score: float = Field(ge=0.0, le=1.0)  # continuous; ranks facets for risk-coverage
    evidence_sufficiency: EvidenceSufficiency
    evidence: Tuple[EvidenceItem, ...] = ()


class Tension(_Frozen):
    facet_id: str = Field(min_length=1)
    claim_id: Optional[str] = None                  # None for a facet-level INSUFFICIENT_EVIDENCE marker
    status: TensionStatus
    supporting_evidence: Tuple[EvidenceItem, ...] = ()
    challenging_evidence: Tuple[EvidenceItem, ...] = ()

    @model_validator(mode="after")
    def _conflicting_needs_both_sides(self) -> "Tension":
        if self.status == TensionStatus.CONFLICTING:
            if not self.supporting_evidence or not self.challenging_evidence:
                raise ValueError("CONFLICTING requires both supporting and challenging evidence")
            papers = {e.paper_id for e in self.supporting_evidence + self.challenging_evidence if e.paper_id}
            if len(papers) < 2:
                raise ValueError("CONFLICTING requires evidence from at least two distinct papers")
        return self


class LimitationReport(_Frozen):
    """An ATTRIBUTED assertion: 'paper P reports that method M has limitation L'."""

    method_id: str
    limitation_id: str
    reported_by: str = Field(pattern=PAPER_ID_PATTERN)
    attribution: str = Field(pattern=r"^(SELF_REPORTED|THIRD_PARTY)$")
    evidence: Tuple[EvidenceItem, ...] = Field(min_length=1)


class RuntimeOutput(_Frozen):
    request_id: str = Field(min_length=1)
    proposal: ProposalGrounding
    prior_work: Tuple[PriorWorkItem, ...] = ()
    reading_path: Tuple[ReadingPathItem, ...] = ()
    positioning: Tuple[FacetPositioning, ...] = ()
    tensions: Tuple[Tension, ...] = ()
    limitations: Tuple[LimitationReport, ...] = ()
    evidence_sufficiency: EvidenceSufficiency
    warnings: Tuple[str, ...] = ()

    @field_validator("reading_path")
    @classmethod
    def _ranks_contiguous(cls, v: Tuple[ReadingPathItem, ...]) -> Tuple[ReadingPathItem, ...]:
        ranks = [i.rank for i in v]
        if ranks != list(range(1, len(v) + 1)):
            raise ValueError("reading_path ranks must run 1..n in order")
        ids = [i.paper_id for i in v]
        if len(ids) != len(set(ids)):
            raise ValueError("reading_path must not repeat a paper")
        return v

    @model_validator(mode="after")
    def _cross_checks(self) -> "RuntimeOutput":
        facet_ids = {f.facet_id for f in self.proposal.facets}
        pos_ids = [p.facet_id for p in self.positioning]
        if len(pos_ids) != len(set(pos_ids)):
            raise ValueError("positioning must contain at most one entry per facet")
        if self.proposal.facets and set(pos_ids) != facet_ids:
            raise ValueError("positioning must cover exactly the proposal's facets")
        for t in self.tensions:
            if facet_ids and t.facet_id not in facet_ids:
                raise ValueError(f"tension references unknown facet {t.facet_id!r}")
        if self.evidence_sufficiency == EvidenceSufficiency.INSUFFICIENT and INSUFFICIENT_MESSAGE not in self.warnings:
            raise ValueError(f"INSUFFICIENT output must carry the warning {INSUFFICIENT_MESSAGE!r}")
        texts: List[str] = list(self.warnings)
        texts += [i.reason for i in self.reading_path] + [i.relationship_to_proposal for i in self.reading_path]
        for text in texts:
            if NOVELTY_CLAIM_RE.search(text):
                raise ValueError(f"system-authored text claims novelty (forbidden by Section 20): {text!r}")
        return self
