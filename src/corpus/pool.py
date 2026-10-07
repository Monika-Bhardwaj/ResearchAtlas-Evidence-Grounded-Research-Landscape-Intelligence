"""Normalized corpus candidate identity resolution."""
from __future__ import annotations

import re
import unicodedata
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

from src.ingestion.models import PaperRecord, ReferenceRecord, CitationContextRecord

CANDIDATE_POOL = Path("data/corpus/candidate_pool.json")
AMBIGUOUS_IDENTITY = Path("data/corpus/ambiguous_identities.json")


def normalize_doi(value: Optional[str]) -> Optional[str]:
    if not value: return None
    v = value.strip().lower()
    v = re.sub(r"^https?://(dx\.)?doi\.org/", "", v)
    v = re.sub(r"^doi:\s*", "", v)
    v = v.strip().rstrip(".")
    return v or None


def normalize_arxiv(value: Optional[str]) -> Optional[str]:
    if not value: return None
    v = value.strip().lower()
    v = re.sub(r"^https?://arxiv\.org/(abs|pdf)/", "", v)
    v = re.sub(r"^arxiv[:/ ]?", "", v)
    v = v.replace(".pdf", "")
    v = re.sub(r"v\d+$", "", v)
    return v or None


def normalize_s2(value: Optional[str]) -> Optional[str]:
    if not value: return None
    v = value.strip().lower()
    if v.startswith("https://"): v = v.rsplit("/", 1)[-1]
    return v or None


def normalize_title(value: str) -> str:
    if not value: return ""
    v = unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode()
    v = v.lower()
    v = re.sub(r"[^a-z0-9]+", " ", v)
    return " ".join(v.split())


def first_author_key(authors: List[str]) -> str:
    if not authors: return "unknown"
    tokens = re.sub(r"[^a-zA-Z0-9]+", " ", authors[0]).split()
    return tokens[-1].lower() if tokens else "unknown"


def fallback_key(record: PaperRecord) -> str:
    year = record.year or "unknown"
    return f"title:{normalize_title(record.title)}:{year}:{first_author_key(record.authors)}"


def _record_keys(record: PaperRecord) -> List[Tuple[str, str]]:
    out: List[Tuple[str, str]] = []
    for value, typ in [
        (normalize_doi(record.doi), "doi"),
        (normalize_arxiv(record.arxiv_id), "arxiv"),
        (normalize_s2(record.s2_paper_id), "s2"),
    ]:
        if value:
            out.append((typ, value))
    return out


