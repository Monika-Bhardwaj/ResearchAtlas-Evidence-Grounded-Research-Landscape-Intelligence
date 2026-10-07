# ResearchMap

ResearchMap is a provenance-backed **research-decision engine** for the topic:

> **Persistent / Long-Term Memory for LLM Agents**

It collects a focused corpus of papers, turns that corpus into an explicit,
independently inspectable knowledge state, and then analyzes a new proposal that
was **not** in the corpus. The output is structured guidance a researcher can act
on: closest prior work, typed overlap, citation connectivity, reading path,
limitations/tensions, positioning, and uncertainty.

It is not a paper search engine, generic RAG wrapper, analytics dashboard, or
autonomous agent.

---

## What problem does it solve?

A new researcher entering a field needs more than paper links. They need to know:

- what is foundational
- what builds on what
- what concepts and methods a paper uses
- where work is dense, sparse, or contradictory
- whether a proposed idea has direct coverage in the corpus
- what to read first

ResearchMap models the research landscape rather than only storing papers.

---

## Corpus / dataset

Topic: persistent and long-term memory for LLM agents.

Frozen corpus:
- 70 papers selected from 924 normalized candidate groups
- 1051 raw source records
- current relation-source audit in `docs/m2_relation_source_audit.md`
- Section 11 corpus statistics in `docs/m2_corpus_quality_stats.md`

Source status:
- OpenAlex and arXiv raw caches are committed.
- Semantic Scholar is the M1 primary source, but no API key is available; the
  client is implemented under `src/ingestion/semantic_scholar.py`.

Important corpus limitations:
- 29 in-corpus CITES edges
- 41 isolated papers
- many M2 queries return recent 2024–2026 work
- `REPORTS_LIMITATION`, `SUPPORTS`, `CHALLENGES`, `MOTIVATES`,
  `PREREQUISITE_FOR`, etc. require human curation and are currently sparse/zero.

---

## Project structure

```text
config/
  default.yaml         frozen M1 scoring/reading-path/gold parameters
  corpus.yaml          deterministic M2 seed queries, quotas, selection weights
data/
  raw/                 committed raw API responses
  cache/records/       normalized PaperRecord JSON grouped by provider/query
  corpus/              candidate pool, ambiguous identities, normalized report
  curation/            human vocabulary + blank/approved curation files
  evaluation/          blank gold templates only
knowledge/
  knowledge_state.json inspectable M3 knowledge state
  manifest.json        knowledge-state manifest
docs/
  research_contract.md frozen M1 contract v0.1
  m2_corpus_quality_stats.md
  m2_relation_source_audit.md
  m3_knowledge_build_report.json
src/
  ingestion/           arXiv, OpenAlex, Semantic Scholar clients and raw caches
  corpus/              identity resolution, selection, statistics, audit, manifest
  ontology/            closed M1 vocabulary and loader
  knowledge/           models, validators, canonical I/O, curation, builder
  reasoning/           deterministic proposal grounding, scoring, output builder
  interface/           CLI entry point
  output/              runtime output models
  evaluation/          gold-set models/sealing only
scripts/
  build_corpus.py
  build_knowledge_state.py
  validate_knowledge_state.py
  inspect_knowledge.py
  export_schemas.py
  render_docs.py
  seal_gold.py
tests/
  unit/
  integration/
  adversarial/
```

---

## How it works

```text
M1: Contract, ontology, schemas, provenance, validators
    ↓
M2: arXiv/OpenAlex/S2 acquisition → raw cache → identity normalization →
    candidate pool → deterministic selection → corpus manifest → quality stats
    ↓
M3: approved vocabulary + deterministic rules → provenance-rich edges →
    validated knowledge_state.json
    ↓
M4: new proposal → deterministic grounding → candidate retrieval →
    bounded reasoning path → prior-work score → positioning/tensions/reading path
    ↓
M5: frozen gold evaluation, baselines, ablations, adversarial testing
    (M5 formal gold annotation remains future work; no agent-authored gold)
```

---

