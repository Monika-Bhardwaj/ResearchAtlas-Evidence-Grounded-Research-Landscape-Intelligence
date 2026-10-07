"""Normalized paper records produced by ingestion.

These records are metadata only. They are never used to infer semantic relations
without an explicit M1 provenance type and an explicit rule or human curation.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ReferenceRecord:
    source_paper_id: Optional[str] = None
    canonical_id: Optional[str] = None
    title: Optional[str] = None
    year: Optional[int] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    s2_paper_id: Optional[str] = None


@dataclass
class CitationContextRecord:
    source_paper_id: Optional[str] = None
    canonical_id: Optional[str] = None
    title: Optional[str] = None
    year: Optional[int] = None
    context: Optional[str] = None
    is_influential: Optional[bool] = None


@dataclass
class PaperRecord:
    source: str
    source_id: str
    title: str
    abstract: Optional[str] = None
    authors: List[str] = field(default_factory=list)
    year: Optional[int] = None
    publication_date: Optional[str] = None
    venue: Optional[str] = None
    doi: Optional[str] = None
    arxiv_id: Optional[str] = None
    s2_paper_id: Optional[str] = None
    url: Optional[str] = None
    citation_count: Optional[int] = None
    reference_count: Optional[int] = None
    references: List[ReferenceRecord] = field(default_factory=list)
    citations: List[CitationContextRecord] = field(default_factory=list)
    seed_queries: List[str] = field(default_factory=list)
    raw_path: Optional[str] = None
    raw_sha256: Optional[str] = None
    source_payload: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["references"] = [x.__dict__ for x in self.references]
        d["citations"] = [x.__dict__ for x in self.citations]
        return d

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "PaperRecord":
        refs = [ReferenceRecord(**x) for x in d.get("references", [])]
        cites = [CitationContextRecord(**x) for x in d.get("citations", [])]
        kwargs = {k: v for k, v in d.items() if k not in {"references", "citations"}}
        return cls(**kwargs, references=refs, citations=cites)
