"""Closed vocabularies (Sections 6, 7, 8).

These enums ARE the closed vocabulary. The ontology YAML must define exactly these keys;
the loader fails if it defines more or fewer (no aliases, no new predicates).
"""
from __future__ import annotations

from enum import Enum


class EntityType(str, Enum):
    PAPER = "Paper"
    RESEARCH_PROBLEM = "ResearchProblem"
    METHOD = "Method"
    TECHNIQUE = "Technique"
    CONCEPT = "Concept"
    BENCHMARK = "Benchmark"
    CLAIM = "Claim"
    LIMITATION = "Limitation"
    RESEARCH_DIRECTION = "ResearchDirection"


class RelationType(str, Enum):
    # Bibliographic
    CITES = "CITES"
    CITED_BY = "CITED_BY"
    # Research structure
    ADDRESSES = "ADDRESSES"
    PROPOSES = "PROPOSES"
    USES = "USES"
    DEPENDS_ON = "DEPENDS_ON"
    EVALUATES_ON = "EVALUATES_ON"
    MEASURES_WITH = "MEASURES_WITH"
    BUILDS_ON = "BUILDS_ON"
    EXTENDS = "EXTENDS"
    COMPARES_WITH = "COMPARES_WITH"
    # Evidence
    SUPPORTS = "SUPPORTS"
    CHALLENGES = "CHALLENGES"
    REPORTS_LIMITATION = "REPORTS_LIMITATION"
    # Research direction
    MOTIVATES = "MOTIVATES"
    PREREQUISITE_FOR = "PREREQUISITE_FOR"
    ALTERNATIVE_TO = "ALTERNATIVE_TO"
    GENERALIZES = "GENERALIZES"
    SPECIALIZES = "SPECIALIZES"
    COMBINES_WITH = "COMBINES_WITH"


class ProvenanceType(str, Enum):
    """Section 8. UNKNOWN, UNSOURCED and LLM_INFERRED deliberately do not exist."""

    EXPLICIT_METADATA = "EXPLICIT_METADATA"
    RULE_DERIVED = "RULE_DERIVED"
    MANUALLY_CURATED = "MANUALLY_CURATED"


class SourceField(str, Enum):
    TITLE = "title"
    ABSTRACT = "abstract"
    AUTHORS = "authors"
    YEAR = "year"
    VENUE = "venue"
    IDENTIFIERS = "identifiers"
    REFERENCES = "references"
    CITATIONS = "citations"
    CITATION_CONTEXT = "citation_context"  # raw evidence only; never a semantic label
    CURATION_FILE = "curation_file"


METADATA_FIELDS = frozenset(
    {SourceField.AUTHORS, SourceField.YEAR, SourceField.VENUE, SourceField.IDENTIFIERS,
     SourceField.REFERENCES, SourceField.CITATIONS}
)
TEXT_FIELDS = frozenset({SourceField.TITLE, SourceField.ABSTRACT, SourceField.CITATION_CONTEXT})


class RelationStatus(str, Enum):
    ACTIVE = "ACTIVE"                    # storable in the knowledge state
    DERIVED_INVERSE = "DERIVED_INVERSE"  # defined, but computed from its inverse; never stored
    DEFERRED = "DEFERRED"                # defined, not instantiable in v0.1


class EntitySource(str, Enum):
    CORPUS = "CORPUS"                            # created from the frozen corpus manifest
    APPROVED_VOCABULARY = "APPROVED_VOCABULARY"  # created from the human-approved vocabulary file


class ExpectedPrecision(str, Enum):
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    NOT_APPLICABLE = "NOT_APPLICABLE"