## Install

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements-dev.txt
```

Python 3.10+ is required. This repository was verified on Python 3.14 in the
local sandbox.

---

## Environment variables / configuration

Required for live Semantic Scholar acquisition only:

```bash
export SEMANTIC_SCHOLAR_API_KEY="your-key"
```

Do **not** commit the key.

Other configuration:
- `config/default.yaml` — M1 frozen parameters: traversal, reading-path size,
  scoring weights, gold structure.
- `config/corpus.yaml` — M2 frozen acquisition/selection parameters: topic,
  seed queries, temporal quotas, scoring weights.

---

## Load or regenerate the corpus (M2)

The committed corpus is already frozen. To regenerate from caches:

```bash
.venv/bin/python scripts/build_corpus.py normalize
.venv/bin/python scripts/build_corpus.py select --target-size 70
```

These commands read committed provider records under `data/cache/records/` and
write:
- `data/corpus/candidate_pool.json`
- `data/corpus/selected_pool.json`
- `data/corpus_manifest.json`
- `docs/m2_corpus_quality_stats.{md,json}`
- `docs/m2_relation_source_audit.{md,json}`

To re-run live acquisition instead:

```bash
.venv/bin/python scripts/build_corpus.py acquire --provider openalex --limit 50 --expand-references-limit 2
.venv/bin/python scripts/build_corpus.py acquire --provider arxiv --limit 50
# .venv/bin/python scripts/build_corpus.py acquire --provider semantic_scholar --limit 50 --require-s2-key
```

---

## Regenerate the knowledge state (M3)

```bash
.venv/bin/python scripts/build_knowledge_state.py
.venv/bin/python scripts/validate_knowledge_state.py
```

Outputs:
- `knowledge/knowledge_state.json`
- `knowledge/manifest.json`
- `docs/m3_knowledge_build_report.json`

The state contains:
- `schema_version`
- `ontology_version`
- `corpus_version`
- `knowledge_build_version`
- `entities`
- `relationships`
- `ambiguities`
- `build_metadata`
- `integrity` hash

A reviewer can open this JSON without running code and see exactly which papers,
concepts, methods, limitations, benchmarks, and relations exist and why.

---

## Run the testable interface / give it a new input

```bash
.venv/bin/python -m src.interface.cli \
  --proposal "I want to build an LLM agent with episodic memory, semantic memory, memory consolidation, and selective forgetting."
```

Machine-readable JSON:

```bash
.venv/bin/python -m src.interface.cli --json \
  --proposal "I want to build an LLM agent with episodic memory, semantic memory, memory consolidation, and selective forgetting."
```

The CLI prints:
- proposal grounding
- closest prior work
- recommended reading order
- literature tensions
- facet positioning
- limitations
- uncertainty/warnings

Example supported checks:
```bash
.venv/bin/python scripts/inspect_knowledge.py --stats
.venv/bin/python scripts/inspect_knowledge.py --relation PROPOSES
.venv/bin/python scripts/inspect_knowledge.py --entity paper:doi_10_48550_arxiv_2310_08560
```

---

## Evaluation / adversarial status (M5)

The M1 contract defines the formal M5 evaluation: frozen human-authored gold,
proposal-weighted facet macro-F1, T1 nDCG@5 guard, baselines A–E, ablations
L0–L5, leakage audit, bootstrap CIs, T3 rubric scoring, and T4 tension
precision/recall.

Current repository status:
- `data/evaluation/gold_dev.template.yaml` and `gold_test.template.yaml` are blank.
- No agent-authored gold labels, facet text, tensions, or limitation labels exist.
- `src/evaluation/gold.py` validates/seal structure but has no content to freeze.
- `tests/integration/test_m4_cli.py` is a deterministic smoke test, not a formal
  T2 benchmark.

This remaining M5 work is explicitly documented in `approach.md`.

---

## Testing

Full sandbox test command:

```bash
.venv/bin/python -m pytest -q
```

Useful targeted commands:

```bash
.venv/bin/python -m pytest tests/unit/test_corpus_m2.py -q
.venv/bin/python -m pytest tests/unit/test_reasoning_m4.py -q
.venv/bin/python -m pytest tests/integration/test_m4_cli.py -q
.venv/bin/python scripts/export_schemas.py --check
.venv/bin/python scripts/render_docs.py --check
```

All M1-M4 construction and validation checks passed in the local sandbox test run.

---

## Limitations

- Semantic Scholar is not part of the committed corpus because no API key is available.
- The corpus is sparse in citation connectivity, honestly reflected in the statistics.
- There are no fabricated `SUPPORTS`, `CHALLENGES`, `MOTIVATES`, or dense
  `REPORTS_LIMITATION` claims without human/curated evidence.
- Formal M5 metrics cannot be produced until human-authored gold sets are created.
- The runtime system does not claim novelty; it reports only evidence found in the indexed corpus.
