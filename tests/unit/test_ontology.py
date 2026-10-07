import copy

import pytest
import yaml

from src.errors import OntologyError
from src.ontology.enums import EntityType, ProvenanceType, RelationStatus, RelationType
from src.ontology.loader import DEFAULT_ONTOLOGY_PATH, load_ontology

SECTION_7 = {
    "CITES", "CITED_BY",
    "ADDRESSES", "PROPOSES", "USES", "DEPENDS_ON", "EVALUATES_ON", "MEASURES_WITH", "BUILDS_ON", "EXTENDS", "COMPARES_WITH",
    "SUPPORTS", "CHALLENGES", "REPORTS_LIMITATION",
    "MOTIVATES", "PREREQUISITE_FOR", "ALTERNATIVE_TO", "GENERALIZES", "SPECIALIZES", "COMBINES_WITH",
}


def _variant(tmp_path, mutate):
    raw = yaml.safe_load(DEFAULT_ONTOLOGY_PATH.read_text(encoding="utf-8"))
    raw = copy.deepcopy(raw)
    mutate(raw)
    p = tmp_path / "ontology.yaml"
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return p


# ---------------------------------------------------------------- closed vocabulary
def test_exactly_the_20_section_7_relations(ontology):
    assert set(ontology.spec.relations) == SECTION_7
    assert {r.value for r in RelationType} == SECTION_7
    assert len(SECTION_7) == 20


def test_exactly_the_9_entities(ontology):
    assert len(EntityType) == 9
    assert set(ontology.spec.entities) == {e.value for e in EntityType}


def test_storable_deferred_derived_counts(ontology):
    by = {s: [k for k, v in ontology.spec.relations.items() if v.status == s] for s in RelationStatus}
    assert len(by[RelationStatus.ACTIVE]) == 18
    assert by[RelationStatus.DERIVED_INVERSE] == ["CITED_BY"]
    assert by[RelationStatus.DEFERRED] == ["MEASURES_WITH"]


@pytest.mark.parametrize("label", ["HAS_LIMITATION", "CONFLICTING", "INSUFFICIENT_EVIDENCE"])
def test_non_relations_are_not_relations(ontology, label):
    assert label in ontology.spec.non_relations
    assert label not in ontology.spec.relations
    assert label not in {r.value for r in RelationType}


def test_every_relation_has_definition_rationale_and_provenance_policy(ontology):
    for name, r in ontology.spec.relations.items():
        assert r.definition.strip() and r.rationale.strip(), name
        if r.status == RelationStatus.ACTIVE:
            assert r.allowed_provenance, name
            assert r.primary_source in {p.value for p in r.allowed_provenance}, name


def test_no_provenance_type_outside_the_three_allowed():
    assert {p.value for p in ProvenanceType} == {"EXPLICIT_METADATA", "RULE_DERIVED", "MANUALLY_CURATED"}
    for bad in ("UNKNOWN", "UNSOURCED", "LLM_INFERRED"):
        assert bad not in {p.value for p in ProvenanceType}


# ---------------------------------------------------------------- domain / range audit
def test_reports_limitation_is_method_to_limitation_with_mandatory_provenance(ontology):
    r = ontology.relation(RelationType.REPORTS_LIMITATION)
    assert set(r.domain) == {"Method"} and set(r.range) == {"Limitation"}
    assert r.requires_source_paper and r.requires_evidence and r.requires_attribution


def test_addresses_range_extension_is_defined_precisely(ontology):
    r = ontology.relation(RelationType.ADDRESSES)
    assert set(r.domain) == {"Paper"}
    assert set(r.range) == {"ResearchProblem", "Concept"}
    assert r.range_extension and set(r.range_semantics) == {"ResearchProblem", "Concept"}
    assert "mentions" in r.definition.lower()          # states what ADDRESSES is NOT
    assert "title" in r.range_semantics["Concept"].lower()


@pytest.mark.parametrize("rel", [RelationType.SUPPORTS, RelationType.CHALLENGES])
def test_supports_and_challenges_are_paper_to_claim_and_curated_only(ontology, rel):
    r = ontology.relation(rel)
    assert set(r.domain) == {"Paper"} and set(r.range) == {"Claim"}
    assert r.allowed_provenance == (ProvenanceType.MANUALLY_CURATED,)


def test_prerequisite_for_is_entity_level_and_curated_only(ontology):
    r = ontology.relation(RelationType.PREREQUISITE_FOR)
    assert set(r.domain) == set(r.range) == {"Concept", "Technique", "Method"}
    assert r.allowed_provenance == (ProvenanceType.MANUALLY_CURATED,)


