"""Semantic Scholar Academic Graph API client.

Raw responses are cached byte-for-byte. Raw citation intents/influence flags are never
used as semantic relations in the knowledge state.
"""
from __future__ import annotations

import os
import random
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from src.ingestion.cache import write_raw_json, cache_metadata
from src.ingestion.models import PaperRecord, ReferenceRecord, CitationContextRecord

BASE_URL = "https://api.semanticscholar.org/graph/v1"
FIELDS = "paperId,externalIds,title,abstract,authors.name,year,publicationDate,venue,url,citationCount,referenceCount"


class SemanticScholarError(RuntimeError):
    pass


def _cache_name(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", text)[:180].strip("_").lower() or "query"


def _request_json(path: str, params: Dict[str, Any], api_key: Optional[str] = None, max_retries: int = 5) -> Dict[str, Any]:
    url = BASE_URL + path
    headers = {"User-Agent": "ResearchMap/0.1"}
    if api_key:
        headers["x-api-key"] = api_key
    for attempt in range(max_retries):
        try:
            resp = requests.get(url, params=params, headers=headers, timeout=30)
            if resp.status_code == 429 or resp.status_code >= 500:
                retry_after = resp.headers.get("Retry-After")
                try:
                    wait = float(retry_after) if retry_after else (2 ** attempt) + random.random()
                except ValueError:
                    wait = (2 ** attempt) + random.random()
                time.sleep(min(wait, 60))
                continue
            if resp.status_code >= 400:
                raise SemanticScholarError(f"HTTP {resp.status_code}: {resp.text[:500]}")
            return resp.json()
        except requests.RequestException as exc:
            if attempt == max_retries - 1:
                raise SemanticScholarError(str(exc)) from exc
            time.sleep(min((2 ** attempt) + random.random(), 60))
    raise SemanticScholarError("max retries exceeded")


def _paper_from_s2(entry: Dict[str, Any], seed_query: Optional[str] = None, raw_path: Optional[str] = None, raw_sha256: Optional[str] = None) -> PaperRecord:
    ext = entry.get("externalIds") or {}
    authors = []
    for a in entry.get("authors") or []:
        if isinstance(a, dict) and a.get("name"):
            authors.append(a["name"])
        elif isinstance(a, str):
            authors.append(a)
    refs = []
    for collection in entry.get("references", []) or []:
        p = collection.get("paperId") if isinstance(collection, dict) else collection
        if p:
            refs.append(ReferenceRecord(source_paper_id=p))
    citations = []
    for collection in entry.get("citations", []) or []:
        if isinstance(collection, dict):
            citations.append(CitationContextRecord(source_paper_id=collection.get("paperId"), context=collection.get("citationContexts")))
    return PaperRecord(
        source="semantic_scholar",
        source_id=entry.get("paperId") or "",
        title=entry.get("title") or "",
        abstract=entry.get("abstract"),
        authors=authors,
        year=entry.get("year"),
        publication_date=entry.get("publicationDate"),
        venue=entry.get("venue"),
        doi=ext.get("DOI"),
        arxiv_id=ext.get("ArXiv"),
        s2_paper_id=entry.get("paperId"),
        url=entry.get("url"),
        citation_count=entry.get("citationCount"),
        reference_count=entry.get("referenceCount"),
        references=refs,
        citations=citations,
        seed_queries=[seed_query] if seed_query else [],
        raw_path=raw_path,
        raw_sha256=raw_sha256,
        source_payload=entry,
    )


def search_papers(query: str, limit: int = 100, api_key: Optional[str] = None, cache_name: Optional[str] = None) -> Tuple[List[PaperRecord], Path]:
    cache_name = cache_name or _cache_name(query)
    params = {"query": query, "limit": min(limit, 100), "fields": FIELDS}
    payload = _request_json("/paper/search", params, api_key=api_key)
    path = write_raw_json("semantic_scholar", "paper_search", payload, cache_name)
    meta = cache_metadata(path)
    rows = []
    for entry in payload.get("data", []):
        rows.append(_paper_from_s2(entry, seed_query=query, **meta))
    return rows, path


def fetch_reference_records(s2_paper_id: str, api_key: Optional[str] = None, limit: int = 1000) -> Tuple[List[PaperRecord], Path]:
    params = {"limit": min(limit, 1000), "fields": FIELDS.replace(",referenceCount", "")}
    payload = _request_json(f"/paper/{s2_paper_id}/references", params, api_key=api_key)
    path = write_raw_json("semantic_scholar", "references", payload, _cache_name(s2_paper_id))
    out: List[PaperRecord] = []
    meta = cache_metadata(path)
    for item in payload.get("data", []):
        p = item.get("citedPaper") or item
        if p.get("paperId"):
            out.append(_paper_from_s2(p, seed_query=f"reference_expansion:{s2_paper_id}", raw_path=meta["raw_path"], raw_sha256=meta["raw_sha256"]))
    return out, path


def fetch_references(s2_paper_id: str, api_key: Optional[str] = None, limit: int = 1000) -> List[ReferenceRecord]:
    params = {"limit": min(limit, 1000), "fields": FIELDS.replace(",referenceCount", "")}
    try:
        payload = _request_json(f"/paper/{s2_paper_id}/references", params, api_key=api_key)
    except SemanticScholarError:
        return []
    path = write_raw_json("semantic_scholar", "references", payload, _cache_name(s2_paper_id))
    out: List[ReferenceRecord] = []
    for item in payload.get("data", []):
        p = item.get("citedPaper") or item
        ext = p.get("externalIds") or {}
        out.append(ReferenceRecord(
            source_paper_id=p.get("paperId"),
            canonical_id=f"s2:{p.get('paperId')}" if p.get("paperId") else None,
            title=p.get("title"),
            year=p.get("year"),
            doi=ext.get("DOI"),
            arxiv_id=ext.get("ArXiv"),
            s2_paper_id=p.get("paperId"),
        ))
    return out


def fetch_citations(s2_paper_id: str, api_key: Optional[str] = None, limit: int = 1000) -> List[CitationContextRecord]:
    params = {"limit": min(limit, 1000), "fields": FIELDS.replace(",referenceCount", "") + ",citationContexts,isInfluential"}
    try:
        payload = _request_json(f"/paper/{s2_paper_id}/citations", params, api_key=api_key)
    except SemanticScholarError:
        return []
    path = write_raw_json("semantic_scholar", "citations", payload, _cache_name(s2_paper_id))
    out: List[CitationContextRecord] = []
    for item in payload.get("data", []):
        p = item.get("citingPaper") or item
        ext = p.get("externalIds") or {}
        contexts = item.get("citationContexts") or item.get("contexts") or []
        if isinstance(contexts, str):
            contexts = [contexts]
        for c in contexts:
            out.append(CitationContextRecord(source_paper_id=p.get("paperId"), title=p.get("title"), year=p.get("year"), context=c, is_influential=item.get("isInfluential")))
        if not contexts:
            out.append(CitationContextRecord(source_paper_id=p.get("paperId"), title=p.get("title"), year=p.get("year"), is_influential=item.get("isInfluential")))
    return out
