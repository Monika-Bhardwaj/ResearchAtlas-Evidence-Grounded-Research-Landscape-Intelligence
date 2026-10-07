"""Render the human-readable ontology docs FROM ontology.yaml so docs cannot drift from the spec."""
from __future__ import annotations

from typing import List

from src.ontology.enums import EntityType, ProvenanceType, RelationType
from src.ontology.loader import Ontology

_CATEGORY_TITLES = {
    "bibliographic": "Bibliographic",
    "research_structure": "Research structure",
    "evidence": "Evidence",
    "research_direction": "Research direction",
}


def _cell(s: str) -> str:
    return " ".join(str(s).split()).replace("|", "\\|")


def render_ontology_md(onto: Ontology) -> str:
    spec = onto.spec
    out: List[str] = []
    out.append(f"# Ontology v{spec.ontology_version}\n")
    out.append("_Generated from `src/ontology/ontology.yaml` by `scripts/render_docs.py`. Do not edit by hand._\n")
    out.append(f"The vocabulary is **closed**: exactly {len(EntityType)} entity types and {len(RelationType)} relation types "
               "(Sections 6 and 7). The loader fails if the YAML defines any other key.\n")
    out.append("## Entities\n")
    out.append("| Entity | Id prefix | Created from | Definition | Why it exists | Required attributes |")
    out.append("|---|---|---|---|---|---|")
    for e in EntityType:
        s = spec.entities[e.value]
        out.append(f"| {e.value} | `{s.id_prefix}:` | {s.entity_source.value} | {_cell(s.definition)} | {_cell(s.rationale)} | {', '.join(s.required_attributes) or '-'} |")
    out.append("\n### Deferred and excluded entity types\n")
    for n, d in spec.deferred_entities.items():
        out.append(f"- **{n}** (deferred): {_cell(d.reason)}")
    for n, d in spec.excluded_entities.items():
        out.append(f"- **{n}** (excluded): {_cell(d.reason)}")
    out.append("\n### Labels that are NOT relations\n")
    for n, d in spec.non_relations.items():
        out.append(f"- `{n}`: {_cell(d)}")
    out.append("\n## Relations\n")
    out.append("Status: **ACTIVE** relations may be stored; **DERIVED_INVERSE** relations are computed, never stored; "
               "**DEFERRED** relations are defined but not instantiable in v0.1.\n")
    for cat, title in _CATEGORY_TITLES.items():
        out.append(f"### {title}\n")
        out.append("| Relation | Domain → Range | Status | Allowed provenance | Definition |")
        out.append("|---|---|---|---|---|")
        for r in RelationType:
            s = spec.relations[r.value]
            if s.category != cat:
                continue
            prov = ", ".join(p.value for p in s.allowed_provenance) or "none (not stored)"
            out.append(f"| {r.value} | {' / '.join(s.domain)} → {' / '.join(s.range)} | {s.status.value} | {prov} | {_cell(s.definition)} |")
        out.append("")
    out.append("### Per-relation constraints and notes\n")
    for r in RelationType:
        s = spec.relations[r.value]
        notes: List[str] = []
        if s.inverse_of:
            notes.append(f"derived inverse of {s.inverse_of.value}")
        if s.mirror_of:
            notes.append(f"mirror of {s.mirror_of.value}: the same fact must not be stored in both forms")
        if s.symmetric:
            notes.append("symmetric: stored once with source id < target id")
        if s.requires_source_paper:
            notes.append("provenance.source_paper_id is mandatory (the reporting paper must be a corpus Paper)")
        if s.requires_evidence:
            notes.append("an evidence span is mandatory for every provenance type")
        if s.requires_attribution:
            notes.append("attribution (SELF_REPORTED or THIRD_PARTY) is mandatory and cross-checked against PROPOSES edges")
        if s.range_semantics:
            for rng, sem in s.range_semantics.items():
                notes.append(f"range {rng}: {_cell(sem)}")
        if notes:
            out.append(f"**{r.value}**")
            out.extend(f"- {n}" for n in notes)
            out.append("")
    return "\n".join(out).rstrip() + "\n"


def _range(t) -> str:
    lo, hi = t
    return f"{lo:g}" if lo == hi else f"{lo:g}-{hi:g}"


def render_inventory_md(onto: Ontology) -> str:
    spec = onto.spec
    out: List[str] = []
    out.append("# Relation-source inventory (ESTIMATED, M1)\n")
    out.append("_Generated from `src/ontology/ontology.yaml` by `scripts/render_docs.py`. Do not edit by hand._\n")
    out.append("**These are planning estimates made before any corpus or rule exists. They are not quotas.** "
               "An edge that cannot be justified is not created, and a relation type may end up sparse or empty. "
               "A measured inventory is produced at Milestone 3 and reported next to these estimates; "
               "CITES counts are measured at Milestone 2.\n")
    out.append("| Relation | Status | Allowed provenance | Primary source | Expected precision | Est. edges | Est. curated edges | Est. min/curated edge |")
    out.append("|---|---|---|---|---|---|---|---|")
    tot_e = [0, 0]
    tot_c = [0, 0]
    hours = [0.0, 0.0]
    for r in RelationType:
        s = spec.relations[r.value]
        e = s.estimate
        prov = ", ".join(p.value for p in s.allowed_provenance) or "-"
        out.append(f"| {r.value} | {s.status.value} | {prov} | {s.primary_source} | {s.expected_precision.value} | "
                   f"{_range(e.edges)} | {_range(e.curated_edges)} | {_range(e.curation_minutes_per_edge)} |")
        tot_e = [tot_e[0] + e.edges[0], tot_e[1] + e.edges[1]]
        tot_c = [tot_c[0] + e.curated_edges[0], tot_c[1] + e.curated_edges[1]]
        hours = [hours[0] + e.curated_edges[0] * e.curation_minutes_per_edge[0] / 60.0,
                 hours[1] + e.curated_edges[1] * e.curation_minutes_per_edge[1] / 60.0]
    out.append(f"| **Total (excluding CITES, measured at M2)** | | | | | {_range(tot_e)} | {_range(tot_c)} | |")
    out.append("")
    out.append(f"**Estimated human curation workload:** about {_range(tot_c)} curated edges, roughly "
               f"{hours[0]:.0f}-{hours[1]:.0f} hours at the per-edge times above. This excludes gold-set annotation.\n")
    out.append("## Source classification summary\n")
    for pt in ProvenanceType:
        names = [r.value for r in RelationType if spec.relations[r.value].primary_source == pt.value]
        out.append(f"- **{pt.value}** is the primary source for: {', '.join(names) or '-'}")
    out.append("- **Never stored:** " + ", ".join(r.value for r in RelationType if spec.relations[r.value].primary_source == "NONE"))
    out.append("\n## Failure modes by relation\n")
    for r in RelationType:
        s = spec.relations[r.value]
        if s.failure_modes:
            out.append(f"- **{r.value}**: {'; '.join(s.failure_modes)}")
    out.append("\n## Notes per relation\n")
    for r in RelationType:
        out.append(f"- **{r.value}**: {_cell(spec.relations[r.value].estimate_note)}")
    out.append("\n## Review gates for this inventory\n")
    out.append("1. Every relation is classified as explicit metadata, rule-derived, or human-curated.")
    out.append("2. Estimated curated workload is realistic for one human author. If it is not, scope down L4/T4 rather than weaken provenance.")
    out.append("3. Limitation, SUPPORTS, CHALLENGES, PREREQUISITE_FOR and tension rules are concrete, with stated failure modes. Prefer no edge over an unjustified edge.")
    return "\n".join(out).rstrip() + "\n"
