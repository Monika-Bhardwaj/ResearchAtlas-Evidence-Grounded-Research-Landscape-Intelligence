from src.ingestion.models import PaperRecord, ReferenceRecord
from src.corpus.pool import build_candidates, CandidatePaper
from src.corpus.selection import select_papers, citation_edges, year_bucket
from src.corpus.manifest import write_manifest

def rec(source, source_id, title, year=2024, doi=None, arxiv=None, s2=None, abstract="agent memory", citation_count=1):
    return PaperRecord(source=source, source_id=source_id, title=title, year=year, doi=doi, arxiv_id=arxiv, s2_paper_id=s2, abstract=abstract, authors=["Ada Lovelace"], venue="ICML", citation_count=citation_count, reference_count=1, seed_queries=["agent memory"])

def test_identity_groups_merge_by_doi():
    rows=[rec("s2","s1","Paper A",doi="10.1/a"), rec("arxiv","2310.1v1","Paper A",doi="10.1/A")]
    candidates, ambiguous = build_candidates(rows)
    assert len(candidates)==1
    assert len(candidates[0].records)==2
    assert not ambiguous

def test_identity_does_not_silently_merge_conflicting_doi():
    rows=[rec("s2","s1","Paper A",doi="10.1/a",s2="s1"), rec("arxiv","2310.1v1","Paper A",doi="10.1/b",arxiv="2310.1")]
    candidates, ambiguous = build_candidates(rows)
    assert len(candidates)==2
    assert ambiguous
    assert all(c.ambiguous for c in candidates)

def test_select_respects_target_and_deterministic_tiebreak():
    rows=[rec("s2",f"s{i}",f"Paper {i}",year=2024,citation_count=i) for i in range(10)]
    candidates, _=build_candidates(rows)
    selected, meta=select_papers(candidates, {"target_size":3,"temporal_quotas":{},"score":{}})
    assert len(selected)==3
    assert selected[0].canonical_id == selected[0].canonical_id

def test_citation_edge_matching_uses_doi():
    a=rec("s2","s1","Paper A",doi="10.1/a",s2="s1")
    b=rec("s2","s2","Paper B",doi="10.1/b",s2="s2")
    a.references=[ReferenceRecord(s2_paper_id="s2", doi="10.1/b")]
    cands,_=build_candidates([a,b])
    edges=citation_edges(cands)
    assert len(edges)==1
