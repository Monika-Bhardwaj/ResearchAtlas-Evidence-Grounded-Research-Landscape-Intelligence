import pytest

from src.errors import Severity, ValidationFailed
from src.knowledge.models import AmbiguityRecord, Attribution, Entity
from src.knowledge.validation import assert_valid, validate_knowledge_state
from src.ontology.enums import EntityType, RelationType
from tests.helpers import (
    base_edges, base_entities, edge, ent, make_state, prov_cur, prov_meta, prov_rule,
)

R = RelationType


def codes(state, onto, **kw):
    return {i.code for i in validate_knowledge_state(state, onto, **kw) if i.severity == Severity.ERROR}


def with_edge(extra, drop=()):
    return make_state(edges=[e for e in base_edges() if e.edge_id not in drop] + list(extra))


def test_valid_baseline_state_has_no_issues(ontology):
    assert validate_knowledge_state(make_state(), ontology) == []
    assert_valid(make_state(), ontology)


def test_unknown_endpoint(ontology):
    st = with_edge([edge(50, "paper:s2_a", R.CITES, "paper:ghost", prov_meta())])
    assert "EDGE_UNKNOWN_ENDPOINT" in codes(st, ontology)


def test_domain_and_range_violations(ontology):
    assert "EDGE_DOMAIN" in codes(with_edge([edge(50, "method:m2", R.PROPOSES, "method:m1", prov_rule())]), ontology)
    assert "EDGE_RANGE" in codes(with_edge([edge(50, "paper:s2_b", R.PROPOSES, "concept:c2", prov_rule())]), ontology)


def test_reports_limitation_is_not_paper_to_limitation(ontology):
    bad = edge(50, "paper:s2_a", R.REPORTS_LIMITATION, "limitation:l1",
               prov_cur(50, source_paper_id="paper:s2_a", evidence="x", attribution=Attribution.SELF_REPORTED))
    assert "EDGE_DOMAIN" in codes(with_edge([bad]), ontology)


def test_derived_inverse_and_deferred_relations_cannot_be_stored(ontology):
    assert "EDGE_RELATION_NOT_STORABLE" in codes(with_edge([edge(50, "paper:s2_b", R.CITED_BY, "paper:s2_a", prov_meta())]), ontology)
    assert "EDGE_RELATION_NOT_STORABLE" in codes(with_edge([edge(51, "paper:s2_a", R.MEASURES_WITH, "concept:c1", prov_rule())]), ontology)


@pytest.mark.parametrize("rel,src,tgt,prov", [
    (R.SUPPORTS, "paper:s2_a", "claim:k1", prov_rule()),                       # curated-only relation
    (R.PREREQUISITE_FOR, "concept:c2", "method:m1", prov_rule()),              # curated-only relation
    (R.CITES, "paper:s2_b", "paper:s2_a", prov_cur(60)),                       # metadata-only relation
])
def test_provenance_type_must_be_allowed_for_the_relation(ontology, rel, src, tgt, prov):
    assert "EDGE_PROVENANCE_NOT_ALLOWED" in codes(with_edge([edge(60, src, rel, tgt, prov)]), ontology)


def test_corroborating_provenance_is_also_checked(ontology):
    e = edge(50, "paper:s2_b", R.CITES, "paper:s2_a", prov_meta(), corroborating=(prov_cur(51),))
    assert "EDGE_PROVENANCE_NOT_ALLOWED" in codes(with_edge([e]), ontology)


def test_symmetric_relation_stored_once_in_id_order(ontology):
    st = with_edge([edge(50, "concept:c2", R.COMBINES_WITH, "concept:c1", prov_cur(50))])
    assert "EDGE_SYMMETRIC_ORDER" in codes(st, ontology)
    assert "EDGE_DUP_TRIPLE" not in codes(st, ontology)


def test_generalizes_specializes_mirror_conflict(ontology):
    st = with_edge([edge(50, "concept:c1", R.GENERALIZES, "concept:c2", prov_cur(50)),
                    edge(51, "concept:c2", R.SPECIALIZES, "concept:c1", prov_cur(51))])
    assert "EDGE_MIRROR_CONFLICT" in codes(st, ontology)


def test_duplicate_ids_triples_and_self_loops(ontology):
    dup_id = make_state(edges=list(base_edges()) + [edge(1, "paper:s2_b", R.CITES, "paper:s2_a", prov_meta())])
    assert "EDGE_DUP_ID" in codes(dup_id, ontology)
    dup_triple = with_edge([edge(50, "paper:s2_a", R.CITES, "paper:s2_b", prov_meta())])
    assert "EDGE_DUP_TRIPLE" in codes(dup_triple, ontology)
    assert "EDGE_SELF_LOOP" in codes(with_edge([edge(51, "paper:s2_a", R.CITES, "paper:s2_a", prov_meta())]), ontology)
    dup_entity = make_state(entities=list(base_entities()) + [ent("concept:c1", EntityType.CONCEPT)])
    assert "ENT_DUP_ID" in codes(dup_entity, ontology)


def test_entity_prefix_must_match_type_and_required_attributes(ontology):
    wrong = make_state(entities=list(base_entities()) + [Entity(id="method:odd", type=EntityType.CONCEPT, label="odd")])
    assert "ENT_PREFIX_MISMATCH" in codes(wrong, ontology)
    no_title = make_state(entities=[e for e in base_entities() if e.id != "paper:s2_a"] +
                          [ent("paper:s2_a", EntityType.PAPER)], edges=[])
    assert "ENT_MISSING_ATTR" in codes(no_title, ontology)


