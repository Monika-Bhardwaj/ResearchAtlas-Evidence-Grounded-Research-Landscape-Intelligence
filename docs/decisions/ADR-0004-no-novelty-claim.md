# ADR-0004: No novelty claim: UNKNOWN is a class, ABSTAIN is a decision

**Status:** Accepted for Milestone 1 review.

## Decision
Outputs say what the indexed corpus does and does not contain. UNKNOWN is a positioning class; ABSTAIN is a separate system decision; evidence of absence and absence of evidence are kept distinct.

## Alternatives considered
A novelty score; collapsing UNKNOWN and ABSTAIN.

## Rationale
Section 20. Keeping the two separate lets abstention be scored without gaming the primary metric.

## Consequences
Every system emits a forced label even when it abstains. `RuntimeOutput` rejects system-authored text that claims novelty.

## Rejected alternatives
Any wording that converts UNKNOWN into a claim about the world.
