# Approach

## 1. Problem

A new researcher entering a field needs more than a paper list. They need:
- what is foundational
- what builds on what
- where the literature disagrees or is sparse
- what to read first
- whether their proposed combination has direct prior work

Existing tools mostly retrieve papers. ResearchMap models the research landscape as typed entities and relationships, then uses that model to answer those questions.

## 2. Why simple retrieval is not enough

BM25 or embedding retrieval can find related papers, but it cannot explain:
- which *method* a paper proposes
- which *concept* a paper addresses
- which *benchmark* a paper evaluates
- whether a paper reports a limitation
- whether two papers support or challenge the same claim
- whether a new proposal combines concepts that are separately represented but under-connected

A flat paper store is not a knowledge base.

## 3. Corpus scope and selection

Corpus topic:

> Persistent / long-term memory for LLM agents.

Subtopics:
- persistent memory
- episodic memory
- semantic memory
- memory consolidation
- selective forgetting
- memory retrieval
- long-horizon agent evaluation

Committed corpus:
- **70 papers**
- candidate pool: 924 normalized groups
- raw records: 1051
- sources: arXiv and OpenAlex; Semantic Scholar client ready but skipped until an API key is available
- raw caches committed under `data/raw/`
- selection procedure: `scripts/build_corpus.py normalize` → `scripts/build_corpus.py select --target-size 70`

Temporal distribution currently:
- ≤2021: 11
- 2022–2023: 20
- ≥2024: 40

The corpus is not perfect: many OpenAlex search hits are recent, citation edge count is 29 inside the selected set, and 41 papers have no in-corpus citation links. This is documented rather than hidden.

## 4. Entities and relationships

Entity types:
- `Paper`
- `ResearchProblem`
- `Method`
- `Technique`
- `Concept`
- `Benchmark`
- `Claim`
- `Limitation`
- `ResearchDirection`

Relations retained from the M1 frozen ontology:
- `CITES`
- `PROPOSES`
- `USES`
- `EVALUATES_ON`
- `COMPARES_WITH`
- `EXTENDS`
- `BUILDS_ON`
- `ADDRESSES`
- `DEPENDS_ON`
- `PREREQUISITE_FOR`
- `ALTERNATIVE_TO`
- `GENERALIZES`
- `SPECIALIZES`
- `COMBINES_WITH`
- `SUPPORTS`
- `CHALLENGES`
- `REPORTS_LIMITATION`
- `MOTIVATES`
- `MEASURES_WITH` (deferred)
- `CITED_BY` (derived inverse, not stored)

Runtime `CONFLICTING` and `INSUFFICIENT_EVIDENCE` are labels, not ontology relations.

## 5. Knowledge construction

Construction happens in two deterministic passes.

### Pass A — identity and corpus selection (M2)

`src/corpus/pool.py` canonicalizes papers using:
1. DOI
2. arXiv ID
3. Semantic Scholar paper ID
4. normalized title + first-author + year fallback

Ambiguous records with conflicting primary IDs are flagged and not silently merged.
The frozen selection is written to:
- `data/corpus/candidate_pool.json`
- `data/corpus/selected_pool.json`
- `data/corpus_manifest.json`

### Pass B — deterministic rule-based graph build (M3)

`src/knowledge/builder.py` uses only the approved vocabulary in `data/curation/vocabulary.yaml` and explicit phrase/contribution-pattern rules.

Current rule-derived edges:
- `ADDRESSES`: alias in title or contribution sentence
- `PROPOSES`: method alias in title or proposal-language sentence
- `USES`: method/technique alias in a usage sentence
- `EVALUATES_ON`: benchmark alias in title or evaluation-language sentence
- `COMPARES_WITH`: method alias in comparison-language sentence
- `REPORTS_LIMITATION`: method + limitation alias in a limitation sentence, with provenance attribution

Explicit citation edges come from source metadata reference lists (`CITES`).

Every rule-derived edge carries:
- `rule_id`
- `source_field`
- evidence span
- mapping decision
- confidence
- ontology/build version
- source paper id when required

No LLM is used to build the graph.

### Current M3 state
- 114 entities
- 85 relationships
- 0 validation errors
- integrity-verified `knowledge/knowledge_state.json`

## 6. Runtime reasoning over a new proposal (M4)

Input is a new proposal that is never added to the corpus.

