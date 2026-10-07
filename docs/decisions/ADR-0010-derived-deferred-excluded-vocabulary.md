# ADR-0010: Derived, deferred and excluded vocabulary

**Status:** Accepted for Milestone 1 review.

## Decision
CITED_BY is a derived inverse of CITES and never stored. MEASURES_WITH is defined but deferred, along with the Metric entity. Author is a Paper attribute and Dataset is folded into Benchmark. SPECIALIZES stays ACTIVE with a mirror rule against GENERALIZES. ALTERNATIVE_TO and COMBINES_WITH are symmetric and stored once with source id < target id.

## Alternatives considered
Storing both directions; adding Metric, Author and Dataset entities.

## Rationale
Avoids duplicate facts and entities no v0.1 task consumes (Section 6: do not add entities because they sound sophisticated).

## Consequences
Enforced by the validators (EDGE_RELATION_NOT_STORABLE, EDGE_MIRROR_CONFLICT, EDGE_SYMMETRIC_ORDER).

## Rejected alternatives
Storing inverse relations.
