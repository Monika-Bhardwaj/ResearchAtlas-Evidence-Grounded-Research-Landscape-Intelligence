# ADR-0009: REPORTS_LIMITATION is the Method-to-Limitation relation

**Status:** Accepted for Milestone 1 review.

## Decision
REPORTS_LIMITATION: Method to Limitation, an attributed assertion by a corpus paper. Source paper, evidence span and attribution (SELF_REPORTED or THIRD_PARTY) are mandatory for every provenance type, and attribution is cross-checked against PROPOSES edges. HAS_LIMITATION is a rejected alias.

## Alternatives considered
A separate HAS_LIMITATION relation; Paper-to-Limitation.

## Rationale
Section 23 used HAS_LIMITATION, which is not in Section 7's closed list. A Method cannot itself report anything, so the reporting paper must live in provenance.

## Consequences
Limitations are never stated as facts about a method in outputs; they are reported as 'reported by'.

## Rejected alternatives
A second limitation relation; unattributed limitations.
