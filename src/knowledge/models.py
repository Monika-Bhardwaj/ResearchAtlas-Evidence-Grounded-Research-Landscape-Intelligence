"""Knowledge-state models (Sections 8, 9, 15, 16).

Provenance is the core of the model: the three allowed types, their required fields, and the
absence of any UNKNOWN / UNSOURCED / LLM_INFERRED type are enforced HERE, at construction time.
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, Literal, Optional, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.ids import ID_PATTERN, PAPER_ID_PATTERN
from src.ontology.enums import (
    METADATA_FIELDS,
    TEXT_FIELDS,
    EntityType,
    ProvenanceType,
    RelationType,
    SourceField,
)

EDGE_ID_PATTERN = r"^edge_[0-9]{4,}$"
RULE_ID_PATTERN = r"^[A-Za-z][A-Za-z0-9_.\-]*$"
CURATION_REF_PATTERN = r"^cur_[0-9]{4,}$"


class Attribution(str, Enum):
    """Who reports a limitation (REPORTS_LIMITATION only)."""

    SELF_REPORTED = "SELF_REPORTED"  # the reporting paper proposes the method
    THIRD_PARTY = "THIRD_PARTY"      # the reporting paper does not propose the method


class IdentityStatus(str, Enum):
    RESOLVED = "RESOLVED"
    AMBIGUOUS = "AMBIGUOUS"          # never silently merged (Section 12)


class MetadataStatus(str, Enum):
    COMPLETE = "COMPLETE"
    PARTIAL_METADATA = "PARTIAL_METADATA"  # Section 27: mark, do not fabricate


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Provenance(_Frozen):
    type: ProvenanceType
    source_field: Optional[SourceField] = None
    rule_id: Optional[str] = Field(default=None, pattern=RULE_ID_PATTERN)
    mapping_decision: Optional[str] = Field(default=None, min_length=1)
    evidence: Optional[str] = Field(default=None, min_length=1)
    source_paper_id: Optional[str] = Field(default=None, pattern=PAPER_ID_PATTERN)
    curated_by: Optional[str] = Field(default=None, min_length=1)
    curation_ref: Optional[str] = Field(default=None, pattern=CURATION_REF_PATTERN)
    attribution: Optional[Attribution] = None
    ontology_version: str = Field(min_length=1)
    knowledge_build_version: str = Field(min_length=1)

    @model_validator(mode="after")
    def _required_fields_by_type(self) -> "Provenance":
        t = self.type
        if t == ProvenanceType.EXPLICIT_METADATA:
            if self.source_field is None or self.source_field not in METADATA_FIELDS:
                raise ValueError("EXPLICIT_METADATA requires source_field in the bibliographic metadata fields")
            if self.rule_id or self.curated_by or self.curation_ref:
                raise ValueError("EXPLICIT_METADATA must not carry rule_id / curated_by / curation_ref")
        elif t == ProvenanceType.RULE_DERIVED:
            missing = [n for n in ("rule_id", "mapping_decision", "evidence") if not getattr(self, n)]
            if missing:
                raise ValueError(f"RULE_DERIVED requires {missing}")
            if self.source_field is None or self.source_field not in TEXT_FIELDS:
                raise ValueError("RULE_DERIVED requires source_field in {title, abstract, citation_context}")
            if self.curated_by or self.curation_ref:
                raise ValueError("RULE_DERIVED must not carry curated_by / curation_ref")
        elif t == ProvenanceType.MANUALLY_CURATED:
            if not self.curated_by or not self.curation_ref:
                raise ValueError("MANUALLY_CURATED requires curated_by and curation_ref")
            if self.source_field != SourceField.CURATION_FILE:
                raise ValueError("MANUALLY_CURATED requires source_field == curation_file")
            if self.rule_id:
                raise ValueError("MANUALLY_CURATED must not carry a rule_id")
        return self


class Entity(_Frozen):
    id: str = Field(pattern=ID_PATTERN)
    type: EntityType
    label: str = Field(min_length=1)
    aliases: Tuple[str, ...] = ()
    definition: Optional[str] = None
    attributes: Dict[str, Any] = Field(default_factory=dict)


class Edge(_Frozen):
    edge_id: str = Field(pattern=EDGE_ID_PATTERN)
    source: str = Field(pattern=ID_PATTERN)
    relation: RelationType
    target: str = Field(pattern=ID_PATTERN)
    provenance: Provenance
    corroborating_provenance: Tuple[Provenance, ...] = ()
    confidence: float = Field(ge=0.0, le=1.0)


class AmbiguityRecord(_Frozen):
    """Section 15: ambiguous terms are represented, never silently resolved."""

    input: str = Field(min_length=1)
    status: Literal["AMBIGUOUS"] = "AMBIGUOUS"
    candidates: Tuple[str, ...] = Field(min_length=2)


class BuildMetadata(_Frozen):
    generator: str = Field(min_length=1)
    git_sha: Optional[str] = None
    config_hash: Optional[str] = None
    notes: Optional[str] = None


class Integrity(_Frozen):
    content_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class KnowledgeState(_Frozen):
    schema_version: str = Field(min_length=1)
    ontology_version: str = Field(min_length=1)
    corpus_version: str = Field(min_length=1)
    knowledge_build_version: str = Field(min_length=1)
    build_metadata: BuildMetadata
    integrity: Integrity
    entities: Tuple[Entity, ...]
    relationships: Tuple[Edge, ...]
    ambiguities: Tuple[AmbiguityRecord, ...] = ()
