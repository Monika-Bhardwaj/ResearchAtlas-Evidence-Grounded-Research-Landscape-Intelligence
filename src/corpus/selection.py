"""Deterministic corpus selection from normalized candidate papers."""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Set, Tuple

from src.corpus.pool import CandidatePaper, ReferenceRecord


def _canonical_ref(ref: ReferenceRecord) -> Optional[str]:
    return ref.canonical_id or (f"s2:{ref.s2_paper_id}" if ref.s2_paper_id else None) or (f"doi:{ref.doi.lower()}" if ref.doi else None) or (f"arxiv:{ref.arxiv_id}" if ref.arxiv_id else None)


def citation_edges(candidates: List[CandidatePaper]) -> Set[Tuple[str, str]]:
    by_id: Dict[str, str] = {}
    for c in candidates:
        if c.doi: by_id[c.doi.lower()] = c.canonical_id
        if c.arxiv_id: by_id[c.arxiv_id] = c.canonical_id
        if c.s2_paper_id: by_id[c.s2_paper_id.lower()] = c.canonical_id
        for r in c.records:
            by_id[r.source_id.lower()] = c.canonical_id
            if r.s2_paper_id: by_id[r.s2_paper_id.lower()] = c.canonical_id
            if r.doi: by_id[r.doi.lower()] = c.canonical_id
            if r.arxiv_id: by_id[r.arxiv_id] = c.canonical_id
    edges: Set[Tuple[str, str]] = set()
    for c in candidates:
        for ref in c.references:
            target = None
            for key in [ref.source_paper_id, ref.s2_paper_id, ref.doi, ref.arxiv_id]:
                if key and key.lower() in by_id:
                    target = by_id[key.lower()]
                    break
            if target and target != c.canonical_id:
                edges.add((c.canonical_id, target))
    return edges


def score_candidate(c: CandidatePaper, degree: int, config: Dict[str, Any]) -> Tuple[float, Dict[str, float]]:
    weights = config.get("score", {})
    seed_score = weights.get("seed_hit_weight", 10.0) * len(c.seed_queries)
    citation_score = weights.get("citation_count_log_weight", 1.0) * math.log1p(c.citation_count or 0)
    ref_score = weights.get("reference_count_log_weight", 0.5) * math.log1p(c.reference_count or 0)
    degree_score = weights.get("in_pool_citation_weight", 2.0) * degree
    recency_score = weights.get("recency_bonus_2024_plus", 1.0) if (c.year or 0) >= 2024 else 0.0
    total = seed_score + citation_score + ref_score + degree_score + recency_score
    return total, {
        "seed_hits": seed_score,
        "citation_count": citation_score,
        "reference_count": ref_score,
        "in_pool_citation_degree": degree_score,
        "recency": recency_score,
    }


def year_bucket(year: Optional[int]) -> str:
    if year is None: return "unknown"
    if year <= 2021: return "le_2021"
    if 2022 <= year <= 2023: return "y2022_2023"
    return "y2024_plus"


def select_papers(candidates: List[CandidatePaper], config: Dict[str, Any], target_size: Optional[int] = None) -> Tuple[List[CandidatePaper], Dict[str, Any]]:
    target = target_size or config.get("target_size", 70)
    edges = citation_edges(candidates)
    out_degree: Dict[str, int] = {}
    in_degree: Dict[str, int] = {}
    for src, tgt in edges:
        out_degree[src] = out_degree.get(src, 0) + 1
        in_degree[tgt] = in_degree.get(tgt, 0) + 1
    scored = []
    for c in candidates:
        degree = in_degree.get(c.canonical_id, 0) + out_degree.get(c.canonical_id, 0)
        score, parts = score_candidate(c, degree, config)
        scored.append({"candidate": c, "score": score, "parts": parts, "degree": degree, "bucket": year_bucket(c.year)})
    quotas = config.get("temporal_quotas", {})
    selected: List[CandidatePaper] = []
    selected_ids: Set[str] = set()
    # Ensure each bucket meets its minimum quota; candidates with unknown year cannot fill quotas.
    for bucket in ["le_2021", "y2022_2023", "y2024_plus"]:
        quota = quotas.get(bucket, {})
        minimum = int(quota.get("min", 0) or 0)
        pool = sorted([s for s in scored if s["bucket"] == bucket], key=lambda s: (-s["score"], s["candidate"].canonical_id))
        for s in pool[:minimum]:
            if s["candidate"].canonical_id not in selected_ids:
                selected.append(s["candidate"]); selected_ids.add(s["candidate"].canonical_id)
    # Fill remaining slots until target, respecting per-bucket maxima if present.
    pool = sorted(scored, key=lambda s: (-s["score"], s["candidate"].canonical_id))
    bucket_counts = {bucket: sum(1 for c in selected if year_bucket(c.year) == bucket) for bucket in ["le_2021", "y2022_2023", "y2024_plus", "unknown"]}
    for s in pool:
        if len(selected) >= target: break
        c = s["candidate"]
        if c.canonical_id in selected_ids: continue
        bucket = s["bucket"]
        max_q = quotas.get(bucket, {}).get("max")
        if max_q is not None and bucket_counts.get(bucket, 0) >= int(max_q):
            continue
        selected.append(c); selected_ids.add(c.canonical_id); bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
    # If quotas made target impossible, relax to fill to target from unselected best candidates.
    if len(selected) < target:
        for s in pool:
            if len(selected) >= target: break
            c = s["candidate"]
            if c.canonical_id not in selected_ids:
                selected.append(c); selected_ids.add(c.canonical_id)
    selected = sorted(selected, key=lambda c: c.canonical_id)
    return selected, {"edges": [[a, b] for a, b in sorted(edges)], "target_size": target}
