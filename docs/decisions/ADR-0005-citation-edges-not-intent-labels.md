# ADR-0005: Citation edges yes, automatic citation-intent labels no

**Status:** Accepted for Milestone 1 review.

## Decision
CITES comes from reference lists. Semantic Scholar's citation intents and influence flags are never used as relations; citation contexts are raw evidence only.

## Alternatives considered
Using S2 intents as SUPPORTS/CHALLENGES.

## Rationale
Section 4 forbids substituting automatically inferred labels for our own knowledge model.

## Consequences
SUPPORTS and CHALLENGES are human-curated.

## Rejected alternatives
S2 intent or influence labels as graph edges.
