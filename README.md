# ResearchMap

A provenance-backed research-decision engine. It models a focused research landscape (persistent
and long-term memory for LLM agents) as typed entities and relationships, then positions a
previously unseen research proposal within that landscape. It reports what the indexed corpus
does and does not contain. It never claims novelty.

**Status: Milestone 1 approved; Milestone 2 (ingestion and corpus) in progress.** No graph, no
gold data and no reasoning code exist yet.

| Milestone | Scope | Status |
|---|---|---|
| M0 | Reconnaissance, A-J design review | done |
| M1 | Ontology, schemas, provenance, validators, contract | **approved/frozen** |
| M2 | Ingestion and corpus | **in progress** |
| M3 | Knowledge construction | not started |
| M4 | Proposal reasoning and CLI | not started |
| M5 | Evaluation and adversarial testing | not started |
| M6 | Optional LLM explanation layer | not started |

## Install and test

    python -m venv .venv && . .venv/bin/activate
    pip install -r requirements-dev.txt
    python -m pytest

## What exists in M1

    src/ontology/     closed vocabulary (20 relations, 9 entities), loader that fails on any invalid state
    src/knowledge/    provenance and knowledge-state models, validators, canonical I/O, curation formats
    src/evaluation/   gold-set schema, structural validators, sealing
    src/output/       runtime output schema
    config/           all constants; M1 values are frozen
    schemas/          JSON Schemas, so the knowledge state can be checked without our code
    docs/             ontology, relation-source inventory, research contract, ADRs, review guide
    data/             blank human-authored templates only

Start with `docs/m1_review_guide.md`.

## How the hard constraints are enforced

| Constraint | Where |
|---|---|
| No automatic entity/relation extraction | The only edge sources are explicit metadata, registered approved rules, and a human-authored curation file (`ProvenanceType` has no other value). No NLP or LLM dependency exists. |
| Closed relation vocabulary | `RelationType` enum and the loader's exact key check |
| Every derived edge has provenance | `Provenance` model validators; graph validators |
| Corrupt state fails fast | integrity hash, `KnowledgeStateCorruptError`, `scripts/validate_knowledge_state.py` |
| Human-owned curated edges and gold | `authorship: HUMAN` attestation in the schemas; templates are blank |

## Commands

    python scripts/validate_knowledge_state.py   # exit 2 until a build exists (Milestone 3)
    python scripts/export_schemas.py --check
    python scripts/render_docs.py --check
    python scripts/seal_gold.py <gold file> [--verify]

## Limitations (Milestone 1)

Estimates in `docs/relation_source_inventory.md` are planning estimates made before any corpus
exists. The Semantic Scholar and arXiv hosts are not reachable from the authoring sandbox, so
Milestone 2 ingestion must be run on a machine with network access.
