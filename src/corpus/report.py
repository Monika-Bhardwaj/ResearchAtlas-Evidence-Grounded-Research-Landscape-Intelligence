"""Corpus quality statistics and relation-source viability reporting for M2."""
from __future__ import annotations

import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Dict, List, Set, Tuple

from src.corpus.pool import CandidatePaper
from src.corpus.selection import citation_edges, year_bucket
from src.config import REPO_ROOT

LIMITATION_MARKERS = [
    "limitation", "limitations", "limited to", "limited by", "shortcoming", "trade-off",
    "tradeoff", "fails to", "does not scale", "cannot handle", "memory overhead", "catastrophic forgetting",
]


def connected_components(nodes: List[str], edges: Set[Tuple[str, str]]) -> List[Set[str]]:
    adjacency: Dict[str, Set[str]] = {n: set() for n in nodes}
    for a, b in edges:
        if a in adjacency and b in adjacency:
            adjacency[a].add(b); adjacency[b].add(a)
    seen: Set[str] = set()
    comps = []
    for n in nodes:
        if n in seen: continue
        stack = [n]; seen.add(n); comp = set()
        while stack:
            x = stack.pop(); comp.add(x)
            for y in adjacency[x]:
                if y not in seen:
                    seen.add(y); stack.append(y)
        comps.append(comp)
    return comps


def corpus_stats(candidates: List[CandidatePaper], selected: List[CandidatePaper]) -> Dict[str, Any]:
    selected_edges = citation_edges(selected)
    years = Counter([c.year for c in selected if c.year is not None])
    nodes = [c.canonical_id for c in selected]
    comps = connected_components(nodes, selected_edges)
    degrees: Dict[str, int] = defaultdict(int)
    for a, b in selected_edges:
        degrees[a] += 1; degrees[b] += 1
    missing = {
        "abstract": sum(1 for c in selected if not c.abstract),
        "year": sum(1 for c in selected if c.year is None),
        "authors": sum(1 for c in selected if not c.authors),
        "venue": sum(1 for c in selected if not c.venue),
        "doi": sum(1 for c in selected if not c.doi),
        "arxiv_id": sum(1 for c in selected if not c.arxiv_id),
        "s2_paper_id": sum(1 for c in selected if not c.s2_paper_id),
    }
    seed_counts = Counter(q for c in selected for q in c.seed_queries)
    all_seed_counts = Counter(q for c in candidates for q in c.seed_queries)
    return {
        "paper_count": len(selected),
        "candidate_count": len(candidates),
        "year_distribution": {str(k): v for k, v in sorted(years.items())},
        "citation_edge_count": len(selected_edges),
        "average_degree": round(sum(degrees.values()) / max(1, len(nodes)), 3),
        "isolated_nodes": sum(1 for n in nodes if degrees.get(n, 0) == 0),
        "connected_components": sorted([len(c) for c in comps], reverse=True),
        "relationship_distribution": {"CITES": len(selected_edges)},
        "missing_metadata": missing,
        "duplicate_rate": None,
        "seed_coverage": {q: {"candidate_count": all_seed_counts[q], "selected_count": seed_counts[q]} for q in sorted(all_seed_counts)},
        "concept_coverage": "NOT_AVAILABLE_AT_M2_CONTROLLED_VOCABULARY_NOT_YET_APPROVED",
    }


