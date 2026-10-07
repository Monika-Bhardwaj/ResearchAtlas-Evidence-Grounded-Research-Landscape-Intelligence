#!/usr/bin/env python3
"""Build the M2 corpus artifacts: acquisition cache, normalized candidates, selection, stats, manifest."""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

import _bootstrap  # noqa: F401
from _bootstrap import ROOT

import yaml

from src.config import REPO_ROOT
from src.ingestion.models import PaperRecord, ReferenceRecord
from src.ingestion.arxiv import search_papers as arxiv_search
from src.ingestion.semantic_scholar import (
    SemanticScholarError,
    fetch_reference_records,
    search_papers as s2_search,
)
from src.corpus.pool import build_candidates, write_candidate_pool, load_candidate_pool, CandidatePaper, CANDIDATE_POOL
from src.corpus.selection import select_papers, citation_edges
from src.corpus.report import corpus_stats, relation_audit, write_stats_report, write_audit_report
from src.corpus.manifest import write_manifest, MANIFEST

CONFIG_PATH = REPO_ROOT / "config" / "corpus.yaml"
ACQ_MANIFEST = REPO_ROOT / "data" / "corpus_acquisition.json"
RECORDS_DIR = REPO_ROOT / "data" / "cache" / "records"
SELECTED_PATH = REPO_ROOT / "data" / "corpus" / "selected_pool.json"


def load_config() -> Dict[str, Any]:
    payload = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    return payload["corpus"]


