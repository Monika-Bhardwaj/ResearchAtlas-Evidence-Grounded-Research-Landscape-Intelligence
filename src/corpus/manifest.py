"""Corpus manifest writer for M2."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List

from src.corpus.pool import CandidatePaper
from src.config import REPO_ROOT

MANIFEST = REPO_ROOT / "data" / "corpus_manifest.json"


def candidate_to_manifest_entry(c: CandidatePaper, selection_reason: str) -> Dict[str, Any]:
    return {
        "canonical_id": c.canonical_id,
        "title": c.title,
        "authors": c.authors,
        "year": c.year,
        "venue": c.venue,
        "doi": c.doi,
        "arxiv_id": c.arxiv_id,
        "s2_paper_id": c.s2_paper_id,
        "url": c.url,
        "sources": c.sources,
        "source_ids": c.source_ids,
        "seed_queries": c.seed_queries,
        "selection_reason": selection_reason,
        "abstract_available": bool(c.abstract),
        "citation_count": c.citation_count,
        "reference_count": c.reference_count,
        "ambiguous": c.ambiguous,
        "ambiguity_notes": c.ambiguity_notes,
    }


def write_manifest(selected: List[CandidatePaper], config: Dict[str, Any], path: Path = MANIFEST) -> Dict[str, Any]:
    entries = []
    for c in selected:
        reasons = ["seed:" + ",".join(c.seed_queries)] if c.seed_queries else ["reference_expansion"]
        entries.append(candidate_to_manifest_entry(c, "; ".join(reasons)))
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "schema_version": "0.1.0",
        "corpus_version": config.get("version", "0.1.0"),
        "topic": config.get("topic"),
        "scope": config.get("scope"),
        "created_utc": datetime.now(timezone.utc).replace(microsecond=0).isoformat(),
        "target_size": config.get("target_size"),
        "selection_config": config,
        "paper_count": len(selected),
        "papers": entries,
    }
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    path.write_text(text, encoding="utf-8")
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    provenance = {"manifest_path": str(path.relative_to(REPO_ROOT)), "sha256": digest, "frozen": True}
    (path.parent / f"{path.stem}.sha256.json").write_text(json.dumps(provenance, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return payload