Pipeline:
1. deterministic grounding against `data/curation/vocabulary.yaml`
2. ambiguity marking for shared aliases
3. candidate paper retrieval via typed edges
4. bounded local graph traversal (in-progress implementation is neighbor/coverage-based; the explicit bounded BFS is intentionally simple and documented)
5. evidence aggregation from source edges
6. explicit prior-work scoring
7. facet-level positioning
8. absence or evidence-sufficiency warnings
9. deterministic structured output

The scoring function follows Section 21:

```text
PriorWorkScore =
0.30 * ConceptOverlap +
0.20 * MethodOverlap +
0.15 * ProblemOverlap +
0.10 * BenchmarkOverlap +
0.10 * GraphProximity +
0.10 * CitationConnectivity +
0.05 * TemporalRelevance
```

Current scoring is deterministic and explainable; papers are ranked by direct typed overlap and direct citation connectivity only where source metadata exists.

## 7. Constraint compliance

The system does **not** use:
- spaCy NER
- GLiNER
- REBEL
- OpenIE
- LLM relation extraction
- automatic knowledge-graph builders
- Semantic Scholar citation intent/influence labels as semantic relations

Allowed sources of graph facts:
- explicit source metadata (`CITES`)
- human-authored vocabulary + explicit rules
- future approved human curation

No automatic NER/extraction library constructs the graph.

## 8. Provenance and auditability

Every edge has a typed provenance record:
- `EXPLICIT_METADATA` for citation edges
- `RULE_DERIVED` for title/abstract phrase rules
- `MANUALLY_CURATED` for human curated future edges

`REPORTS_LIMITATION` requires:
- reporting paper id
- evidence span
- attribution: `SELF_REPORTED` or `THIRD_PARTY`

The knowledge state is inspectable without code via `knowledge/manifest.json` and the raw JSON.

## 9. Abstention and uncertainty

If a facet has no sufficient support, the system returns:

> Insufficient evidence in the indexed corpus.

It never says the proposal is novel.
It never converts `UNKNOWN` into `novel`.

## 10. Tensions and negative knowledge

Tensions/limitations require explicit edges:
- `SUPPORTS`
- `CHALLENGES`
- `REPORTS_LIMITATION` → `MOTIVATES`

Because the current committed corpus has sparse abstract evidence for claims, the CLI emits:
- `INSUFFICIENT_EVIDENCE` for tensions
- no fabricated reports_limitation edges unless the metadata/rule conditions are met

This is intentional: sparse honest evidence is preferred over dense invented edges.

## 11. Baselines and evaluation status

Mandatory evaluation would use:
- Baseline A: BM25-style retrieval
- Baseline B: embedding similarity
- Baseline C: citation graph retrieval
- Baseline D: abstract RAG
- Baseline E: typed concept overlap
- System: typed graph + provenance reasoning

These are not fully executable in this committed state because:
- no Semantic Scholar key exists yet
- no human-authored frozen gold set exists yet
- embeddings/networkx dependencies are not enabled in the minimal committed environment
- M1 prohibits the agent from authoring gold labels/facet text

A deterministic CLI smoke test is present and passes:

```bash
.venv/bin/python -m pytest tests/integration/test_m4_cli.py -q
```

## 12. Failure handling

- corrupt knowledge state: `KnowledgeStateCorruptError` in M1 validation
- corrupt raw cache: ingestion fails with API/cache error
- missing metadata: marked `PARTIAL_METADATA`
- ambiguous identity: flagged and not merged
- API timeout/retries: bounded exponential backoff in clients
- unknown proposal terms: reported as unknown concepts, not forced into the ontology
- no matched concepts: warnings and `UNKNOWN` positioning
- no tools: deterministic output still returned

## 13. What is built today

Mandatory deliverables:
- `README.md`
- `approach.md`
- `knowledge/knowledge_state.json`
- `data/corpus_manifest.json`
- CLI: `python -m src.interface.cli`
- knowledge inspector: `scripts/inspect_knowledge.py`
- reproducible build/validation tests

## 14. Limitations and next steps

- Add S2 cache once a key is available.
- Build a human-authored dev/test gold set for M5.
- Add deterministic baselines A–E and run the ablation ladder.
- Improve ADDRESSES/REPORTS_LIMITATION precision.
- Collect more citation contexts before using T4.
- Add a richer but still deterministic bounded traversal with explicit depth cap and node cap.

## 15. Design tradeoffs

- Small curated corpus over broad shallow coverage: committed to 70 selected papers.
- Exact alias rules over fuzzy matching: precision first.
- No automatic extraction: preserves assignment constraint.
- Flat JSON over Neo4j: independently inspectable and no services.
- Sparse edge coverage over inferred fabrication: sparse is preferable to fake knowledge.
