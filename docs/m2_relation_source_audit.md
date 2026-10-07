# M2 relation-source availability and viability audit

## abstract_coverage
```json
{
  "count": 64,
  "of": 70
}
```
## identifier_coverage
```json
{
  "arxiv": 22,
  "doi": 70,
  "s2_paper_id": 0,
  "selected_papers": 70
}
```
## citation_contexts_collected
0
## limitation_marked_abstracts
7
## relation_source_availability
- `CITES`: measured=29, availability=29 normalized in-corpus citation edges; 0 papers have S2 IDs, path=EXPLICIT_METADATA, viability=available_for_M3_validation
- `REPORTS_LIMITATION`: measured=0, availability=7/70 selected paper abstracts contain explicit limitation markers; rule derivation is not attempted at M2, path=RULE_DERIVED + MANUALLY_CURATED, viability=under_supported_do_not_treat_L4_as_supported
- `SUPPORTS/CHALLENGES`: measured=0, availability=0 citation-context strings collected; no claims/support edges are inferred at M2, path=MANUALLY_CURATED, viability=under_supported_manual_curation_required
- `DEPENDS_ON`: measured=0, availability=No raw metadata field carries this relation; it requires human-approved curated edges, path=MANUALLY_CURATED, viability=requires_human_curation_before_L4_T4_viability
- `PREREQUISITE_FOR`: measured=0, availability=No raw metadata field carries this relation; it requires human-approved curated edges, path=MANUALLY_CURATED, viability=requires_human_curation_before_L4_T4_viability
- `MOTIVATES`: measured=0, availability=No raw metadata field carries this relation; it requires human-approved curated edges, path=MANUALLY_CURATED, viability=requires_human_curation_before_L4_T4_viability
- `ALTERNATIVE_TO`: measured=0, availability=No raw metadata field carries this relation; it requires human-approved curated edges, path=MANUALLY_CURATED, viability=requires_human_curation_before_L4_T4_viability
- `GENERALIZES`: measured=0, availability=No raw metadata field carries this relation; it requires human-approved curated edges, path=MANUALLY_CURATED, viability=requires_human_curation_before_L4_T4_viability
- `SPECIALIZES`: measured=0, availability=No raw metadata field carries this relation; it requires human-approved curated edges, path=MANUALLY_CURATED, viability=requires_human_curation_before_L4_T4_viability
- `COMBINES_WITH`: measured=0, availability=No raw metadata field carries this relation; it requires human-approved curated edges, path=MANUALLY_CURATED, viability=requires_human_curation_before_L4_T4_viability
- `BUILDS_ON/EXTENDS/COMPARES_WITH`: measured=0, availability=S2 metadata present on 0/70 papers; citation edges exist but phrase/alias evidence must be audited at M3, path=RULE_DERIVED + MANUALLY_CURATED, viability=rule_derivation_not_attempted_at_M2
## L4_T4_viability_review
```json
{
  "PREREQUISITE_FOR": "requires_human_curation",
  "REPORTS_LIMITATION": "insufficient_at_M2",
  "SUPPORTS_CHALLENGES": "insufficient_at_M2",
  "recommendation": "Do not author gold facets until L4/T4 support is judged against M3 curated evidence. If markers/contexts remain scarce, scope L4/T4 down rather than weakening provenance."
}
```
