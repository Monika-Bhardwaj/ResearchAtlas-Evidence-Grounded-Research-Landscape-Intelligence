"""OpenAlex Works API client used for citation metadata when S2 is unavailable."""
from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import requests

from src.ingestion.cache import write_raw_json, cache_metadata
from src.ingestion.models import CitationContextRecord, PaperRecord, ReferenceRecord

BASE_URL = "https://api.openalex.org"
SELECT_FIELDS = "id,doi,title,display_name,publication_year,publication_date,authorships,primary_location,abstract_inverted_index,cited_by_count,referenced_works,ids"


class OpenAlexError(RuntimeError): pass


def _cache_name(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", text)[:180].strip("_").lower() or "query"


def _reconstruct_abstract(inv: Optional[Dict[str, List[int]]]) -> Optional[str]:
    if not inv: return None
    positions: Dict[int, str] = {}
    for word, idxs in inv.items():
        for idx in idxs:
            positions[idx] = word
    return " ".join(positions[i] for i in sorted(positions))


def _paper_from_work(work: Dict[str, Any], seed_query: Optional[str] = None, raw_path: Optional[str] = None, raw_sha256: Optional[str] = None) -> PaperRecord:
    title = work.get("display_name") or work.get("title") or ""
    authors = []
    for authorship in work.get("authorships", []) or []:
        author = authorship.get("author") or {}
        if author.get("display_name"): authors.append(author["display_name"])
    primary = work.get("primary_location") or {}
    source = primary.get("source") or {}
    ids = work.get("ids") or {}
    doi = work.get("doi") or ids.get("doi")
    arxiv = None
    if doi and "10.48550/arxiv" in doi.lower():
        m = re.search(r"10\.48550/arxiv\.?(.+)$", doi, re.I)
        if m: arxiv = f"{m.group(1)}"
    return PaperRecord(
        source="openalex",
        source_id=(work.get("id") or "").replace("https://openalex.org/", ""),
        title=title,
        abstract=_reconstruct_abstract(work.get("abstract_inverted_index")),
        authors=authors,
        year=work.get("publication_year"),
        publication_date=work.get("publication_date"),
        venue=source.get("display_name"),
        doi=doi,
        arxiv_id=arxiv,
        url=work.get("id"),
        citation_count=work.get("cited_by_count"),
        reference_count=len(work.get("referenced_works") or []),
        references=[ReferenceRecord(source_paper_id=r.replace("https://openalex.org/", ""), canonical_id=f"openalex:{r.replace('https://openalex.org/', '')}") for r in work.get("referenced_works", []) or []],
        seed_queries=[seed_query] if seed_query else [],
        raw_path=raw_path,
        raw_sha256=raw_sha256,
        source_payload=work,
    )


def fetch_work_records(work_id: str, api_mailto: Optional[str] = None) -> Tuple[Optional[PaperRecord], Optional[Path]]:
    mailto = api_mailto or "moneca@example.com"
    clean = work_id.replace("https://openalex.org/", "").replace("openalex:", "")
    try:
        resp = requests.get(f"{BASE_URL}/works/{clean}", params={"mailto": mailto, "select": SELECT_FIELDS}, timeout=30, headers={"User-Agent": f"ResearchMap/0.1 ({mailto})"})
        if resp.status_code >= 400:
            return None, None
        payload = resp.json()
        path = write_raw_json("openalex", "work", payload, _cache_name(clean))
        meta = cache_metadata(path)
        return _paper_from_work(payload, seed_query=f"reference_expansion:{clean}", **meta), path
    except Exception:
        return None, None


def search_papers(query: str, limit: int = 100, api_mailto: Optional[str] = None, cache_name: Optional[str] = None) -> Tuple[List[PaperRecord], Path]:
    cache_name = cache_name or _cache_name(query)
    params: Dict[str, Any] = {"search": query, "per-page": min(limit, 200), "select": SELECT_FIELDS}
    mailto = api_mailto or "moneca@example.com"
    params["mailto"] = mailto
    last_error: Optional[Exception] = None
    for attempt in range(5):
        try:
            resp = requests.get(f"{BASE_URL}/works", params=params, timeout=30, headers={"User-Agent": f"ResearchMap/0.1 ({mailto})"})
            if resp.status_code >= 500 or resp.status_code == 429:
                last_error = OpenAlexError(f"HTTP {resp.status_code}")
                time.sleep(2 ** attempt)
                continue
            if resp.status_code >= 400:
                raise OpenAlexError(f"HTTP {resp.status_code}: {resp.text[:500]}")
            payload = resp.json()
            path = write_raw_json("openalex", "works_search", payload, cache_name)
            meta = cache_metadata(path)
            rows = [_paper_from_work(w, seed_query=query, **meta) for w in payload.get("results", [])]
            return rows, path
        except Exception as exc:
            last_error = exc
            time.sleep(2 ** attempt)
    raise OpenAlexError(str(last_error))
