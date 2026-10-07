# ADR-0003: Precision-first mapping

**Status:** Accepted for Milestone 1 review.

## Decision
Rules use exact phrases and curated aliases only; a generic word never maps to a specific concept.

## Alternatives considered
Embedding or fuzzy matching for concept mapping.

## Rationale
False edges contaminate downstream reasoning more than missing weak edges (Section 14).

## Consequences
Lower recall, for example ADDRESSES covers focal concepts only. Ambiguous terms are recorded as AmbiguityRecord, never resolved silently.

## Rejected alternatives
Semantic-similarity mapping, rejected for unverifiable false positives.
