# Ontology v0.1.0

_Generated from `src/ontology/ontology.yaml` by `scripts/render_docs.py`. Do not edit by hand._

The vocabulary is **closed**: exactly 9 entity types and 20 relation types (Sections 6 and 7). The loader fails if the YAML defines any other key.

## Entities

| Entity | Id prefix | Created from | Definition | Why it exists | Required attributes |
|---|---|---|---|---|---|
| Paper | `paper:` | CORPUS | A scholarly paper in the frozen corpus, identified by a canonical identifier. | Evidence anchor. Every semantic edge is traceable to a paper. | title |
| ResearchProblem | `problem:` | APPROVED_VOCABULARY | A named problem that papers address (for example, long-horizon recall in agents). | Positioning facets map to problems; supports the ProblemOverlap feature. | - |
| Method | `method:` | APPROVED_VOCABULARY | A named, citable approach proposed by a paper. | Typed method overlap and PROPOSES; subject of reported limitations. | - |
| Technique | `technique:` | APPROVED_VOCABULARY | A reusable mechanism that appears across methods (for example, summarization-based consolidation). | Lets methods be compared and given prerequisites at the mechanism level. | - |
| Concept | `concept:` | APPROVED_VOCABULARY | A controlled-vocabulary notion (for example, episodic memory, selective forgetting). | Deterministic grounding of proposals and facets; ConceptOverlap. | - |
| Benchmark | `benchmark:` | APPROVED_VOCABULARY | A named evaluation suite or dataset-plus-protocol (Dataset is folded into Benchmark). | EVALUATES_ON and the BenchmarkOverlap feature. | - |
| Claim | `claim:` | APPROVED_VOCABULARY | A specific assertion that corpus papers support or challenge. | Tension analysis (T4) needs a shared object that papers support or challenge. | - |
| Limitation | `limitation:` | APPROVED_VOCABULARY | A reported weakness of a method. | Negative knowledge (Section 23); motivates research directions. | - |
| ResearchDirection | `direction:` | APPROVED_VOCABULARY | An open research direction motivated by one or more limitations. | Final link of the decision chain (Section 1). | - |

### Deferred and excluded entity types

- **Metric** (deferred): Metric extraction from abstracts is noisy and no v0.1 task needs it. MEASURES_WITH is defined but not instantiable until Metric is approved.
- **Author** (excluded): A Paper attribute; no reasoning step consumes authors.
- **Dataset** (excluded): Folded into Benchmark to keep one evaluation-target entity.

### Labels that are NOT relations

- `CONFLICTING`: Tension status. An output and evaluation label derived at query time from SUPPORTS and CHALLENGES edges on a Claim; never stored.
- `INSUFFICIENT_EVIDENCE`: Tension and abstention status. An output and evaluation label; never stored.
- `HAS_LIMITATION`: Rejected alias. The canonical Method-to-Limitation relation is REPORTS_LIMITATION.

## Relations

Status: **ACTIVE** relations may be stored; **DERIVED_INVERSE** relations are computed, never stored; **DEFERRED** relations are defined but not instantiable in v0.1.

### Bibliographic

| Relation | Domain → Range | Status | Allowed provenance | Definition |
|---|---|---|---|---|
| CITES | Paper → Paper | ACTIVE | EXPLICIT_METADATA | The source paper's reference list contains the target paper (bibliographic metadata from the source API). |
| CITED_BY | Paper → Paper | DERIVED_INVERSE | none (not stored) | Inverse view of CITES. Computed at query time; never stored. |

### Research structure

