"""Knowledge-state validation. Every check reports an Issue; nothing is silently repaired.

Domain/range, allowed provenance, source-paper/evidence/attribution rules, symmetric ordering and
the GENERALIZES/SPECIALIZES mirror rule are all driven by the ontology, not hard-coded here.
"""
from __future__ import annotations

from typing import Dict, List, Sequence, Set, Tuple

from src.errors import Issue, Severity, ValidationFailed
from src.ids import split_id
from src.knowledge.io import compute_content_hash
from src.knowledge.models import (
    Attribution,
    Edge,
    Entity,
    IdentityStatus,
    KnowledgeState,
    MetadataStatus,
    Provenance,
)
from src.ontology.enums import EntityType, RelationStatus, RelationType
from src.ontology.loader import Ontology


def _err(code: str, msg: str, loc: str = "") -> Issue:
    return Issue(code=code, message=msg, location=loc, severity=Severity.ERROR)


def _check_provenance_allowed(edge: Edge, prov: Provenance, onto: Ontology, loc: str) -> List[Issue]:
    spec = onto.relation(edge.relation)
    issues: List[Issue] = []
    if prov.type not in spec.allowed_provenance:
        issues.append(_err("EDGE_PROVENANCE_NOT_ALLOWED",
                           f"{edge.relation.value} does not allow {prov.type.value} provenance "
                           f"(allowed: {[t.value for t in spec.allowed_provenance]})", loc))
    return issues


