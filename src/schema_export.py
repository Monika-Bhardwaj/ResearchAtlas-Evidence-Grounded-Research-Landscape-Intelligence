"""Deterministic JSON Schema export for every contract-bearing model."""
from __future__ import annotations

from typing import Any, Dict

from src.evaluation.gold import GoldSet
from src.knowledge.curation import CurationFile, VocabularyFile
from src.knowledge.models import KnowledgeState
from src.ontology.spec import OntologySpec
from src.output.models import RuntimeOutput

SCHEMA_MODELS = {
    "knowledge_state": KnowledgeState,
    "runtime_output": RuntimeOutput,
    "ontology": OntologySpec,
    "vocabulary": VocabularyFile,
    "curation": CurationFile,
    "gold_set": GoldSet,
}


def build_schemas() -> Dict[str, Dict[str, Any]]:
    return {name: model.model_json_schema() for name, model in SCHEMA_MODELS.items()}
