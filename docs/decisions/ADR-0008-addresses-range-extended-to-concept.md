# ADR-0008: ADDRESSES range extended to Concept

**Status:** Accepted for Milestone 1 review.

## Decision
ADDRESSES: Paper to ResearchProblem or Concept, with per-range semantics. For Concept, the concept must be the focal subject: an approved alias in the title, or the object of a registered contribution pattern in one abstract sentence. ADDRESSES never means mentions.

## Alternatives considered
A new relation type (for example ABOUT); USES for concepts.

## Rationale
Section 7 has no Paper-to-Concept relation but grounding and concept overlap need one. Extending an existing relation keeps the vocabulary closed.

## Consequences
ConceptOverlap is computed over focal concepts only, so recall is lower by design. The loader requires `range_semantics` for any range-extended relation.

## Rejected alternatives
Adding a relation type (closed-vocabulary violation); a generic mention semantics.
