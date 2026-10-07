"""Human-authored inputs: the approved vocabulary and the curated-edge file (Patch 11).

The coding agent supplies only the FORMAT and VALIDATION below. Content comes from the human
researcher. MANUALLY_CURATED edges must carry authorship == HUMAN. Only APPROVED entries are
used by a build; DRAFT entries are reported and ignored.
"""
from __future__ import annotations

from collections import defaultdict
from enum import Enum
from typing import Dict, List, Literal, Optional, Set, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.errors import Issue, Severity
from src.ids import ID_PATTERN, PAPER_ID_PATTERN
from src.knowledge.models import CURATION_REF_PATTERN, Attribution
from src.ontology.enums import EntitySource, EntityType, ProvenanceType, RelationStatus, RelationType, SourceField
from src.ontology.loader import Ontology


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ApprovalStatus(str, Enum):
    DRAFT = "DRAFT"
    APPROVED = "APPROVED"


class Approval(_Frozen):
    status: ApprovalStatus = ApprovalStatus.DRAFT
    approved_by: Optional[str] = Field(default=None, min_length=1)
    approved_on: Optional[str] = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")

    @model_validator(mode="after")
    def _approved_needs_who_and_when(self) -> "Approval":
        if self.status == ApprovalStatus.APPROVED and not (self.approved_by and self.approved_on):
            raise ValueError("APPROVED requires approved_by and approved_on")
        return self


# ---------------------------------------------------------------- vocabulary
class VocabularyEntry(_Frozen):
    id: str = Field(pattern=ID_PATTERN)
    type: EntityType
    label: str = Field(min_length=1)
    aliases: Tuple[str, ...] = ()
    definition: str = Field(min_length=1)
    drafted_with_ai: bool = False        # disclosure flag for approach.md section 7
    approval: Approval = Approval()


class AmbiguousTerm(_Frozen):
    input: str = Field(min_length=1)
    candidates: Tuple[str, ...] = Field(min_length=2)


class VocabularyFile(_Frozen):
    vocabulary_version: str = Field(min_length=1)
    entries: Tuple[VocabularyEntry, ...] = ()
    ambiguous_terms: Tuple[AmbiguousTerm, ...] = ()


# ---------------------------------------------------------------- curated edges
class EvidenceRef(_Frozen):
    paper_id: str = Field(pattern=PAPER_ID_PATTERN)
    source_field: Optional[SourceField] = None
    passage: str = Field(min_length=1)


class CuratedEdge(_Frozen):
    curation_id: str = Field(pattern=CURATION_REF_PATTERN)
    source: str = Field(pattern=ID_PATTERN)
    relation: RelationType
    target: str = Field(pattern=ID_PATTERN)
    rationale: str = Field(min_length=1)
    evidence: Tuple[EvidenceRef, ...] = ()
    attribution: Optional[Attribution] = None
    authorship: Literal["HUMAN"]          # attestation: authored by the human researcher
    curated_by: str = Field(min_length=1)
    approval: Approval = Approval()


class CurationFile(_Frozen):
    curation_version: str = Field(min_length=1)
    curator: str = Field(min_length=1)
    edges: Tuple[CuratedEdge, ...] = ()


def _err(code: str, msg: str, loc: str) -> Issue:
    return Issue(code=code, message=msg, location=loc, severity=Severity.ERROR)


def _warn(code: str, msg: str, loc: str) -> Issue:
    return Issue(code=code, message=msg, location=loc, severity=Severity.WARNING)


def approved_vocabulary(vocab: VocabularyFile) -> Tuple[VocabularyEntry, ...]:
    return tuple(e for e in vocab.entries if e.approval.status == ApprovalStatus.APPROVED)


def approved_curated_edges(cur: CurationFile) -> Tuple[CuratedEdge, ...]:
    return tuple(e for e in cur.edges if e.approval.status == ApprovalStatus.APPROVED)


