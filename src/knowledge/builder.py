"""Rule-based M3 knowledge-state builder.

Deterministic and auditable: every semantic edge is phrase-matched against the approved
vocabulary. No LLM and no automatic NER/relation extraction is used.
"""
from __future__ import annotations

import argparse
import json
import re
import subprocess
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

import _bootstrap  # noqa: F401
from _bootstrap import ROOT

import yaml

from src.config import REPO_ROOT
from src.corpus.pool import CandidatePaper, load_candidate_pool
from src.errors import ValidationFailed
from src.knowledge.curation import VocabularyEntry, VocabularyFile, approved_vocabulary, validate_vocabulary
from src.knowledge.io import save_knowledge_state
from src.knowledge.models import (
    AmbiguityRecord,
    Attribution,
    BuildMetadata,
    Edge,
    Entity,
    KnowledgeState,
    Provenance,
)
from src.knowledge.validation import validate_knowledge_state, errors_only
from src.ontology.enums import EntityType, ProvenanceType, RelationType, SourceField
from src.ontology.loader import load_ontology

BUILD_VERSION = "0.1.0"
GRAPH_DIR = REPO_ROOT / "knowledge"
VOCAB_PATH = REPO_ROOT / "data" / "curation" / "vocabulary.yaml"
SELECTED_PATH = REPO_ROOT / "data" / "corpus" / "selected_pool.json"

CONTRIBUTION_WORDS = r"\b(we propose|we introduce|we present|we develop|we study|we investigate|we evaluate|we show|we build)\b"
USE_WORDS = r"\b(we use|we employ|we leverage|we build|we integrate)\b"
RESULT_WORDS = r"\b(evaluate|evaluation|results?|benchmark|dataset|performance|ablation)\b"
COMPARE_WORDS = r"\b(compare|comparison|versus|outperform|beats|against)\b"
LIMITATION_WORDS = r"\b(limitation|limitations|limited|shortcoming|trade-?off)\b"


def _slug(text: str) -> str:
    out = re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")
    if not out or not out[0].isalnum():
        out = "x" + out
    return out


def _paper_entity_id(c: CandidatePaper) -> str:
    return f"paper:{_slug(c.canonical_id)}"


def _entry_id_candidates_by_alias(vocab: VocabularyFile) -> Dict[str, Set[str]]:
    out: Dict[str, Set[str]] = defaultdict(set)
    for e in vocab.entries:
        for a in {e.label, *e.aliases}:
            out[a.lower()].add(e.id)
    return out


def _matches(text: str, alias: str) -> bool:
    if not alias: return False
    pattern = r"(?<![A-Za-z0-9_])" + re.escape(alias.lower()) + r"(?![A-Za-z0-9_])"
    return re.search(pattern, text.lower()) is not None


def _sentences(text: Optional[str]) -> List[str]:
    if not text: return []
    # Keep sentence splitting intentionally simple and deterministic.
    raw = re.split(r"(?<=[.!?])\s+", text.replace("\n", " "))
    return [s.strip() for s in raw if s.strip()]


def _title(c: CandidatePaper) -> str: return c.title or ""


def _abstract(c: CandidatePaper) -> str: return c.abstract or ""


def _selected_by_canonical(selected: List[CandidatePaper]) -> Dict[str, CandidatePaper]:
    return {c.canonical_id: c for c in selected}


def _reference_lookup(selected: List[CandidatePaper]) -> Dict[str, str]:
    """Map source IDs/DOIs/arXiv IDs/S2 IDs to selected canonical paper IDs."""
    by_id: Dict[str, str] = {}
    for c in selected:
        by_id[c.canonical_id.lower()] = c.canonical_id
        for r in c.records:
            for v in {r.source_id, r.s2_paper_id, r.doi, r.arxiv_id}:
                if v:
                    by_id[v.lower()] = c.canonical_id
        if c.doi: by_id[c.doi.lower()] = c.canonical_id
        if c.arxiv_id: by_id[c.arxiv_id.lower()] = c.canonical_id
        if c.s2_paper_id: by_id[c.s2_paper_id.lower()] = c.canonical_id
    return by_id


def _entry_map(vocab: VocabularyFile) -> Dict[str, VocabularyEntry]:
    return {e.id: e for e in vocab.entries}


def _entity_entities(vocab: VocabularyFile) -> List[Entity]:
    entities: List[Entity] = []
    for e in vocab.entries:
        entities.append(Entity(id=e.id, type=e.type, label=e.label, aliases=e.aliases, definition=e.definition, attributes={
            "entity_source": "APPROVED_VOCABULARY",
            "drafted_with_ai": e.drafted_with_ai,
            "approval_status": e.approval.status.value,
        }))
    return entities