def safe(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", text)[:120].strip("_").lower() or "query"


def save_records(provider: str, query: str, rows: List[PaperRecord]) -> Path:
    path = RECORDS_DIR / f"{provider}_{safe(query)}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps([r.to_dict() for r in rows], ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def load_manifest() -> Dict[str, Any]:
    if ACQ_MANIFEST.exists():
        return json.loads(ACQ_MANIFEST.read_text(encoding="utf-8"))
    return {"schema_version": "0.1.0", "queries": {}}


def write_acquisition_manifest(manifest: Dict[str, Any]) -> None:
    ACQ_MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    ACQ_MANIFEST.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def acquire(args: argparse.Namespace) -> int:
    config = load_config()
    queries = args.query or config["seed_queries"]
    limit = args.limit or config["max_candidates_per_query"]
    api_key = os.environ.get(args.api_key_env or "SEMANTIC_SCHOLAR_API_KEY")
    manifest = load_manifest()
    failed = 0
    for query in queries:
        manifest["queries"].setdefault(query, {})
        providers = ["semantic_scholar", "arxiv"] if args.provider == "both" else [args.provider]
        for provider in providers:
            try:
                if provider == "semantic_scholar":
                    if not api_key:
                        if args.require_s2_key:
                            print(f"ERROR: {args.api_key_env} is required for Semantic Scholar acquisition.", file=sys.stderr)
                            return 2
                        print(f"WARN: {args.api_key_env} not set; skipping Semantic Scholar query: {query}", file=sys.stderr)
                        manifest["queries"][query]["semantic_scholar"] = {"status": "missing_api_key", "record_count": 0}
                        continue
                    rows, raw_path = s2_search(query, limit=limit, api_key=api_key)
                    rows_path = save_records("semantic_scholar", query, rows)
                    manifest["queries"][query]["semantic_scholar"] = {
                        "status": "ok", "record_count": len(rows), "raw_path": str(raw_path.relative_to(ROOT)), "records_path": str(rows_path.relative_to(ROOT)),
                    }
                    # Deterministic one-hop reference expansion is bounded by --expand-references-limit.
                    expanded_rows: List[PaperRecord] = []
                    if args.expand_references_limit > 0 and config.get("one_hop_reference_expansion", False):
                        for row in rows[: args.expand_references_limit]:
                            try:
                                targets, _ = fetch_reference_records(row.s2_paper_id or row.source_id, api_key=api_key, limit=50)
                            except Exception as exc:
                                print(f"WARN: reference expansion failed for {row.source_id}: {exc}", file=sys.stderr)
                                continue
                            for target in targets:
                                expanded_rows.append(target)
                                row.references.append(ReferenceRecord(
                                    source_paper_id=target.s2_paper_id or target.source_id,
                                    canonical_id=f"s2:{target.s2_paper_id or target.source_id}",
                                    title=target.title, year=target.year, doi=target.doi, arxiv_id=target.arxiv_id, s2_paper_id=target.s2_paper_id,
                                ))
                        if expanded_rows:
                            rows.extend(expanded_rows)
                            rows_path = save_records("semantic_scholar", query, rows)
                            manifest["queries"][query]["semantic_scholar"]["record_count"] = len(rows)
                            manifest["queries"][query]["semantic_scholar"]["records_path"] = str(rows_path.relative_to(ROOT))
                            manifest["queries"][query]["semantic_scholar"]["expanded_reference_records"] = len(expanded_rows)
                else:
                    rows, raw_path = arxiv_search(query, limit=limit)
                    rows_path = save_records("arxiv", query, rows)
                    manifest["queries"][query]["arxiv"] = {
                        "status": "ok", "record_count": len(rows), "raw_path": str(raw_path.relative_to(ROOT)), "records_path": str(rows_path.relative_to(ROOT)),
                    }
            except Exception as exc:
                failed += 1
                print(f"WARN: {provider} query failed for {query!r}: {exc}", file=sys.stderr)
                manifest["queries"][query][provider] = {"status": "error", "error": str(exc), "record_count": 0}
        write_acquisition_manifest(manifest)
    print(f"Acquisition complete. {failed} provider/query failures.")
    return 0 if failed == 0 else 1


def normalize(args: argparse.Namespace) -> int:
    manifest = load_manifest()
    records: List[PaperRecord] = []
    for query, providers in manifest.get("queries", {}).items():
        for provider, meta in providers.items():
            records_path = meta.get("records_path")
            if not records_path:
                continue
            path = REPO_ROOT / records_path
            if not path.exists():
                raise FileNotFoundError(f"missing records cache {path}")
            rows = [PaperRecord.from_dict(d) for d in json.loads(path.read_text(encoding="utf-8"))]
            for row in rows:
                if query not in row.seed_queries:
                    row.seed_queries.append(query)
            records.extend(rows)
    candidates, ambiguous = build_candidates(records)
    write_candidate_pool(candidates, ambiguous)
    (REPO_ROOT / "data" / "corpus").mkdir(parents=True, exist_ok=True)
    (REPO_ROOT / "data" / "corpus" / "normalization_report.json").write_text(json.dumps({
        "raw_records": len(records),
        "candidate_groups": len(candidates),
        "ambiguous_groups": len(ambiguous),
        "duplicates_removed_by_identity": len(records) - len(candidates),
    }, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Normalized {len(records)} records into {len(candidates)} candidate groups ({len(ambiguous)} ambiguous).")
    return 0


def select(args: argparse.Namespace) -> int:
    if not CANDIDATE_POOL.exists():
        print("No candidate pool. Run normalize first.", file=sys.stderr)
        return 2
    config = load_config()
    candidates = load_candidate_pool()
    selected, selection_meta = select_papers(candidates, config, target_size=args.target_size)
    SELECTED_PATH.parent.mkdir(parents=True, exist_ok=True)
    SELECTED_PATH.write_text(json.dumps([c.to_dict() for c in selected], ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    stats = corpus_stats(candidates, selected)
    stats["selection_edges"] = len(selection_meta["edges"])
    stats_path = REPO_ROOT / "docs" / "m2_corpus_quality_stats.json"
    stats_path.write_text(json.dumps(stats, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_stats_report(stats, REPO_ROOT / "docs" / "m2_corpus_quality_stats.md")
    audit = relation_audit(candidates, selected)
    (REPO_ROOT / "docs" / "m2_relation_source_audit.json").write_text(json.dumps(audit, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    write_audit_report(audit, REPO_ROOT / "docs" / "m2_relation_source_audit.md")
    write_manifest(selected, config)
    print(f"Selected {len(selected)} papers; stats and relation audit written; manifest frozen: {MANIFEST}")
    return 0


def all_pipeline(args: argparse.Namespace) -> int:
    code = acquire(args)
    if code not in (0, 1):
        return code
    normalize(args)
    return select(args)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    sub = ap.add_subparsers(dest="command", required=True)

    def add_common(p: argparse.ArgumentParser) -> None:
        p.add_argument("--query", action="append", help="override a seed query; may repeat")
        p.add_argument("--limit", type=int, default=None)
        p.add_argument("--provider", choices=["semantic_scholar", "arxiv", "both"], default="both")
        p.add_argument("--api-key-env", default="SEMANTIC_SCHOLAR_API_KEY")
        p.add_argument("--require-s2-key", action="store_true")
        p.add_argument("--expand-references-limit", type=int, default=10)
        p.add_argument("--target-size", type=int, default=None)

    add_common(sub.add_parser("acquire"))
    sub.add_parser("normalize")
    sub.add_parser("select").add_argument("--target-size", type=int, default=None)
    add_common(sub.add_parser("all"))
    args = ap.parse_args()
    if args.command == "acquire":
        return acquire(args)
    if args.command == "normalize":
        return normalize(args)
    if args.command == "select":
        return select(args)
    if args.command == "all":
        return all_pipeline(args)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
