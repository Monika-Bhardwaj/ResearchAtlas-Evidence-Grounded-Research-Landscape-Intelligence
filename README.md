# ResearchMap

A provenance-backed research-decision engine for **persistent / long-term memory for LLM agents**.

It transforms a collected paper corpus into an explicit knowledge model of papers, methods,
concepts, problems, benchmarks, limitations, and research directions. It then accepts a new
proposal that was not in the corpus and produces a structured, evidence-backed analysis:
- closest prior work
- prerequisite-aware reading path
- literature tensions
- explicit limitations
- positioning across well-explored / partially-explored / underrepresented / unknown
- abstention and uncertainty warnings

**Milestone status:** M1 approved and frozen; M2 corpus built; M3/M4 implementation present.
Semantic Scholar is the primary M1 source; because no S2 API key is available yet, the committed
corpus uses arXiv and OpenAlex metadata, with S2 code ready once a key is provided.

---

## What the project does

You give it:

> I want to build an LLM agent with episodic memory, semantic memory, memory consolidation, and selective forgetting.

It responds with a structured output grounded in the frozen `knowledge_state.json`.

It is **not**:
- a paper search engine
- a vector-only RAG wrapper
- an LLM that extracts a knowledge graph
- an analytics dashboard

---

## Architecture

```text
Raw papers (arXiv/OpenAlex/S2 cache, committed)
    ↓
identity normalization / duplicate grouping / ambiguous marking
    ↓
candidate pool + deterministic corpus selection
    ↓
corpus_manifest.json + Section 11 stats + relation-source audit
    ↓
approved vocabulary + explicit deterministic rules
    ↓
knowledge_state.json (entities, edges, provenance, ambiguities)
    ↓
new proposal
    ↓
proposal grounding → candidate retrieval → bounded traversal → evidence
    ↓
prior work / tensions / reading path / positioning / abstention
```

Human-authored inputs:
- `data/curation/vocabulary.yaml`
- `data/curation/curation.yaml`
- M1 `docs/research_contract.md`

Machine-generated/independently inspectable:
- `data/corpus_manifest.json`
- `data/corpus/selected_pool.json`
- `knowledge/knowledge_state.json`
- `knowledge/manifest.json`
- `docs/m2_corpus_quality_stats.{json,md}`
- `docs/m2_relation_source_audit.{json,md}`
- `docs/m3_knowledge_build_report.json`

---

## Repository layout

```text
config/         frozen M1 and M2 configuration
data/
  raw/          committed raw API responses
  cache/        normalized source records
  corpus/       normalized candidate pool, selected pool, normalization report
  curation/     human-authored vocabulary and empty/curated edge templates
  evaluation/   blank gold templates only; no agent-authored gold
docs/           M1 contract, M2 reports, ontology, ADRs
knowledge/      serialized knowledge_state.json + manifest
scripts/        acquisition, build, validate, inspect, sealing scripts
src/
  ingestion/    S2, arXiv, OpenAlex clients, raw caches, retry logic
  corpus/       identity resolution, deterministic selection, stats, relation audit
  ontology/     closed vocabulary and loader
  knowledge/    provenance, validation, canonical I/O, vocab/curated entrypoint
  reasoning/    proposal grounding, candidate retrieval, bounded graph traversal
  interface/    CLI entry point
  evaluation/   gold structures and sealing
  output/       runtime output models
tests/          unit, integration, adversarial M1 tests
```

---

## Installation