def _paper_entities(selected: List[CandidatePaper]) -> List[Entity]:
    entities: List[Entity] = []
    for c in selected:
        metadata_status = "COMPLETE" if c.abstract and c.year and c.title and c.authors else "PARTIAL_METADATA"
        entities.append(Entity(id=_paper_entity_id(c), type=EntityType.PAPER, label=c.title, attributes={
            "title": c.title,
            "year": c.year,
            "authors": c.authors,
            "venue": c.venue,
            "doi": c.doi,
            "arxiv_id": c.arxiv_id,
            "s2_paper_id": c.s2_paper_id,
            "canonical_id": c.canonical_id,
            "sources": c.sources,
            "identity_status": "RESOLVED",
            "metadata_status": metadata_status,
            "seed_queries": c.seed_queries,
        }))
    return entities


def _add_edge(edges: Dict[Tuple[str, RelationType, str], Edge], source: str, relation: RelationType, target: str, provenance: Provenance, confidence: float, edge_counter: List[int]) -> None:
    key = (source, relation, target)
    if key in edges:
        existing = edges[key]
        edges[key] = existing.model_copy(update={"corroborating_provenance": (*existing.corroborating_provenance, provenance)})
        return
    edge_counter[0] += 1
    edges[key] = Edge(edge_id=f"edge_{edge_counter[0]:04d}", source=source, relation=relation, target=target, provenance=provenance, confidence=confidence)


