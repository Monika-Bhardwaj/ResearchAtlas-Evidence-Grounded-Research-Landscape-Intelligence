"""Builders for small, valid fixtures. Tests mutate these to trigger each validator."""
from __future__ import annotations

from typing import Iterable, Optional, Sequence, Tuple

from src.knowledge.io import with_integrity
from src.knowledge.models import (
    Attribution,
    BuildMetadata,
    Edge,
    Entity,
    Integrity,
    KnowledgeState,
    Provenance,
)
from src.ontology.enums import EntityType, ProvenanceType, RelationType, SourceField

ONT = "0.1.0"
BUILD = "kb-test-0.1.0"


def prov_meta(field: SourceField = SourceField.REFERENCES) -> Provenance:
    return Provenance(type=ProvenanceType.EXPLICIT_METADATA, source_field=field,
                      ontology_version=ONT, knowledge_build_version=BUILD)


def prov_rule(field: SourceField = SourceField.TITLE, **kw) -> Provenance:
    base = dict(type=ProvenanceType.RULE_DERIVED, source_field=field, rule_id="method_mapping_07",
                mapping_decision="title_alias_exact", evidence="fixture evidence span",
                ontology_version=ONT, knowledge_build_version=BUILD)
    base.update(kw)
    return Provenance(**base)


def prov_cur(n: int = 1, **kw) -> Provenance:
    base = dict(type=ProvenanceType.MANUALLY_CURATED, source_field=SourceField.CURATION_FILE,
                curated_by="researcher", curation_ref=f"cur_{n:04d}",
                ontology_version=ONT, knowledge_build_version=BUILD)
    base.update(kw)
    return Provenance(**base)


def ent(eid: str, etype: EntityType, **attrs) -> Entity:
    return Entity(id=eid, type=etype, label=eid.split(":")[1], attributes=attrs)


def edge(n: int, source: str, rel: RelationType, target: str, prov: Provenance, conf: float = 0.9,
         corroborating: Tuple[Provenance, ...] = ()) -> Edge:
    return Edge(edge_id=f"edge_{n:04d}", source=source, relation=rel, target=target, provenance=prov,
                corroborating_provenance=corroborating, confidence=conf)


def base_entities() -> Tuple[Entity, ...]:
    P, M = EntityType.PAPER, EntityType.METHOD
    return (
        ent("paper:s2_a", P, title="Paper A", year=2024),
        ent("paper:s2_b", P, title="Paper B", year=2023),
        ent("method:m1", M), ent("method:m2", M),
        ent("technique:t1", EntityType.TECHNIQUE),
        ent("concept:c1", EntityType.CONCEPT), ent("concept:c2", EntityType.CONCEPT),
        ent("limitation:l1", EntityType.LIMITATION),
        ent("direction:d1", EntityType.RESEARCH_DIRECTION),
        ent("claim:k1", EntityType.CLAIM),
        ent("benchmark:b1", EntityType.BENCHMARK),
        ent("problem:p1", EntityType.RESEARCH_PROBLEM),
    )


def base_edges() -> Tuple[Edge, ...]:
    R = RelationType
    return (
        edge(1, "paper:s2_a", R.CITES, "paper:s2_b", prov_meta()),
        edge(2, "paper:s2_a", R.PROPOSES, "method:m1", prov_rule()),
        edge(3, "paper:s2_a", R.ADDRESSES, "concept:c1", prov_rule(rule_id="concept.example.v1", mapping_decision="title_alias_exact")),
        edge(4, "paper:s2_b", R.ADDRESSES, "problem:p1", prov_rule(SourceField.ABSTRACT, mapping_decision="abstract_contribution_pattern")),
        edge(5, "paper:s2_b", R.EVALUATES_ON, "benchmark:b1", prov_rule(SourceField.ABSTRACT, mapping_decision="exact_benchmark_name")),
        edge(6, "method:m1", R.REPORTS_LIMITATION, "limitation:l1",
             prov_cur(6, source_paper_id="paper:s2_a", evidence="passage naming the limitation",
                      attribution=Attribution.SELF_REPORTED)),
        edge(7, "paper:s2_b", R.SUPPORTS, "claim:k1", prov_cur(7, evidence="supporting passage")),
        edge(8, "paper:s2_a", R.CHALLENGES, "claim:k1", prov_cur(8, evidence="challenging passage")),
        edge(9, "limitation:l1", R.MOTIVATES, "direction:d1", prov_cur(9)),
        edge(10, "concept:c1", R.PREREQUISITE_FOR, "method:m1", prov_cur(10)),
        edge(11, "concept:c1", R.COMBINES_WITH, "concept:c2", prov_cur(11)),
    )


def make_state(entities: Optional[Iterable[Entity]] = None, edges: Optional[Iterable[Edge]] = None,
               ambiguities: Sequence = (), **overrides) -> KnowledgeState:
    fields = dict(
        schema_version="0.1.0", ontology_version=ONT, corpus_version="corpus-test-0.1.0",
        knowledge_build_version=BUILD,
        build_metadata=BuildMetadata(generator="tests", git_sha=None),
        integrity=Integrity(content_sha256="0" * 64),
        entities=tuple(entities if entities is not None else base_entities()),
        relationships=tuple(edges if edges is not None else base_edges()),
        ambiguities=tuple(ambiguities),
    )
    fields.update(overrides)
    return with_integrity(KnowledgeState(**fields))