@dataclass
class CandidatePaper:
    canonical_id: str
    records: List[PaperRecord] = field(default_factory=list)
    ambiguous: bool = False
    ambiguity_notes: List[str] = field(default_factory=list)

    @property
    def sources(self) -> List[str]:
        return sorted({r.source for r in self.records})

    @property
    def source_ids(self) -> List[str]:
        return sorted({f"{r.source}:{r.source_id}" for r in self.records})

    @property
    def title(self) -> str:
        return sorted(self.records, key=lambda r: (-_completeness(r), r.source))[0].title

    @property
    def abstract(self) -> Optional[str]:
        return _first_nonempty([r.abstract for r in self.records])

    @property
    def authors(self) -> List[str]:
        for r in sorted(self.records, key=lambda r: (-_completeness(r), r.source)):
            if r.authors:
                return r.authors
        return []

    @property
    def year(self) -> Optional[int]:
        return _first_nonempty([r.year for r in self.records])

    @property
    def publication_date(self) -> Optional[str]:
        return _first_nonempty([r.publication_date for r in self.records])

    @property
    def venue(self) -> Optional[str]:
        return _first_nonempty([r.venue for r in self.records])

    @property
    def doi(self) -> Optional[str]:
        return _first_nonempty([normalize_doi(r.doi) for r in self.records])

    @property
    def arxiv_id(self) -> Optional[str]:
        return _first_nonempty([normalize_arxiv(r.arxiv_id) for r in self.records])

    @property
    def s2_paper_id(self) -> Optional[str]:
        return _first_nonempty([normalize_s2(r.s2_paper_id) for r in self.records])

    @property
    def url(self) -> Optional[str]:
        return _first_nonempty([r.url for r in self.records])

    @property
    def citation_count(self) -> Optional[int]:
        counts = [r.citation_count for r in self.records if r.citation_count is not None]
        return max(counts) if counts else None

    @property
    def reference_count(self) -> Optional[int]:
        counts = [r.reference_count for r in self.records if r.reference_count is not None]
        return max(counts) if counts else None

    @property
    def references(self) -> List[ReferenceRecord]:
        out: List[ReferenceRecord] = []
        seen = set()
        for r in self.records:
            for ref in r.references:
                key = (ref.source_paper_id, ref.canonical_id, ref.doi, ref.arxiv_id, ref.s2_paper_id, ref.title)
                if key not in seen:
                    seen.add(key)
                    out.append(ref)
        return out

    @property
    def citations(self) -> List[CitationContextRecord]:
        out: List[CitationContextRecord] = []
        seen = set()
        for r in self.records:
            for c in r.citations:
                key = (c.source_paper_id, c.canonical_id, c.doi, c.arxiv_id, c.s2_paper_id, c.title, c.context)
                if key not in seen:
                    seen.add(key)
                    out.append(c)
        return out

    @property
    def seed_queries(self) -> List[str]:
        return sorted({q for r in self.records for q in r.seed_queries})

    def to_dict(self) -> Dict[str, Any]:
        return {
            "canonical_id": self.canonical_id,
            "sources": self.sources,
            "source_ids": self.source_ids,
            "title": self.title,
            "abstract": self.abstract,
            "authors": self.authors,
            "year": self.year,
            "publication_date": self.publication_date,
            "venue": self.venue,
            "doi": self.doi,
            "arxiv_id": self.arxiv_id,
            "s2_paper_id": self.s2_paper_id,
            "url": self.url,
            "citation_count": self.citation_count,
            "reference_count": self.reference_count,
            "references": [r.__dict__ for r in self.references],
            "citations": [c.__dict__ for c in self.citations],
            "seed_queries": self.seed_queries,
            "ambiguous": self.ambiguous,
            "ambiguity_notes": self.ambiguity_notes,
            "records": [r.to_dict() for r in self.records],
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "CandidatePaper":
        records = [PaperRecord.from_dict(x) for x in d.get("records", [])]
        return cls(canonical_id=d["canonical_id"], records=records, ambiguous=d.get("ambiguous", False), ambiguity_notes=d.get("ambiguity_notes", []))


def _completeness(r: PaperRecord) -> int:
    return sum(1 for x in [r.abstract, r.year, r.venue, r.doi, r.arxiv_id, r.s2_paper_id, r.citation_count, r.reference_count] if x not in (None, "", []))


def _first_nonempty(values: Iterable[Any]) -> Any:
    for v in values:
        if v not in (None, "", []): return v
    return None


def build_candidates(records: List[PaperRecord]) -> Tuple[List[CandidatePaper], List[Dict[str, Any]]]:
    """Group duplicate source records by canonical IDs without silent merges."""
    parents = list(range(len(records)))

    def find(i: int) -> int:
        while parents[i] != i:
            parents[i] = parents[parents[i]]; i = parents[i]
        return i

    def union(i: int, j: int) -> None:
        ri, rj = find(i), find(j)
        if ri != rj: parents[rj] = ri

    by_key: Dict[Tuple[str, str], List[int]] = {}
    for i, r in enumerate(records):
        for key in _record_keys(r):
            by_key.setdefault(key, []).append(i)
    for inds in by_key.values():
        for i in inds[1:]: union(inds[0], i)

    exact_groups: Dict[int, List[PaperRecord]] = {}
    for i, r in enumerate(records): exact_groups.setdefault(find(i), []).append(r)

    # Second pass: merge fallback groups only when primary IDs agree.
    exact_group_list = list(exact_groups.values())
    fby: Dict[str, List[List[PaperRecord]]] = {}
    for g in exact_group_list:
        fby.setdefault(fallback_key(g[0]), []).append(g)

    merged: List[CandidatePaper] = []
    ambiguous: List[Dict[str, Any]] = []
    for fgroup in fby.values():
        if len(fgroup) == 1:
            g = fgroup[0]
            merged.append(CandidatePaper(canonical_id=_choose_canonical(g[0]), records=g))
            continue
        ids: Dict[str, set] = {"doi": set(), "arxiv": set(), "s2": set()}
        for g in fgroup:
            for r in g:
                ids["doi"].add(normalize_doi(r.doi)); ids["arxiv"].add(normalize_arxiv(r.arxiv_id)); ids["s2"].add(normalize_s2(r.s2_paper_id))
            for k in ids: ids[k].discard(None)
        if any(len(v) > 1 for v in ids.values()):
            ambiguous.append({
                "fallback_key": fallback_key(fgroup[0][0]),
                "groups": [[r.to_dict() for r in g] for g in fgroup],
                "reason": "fallback title/year/first-author matched but DOI/arXiv/S2 IDs differ; not merged",
            })
            for g in fgroup:
                merged.append(CandidatePaper(canonical_id=_choose_canonical(g[0]), records=g, ambiguous=True, ambiguity_notes=["matched fallback but not merged due to contradictory identifiers"]))
        else:
            rows = [r for g in fgroup for r in g]
            merged.append(CandidatePaper(canonical_id=_choose_canonical(rows[0]), records=rows))
    return sorted(merged, key=lambda c: c.canonical_id), ambiguous


def _choose_canonical(r: PaperRecord) -> str:
    doi = normalize_doi(r.doi)
    if doi: return f"doi:{doi}"
    arxiv = normalize_arxiv(r.arxiv_id)
    if arxiv: return f"arxiv:{arxiv}"
    s2 = normalize_s2(r.s2_paper_id)
    if s2: return f"s2:{s2}"
    return fallback_key(r)


def write_candidate_pool(candidates: List[CandidatePaper], ambiguous: List[Dict[str, Any]]) -> None:
    CANDIDATE_POOL.parent.mkdir(parents=True, exist_ok=True)
    CANDIDATE_POOL.write_text(json_dumps([c.to_dict() for c in candidates]) + "\n", encoding="utf-8")
    AMBIGUOUS_IDENTITY.write_text(json_dumps(ambiguous) + "\n", encoding="utf-8")


def load_candidate_pool(path: Path = CANDIDATE_POOL) -> List[CandidatePaper]:
    return [CandidatePaper.from_dict(d) for d in json_loads(path.read_text(encoding="utf-8"))]


import json

def json_dumps(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=False, indent=2, sort_keys=True)

def json_loads(text: str) -> Any:
    return json.loads(text)