def build_knowledge_state() -> Tuple[KnowledgeState, Dict[str, Any]]:
    selected = [CandidatePaper.from_dict(d) for d in json.loads(SELECTED_PATH.read_text(encoding="utf-8"))]
    vocab = VocabularyFile.model_validate(yaml.safe_load(VOCAB_PATH.read_text(encoding="utf-8")))
    approved = {e.id: e for e in approved_vocabulary(vocab)}
    issues = validate_vocabulary(vocab, load_ontology())
    vocab_errors = [i for i in issues if i.severity.value == "ERROR"]
    if vocab_errors:
        raise RuntimeError("vocabulary validation failed: " + "; ".join(i.message for i in vocab_errors))
    entries = list(approved.values())
    entries_by_id = {e.id: e for e in entries}
    selected_lookup = _selected_by_canonical(selected)
    ref_lookup = _reference_lookup(selected)
    ambiguous_alias_owners = _entry_id_candidates_by_alias(vocab)

    entities: List[Entity] = []
    entities.extend(_paper_entities(selected))
    entities.extend(_entity_entities(vocab))
    edges: Dict[Tuple[str, RelationType, str], Edge] = {}
    edge_counter = [0]
    ambiguities = [AmbiguityRecord(input=t.input, candidates=t.candidates) for t in vocab.ambiguous_terms if all(c in approved for c in t.candidates)]

    # explicit citation edges from metadata reference lists, no inference.
    for c in selected:
        for ref in c.references:
            target_cid = None
            for key in [ref.source_paper_id, ref.s2_paper_id, ref.doi, ref.arxiv_id, ref.canonical_id]:
                if key and key.lower() in ref_lookup:
                    target_cid = ref_lookup[key.lower()]
                    break
            if not target_cid or target_cid == c.canonical_id:
                continue
            target = selected_lookup.get(target_cid)
            if target is None:
                continue
            _add_edge(edges, _paper_entity_id(c), RelationType.CITES, _paper_entity_id(target), Provenance(
                type=ProvenanceType.EXPLICIT_METADATA,
                source_field=SourceField.REFERENCES,
                source_paper_id=_paper_entity_id(c),
                evidence=ref.title or ref.canonical_id or json.dumps(ref.__dict__, ensure_ascii=False),
                ontology_version="0.1.0",
                knowledge_build_version=BUILD_VERSION,
            ), 0.95, edge_counter)

    for c in selected:
        text = (_title(c) + " | " + (_abstract(c) or "")).lower()
        sentences = _sentences(_abstract(c))
        for entry in entries:
            entry_aliases = [entry.label, *entry.aliases]
            if entry.type in (EntityType.RESEARCH_PROBLEM, EntityType.CONCEPT):
                matched = False
                for alias in entry_aliases:
                    if matched and alias.lower() == entry.label.lower(): continue
                    owners = approved_alias_owners(entry.label.lower(), approved, vocab)
                    if owners and len(owners) > 1:
                        continue
                    if _matches(_title(c), alias) or any(_matches(s, alias) and re.search(CONTRIBUTION_WORDS, s, re.I) for s in sentences):
                        _add_edge(edges, _paper_entity_id(c), RelationType.ADDRESSES, entry.id, Provenance(
                            type=ProvenanceType.RULE_DERIVED,
                            rule_id="addresses.exact_alias.v1",
                            source_field=SourceField.TITLE if _matches(_title(c), alias) else SourceField.ABSTRACT,
                            mapping_decision=("alias in title" if _matches(_title(c), alias) else "alias in contribution sentence"),
                            evidence=_title(c) if _matches(_title(c), alias) else _extract_matching_sentence(sentences, alias),
                            source_paper_id=_paper_entity_id(c),
                            ontology_version="0.1.0",
                            knowledge_build_version=BUILD_VERSION,
                        ), 0.75, edge_counter)
                        matched = True
                        break
                continue

        # PROPOSES / USES / EVALUATES / COMPARES
        proposed_methods: Set[str] = set()
        for entry in entries:
            if entry.type == EntityType.METHOD:
                for alias in [entry.label, *entry.aliases]:
                    title_hit = _matches(_title(c), alias)
                    abstract_hit = any(_matches(s, alias) and re.search(CONTRIBUTION_WORDS, s, re.I) for s in sentences)
                    if title_hit or abstract_hit:
                        _add_edge(edges, _paper_entity_id(c), RelationType.PROPOSES, entry.id, Provenance(
                            type=ProvenanceType.RULE_DERIVED,
                            rule_id="proposes.title_or_abstract_pattern.v1",
                            source_field=SourceField.TITLE if title_hit else SourceField.ABSTRACT,
                            mapping_decision="method alias appears in title or proposal language",
                            evidence=_title(c) if title_hit else _extract_matching_sentence(sentences, alias),
                            source_paper_id=_paper_entity_id(c),
                            ontology_version="0.1.0",
                            knowledge_build_version=BUILD_VERSION,
                        ), 0.85, edge_counter)
                        proposed_methods.add(entry.id)
                        break
        for entry in entries:
            if entry.type in (EntityType.METHOD, EntityType.TECHNIQUE):
                for alias in [entry.label, *entry.aliases]:
                    hit = any(_matches(s, alias) and re.search(USE_WORDS, s, re.I) for s in sentences)
                    if hit:
                        _add_edge(edges, _paper_entity_id(c), RelationType.USES, entry.id, Provenance(
                            type=ProvenanceType.RULE_DERIVED,
                            rule_id="uses.alias_in_usage_sentence.v1",
                            source_field=SourceField.ABSTRACT,
                            mapping_decision="method/technique alias appears beside usage language",
                            evidence=_extract_matching_sentence(sentences, alias),
                            source_paper_id=_paper_entity_id(c),
                            ontology_version="0.1.0",
                            knowledge_build_version=BUILD_VERSION,
                        ), 0.70, edge_counter)
                        break
        for entry in entries:
            if entry.type == EntityType.BENCHMARK:
                for alias in [entry.label, *entry.aliases]:
                    title_hit = _matches(_title(c), alias)
                    abstract_hit = any(_matches(s, alias) and re.search(RESULT_WORDS, s, re.I) for s in sentences)
                    if title_hit or abstract_hit:
                        _add_edge(edges, _paper_entity_id(c), RelationType.EVALUATES_ON, entry.id, Provenance(
                            type=ProvenanceType.RULE_DERIVED,
                            rule_id="evaluates_on.exact_alias.v1",
                            source_field=SourceField.TITLE if title_hit else SourceField.ABSTRACT,
                            mapping_decision="benchmark alias appears in title or evaluation language",
                            evidence=_title(c) if title_hit else _extract_matching_sentence(sentences, alias),
                            source_paper_id=_paper_entity_id(c),
                            ontology_version="0.1.0",
                            knowledge_build_version=BUILD_VERSION,
                        ), 0.80, edge_counter)
                        break
        for entry in entries:
            if entry.type == EntityType.METHOD:
                for alias in [entry.label, *entry.aliases]:
                    hit = any(_matches(s, alias) and re.search(COMPARE_WORDS, s, re.I) for s in sentences)
                    if hit:
                        _add_edge(edges, _paper_entity_id(c), RelationType.COMPARES_WITH, entry.id, Provenance(
                            type=ProvenanceType.RULE_DERIVED,
                            rule_id="compares_with.alias_in_comparison_sentence.v1",
                            source_field=SourceField.ABSTRACT,
                            mapping_decision="method alias appears beside comparison language",
                            evidence=_extract_matching_sentence(sentences, alias),
                            source_paper_id=_paper_entity_id(c),
                            ontology_version="0.1.0",
                            knowledge_build_version=BUILD_VERSION,
                        ), 0.65, edge_counter)
                        break
        for limitation in [e for e in entries if e.type == EntityType.LIMITATION]:
            for method in [e for e in entries if e.type == EntityType.METHOD]:
                hit_sentence: Optional[str] = None
                for s in sentences:
                    if re.search(LIMITATION_WORDS, s, re.I) and _matches(s, limitation.label) and (_matches(s, method.label) or any(_matches(s, a) for a in method.aliases)):
                        hit_sentence = s
                        break
                if hit_sentence:
                    self_reported = method.id in proposed_methods
                    _add_edge(edges, method.id, RelationType.REPORTS_LIMITATION, limitation.id, Provenance(
                        type=ProvenanceType.RULE_DERIVED,
                        rule_id="reports_limitation.method_and_limitation_in_sentence.v1",
                        source_field=SourceField.ABSTRACT,
                        mapping_decision="method and limitation aliases appear with limitation language",
                        evidence=hit_sentence,
                        source_paper_id=_paper_entity_id(c),
                        attribution=Attribution.SELF_REPORTED if self_reported else Attribution.THIRD_PARTY,
                        ontology_version="0.1.0",
                        knowledge_build_version=BUILD_VERSION,
                    ), 0.60, edge_counter)

    state = KnowledgeState(
        schema_version="0.1.0",
        ontology_version="0.1.0",
        corpus_version=_config_version(),
        knowledge_build_version=BUILD_VERSION,
        build_metadata=BuildMetadata(generator="ResearchMap build_knowledge_state.py", git_sha=_git_sha(), config_hash=_corpus_config_hash(), notes="M3 rule-based human-ontology build"),
        integrity=__import__("src.knowledge.models", fromlist=["Integrity"]).Integrity(content_sha256="0"*64),
        entities=tuple(entities),
        relationships=tuple(edges.values()),
        ambiguities=tuple(ambiguities),
    )
    from src.knowledge.io import with_integrity
    state = with_integrity(state)
    return state, {"paper_count": len(selected), "entity_count": len(entities), "edge_count": len(edges), "ambiguous": len(ambiguities)}