def relation_audit(candidates: List[CandidatePaper], selected: List[CandidatePaper]) -> Dict[str, Any]:
    selected_edges = citation_edges(selected)
    contexts = [ctx for c in selected for ctx in c.citations]
    limitation_hits = []
    for c in selected:
        text = (c.abstract or "").lower()
        if any(m in text for m in LIMITATION_MARKERS): limitation_hits.append(c.canonical_id)
    abstract_count = sum(1 for c in selected if c.abstract)
    doi_count = sum(1 for c in selected if c.doi)
    arxiv_count = sum(1 for c in selected if c.arxiv_id)
    s2_count = sum(1 for c in selected if c.s2_paper_id)
    relation_rows = []
    relation_rows.append({
        "relation": "CITES",
        "measured_m2_edges": len(selected_edges),
        "raw_source_availability": f"{len(selected_edges)} normalized in-corpus citation edges; {sum(1 for c in selected if c.s2_paper_id)} papers have S2 IDs",
        "construction_path": "EXPLICIT_METADATA",
        "viability": "available_for_M3_validation" if selected_edges else "sparse_or_missing",
    })
    relation_rows.append({
        "relation": "REPORTS_LIMITATION",
        "measured_m2_edges": 0,
        "raw_source_availability": f"{len(limitation_hits)}/{len(selected)} selected paper abstracts contain explicit limitation markers; rule derivation is not attempted at M2",
        "construction_path": "RULE_DERIVED + MANUALLY_CURATED",
        "viability": "provisionally_supported_for_inventory_audit" if len(limitation_hits) >= 10 else "under_supported_do_not_treat_L4_as_supported",
    })
    relation_rows.append({
        "relation": "SUPPORTS/CHALLENGES",
        "measured_m2_edges": 0,
        "raw_source_availability": f"{len(contexts)} citation-context strings collected; no claims/support edges are inferred at M2",
        "construction_path": "MANUALLY_CURATED",
        "viability": "provisionally_supported_for_context_review" if len(contexts) >= 20 else "under_supported_manual_curation_required",
    })
    for rel in ["DEPENDS_ON", "PREREQUISITE_FOR", "MOTIVATES", "ALTERNATIVE_TO", "GENERALIZES", "SPECIALIZES", "COMBINES_WITH"]:
        relation_rows.append({
            "relation": rel,
            "measured_m2_edges": 0,
            "raw_source_availability": "No raw metadata field carries this relation; it requires human-approved curated edges",
            "construction_path": "MANUALLY_CURATED",
            "viability": "requires_human_curation_before_L4_T4_viability",
        })
    relation_rows.append({
        "relation": "BUILDS_ON/EXTENDS/COMPARES_WITH",
        "measured_m2_edges": 0,
        "raw_source_availability": f"S2 metadata present on {s2_count}/{len(selected)} papers; citation edges exist but phrase/alias evidence must be audited at M3",
        "construction_path": "RULE_DERIVED + MANUALLY_CURATED",
        "viability": "rule_derivation_not_attempted_at_M2",
    })
    return {
        "abstract_coverage": {"count": abstract_count, "of": len(selected)},
        "identifier_coverage": {"doi": doi_count, "arxiv": arxiv_count, "s2_paper_id": s2_count, "selected_papers": len(selected)},
        "citation_contexts_collected": len(contexts),
        "limitation_marked_abstracts": len(limitation_hits),
        "relation_source_availability": relation_rows,
        "L4_T4_viability_review": {
            "REPORTS_LIMITATION": "supported_for_review" if len(limitation_hits) >= 10 else "insufficient_at_M2",
            "SUPPORTS_CHALLENGES": "supported_for_review" if len(contexts) >= 20 else "insufficient_at_M2",
            "PREREQUISITE_FOR": "requires_human_curation",
            "recommendation": "Do not author gold facets until L4/T4 support is judged against M3 curated evidence. If markers/contexts remain scarce, scope L4/T4 down rather than weakening provenance.",
        },
    }


def write_stats_report(stats: Dict[str, Any], path: Path) -> None:
    lines = ["# Corpus quality report (M2, Section 11)", ""]
    for key, value in stats.items():
        if isinstance(value, dict):
            lines.append(f"## {key}")
            lines.append("```json")
            lines.append(json.dumps(value, indent=2, sort_keys=True))
            lines.append("```")
        else:
            lines.append(f"- **{key}:** {value}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def write_audit_report(audit: Dict[str, Any], path: Path) -> None:
    lines = ["# M2 relation-source availability and viability audit", ""]
    for key, value in audit.items():
        lines.append(f"## {key}")
        if isinstance(value, list):
            for row in value:
                lines.append(f"- `{row.get('relation')}`: measured={row.get('measured_m2_edges')}, availability={row.get('raw_source_availability')}, path={row.get('construction_path')}, viability={row.get('viability')}")
        elif isinstance(value, dict):
            lines.append("```json")
            lines.append(json.dumps(value, indent=2, sort_keys=True))
            lines.append("```")
        else:
            lines.append(str(value))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
