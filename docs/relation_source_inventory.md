# Relation-source inventory (ESTIMATED, M1)

_Generated from `src/ontology/ontology.yaml` by `scripts/render_docs.py`. Do not edit by hand._

**These are planning estimates made before any corpus or rule exists. They are not quotas.** An edge that cannot be justified is not created, and a relation type may end up sparse or empty. A measured inventory is produced at Milestone 3 and reported next to these estimates; CITES counts are measured at Milestone 2.

| Relation | Status | Allowed provenance | Primary source | Expected precision | Est. edges | Est. curated edges | Est. min/curated edge |
|---|---|---|---|---|---|---|---|
| CITES | ACTIVE | EXPLICIT_METADATA | EXPLICIT_METADATA | HIGH | 0 | 0 | 0 |
| CITED_BY | DERIVED_INVERSE | - | NONE | NOT_APPLICABLE | 0 | 0 | 0 |
| ADDRESSES | ACTIVE | RULE_DERIVED, MANUALLY_CURATED | RULE_DERIVED | MEDIUM | 40-110 | 0-15 | 2-3 |
| PROPOSES | ACTIVE | RULE_DERIVED, MANUALLY_CURATED | RULE_DERIVED | HIGH | 20-45 | 0-10 | 2-3 |
| USES | ACTIVE | RULE_DERIVED, MANUALLY_CURATED | RULE_DERIVED | MEDIUM | 40-120 | 0-15 | 2-3 |
| DEPENDS_ON | ACTIVE | MANUALLY_CURATED | MANUALLY_CURATED | HIGH | 20-40 | 20-40 | 2-3 |
| EVALUATES_ON | ACTIVE | RULE_DERIVED, MANUALLY_CURATED | RULE_DERIVED | HIGH | 15-50 | 0-8 | 2-3 |
| MEASURES_WITH | DEFERRED | - | NONE | NOT_APPLICABLE | 0 | 0 | 0 |
| BUILDS_ON | ACTIVE | RULE_DERIVED, MANUALLY_CURATED | RULE_DERIVED | MEDIUM | 0-25 | 0-8 | 3-5 |
| EXTENDS | ACTIVE | RULE_DERIVED, MANUALLY_CURATED | RULE_DERIVED | MEDIUM | 0-25 | 0-8 | 3-5 |
| COMPARES_WITH | ACTIVE | RULE_DERIVED, MANUALLY_CURATED | RULE_DERIVED | MEDIUM | 5-30 | 0-8 | 2-3 |
| SUPPORTS | ACTIVE | MANUALLY_CURATED | MANUALLY_CURATED | HIGH | 25-60 | 25-60 | 5-8 |
| CHALLENGES | ACTIVE | MANUALLY_CURATED | MANUALLY_CURATED | HIGH | 5-20 | 5-20 | 5-8 |
| REPORTS_LIMITATION | ACTIVE | RULE_DERIVED, MANUALLY_CURATED | MANUALLY_CURATED | MEDIUM | 10-30 | 8-25 | 5-8 |
| MOTIVATES | ACTIVE | MANUALLY_CURATED | MANUALLY_CURATED | MEDIUM | 10-25 | 10-25 | 2-3 |
| PREREQUISITE_FOR | ACTIVE | MANUALLY_CURATED | MANUALLY_CURATED | MEDIUM | 20-40 | 20-40 | 2-3 |
| ALTERNATIVE_TO | ACTIVE | MANUALLY_CURATED | MANUALLY_CURATED | MEDIUM | 8-20 | 8-20 | 2-3 |
| GENERALIZES | ACTIVE | MANUALLY_CURATED | MANUALLY_CURATED | MEDIUM | 5-15 | 5-15 | 2-3 |
| SPECIALIZES | ACTIVE | MANUALLY_CURATED | MANUALLY_CURATED | MEDIUM | 5-10 | 5-10 | 2-3 |
| COMBINES_WITH | ACTIVE | MANUALLY_CURATED | MANUALLY_CURATED | MEDIUM | 5-15 | 5-15 | 2-3 |
| **Total (excluding CITES, measured at M2)** | | | | | 233-680 | 111-342 | |

**Estimated human curation workload:** about 111-342 curated edges, roughly 6-26 hours at the per-edge times above. This excludes gold-set annotation.