Python 3.10+ recommended. This repo was developed on Python 3.14.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
```

---

## Environment variables

Optional, only needed for live Semantic Scholar acquisition:

```bash
export SEMANTIC_SCHOLAR_API_KEY="..."
```

**Do not commit this key.**

---

## Data acquisition

Corpus acquisition code lives in `scripts/build_corpus.py`.

The deterministic seed queries are fixed in `config/corpus.yaml`. The committed acquisition used:
- arXiv API (`src/ingestion/arxiv.py`)
- OpenAlex Works API (`src/ingestion/openalex.py`)
- Semantic Scholar client ready but skipped (`src/ingestion/semantic_scholar.py`) due to no key.

Raw caches are preserved byte-for-byte under `data/raw/`.

To re-run an arXiv/OpenAlex acquisition:

```bash
.venv/bin/python scripts/build_corpus.py acquire --provider openalex --limit 50 --expand-references-limit 2
.venv/bin/python scripts/build_corpus.py acquire --provider arxiv --limit 50
```

To rebuild the candidate pool, selected corpus, Section 11 stats, relation audit, and manifest:

```bash
.venv/bin/python scripts/build_corpus.py normalize
.venv/bin/python scripts/build_corpus.py select --target-size 70
```

Current committed corpus:
- 70 selected papers
- 924 normalized candidate groups from 1051 raw records
- 29 CITES edges inside the selected corpus
- 41 isolated papers (sparse citation connectivity is documented, not hidden)

Current Section 11 statistics and L4/T4 relation-source audit are in:
- `docs/m2_corpus_quality_stats.md`
- `docs/m2_relation_source_audit.md`

---

## Knowledge-state generation

Prerequisite: `data/corpus/selected_pool.json` and `data/curation/vocabulary.yaml`.

```bash
.venv/bin/python scripts/build_knowledge_state.py
```

What it produces:
- `knowledge/knowledge_state.json`
- `knowledge/manifest.json`
- `docs/m3_knowledge_build_report.json`

Current M3 validation result:
- 114 entities
- 85 relationships
- relation distribution in `docs/m3_knowledge_build_report.json`
- validation errors: 0

Validate independently:

```bash
.venv/bin/python scripts/validate_knowledge_state.py
```

---

## Human-owned vocabulary and curation

`data/curation/vocabulary.yaml` defines the approved Concept/Method/Technique/Problem/Benchmark/Limitation/ResearchDirection entries used by the builder.

`data/curation/curation.yaml` is empty in the committed build; it exists so human curated
edges can be added without weakening provenance.

No curated edges, gold facets, or automatic extracted triplets are fabricated by the agent.

---

## Running the CLI on a new proposal

```bash
.venv/bin/python -m src.interface.cli \
  --proposal "I want to build an LLM agent with episodic memory, semantic memory, memory consolidation, and selective forgetting."
```

Add `--json` for machine-readable output, and `--verbose` for extra provenance hints.

The output reports:
- proposal grounding
- closest prior work
- recommended reading order
- literature tensions
- positioning
- limitations
- uncertainty/warnings

The system never claims a proposal is “novel”; it says what the indexedcorpus does or does not contain.

---

## Inspecting the knowledge state

```bash
.venv/bin/python scripts/inspect_knowledge.py --stats
.venv/bin/python scripts/inspect_knowledge.py --relation PROPOSES
.venv/bin/python scripts/inspect_knowledge.py --entity paper:doi_10_48550_arxiv_2310_08560
.venv/bin/python scripts/inspect_knowledge.py --neighbors concept:episodic_memory
```

You can open `knowledge/knowledge_state.json` directly and inspect:
- schema and ontology versions
- entities
- relationships
- provenance per edge
- provenance type, rule id, source field, evidence span, confidence
- ambiguity records
- integrity hash

---

## Testing

```bash
.venv/bin/python -m pytest tests/unit/test_corpus_m2.py -q
.venv/bin/python -m pytest tests/unit/test_reasoning_m4.py -q
.venv/bin/python -m pytest tests/integration/test_m4_cli.py -q
.venv/bin/python -m pytest tests/unit/test_contract_traceability.py -q
```

The M1 placeholder gate was updated when M2/M3/M4 code landed; the current contract test expects the M2/M4 entry points to exist.

---

## Evaluation status

Formal M5 evaluation, baselines, adversarial gold sets, and frozen test proposals are not yet available because:
- `data/evaluation/gold_*.yaml` are blank by M1 contract
- the agent must not author or revise gold labels/facet text
- Semantic Scholar citation intents/influence labels are intentionally unused

A functional deterministic CLI smoke test exists:

```bash
.venv/bin/python -m pytest tests/integration/test_m4_cli.py -q
```

Human-authored M5 gold annotation and sealed test sets remain future work.

---

## Reproducibility

To regenerate the committed M2/M3 state from the committed cache:

```bash
.venv/bin/python scripts/build_corpus.py normalize
.venv/bin/python scripts/build_corpus.py select --target-size 70
.venv/bin/python scripts/build_knowledge_state.py
.venv/bin/python scripts/validate_knowledge_state.py
```

The corpus manifest is content-hashed in `data/corpus_manifest.sha256.json`.
The knowledge state integrity hash is stored inside `knowledge/knowledge_state.json`.

---

## Limitations

- Semantic Scholar acquisition is blocked until an API key is provided.
- Most selected corpus papers are recent; some queries return no exact arXiv hits.
- OpenAlex citation edges are sparse in the frozen selected corpus.
- Abstracts contain no strong tension/support claims, so T4 has insufficient evidence by design.
- `REPORTS_LIMITATION`, `MOTIVATES`, `SUPPORTS`, and `CHALLENGES` currently have zero edges because they require human-curated claim/limitation evidence.
- No embedding models are installed/used; baselines requiring embeddings must run on a machine with network access.
- This is an engineering prototype, not a bibliographic analyzer.

---

## What would I build next?

1. Add Semantic Scholar cache when a key is available.
2. Add human-curated limitation/claim edges to strengthen L4/T4.
3. Add a frozen human-authored dev/test proposal set for M5 metrics.
4. Run the baseline comparison and ablation ladder.
5. Add a local UI only if the deterministic CLI needs it for demo.
