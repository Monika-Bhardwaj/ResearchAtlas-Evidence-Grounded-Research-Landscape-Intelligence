"""Pydantic model of the ontology YAML (the structure; cross-checks live in the loader)."""
from __future__ import annotations

from typing import Dict, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.ontology.enums import (
    EntitySource,
    ExpectedPrecision,
    ProvenanceType,
    RelationStatus,
    RelationType,
)


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Estimate(_Frozen):
    """Planning estimates made BEFORE any corpus or rule exists. Not quotas."""

    edges: Tuple[int, int]
    curated_edges: Tuple[int, int]
    curation_minutes_per_edge: Tuple[float, float]

    @model_validator(mode="after")
    def _sane(self) -> "Estimate":
        for name in ("edges", "curated_edges", "curation_minutes_per_edge"):
            lo, hi = getattr(self, name)
            if lo < 0 or hi < lo:
                raise ValueError(f"{name} must satisfy 0 <= min <= max, got {(lo, hi)}")
        if self.curated_edges[1] > self.edges[1]:
            raise ValueError("curated_edges max cannot exceed edges max")
        return self


class EntitySpec(_Frozen):
    id_prefix: str = Field(pattern=r"^[a-z]+$")
    entity_source: EntitySource
    definition: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    required_attributes: Tuple[str, ...] = ()


class ReasonOnly(_Frozen):
    reason: str = Field(min_length=1)


class RelationSpec(_Frozen):
    category: Literal["bibliographic", "research_structure", "evidence", "research_direction"]
    domain: Tuple[str, ...] = Field(min_length=1)
    range: Tuple[str, ...] = Field(min_length=1)
    status: RelationStatus
    definition: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    allowed_provenance: Tuple[ProvenanceType, ...]
    primary_source: str  # a ProvenanceType value, or "NONE" for relations that are never stored
    expected_precision: ExpectedPrecision
    failure_modes: Tuple[str, ...] = ()
    estimate: Estimate
    estimate_note: str = Field(min_length=1)
    inverse_of: Optional[RelationType] = None
    mirror_of: Optional[RelationType] = None
    symmetric: bool = False
    requires_source_paper: bool = False
    requires_evidence: bool = False
    requires_attribution: bool = False
    range_extension: bool = False  # True when the range was widened beyond the plain Section 7 reading
    range_semantics: Optional[Dict[str, str]] = None


class OntologySpec(_Frozen):
    ontology_version: str = Field(min_length=1)
    schema_version: str = Field(min_length=1)
    entities: Dict[str, EntitySpec]
    deferred_entities: Dict[str, ReasonOnly]
    excluded_entities: Dict[str, ReasonOnly]
    non_relations: Dict[str, str]
    relations: Dict[str, RelationSpec]
