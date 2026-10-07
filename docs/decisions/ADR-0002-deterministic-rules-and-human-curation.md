# ADR-0002: Deterministic rules and human curation, not LLM extraction

**Status:** Accepted for Milestone 1 review.

## Decision
Edges come only from explicit metadata, registered approved rules, or the human-authored curation file.

## Alternatives considered
LLM triplet extraction; spaCy/REBEL/OpenIE pipelines.

## Rationale
Section 5 prohibits automatic entity/relation extraction. Rule-derived edges are auditable by rule_id and evidence span.

## Consequences
Recall is low and curation effort is real. Sparse relation types are acceptable.

## Rejected alternatives
Any step of the form paper text, then model, then relations, then graph, is prohibited even with a human approval step after it (Patch 11).
