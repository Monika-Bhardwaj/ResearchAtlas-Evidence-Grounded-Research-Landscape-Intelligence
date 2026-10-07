"""arXiv metadata API client."""
from __future__ import annotations

import re
import time
import xml.etree.ElementTree as ET
from pathlib import Path
from typing import List, Optional, Tuple

import requests

from src.ingestion.cache import write_raw_bytes, cache_metadata
from src.ingestion.models import PaperRecord

ARXIV_API = "http://export.arxiv.org/api/query"
NS = {
    "atom": "http://www.w3.org/2005/Atom",
    "arxiv": "http://arxiv.org/schemas/atom",
    "opensearch": "http://a9.com/-/spec/opensearch/1.1/",
}


class ArxivError(RuntimeError): pass


def _cache_name(text: str) -> str:
    return re.sub(r"[^a-zA-Z0-9_.-]+", "_", text)[:180].strip("_").lower() or "query"


def _arxiv_id_from_url(url: str) -> Optional[str]:
    m = re.search(r"/(?:abs|pdf)/([^?#/]+)", url)
    if not m: return None
    return re.sub(r"v\d+$", "", m.group(1))


def _parse_entry(entry: ET.Element, seed_query: Optional[str] = None, raw_path: Optional[str] = None, raw_sha256: Optional[str] = None) -> PaperRecord:
    def text(tag: str, ns: str = "atom") -> Optional[str]:
        el = entry.find(f"{ns}:{tag}", NS)
        return " ".join(el.text.split()) if el is not None and el.text else None

    url = text("id") or ""
    arxiv_id = _arxiv_id_from_url(url)
    published = text("published")
    year = int(published[:4]) if published and published[:4].isdigit() else None
    authors = []
    for a in entry.findall("atom:author", NS):
        name = a.find("atom:name", NS)
        if name is not None and name.text: authors.append(" ".join(name.text.split()))
    doi_el = entry.find("arxiv:doi", NS)
    doi = doi_el.text.strip() if doi_el is not None and doi_el.text else None
    primary = entry.find("arxiv:primary_category", NS)
    venue = None
    for link in entry.findall("atom:link", NS):
        if link.attrib.get("title") == "journal_ref":
            venue = link.attrib.get("href")
    return PaperRecord(
        source="arxiv",
        source_id=arxiv_id or url,
        title=text("title") or "",
        abstract=text("summary"),
        authors=authors,
        year=year,
        publication_date=published[:10] if published else None,
        venue=venue or (primary.attrib.get("term") if primary is not None else None),
        doi=doi,
        arxiv_id=arxiv_id,
        url=url,
        references=[],
        seed_queries=[seed_query] if seed_query else [],
        raw_path=raw_path,
        raw_sha256=raw_sha256,
        source_payload={"id": url, "title": text("title"), "summary": text("summary")},
    )


def search_papers(query: str, limit: int = 100, cache_name: Optional[str] = None) -> Tuple[List[PaperRecord], Path]:
    cache_name = cache_name or _cache_name(query)
    params = {"search_query": f'all:"{query}"', "start": 0, "max_results": min(limit, 200)}
    last_error: Optional[Exception] = None
    for attempt in range(5):
        try:
            resp = requests.get(ARXIV_API, params=params, timeout=30, headers={"User-Agent": "ResearchAtlas/0.1"})
            if resp.status_code >= 500 or resp.status_code == 429:
                last_error = ArxivError(f"HTTP {resp.status_code}")
                time.sleep(2 ** attempt)
                continue
            if resp.status_code >= 400:
                raise ArxivError(f"HTTP {resp.status_code}: {resp.text[:500]}")
            raw = resp.content
            path = write_raw_bytes("arxiv", "api_query", raw, cache_name, "atom")
            meta = cache_metadata(path)
            root = ET.fromstring(raw)
            rows = [_parse_entry(e, seed_query=query, **meta) for e in root.findall("atom:entry", NS)]
            return rows, path
        except Exception as exc:
            last_error = exc
            time.sleep(2 ** attempt)
    raise ArxivError(str(last_error))
