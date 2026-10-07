# ADR-0007: Human ownership of curated edges, gold sets and ontology approval

**Status:** Accepted for Milestone 1 review.

## Decision
The ontology and rule registry may be AI-drafted, but are authoritative only after human approval. MANUALLY_CURATED edges and all gold labels and facet text are human-authored; the coding agent supplies only formats and validators. The frozen test gold is sealed by hash.

## Alternatives considered
Agent-drafted curated edges with human approval; agent-authored gold.

## Rationale
An agent that reads abstracts and proposes edges is close to the prohibited extraction pattern, and an agent that writes the test set grades its own work.

## Consequences
More human effort (see docs/relation_source_inventory.md). approach.md section 7 must disclose the AI-assisted drafting of the ontology and rule registry.

## Rejected alternatives
Agent-authored curated edges or gold, even with approval.