def validate_vocabulary(vocab: VocabularyFile, onto: Ontology) -> List[Issue]:
    issues: List[Issue] = []
    prefix_map = onto.prefix_to_type()
    seen: Set[str] = set()
    alias_owners: Dict[str, Set[str]] = defaultdict(set)
    for e in vocab.entries:
        loc = f"vocabulary {e.id}"
        if e.id in seen:
            issues.append(_err("VOCAB_DUP_ID", "duplicate vocabulary id", loc))
        seen.add(e.id)
        if onto.spec.entities[e.type.value].entity_source != EntitySource.APPROVED_VOCABULARY:
            issues.append(_err("VOCAB_WRONG_SOURCE", f"{e.type.value} entities come from the corpus, not the vocabulary file", loc))
        prefix = e.id.split(":", 1)[0]
        if prefix_map.get(prefix) != e.type:
            issues.append(_err("VOCAB_PREFIX_MISMATCH", f"id prefix {prefix!r} does not belong to {e.type.value}", loc))
        if e.approval.status == ApprovalStatus.DRAFT:
            issues.append(_warn("VOCAB_DRAFT", "DRAFT entries are ignored by the build until approved", loc))
        for a in {e.label.lower(), *(x.lower() for x in e.aliases)}:
            alias_owners[a].add(e.id)
    declared = {t.input.lower(): set(t.candidates) for t in vocab.ambiguous_terms}
    for term, owners in alias_owners.items():
        if len(owners) > 1 and declared.get(term) != owners:
            issues.append(_err("VOCAB_UNDECLARED_AMBIGUITY",
                               f"term {term!r} maps to {sorted(owners)} but is not declared in ambiguous_terms with exactly those candidates "
                               "(ambiguity must be represented, never silently resolved)", "vocabulary"))
    for t in vocab.ambiguous_terms:
        missing = [c for c in t.candidates if c not in seen]
        if missing:
            issues.append(_err("VOCAB_AMBIGUITY_CANDIDATE", f"candidates not in vocabulary: {missing}", f"ambiguous term {t.input!r}"))
    return issues


def validate_curation(cur: CurationFile, onto: Ontology) -> List[Issue]:
    issues: List[Issue] = []
    seen: Set[str] = set()
    triples: Set[Tuple[str, RelationType, str]] = {(e.source, e.relation, e.target) for e in cur.edges}
    for e in cur.edges:
        loc = f"curated edge {e.curation_id}"
        if e.curation_id in seen:
            issues.append(_err("CUR_DUP_ID", "duplicate curation id", loc))
        seen.add(e.curation_id)
        spec = onto.relation(e.relation)
        if spec.status != RelationStatus.ACTIVE:
            issues.append(_err("CUR_RELATION_NOT_STORABLE", f"{e.relation.value} is {spec.status.value}", loc))
            continue
        if ProvenanceType.MANUALLY_CURATED not in spec.allowed_provenance:
            issues.append(_err("CUR_NOT_CURATABLE", f"{e.relation.value} does not allow MANUALLY_CURATED provenance", loc))
        if e.source == e.target:
            issues.append(_err("CUR_SELF_LOOP", "self-loops are not allowed", loc))
        st, tt = onto.type_of_id(e.source), onto.type_of_id(e.target)
        if st is None or tt is None:
            issues.append(_err("CUR_UNKNOWN_PREFIX", "source/target id prefix does not map to an entity type", loc))
            continue
        if st not in onto.domain_types(e.relation):
            issues.append(_err("CUR_DOMAIN", f"{e.relation.value} domain is {list(spec.domain)}, got {st.value}", loc))
        if tt not in onto.range_types(e.relation):
            issues.append(_err("CUR_RANGE", f"{e.relation.value} range is {list(spec.range)}, got {tt.value}", loc))
        if spec.symmetric and e.source > e.target:
            issues.append(_err("CUR_SYMMETRIC_ORDER", "symmetric relations are stored once with source id < target id", loc))
        if spec.mirror_of is not None and (e.target, spec.mirror_of, e.source) in triples:
            issues.append(_err("CUR_MIRROR_CONFLICT", f"duplicates {spec.mirror_of.value}({e.target},{e.source})", loc))
        if spec.requires_source_paper and not any(r.paper_id for r in e.evidence):
            issues.append(_err("CUR_SOURCE_PAPER_REQUIRED", f"{e.relation.value} requires an evidence reference naming the reporting paper", loc))
        if spec.requires_attribution and e.attribution is None:
            issues.append(_err("CUR_ATTRIBUTION_REQUIRED", f"{e.relation.value} requires attribution", loc))
        if e.attribution is not None and not spec.requires_attribution:
            issues.append(_err("CUR_ATTRIBUTION_FORBIDDEN", f"attribution is not used by {e.relation.value}", loc))
        if st == EntityType.PAPER and not any(r.paper_id == e.source for r in e.evidence):
            issues.append(_err("CUR_EVIDENCE_REQUIRED", "a curated edge whose source is a Paper needs an evidence passage from that paper", loc))
        if e.approval.status == ApprovalStatus.DRAFT:
            issues.append(_warn("CUR_DRAFT", "DRAFT edges are ignored by the build until approved", loc))
    return issues