def test_paper_status_attributes_are_controlled(ontology):
    bad = make_state(entities=[e for e in base_entities() if e.id != "paper:s2_b"] +
                     [ent("paper:s2_b", EntityType.PAPER, title="B", identity_status="MAYBE")], edges=[])
    assert "ENT_BAD_STATUS" in codes(bad, ontology)
    ok = make_state(entities=[e for e in base_entities() if e.id != "paper:s2_b"] +
                    [ent("paper:s2_b", EntityType.PAPER, title="B", identity_status="AMBIGUOUS", metadata_status="PARTIAL_METADATA")], edges=[])
    assert "ENT_BAD_STATUS" not in codes(ok, ontology)


# ---------------------------------------------------------------- REPORTS_LIMITATION semantics
def rl(n, **prov_kw):
    base = dict(source_paper_id="paper:s2_a", evidence="passage", attribution=Attribution.SELF_REPORTED)
    base.update(prov_kw)
    prov = prov_cur(n, **{k: v for k, v in base.items() if v is not None})
    return edge(n, "method:m2", R.REPORTS_LIMITATION, "limitation:l1", prov)


def test_reports_limitation_requires_source_paper(ontology):
    assert "EDGE_SOURCE_PAPER_REQUIRED" in codes(with_edge([rl(50, source_paper_id=None)]), ontology)


def test_reports_limitation_source_paper_must_be_a_corpus_paper(ontology):
    assert "EDGE_SOURCE_PAPER_INVALID" in codes(with_edge([rl(50, source_paper_id="paper:not_in_corpus")]), ontology)
    # a non-Paper entity cannot be named as the reporting paper (the id pattern forbids it at construction)
    with pytest.raises(Exception):
        rl(51, source_paper_id="concept:c1")


def test_reports_limitation_requires_evidence_even_when_curated(ontology):
    assert "EDGE_EVIDENCE_REQUIRED" in codes(with_edge([rl(50, evidence=None)]), ontology)


def test_reports_limitation_requires_attribution(ontology):
    assert "EDGE_ATTRIBUTION_REQUIRED" in codes(with_edge([rl(50, attribution=None)]), ontology)


def test_self_reported_requires_a_proposes_edge(ontology):
    # paper:s2_a proposes method:m1 (baseline) but NOT method:m2
    assert "EDGE_ATTRIBUTION_INCONSISTENT" in codes(with_edge([rl(50, attribution=Attribution.SELF_REPORTED)]), ontology)
    assert "EDGE_ATTRIBUTION_INCONSISTENT" not in codes(with_edge([rl(51, attribution=Attribution.THIRD_PARTY)]), ontology)


def test_third_party_is_inconsistent_when_the_reporter_proposes_the_method(ontology):
    e = edge(50, "method:m1", R.REPORTS_LIMITATION, "limitation:l1",
             prov_cur(50, source_paper_id="paper:s2_a", evidence="x", attribution=Attribution.THIRD_PARTY))
    st = with_edge([e])
    assert "EDGE_ATTRIBUTION_INCONSISTENT" in codes(st, ontology)


def test_attribution_is_forbidden_on_other_relations(ontology):
    e = edge(50, "paper:s2_b", R.SUPPORTS, "claim:k1", prov_cur(50, attribution=Attribution.THIRD_PARTY))
    assert "EDGE_ATTRIBUTION_FORBIDDEN" in codes(with_edge([e], drop={"edge_0007"}), ontology)


# ---------------------------------------------------------------- versions, integrity, ambiguity
def test_version_mismatches(ontology):
    assert "KS_ONTOLOGY_VERSION" in codes(make_state(ontology_version="9.9.9"), ontology)
    assert "KS_SCHEMA_VERSION" in codes(make_state(schema_version="9.9.9"), ontology)
    bad_prov = with_edge([edge(50, "paper:s2_b", R.CITES, "paper:s2_a", prov_meta().model_copy(update={"ontology_version": "0.0.1"}))])
    assert "EDGE_PROV_VERSION" in codes(bad_prov, ontology)


def test_integrity_hash_detects_tampering(ontology):
    st = make_state()
    tampered = st.model_copy(update={"relationships": st.relationships[:-1]})   # hash NOT recomputed
    assert "KS_INTEGRITY" in codes(tampered, ontology)
    assert "KS_INTEGRITY" not in codes(tampered, ontology, check_integrity=False)


def test_ambiguity_records_must_point_at_real_entities(ontology):
    ok = make_state(ambiguities=[AmbiguityRecord(input="forgetting", candidates=("concept:c1", "concept:c2"))])
    assert codes(ok, ontology) == set()
    bad = make_state(ambiguities=[AmbiguityRecord(input="forgetting", candidates=("concept:c1", "concept:ghost"))])
    assert "AMB_UNKNOWN_CANDIDATE" in codes(bad, ontology)


def test_assert_valid_raises_with_every_error_listed(ontology):
    st = with_edge([edge(50, "paper:s2_a", R.CITES, "paper:ghost", prov_meta()),
                    edge(51, "method:m2", R.PROPOSES, "method:m1", prov_rule())])
    with pytest.raises(ValidationFailed) as exc:
        assert_valid(st, ontology)
    assert {i.code for i in exc.value.issues} >= {"EDGE_UNKNOWN_ENDPOINT", "EDGE_DOMAIN"}
