# ADR-0011: Optional LLM layer only at the explanation layer

**Status:** Accepted for Milestone 1 review.

## Decision
Any LLM is added after the deterministic system works (Milestone 6) and only explains already-selected evidence.

## Alternatives considered
LLM in grounding, scoring or graph construction.

## Rationale
Section 29. The system must stay fully functional without an LLM.

## Consequences
No LLM dependency exists in Milestone 1.

## Rejected alternatives
Any LLM that creates edges, claims, limitations or confidence.