def validate_knowledge_state(state: KnowledgeState, onto: Ontology, *, check_integrity: bool = True) -> List[Issue]:
    issues: List[Issue] = []

    # ---- versions and integrity
    if state.ontology_version != onto.version:
        issues.append(_err("KS_ONTOLOGY_VERSION", f"state ontology_version {state.ontology_version!r} != ontology {onto.version!r}"))
    if state.schema_version != onto.schema_version:
        issues.append(_err("KS_SCHEMA_VERSION", f"state schema_version {state.schema_version!r} != ontology {onto.schema_version!r}"))
    if check_integrity:
        actual = compute_content_hash(state)
        if actual != state.integrity.content_sha256:
            issues.append(_err("KS_INTEGRITY", "content hash does not match integrity.content_sha256 (file modified or corrupt)"))

    # ---- entities
    by_id: Dict[str, Entity] = {}
    prefix_map = onto.prefix_to_type()
    for ent in state.entities:
        loc = f"entity {ent.id}"
        if ent.id in by_id:
            issues.append(_err("ENT_DUP_ID", "duplicate entity id", loc))
            continue
        by_id[ent.id] = ent
        try:
            prefix, _ = split_id(ent.id)
        except ValueError:
            issues.append(_err("ENT_ID_FORMAT", "malformed id", loc))
            continue
        if prefix_map.get(prefix) != ent.type:
            issues.append(_err("ENT_PREFIX_MISMATCH", f"prefix {prefix!r} does not belong to type {ent.type.value}", loc))
        required = onto.spec.entities[ent.type.value].required_attributes
        for attr in required:
            if attr not in ent.attributes or ent.attributes[attr] in (None, ""):
                issues.append(_err("ENT_MISSING_ATTR", f"{ent.type.value} requires attribute {attr!r}", loc))
        if ent.type == EntityType.PAPER:
            ids = ent.attributes.get("identity_status")
            if ids is not None and ids not in {s.value for s in IdentityStatus}:
                issues.append(_err("ENT_BAD_STATUS", f"identity_status {ids!r} is not RESOLVED/AMBIGUOUS", loc))
            ms = ent.attributes.get("metadata_status")
            if ms is not None and ms not in {s.value for s in MetadataStatus}:
                issues.append(_err("ENT_BAD_STATUS", f"metadata_status {ms!r} is not COMPLETE/PARTIAL_METADATA", loc))

    # ---- edges
    seen_ids: Set[str] = set()
    seen_triples: Set[Tuple[str, str, str]] = set()
    triples: Set[Tuple[str, RelationType, str]] = {(e.source, e.relation, e.target) for e in state.relationships}
    for edge in state.relationships:
        loc = f"edge {edge.edge_id}"
        if edge.edge_id in seen_ids:
            issues.append(_err("EDGE_DUP_ID", "duplicate edge id", loc))
        seen_ids.add(edge.edge_id)
        triple = (edge.source, edge.relation.value, edge.target)
        if triple in seen_triples:
            issues.append(_err("EDGE_DUP_TRIPLE", "same (source, relation, target) stored twice; use corroborating_provenance", loc))
        seen_triples.add(triple)

        spec = onto.relation(edge.relation)
        if spec.status != RelationStatus.ACTIVE:
            issues.append(_err("EDGE_RELATION_NOT_STORABLE", f"{edge.relation.value} is {spec.status.value} and must not be stored", loc))
            continue
        if edge.source == edge.target:
            issues.append(_err("EDGE_SELF_LOOP", "self-loops are not allowed", loc))
        src, tgt = by_id.get(edge.source), by_id.get(edge.target)
        if src is None or tgt is None:
            missing = [i for i, e in ((edge.source, src), (edge.target, tgt)) if e is None]
            issues.append(_err("EDGE_UNKNOWN_ENDPOINT", f"endpoint(s) not in entities: {missing}", loc))
            continue
        if src.type not in onto.domain_types(edge.relation):
            issues.append(_err("EDGE_DOMAIN", f"{edge.relation.value} domain is {list(spec.domain)}, got {src.type.value}", loc))
        if tgt.type not in onto.range_types(edge.relation):
            issues.append(_err("EDGE_RANGE", f"{edge.relation.value} range is {list(spec.range)}, got {tgt.type.value}", loc))
        if spec.symmetric and edge.source > edge.target:
            issues.append(_err("EDGE_SYMMETRIC_ORDER", "symmetric relations are stored once with source id < target id", loc))
        if spec.mirror_of is not None and (edge.target, spec.mirror_of, edge.source) in triples:
            issues.append(_err("EDGE_MIRROR_CONFLICT",
                               f"{edge.relation.value}({edge.source},{edge.target}) duplicates "
                               f"{spec.mirror_of.value}({edge.target},{edge.source})", loc))

        all_prov = (edge.provenance,) + tuple(edge.corroborating_provenance)
        for prov in all_prov:
            issues += _check_provenance_allowed(edge, prov, onto, loc)
            if prov.ontology_version != state.ontology_version or prov.knowledge_build_version != state.knowledge_build_version:
                issues.append(_err("EDGE_PROV_VERSION", "provenance ontology/build version differs from the knowledge state", loc))
            if prov.attribution is not None and not spec.requires_attribution:
                issues.append(_err("EDGE_ATTRIBUTION_FORBIDDEN", f"attribution is only used by relations that require it, not {edge.relation.value}", loc))
            if spec.requires_source_paper:
                if not prov.source_paper_id:
                    issues.append(_err("EDGE_SOURCE_PAPER_REQUIRED", f"{edge.relation.value} requires provenance.source_paper_id", loc))
                else:
                    p = by_id.get(prov.source_paper_id)
                    if p is None or p.type != EntityType.PAPER:
                        issues.append(_err("EDGE_SOURCE_PAPER_INVALID", f"source_paper_id {prov.source_paper_id!r} is not a Paper in the corpus", loc))
            if spec.requires_evidence and not prov.evidence:
                issues.append(_err("EDGE_EVIDENCE_REQUIRED", f"{edge.relation.value} requires an evidence span for every provenance type", loc))
            if spec.requires_attribution:
                if prov.attribution is None:
                    issues.append(_err("EDGE_ATTRIBUTION_REQUIRED", f"{edge.relation.value} requires attribution (SELF_REPORTED or THIRD_PARTY)", loc))
                elif prov.source_paper_id:
                    proposes = (prov.source_paper_id, RelationType.PROPOSES, edge.source) in triples
                    if prov.attribution == Attribution.SELF_REPORTED and not proposes:
                        issues.append(_err("EDGE_ATTRIBUTION_INCONSISTENT", f"SELF_REPORTED requires PROPOSES({prov.source_paper_id}, {edge.source}) in the graph", loc))
                    if prov.attribution == Attribution.THIRD_PARTY and proposes:
                        issues.append(_err("EDGE_ATTRIBUTION_INCONSISTENT", f"THIRD_PARTY but {prov.source_paper_id} PROPOSES {edge.source}", loc))

    # ---- ambiguity records
    for amb in state.ambiguities:
        missing = [c for c in amb.candidates if c not in by_id]
        if missing:
            issues.append(_err("AMB_UNKNOWN_CANDIDATE", f"candidates not in entities: {missing}", f"ambiguity {amb.input!r}"))
    return issues


def errors_only(issues: Sequence[Issue]) -> List[Issue]:
    return [i for i in issues if i.severity == Severity.ERROR]


def assert_valid(state: KnowledgeState, onto: Ontology, *, check_integrity: bool = True) -> None:
    """Raise ValidationFailed on any ERROR. Used by the build and by the CLI (fail fast)."""
    errs = errors_only(validate_knowledge_state(state, onto, check_integrity=check_integrity))
    if errs:
        raise ValidationFailed(errs)
