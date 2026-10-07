import pytest
from pydantic import ValidationError

from src.knowledge.models import Edge, Provenance
from src.ontology.enums import ProvenanceType, RelationType, SourceField
from tests.helpers import BUILD, ONT, edge, prov_cur, prov_meta, prov_rule

COMMON = dict(ontology_version=ONT, knowledge_build_version=BUILD)


@pytest.mark.parametrize("missing", ["rule_id", "mapping_decision", "evidence"])
def test_rule_derived_requires_each_field(missing):
    kw = dict(type="RULE_DERIVED", source_field="title", rule_id="r.v1", mapping_decision="exact", evidence="span", **COMMON)
    kw.pop(missing)
    with pytest.raises(ValidationError, match="RULE_DERIVED requires"):
        Provenance(**kw)


def test_rule_derived_must_come_from_text_field():
    with pytest.raises(ValidationError, match="source_field"):
        prov_rule(SourceField.REFERENCES)


@pytest.mark.parametrize("bad", ["LLM_INFERRED", "UNKNOWN", "UNSOURCED"])
def test_forbidden_provenance_types_cannot_be_constructed(bad):
    with pytest.raises(ValidationError):
        Provenance(type=bad, source_field="title", **COMMON)


def test_explicit_metadata_rejects_text_fields_and_rule_ids():
    with pytest.raises(ValidationError, match="bibliographic"):
        Provenance(type="EXPLICIT_METADATA", source_field="abstract", **COMMON)
    with pytest.raises(ValidationError, match="must not carry"):
        Provenance(type="EXPLICIT_METADATA", source_field="references", rule_id="r.v1", **COMMON)


def test_curated_requires_curator_ref_and_curation_source():
    with pytest.raises(ValidationError, match="curated_by and curation_ref"):
        Provenance(type="MANUALLY_CURATED", source_field="curation_file", **COMMON)
    with pytest.raises(ValidationError, match="curation_file"):
        Provenance(type="MANUALLY_CURATED", source_field="title", curated_by="x", curation_ref="cur_0001", **COMMON)
    with pytest.raises(ValidationError, match="rule_id"):
        prov_cur(rule_id="r.v1")


def test_unknown_fields_are_rejected():
    with pytest.raises(ValidationError):
        Provenance(type="EXPLICIT_METADATA", source_field="references", llm_confidence=0.9, **COMMON)


def test_curation_ref_and_edge_id_formats():
    with pytest.raises(ValidationError):
        prov_cur(curation_ref="manual-1")
    with pytest.raises(ValidationError):
        Edge(edge_id="e1", source="paper:a", relation=RelationType.CITES, target="paper:b", provenance=prov_meta(), confidence=0.5)


@pytest.mark.parametrize("conf", [-0.01, 1.01])
def test_confidence_is_bounded(conf):
    with pytest.raises(ValidationError):
        edge(1, "paper:a", RelationType.CITES, "paper:b", prov_meta(), conf=conf)
