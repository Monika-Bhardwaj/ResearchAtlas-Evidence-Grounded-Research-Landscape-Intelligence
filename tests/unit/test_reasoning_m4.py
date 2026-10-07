import pytest

from src.knowledge.models import Entity, Edge, KnowledgeState, Provenance, BuildMetadata, Integrity
from src.ontology.enums import EntityType, RelationType, SourceField, ProvenanceType
from src.ontology.loader import load_ontology
from src.knowledge.io import with_integrity
from src.knowledge.validation import errors_only, validate_knowledge_state
from src.knowledge.curation import VocabularyFile
from src.reasoning.engine import analyze_proposal
from src.output.models import PositioningLabel

VOCAB = {
  "vocabulary_version": "0.1.0",
  "entries": [
    {"id": "method:episodic_memory", "type": "Method", "label": "Episodic memory", "aliases": [], "definition": "x", "drafted_with_ai": True, "approval": {"status": "APPROVED", "approved_by": "a", "approved_on": "2026-01-01"}},
    {"id": "concept:agent_memory", "type": "Concept", "label": "Agent memory", "aliases": [], "definition": "x", "drafted_with_ai": True, "approval": {"status": "APPROVED", "approved_by": "a", "approved_on": "2026-01-01"}}
  ],
  "ambiguous_terms": []
}

def make_state():
    entities = [
        Entity(id="paper:p0001", type=EntityType.PAPER, label="P", attributes={"title": "P", "year": 2025, "venue": "x", "identity_status": "RESOLVED", "metadata_status": "COMPLETE"}),
        Entity(id="method:episodic_memory", type=EntityType.METHOD, label="Episodic memory", aliases=(), definition="x", attributes={}),
        Entity(id="concept:agent_memory", type=EntityType.CONCEPT, label="Agent memory", aliases=(), definition="x", attributes={}),
    ]
    prov = Provenance(type=ProvenanceType.RULE_DERIVED, rule_id="r.v1", source_field=SourceField.ABSTRACT, mapping_decision="alias", evidence="we propose episodic memory", source_paper_id="paper:p0001", ontology_version="0.1.0", knowledge_build_version="0.1.0")
    edges = [
        Edge(edge_id="edge_0001", source="paper:p0001", relation=RelationType.PROPOSES, target="method:episodic_memory", provenance=prov, confidence=0.9),
        Edge(edge_id="edge_0002", source="paper:p0001", relation=RelationType.ADDRESSES, target="concept:agent_memory", provenance=prov.model_copy(update={"evidence": "agent memory"}), confidence=0.8),
    ]
    state = KnowledgeState(schema_version="0.1.0", ontology_version="0.1.0", corpus_version="0.1.0", knowledge_build_version="0.1.0", build_metadata=BuildMetadata(generator="t"), integrity=Integrity(content_sha256="0"*64), entities=tuple(entities), relationships=tuple(edges), ambiguities=())
    return with_integrity(state)

def test_analyzer_grounds_and_scores():
    state = make_state()
    vocab = VocabularyFile.model_validate(VOCAB)
    errs = errors_only(validate_knowledge_state(state, load_ontology()))
    assert not errs
    out = analyze_proposal("I want episodic memory for an agent memory system", state, vocab)
    assert out.proposal.matched_concepts
    assert out.prior_work
    assert out.positioning[0].label in {PositioningLabel.WELL_EXPLORED, PositioningLabel.PARTIALLY_EXPLORED, PositioningLabel.UNDERREPRESENTED, PositioningLabel.UNKNOWN}