def _extract_matching_sentence(sentences: List[str], alias: str) -> str:
    for s in sentences:
        if _matches(s, alias):
            return s
    return ""


def approved_alias_owners(alias: str, approved: Dict[str, VocabularyEntry], vocab: VocabularyFile) -> Set[str]:
    out: Set[str] = set()
    for e in vocab.entries:
        if e.approval.status.value != "APPROVED": continue
        if alias == e.label.lower() or alias in {a.lower() for a in e.aliases}:
            out.add(e.id)
    return out


def _config_version() -> str:
    root = yaml.safe_load((REPO_ROOT / "config" / "corpus.yaml").read_text(encoding="utf-8"))
    return str(root.get("corpus", {}).get("version", "0.1.0"))


def _corpus_config_hash() -> str:
    import hashlib
    return hashlib.sha256((REPO_ROOT / "config" / "corpus.yaml").read_bytes()).hexdigest()


def _git_sha() -> Optional[str]:
    try:
        return subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, text=True).strip()
    except Exception:
        return None


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--out", default=str(REPO_ROOT / "knowledge" / "knowledge_state.json"))
    ap.add_argument("--report", default=str(REPO_ROOT / "docs" / "m3_knowledge_build_report.json"))
    args = ap.parse_args()
    state, report = build_knowledge_state()
    errs = errors_only(validate_knowledge_state(state, load_ontology()))
    report["validation_errors"] = len(errs)
    report["relation_distribution"] = {}
    for e in state.relationships:
        report["relation_distribution"][e.relation.value] = report["relation_distribution"].get(e.relation.value, 0) + 1
    report_path = Path(args.report)
    if not report_path.is_absolute():
        report_path = REPO_ROOT / report_path
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    if errs:
        for e in errs[:20]:
            print(e, file=__import__("sys").stderr)
        print(f"Knowledge build failed validation with {len(errs)} errors.", file=__import__("sys").stderr)
        return 1
    out_path = Path(args.out)
    if not out_path.is_absolute():
        out_path = REPO_ROOT / out_path
    saved = save_knowledge_state(state, out_path)
    manifest = {
        "schema_version": saved.schema_version,
        "ontology_version": saved.ontology_version,
        "corpus_version": saved.corpus_version,
        "knowledge_build_version": saved.knowledge_build_version,
        "integrity": saved.integrity.content_sha256,
        "entity_count": len(saved.entities),
        "relationship_count": len(saved.relationships),
        "build_report": str(report_path.relative_to(REPO_ROOT)),
    }
    (REPO_ROOT / "knowledge" / "manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"Knowledge state written: {args.out} entities={len(saved.entities)} edges={len(saved.relationships)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
