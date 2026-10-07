# Approach

## 1. Problem

The project solves the problem of **research paper onboarding**.

A researcher entering a narrow area usually has to manually answer:
- What is foundational?
- Which papers propose which methods?
- Which concepts are covered in which papers?
- Where is prior work closest to a proposed idea?
- Where is the literature underrepresented or unknown?
- What should I read next?

A flat paper list cannot answer these questions because it stores papers, not the typed relationships between papers, methods, concepts, benchmark results, limitations, and research directions.

ResearchAtlas therefore models the **research landscape**, not just papers.

## 2. Why simple retrieval is not enough

BM25, embeddings, citation recommendation, or generic RAG can retrieve related papers. They do not explain:
- the specific method a paper proposes
- which controlled concepts are connected to that method
- which benchmarks the paper evaluates
- which limitation it reports
- which claims are supported or challenged
- whether two papers directly cover the same novel combination

The system is intentionally deterministic and typed. A flat or opaque ranking would not satisfy the engineering judgment and inspectability requirements.

## 3. Scope of the selected corpus

Narrow topic:

> Persistent / long-term memory for LLM agents.

Seed concepts include:
- persistent memory
- long-term agent memory
- episodic memory
- semantic memory
- memory consolidation
- selective forgetting
- memory retrieval
- long-horizon interaction

Candidate sources:
- arXiv
- OpenAlex
- Semantic Scholar code path exists, but no API key was available at this stage

Why this topic?
- It is bounded enough for about 70 papers.
- It has clear methods and concepts.
- It has useful evaluation/benchmark papers.
- It still has sparse gaps, making underrepresented positioning meaningful.

Committed M2 corpus:
- 70 papers selected by deterministic rules
- 924 normalized candidate groups from 1051 raw records
- 29 in-corpus CITES edges
- 41 papers with zero in-corpus citation degree

The sparse citation connectivity is a reported limitation, not hidden.

## 4. Milestone progression

### M1 — Specification, ontology, provenance, contract v0.1

M1 froze the research contract and kept implementation minimal:
- closed vocabulary of 9 entities and 20 relations
- provenance models with explicit `EXPLICIT_METADATA`, `RULE_DERIVED`, and `MANUALLY_CURATED`
- JSON Schemas for inspectable serialization
- adversarial M1 validation tests
- research contract with hypotheses, baselines, T0–T5, primary metric, freeze points, and parameters fixed at M1 approval

### M2 — Corpus acquisition, raw cache, identity normalization, selection, manifest

M2 built the reproducible corpus:
- deterministic seed queries from `config/corpus.yaml`
- raw arXiv/OpenAlex responses committed under `data/raw/`
- normalized PaperRecord cache under `data/cache/records/`
- identity resolution merged by DOI → arXiv ID → S2 ID → normalized title/year/first-author
- ambiguous candidates flagged rather than silently merged
- greedy deterministic paper selection with temporal quotas and citation-aware scores
- frozen `data/corpus_manifest.json`
- Section 11 corpus statistics and M5-ready relation-source audit

### M3 — Deterministic knowledge construction

M3 built the inspectable graph:
- paper and curated vocabulary entities
- deterministic alias/title/abstract rules
- canonical edges with provenance
- no extraction libraries
- `knowledge/knowledge_state.json` validated and integrity-hashed

Current build:
- 114 entities
- 85 relationships
- distribution: 29 CITES, 45 PROPOSES, 7 EVALUATES_ON, 3 ADDRESSES, 1 COMPARES_WITH
- validation errors: 0

### M4 — New-input reasoning and CLI

M4 handles a new proposal:
1. normalize proposal text
2. ground against the controlled vocabulary
3. mark ambiguous terms
4. retrieve candidate papers using typed paper→entity edges
5. aggregate explicit evidence
6. score prior work with the M1 formula
7. generate reading path
8. emit tension/absence status and positioning
9. never claim novelty

CLI: `python -m src.interface.cli`

### M5 — Evaluation and adversarial testing (planned)

The formal M5 protocol is fixed in the frozen contract, but its gold sets are not authored by the agent.

Formal protocol:
- dev set: 8–10 proposals
- frozen test set: 24 proposals (20 in-scope + 4 out-of-scope)
- 3–5 gold facets per proposal, target 4, at least 1 combination facet
- minimum ≥8 gold facets per class
- T2 primary metric: proposal-weighted facet macro-F1
- T1 guard: nDCG@5 with fixed tolerance δ=0.10 and non-inferiority criterion
- T3 human rubric for prerequisite-aware reading path
- T4 tension precision/recall against human gold tensions; insufficient-evidence correctness
- T5 abstention risk-coverage/AURC
- baselines A–E
- ablation ladder L0–L5
- leakage audit before frozen test execution
- bootstrap CIs from proposal-level resamples

Current M5 reality:
- blank gold templates only
- deterministic CLI integration smoke test passes
- full M5 workflow cannot run until the human authors and seals gold data

## 5. Entities and reasoning behind them