def test_symmetric_and_mirror_flags(ontology):
    assert ontology.relation(RelationType.ALTERNATIVE_TO).symmetric
    assert ontology.relation(RelationType.COMBINES_WITH).symmetric
    assert ontology.relation(RelationType.SPECIALIZES).mirror_of == RelationType.GENERALIZES


def test_cited_by_is_the_swapped_inverse_of_cites(ontology):
    cb = ontology.relation(RelationType.CITED_BY)
    assert cb.inverse_of == RelationType.CITES and cb.allowed_provenance == ()


def test_type_of_id_uses_prefix(ontology):
    assert ontology.type_of_id("paper:abc") == EntityType.PAPER
    assert ontology.type_of_id("direction:x") == EntityType.RESEARCH_DIRECTION
    assert ontology.type_of_id("nonsense:x") is None
    assert ontology.type_of_id("not an id") is None


def test_estimates_are_coherent_with_provenance(ontology):
    for name, r in ontology.spec.relations.items():
        if r.allowed_provenance == (ProvenanceType.MANUALLY_CURATED,):
            assert r.estimate.curated_edges == r.estimate.edges, name


# ---------------------------------------------------------------- invalid ontologies FAIL
def test_loader_rejects_extra_relation(tmp_path):
    def m(raw):
        raw["relations"]["HAS_LIMITATION"] = copy.deepcopy(raw["relations"]["REPORTS_LIMITATION"])
    with pytest.raises(OntologyError, match="HAS_LIMITATION"):
        load_ontology(_variant(tmp_path, m))


def test_loader_rejects_missing_relation(tmp_path):
    with pytest.raises(OntologyError, match="missing"):
        load_ontology(_variant(tmp_path, lambda raw: raw["relations"].pop("USES")))


def test_loader_rejects_extra_entity(tmp_path):
    def m(raw):
        raw["entities"]["Author"] = copy.deepcopy(raw["entities"]["Paper"])
        raw["entities"]["Author"]["id_prefix"] = "author"
    with pytest.raises(OntologyError, match="Author"):
        load_ontology(_variant(tmp_path, m))


def test_loader_rejects_unknown_domain_type(tmp_path):
    with pytest.raises(OntologyError, match="unknown or inactive"):
        load_ontology(_variant(tmp_path, lambda raw: raw["relations"]["USES"].update(domain=["Paper", "Metric"])))


def test_loader_rejects_non_relation_listed_as_relation(tmp_path):
    def m(raw):
        raw["non_relations"]["USES"] = "bad"
    with pytest.raises(OntologyError, match="non-relation"):
        load_ontology(_variant(tmp_path, m))


def test_loader_rejects_range_extension_without_semantics(tmp_path):
    with pytest.raises(OntologyError, match="range_semantics"):
        load_ontology(_variant(tmp_path, lambda raw: raw["relations"]["ADDRESSES"].update(range_semantics={"Concept": "x"})))


def test_loader_rejects_attribution_without_source_paper(tmp_path):
    with pytest.raises(OntologyError, match="requires_attribution"):
        load_ontology(_variant(tmp_path, lambda raw: raw["relations"]["REPORTS_LIMITATION"].update(requires_source_paper=False)))


def test_loader_rejects_symmetric_with_asymmetric_types(tmp_path):
    with pytest.raises(OntologyError, match="symmetric"):
        load_ontology(_variant(tmp_path, lambda raw: raw["relations"]["ALTERNATIVE_TO"].update(domain=["Method"])))


def test_loader_rejects_curated_estimate_mismatch(tmp_path):
    def m(raw):
        raw["relations"]["PREREQUISITE_FOR"]["estimate"]["curated_edges"] = [0, 5]
    with pytest.raises(OntologyError, match="curated_edges == edges"):
        load_ontology(_variant(tmp_path, m))


def test_loader_rejects_unknown_provenance_type(tmp_path):
    with pytest.raises(OntologyError, match="structure error"):
        load_ontology(_variant(tmp_path, lambda raw: raw["relations"]["CITES"].update(allowed_provenance=["LLM_INFERRED"])))


def test_loader_rejects_stored_derived_inverse_with_provenance(tmp_path):
    with pytest.raises(OntologyError, match="non-storable"):
        load_ontology(_variant(tmp_path, lambda raw: raw["relations"]["CITED_BY"].update(allowed_provenance=["EXPLICIT_METADATA"])))


def test_loader_rejects_invalid_yaml_and_missing_file(tmp_path):
    bad = tmp_path / "bad.yaml"
    bad.write_text("relations: [unclosed", encoding="utf-8")
    with pytest.raises(OntologyError, match="not valid YAML"):
        load_ontology(bad)
    with pytest.raises(OntologyError, match="not found"):
        load_ontology(tmp_path / "missing.yaml")