## Source classification summary

- **EXPLICIT_METADATA** is the primary source for: CITES
- **RULE_DERIVED** is the primary source for: ADDRESSES, PROPOSES, USES, EVALUATES_ON, BUILDS_ON, EXTENDS, COMPARES_WITH
- **MANUALLY_CURATED** is the primary source for: DEPENDS_ON, SUPPORTS, CHALLENGES, REPORTS_LIMITATION, MOTIVATES, PREREQUISITE_FOR, ALTERNATIVE_TO, GENERALIZES, SPECIALIZES, COMBINES_WITH
- **Never stored:** CITED_BY, MEASURES_WITH

## Failure modes by relation

- **CITES**: Reference lists incomplete or mis-resolved by the source API; Identity ambiguity between versions of a paper
- **ADDRESSES**: Alias also names a background topic; Contribution pattern matches a related-work sentence; Low recall because abstracts rarely state focus explicitly
- **PROPOSES**: Method name appears in the title of a paper that only evaluates it; Papers that propose a method without a distinctive name
- **USES**: Mention is treated as use; Use in a baseline versus use in the proposed system is not distinguished
- **DEPENDS_ON**: Optional components recorded as hard dependencies
- **EVALUATES_ON**: Benchmark named only in related work
- **BUILDS_ON**: Generic "building on prior work" phrases without a resolvable target
- **EXTENDS**: Confusion with BUILDS_ON; Phrase without a resolvable target
- **COMPARES_WITH**: Comparison language used for related work; not experiments
- **SUPPORTS**: Claim wording drifts from what the paper shows; Single-paper support over-read as consensus
- **CHALLENGES**: Different experimental regimes read as disagreement
- **REPORTS_LIMITATION**: Abstracts rarely state limitations; Limitation phrase not linkable to a specific method; Third-party critique recorded as self-report
- **MOTIVATES**: Directions asserted without corpus support
- **PREREQUISITE_FOR**: Prerequisite cycles; Pedagogical order confused with technical dependency
- **ALTERNATIVE_TO**: Complementary approaches recorded as alternatives
- **GENERALIZES**: Direction inverted
- **SPECIALIZES**: Direction inverted
- **COMBINES_WITH**: Co-occurrence read as combination

## Notes per relation

- **CITES**: Count is determined by the frozen corpus and is measured at M2, not estimated here.
- **CITED_BY**: Not stored.
- **ADDRESSES**: Mostly rule-derived; curation only fills clear rule misses.
- **PROPOSES**: High precision, low recall (title-name matching).
- **USES**: Main precision risk is that a mention is not a use.
- **DEPENDS_ON**: Entity-level, so the curated set stays small.
- **EVALUATES_ON**: Exact benchmark names only.
- **MEASURES_WITH**: Deferred.
- **BUILDS_ON**: Created only when an explicit phrase, a registered alias and a citation all agree. May be sparse or empty.
- **EXTENDS**: Same conditions as BUILDS_ON. May be sparse or empty.
- **COMPARES_WITH**: Phrase plus registered alias; sparse.
- **SUPPORTS**: Curated because abstract-only data cannot support rule-derived claim evidence at useful precision.
- **CHALLENGES**: Expected to be rare. Sparse is preferable to invented edges.
- **REPORTS_LIMITATION**: Rule coverage is expected to be small; most edges will be curated. Sparse is acceptable.
- **MOTIVATES**: Entity-level; the curated set stays small.
- **PREREQUISITE_FOR**: Entity-level. The validator rejects cycles at M3.
- **ALTERNATIVE_TO**: Entity-level.
- **GENERALIZES**: Entity-level. Curate either GENERALIZES or SPECIALIZES for a pair, never both.
- **SPECIALIZES**: Entity-level.
- **COMBINES_WITH**: Entity-level.

## Review gates for this inventory

1. Every relation is classified as explicit metadata, rule-derived, or human-curated.
2. Estimated curated workload is realistic for one human author. If it is not, scope down L4/T4 rather than weaken provenance.
3. Limitation, SUPPORTS, CHALLENGES, PREREQUISITE_FOR and tension rules are concrete, with stated failure modes. Prefer no edge over an unjustified edge.