| Relation | Domain → Range | Status | Allowed provenance | Definition |
|---|---|---|---|---|
| ADDRESSES | Paper → ResearchProblem / Concept | ACTIVE | RULE_DERIVED, MANUALLY_CURATED | The target is the focal subject of the paper's contribution or analysis. ADDRESSES never means "mentions" or "is related to". Incidental, background, comparative, list-style, negated and "such as" occurrences create no edge. |
| PROPOSES | Paper → Method | ACTIVE | RULE_DERIVED, MANUALLY_CURATED | The paper introduces the target as its own named method. |
| USES | Paper → Method / Technique | ACTIVE | RULE_DERIVED, MANUALLY_CURATED | The paper's own approach or experiments employ the target as a component. |
| DEPENDS_ON | Method → Technique / Concept | ACTIVE | MANUALLY_CURATED | The method requires the target technique or concept in order to function. |
| EVALUATES_ON | Paper → Benchmark | ACTIVE | RULE_DERIVED, MANUALLY_CURATED | The paper reports results on the target benchmark. |
| MEASURES_WITH | Paper → Metric | DEFERRED | none (not stored) | Deferred. The paper reports the target metric. Not instantiable until Metric is approved. |
| BUILDS_ON | Paper → Paper | ACTIVE | RULE_DERIVED, MANUALLY_CURATED | The source paper states that it builds on the target paper, and cites it. |
| EXTENDS | Paper → Paper | ACTIVE | RULE_DERIVED, MANUALLY_CURATED | The source paper states that it extends the target paper's method, and cites it. |
| COMPARES_WITH | Paper → Method | ACTIVE | RULE_DERIVED, MANUALLY_CURATED | The paper reports an empirical or analytical comparison against the target method. |

### Evidence

| Relation | Domain → Range | Status | Allowed provenance | Definition |
|---|---|---|---|---|
| SUPPORTS | Paper → Claim | ACTIVE | MANUALLY_CURATED | The paper provides evidence for the target claim. |
| CHALLENGES | Paper → Claim | ACTIVE | MANUALLY_CURATED | The paper provides evidence against the target claim. |
| REPORTS_LIMITATION | Method → Limitation | ACTIVE | RULE_DERIVED, MANUALLY_CURATED | Paper P reports that Method M has Limitation L. This is an ATTRIBUTED assertion by P, not a verified property of M. The reporting paper, source field, evidence span and attribution (SELF_REPORTED if P proposes M, THIRD_PARTY otherwise) are mandatory in provenance for every provenance type. |

### Research direction

| Relation | Domain → Range | Status | Allowed provenance | Definition |
|---|---|---|---|---|
| MOTIVATES | Limitation → ResearchDirection | ACTIVE | MANUALLY_CURATED | Addressing the source limitation is a reason for pursuing the target direction. |
| PREREQUISITE_FOR | Concept / Technique / Method → Concept / Technique / Method | ACTIVE | MANUALLY_CURATED | Understanding or implementing the source is required to understand or implement the target. |
| ALTERNATIVE_TO | Method / Technique → Method / Technique | ACTIVE | MANUALLY_CURATED | The two entities are interchangeable approaches to the same sub-problem. Symmetric; stored once with source id < target id. |
| GENERALIZES | Concept / Technique / Method → Concept / Technique / Method | ACTIVE | MANUALLY_CURATED | The source is a more general form of the target. |
| SPECIALIZES | Concept / Technique / Method → Concept / Technique / Method | ACTIVE | MANUALLY_CURATED | The source is a more specific form of the target. SPECIALIZES(B, A) states the same fact as GENERALIZES(A, B), so the validator rejects storing both. |
| COMBINES_WITH | Concept / Technique / Method → Concept / Technique / Method | ACTIVE | MANUALLY_CURATED | The two entities are used together in published work. Symmetric; stored once with source id < target id. |

### Per-relation constraints and notes

**CITED_BY**
- derived inverse of CITES

**ADDRESSES**
- range ResearchProblem: The paper states that its aim is to solve, improve on, or measure the problem.
- range Concept: The concept is the focal subject of the paper. A rule may create the edge only when an approved alias appears in the title, or as the object of a registered contribution pattern ("we propose/study/evaluate ... <alias>") within a single abstract sentence.

**REPORTS_LIMITATION**
- provenance.source_paper_id is mandatory (the reporting paper must be a corpus Paper)
- an evidence span is mandatory for every provenance type
- attribution (SELF_REPORTED or THIRD_PARTY) is mandatory and cross-checked against PROPOSES edges

**ALTERNATIVE_TO**
- symmetric: stored once with source id < target id

**SPECIALIZES**
- mirror of GENERALIZES: the same fact must not be stored in both forms

**COMBINES_WITH**
- symmetric: stored once with source id < target id
