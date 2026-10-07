# ADR-0001: JSON files, not a graph database

**Status:** Accepted for Milestone 1 review.

## Decision
Store the knowledge state as canonical JSON with an embedded integrity hash.

## Alternatives considered
Neo4j or another graph database; SQLite.

## Rationale
A 50-100 paper corpus has well under a few thousand nodes and edges. A reviewer must be able to open the file without running anything (Section 16), and rebuilds must be byte-reproducible.

## Consequences
Traversal is implemented in Python over in-memory structures. Fine at this scale; it would not scale to millions of nodes.

## Rejected alternatives
A database adds infrastructure and hides state; rejected under Section 40.
