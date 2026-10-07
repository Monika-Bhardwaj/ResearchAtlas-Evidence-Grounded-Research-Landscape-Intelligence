# Milestone 1 review guide

Each review gate, where to look, and how to verify it. Nothing here needs the network or any data.

| Gate | Where to look | Verify |
|---|---|---|
| 1. Closed vocabulary: exactly the 20 Section 7 keys | `src/ontology/ontology.yaml`, `docs/ontology.md` | `pytest tests/unit/test_ontology.py` (key set equals a hard-coded Section 7 list; HAS_LIMITATION, CONFLICTING and INSUFFICIENT_EVIDENCE are rejected as relations) |
| 2. Relation-source inventory | `docs/relation_source_inventory.md` | Every relation classified; estimates marked "not quotas"; curated workload total at the bottom |
| 3. Domain/range, especially ADDRESSES, REPORTS_LIMITATION, SUPPORTS, CHALLENGES, PREREQUISITE_FOR | `docs/ontology.md` (per-relation constraints) | `pytest -k "domain or range or addresses or reports_limitation"` |
| 4. Provenance: every derived or curated edge traceable | `src/knowledge/models.py` | `pytest tests/unit/test_provenance.py`; the schema has no UNKNOWN, UNSOURCED or LLM_INFERRED |
| 5. Curation feasibility | `docs/relation_source_inventory.md` | Compare the estimated curated edges and hours with what you can author |
| 6. Validators fail instead of repairing | `src/knowledge/validation.py`, `src/ontology/loader.py` | `pytest tests/unit/test_knowledge_validation.py tests/adversarial` |
| 7. Contract traceability | `docs/research_contract.md` part 2.6 | `pytest tests/unit/test_contract_traceability.py` (every listed artifact exists) |
| 8. No premature implementation | `src/ingestion`, `src/corpus`, `src/reasoning`, `src/interface` | Each contains only a placeholder `__init__.py`; `data/` holds only blank templates |

Run everything: `python -m pytest`.

Things deliberately left for you to decide at this review: the PROPOSED parameters in `docs/research_contract.md` part 2.1, and ADR-0012 (corpus size).