| Entity | Why it exists |
|---|---|
| Paper | Evidence anchor; every semantic edge traces back to a corpus paper. |
| ResearchProblem | Lets facets map to named gaps/problems instead of only methods. |
| Method | The concrete approach a paper proposes. |
| Technique | Reusable mechanism used by a method. |
| Concept | Controlled vocabulary bridge between proposal facets and papers. |
| Benchmark | Captures evaluation context for prior work. |
| Claim | Shared assertion that makes tension analysis possible. |
| Limitation | Negative knowledge; what failed or remains weak. |
| ResearchDirection | Actionable future direction rather than a vague free-form next move. |

## 6. Relationships and reasoning behind them

Bibliographic:
- `CITES`: explicit source metadata only; no inferred intent is trusted.
- `CITED_BY`: derived view only, never stored.

Research structure:
- `ADDRESSES`: paper substantively addresses a problem/concept.
- `PROPOSES`: paper introduces its own method.
- `USES`: paper uses a method/technique.
- `DEPENDS_ON`: method cannot function without another technique/concept.
- `EVALUATES_ON`: paper reports results on a benchmark.
- `MEASURES_WITH`: deferred because Metric is not instantiable in v0.1.
- `BUILDS_ON`, `EXTENDS`, `COMPARES_WITH`: shown only when metadata/rules provide clear evidence.

Evidence:
- `SUPPORTS`, `CHALLENGES`: human-curated only in v0.1 because abstract-only extraction would be noisy.
- `REPORTS_LIMITATION`: method→limitation attributed to a paper, with `SELF_REPORTED` vs `THIRD_PARTY`.

Research direction:
- `MOTIVATES`, `PREREQUISITE_FOR`, `ALTERNATIVE_TO`, `GENERALIZES`, `SPECIALIZES`, `COMBINES_WITH`: entity-level human curation, sparse by design.

Every stored relation is in the closed vocabulary. No free-form edge types are accepted.

## 7. How the knowledge representation is built

Construction is deterministic:

```text
api client → raw JSON/XML cache → normalized PaperRecord →
identity normalization → candidate pool → deterministic selection →
corpus manifest → vocabulary matching + rule-derived edges →
validation → knowledge_state.json
```

Mapping rules are explicit and versioned. Examples:
- exact alias in title → ADDRESSES/PROPOSES/EVALUATES_ON candidate
- contribution phrase + concept alias → ADDRESSES
- method alias + proposal language → PROPOSES
- benchmark alias + evaluation language → EVALUATES_ON
- method alias + limitation language → REPORTS_LIMITATION

No spaCy, GLiNER, REBEL, OpenIE, LLM triplet prompts, or automatic KG libraries are used.

## 8. Tradeoffs

- **Small corpus over breadth:** 70 papers with connectivity is more defensible than shallow coverage.
- **Deterministic rules over recall:** fewer edges, but every edge is explainable.
- **Frozen contract over ad hoc convenience:** M2 statistics inform feasibility review, but do not silently rewrite M1 parameters.
- **JSON knowledge state over graph DB:** inspectable and reproducible without services.
- **Sparse relations over fabricated dense relations:** missing claims are documented as unknown rather than invented.
- **Exact terms over loose matching:** prevents unrelated mentions from becoming edges.

## 9. How a new input is processed

The proposal is never added to the frozen corpus.

Pipeline:
1. ground against approved vocabulary
2. mark ambiguous terms and unknown terms
3. retrieve papers adjacent to matched entities
4. score each paper with fixed M1 weights
5. select a bounded reading path
6. derive positioning from found counts, score confidence, and attributed support
7. report tensions only when evidence exists
8. emit warnings for insufficient evidence

Scoring formula:

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

## 10. Knowledge state inspectability

`knowledge/knowledge_state.json` is mandatory and self-contained.

It includes:
- schema/ontology/corpus/build versions
- entities with IDs and attributes
- relationships with source/relation/target
- provenance for each edge
- ambiguities
- integrity hash
- confidence

It can be reviewed directly without executing code.

## 11. Failure handling

- raw API failure: bounded retry and raw cache preservation
- corrupt cache: fail fast
- corrupt knowledge state: fail validation
- ambiguous records: flagged, never silently merged
- missing metadata: marked partial, not fabricated
- no matched concept: `UNKNOWN` positioning, no forced answer
- no sufficient evidence: abstention warning
- LLM failure: not applicable to current deterministic path

## 12. Limitations

- no complete formal M5 gold evaluation yet
- Semantic Scholar key unavailable; committed corpus uses OpenAlex/arXiv
- sparse citation connectivity and many recent papers
- limitation/tension edges are currently sparse because they require human-level evidence
- corpus selection is deterministic but not perfect for every domain shift

## 13. What I would build next

- add human-authored `data/curation/curation.yaml` edges for methodology, limitations, directions
- add human gold sets for T0–T5
- implement formal baselines A–E and L0–L5
- add citation-context pulls from Semantic Scholar once a key exists
- expand inspector and leakage audit for gold evaluation
