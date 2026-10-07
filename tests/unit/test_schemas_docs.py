import json

import jsonschema
import pytest

from src.config import REPO_ROOT
from src.docs_render import render_inventory_md, render_ontology_md
from src.knowledge.io import to_canonical_dict
from src.schema_export import build_schemas
from src.serialization import canonical_dumps
from tests.helpers import make_state
from tests.unit.test_output_schema import output


@pytest.mark.parametrize("name", sorted(build_schemas()))
def test_checked_in_schema_is_current_and_valid(name):
    schema = build_schemas()[name]
    jsonschema.Draft202012Validator.check_schema(schema)
    path = REPO_ROOT / "schemas" / f"{name}.schema.json"
    assert path.read_text(encoding="utf-8") == canonical_dumps(schema), "run scripts/export_schemas.py"


def test_knowledge_state_validates_against_its_json_schema_without_our_code():
    """A reviewer can validate the file with any JSON Schema validator (Section 16)."""
    schema = json.loads((REPO_ROOT / "schemas" / "knowledge_state.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(to_canonical_dict(make_state()), schema, cls=jsonschema.Draft202012Validator)


def test_runtime_output_validates_against_its_json_schema():
    schema = json.loads((REPO_ROOT / "schemas" / "runtime_output.schema.json").read_text(encoding="utf-8"))
    jsonschema.validate(output().model_dump(mode="json"), schema, cls=jsonschema.Draft202012Validator)


def test_json_schema_rejects_an_llm_inferred_provenance_type():
    schema = json.loads((REPO_ROOT / "schemas" / "knowledge_state.schema.json").read_text(encoding="utf-8"))
    doc = to_canonical_dict(make_state())
    doc["relationships"][0]["provenance"]["type"] = "LLM_INFERRED"
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(doc, schema, cls=jsonschema.Draft202012Validator)


def test_generated_docs_are_current(ontology):
    assert (REPO_ROOT / "docs" / "ontology.md").read_text(encoding="utf-8") == render_ontology_md(ontology), "run scripts/render_docs.py"
    assert (REPO_ROOT / "docs" / "relation_source_inventory.md").read_text(encoding="utf-8") == render_inventory_md(ontology)


def test_generated_docs_state_the_estimate_not_quota_policy(ontology):
    text = render_inventory_md(ontology)
    assert "not quotas" in text and "ESTIMATED" in text
