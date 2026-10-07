# ADR-0006: Bounded graph traversal

**Status:** Accepted for Milestone 1 review.

## Decision
Traversal depth and node count are configuration values (`traversal.max_hops`, `traversal.max_nodes`).

## Alternatives considered
Unbounded closure; fixed constants in code.

## Rationale
Section 19. Bounds keep results explainable and runtime predictable.

## Consequences
Distant relations are not reached. The bound is part of the evaluated configuration.

## Rejected alternatives
Uncontrolled multi-hop expansion.
