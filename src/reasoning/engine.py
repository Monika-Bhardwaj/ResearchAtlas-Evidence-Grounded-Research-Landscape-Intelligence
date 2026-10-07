"""Deterministic proposal reasoning over the frozen knowledge state (M4)."""
from __future__ import annotations

import json
import math
import re
from collections import defaultdict, deque
from typing import Any, Dict, List, Optional, Set, Tuple

from src.ids import split_id
from src.output.models import (
    AmbiguousTerm,
    EvidenceItem,
    EvidenceSufficiency,
    Facet,
    FacetPositioning,
    LimitationReport,
    PositioningLabel,
    PriorWorkItem,
    ProposalGrounding,
    ReadingPathItem,
    RuntimeOutput,
    Tension,
    TensionStatus,
)
from src.knowledge.models import Edge, Entity, KnowledgeState
from src.knowledge.curation import VocabularyFile
from src.ontology.enums import EntityType, RelationType, SourceField

# Deterministic grounding is exact-alias matching; no semantic guessing.
STOPWORDS = {
    "that", "this", "with", "from", "into", "onto", "using", "use", "want", "build",
    "agent", "agents", "memory", "research", "proposal", "wanting", "should", "would",
    "could", "about", "their", "have", "has", "been", "were", "they", "when", "also",
}


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _matches(text: str, alias: str) -> bool:
    if not alias: return False
    pattern = r"(?<![A-Za-z0-9_])" + re.escape(alias.lower()) + r"(?![A-Za-z0-9_])"
    return re.search(pattern, text.lower()) is not None


def _entity_aliases(vocab: VocabularyFile) -> Dict[str, Set[str]]:
    out: Dict[str, Set[str]] = defaultdict(set)
    for e in vocab.entries:
        for a in {e.label, *e.aliases}:
            out[_normalize(a)].add(e.id)
    return out


def _entry_aliases(e) -> Set[str]:
    return {_normalize(a) for a in {e.label, *e.aliases}}


def _ambiguous_inputs(vocab: VocabularyFile) -> Set[str]:
    return {_normalize(t.input) for t in vocab.ambiguous_terms}


def ground_proposal(raw_text: str, vocab: VocabularyFile) -> ProposalGrounding:
    alias_index = _entity_aliases(vocab)
    matched_ids: List[str] = []
    ambiguous: List[AmbiguousTerm] = []
    for entry in vocab.entries:
        if entry.type not in {EntityType.CONCEPT, EntityType.RESEARCH_PROBLEM, EntityType.METHOD, EntityType.TECHNIQUE, EntityType.BENCHMARK}:
            continue
        hit = any(_matches(raw_text, a) for a in {entry.label, *entry.aliases})
        if not hit:
            continue
        alias_name = next((a for a in {entry.label, *entry.aliases} if _matches(raw_text, a)), entry.label)
        owners = alias_index.get(_normalize(alias_name), set())
        if _normalize(alias_name) in _ambiguous_inputs(vocab) and len(owners) > 1:
            ambiguous.append(AmbiguousTerm(input=alias_name, candidates=tuple(sorted(owners))))
        else:
            matched_ids.append(entry.id)
    # De-duplicate while preserving deterministic order.
    matched_ids = sorted(set(matched_ids))
    seen_ambiguous: Set[Tuple[str, Tuple[str, ...]]] = set()
    deduped: List[AmbiguousTerm] = []
    for a in ambiguous:
        key = (a.input.lower(), tuple(a.candidates))
        if key not in seen_ambiguous:
            seen_ambiguous.add(key)
            deduped.append(a)
    ambiguous = deduped
    # Candidate unknown terms: meaningful non-alias words, lexical and deterministic.
    words = re.findall(r"[A-Za-z][A-Za-z0-9-]{4,}", raw_text)
    ambiguous_entry_texts = {_normalize(a) for call in ambiguous for e in vocab.entries if e.id in call.candidates for a in {e.label, *e.aliases}}
    matched_entry_texts = {_normalize(a) for mid in matched_ids for e in vocab.entries if e.id == mid for a in {e.label, *e.aliases}} | ambiguous_entry_texts
    unknown = sorted({w for w in words if w.lower() not in STOPWORDS and w.lower() not in {piece for phrase in matched_entry_texts for piece in phrase.split()}})[:5]
    if not unknown and not matched_ids:
        unknown = [raw_text.strip()[:64] or "empty_input"]
    facet = Facet(
        facet_id="facet_001",
        facet_text=raw_text.strip()[:512] or "empty_input",
        grounded_concepts=tuple(matched_ids),
        ambiguous_terms=tuple(ambiguous),
        unknown_terms=tuple(unknown),
    )
    return ProposalGrounding(
        raw_text=raw_text,
        facets=(facet,),
        matched_concepts=tuple(matched_ids),
        ambiguous_concepts=tuple(ambiguous),
        unknown_concepts=tuple(unknown),
    )


def graph_index(state: KnowledgeState) -> Tuple[Dict[str, Entity], Dict[str, List[Edge]], Dict[str, Set[str]]]:
    by_id = {e.id: e for e in state.entities}
    adjacency: Dict[str, Set[str]] = defaultdict(set)
    outgoing: Dict[str, List[Edge]] = defaultdict(list)
    for e in state.relationships:
        adjacency[e.source].add(e.target)
        adjacency[e.target].add(e.source)
        outgoing[e.source].append(e)
    return by_id, outgoing, adjacency


def _paper_entities(by_id: Dict[str, Entity]) -> List[Entity]:
    return [e for e in by_id.values() if e.type == EntityType.PAPER]


def _edge_incident_papers(edge: Edge, by_id: Dict[str, Entity]) -> Set[str]:
    out = set()
    if by_id[edge.source].type == EntityType.PAPER: out.add(edge.source)
    if by_id[edge.target].type == EntityType.PAPER: out.add(edge.target)
    return out


def _adjacent_targets_for_paper(paper_id: str, edges: List[Edge], by_id: Dict[str, Entity]) -> Set[str]:
    targets = set()
    for e in edges:
        if e.source == paper_id and by_id.get(e.target, Entity(id=e.target, type=EntityType.CONCEPT, label="", attributes={})).type in {EntityType.CONCEPT, EntityType.RESEARCH_PROBLEM, EntityType.METHOD, EntityType.TECHNIQUE, EntityType.BENCHMARK}:
            targets.add(e.target)
        if e.target == paper_id and by_id.get(e.source, Entity(id=e.source, type=EntityType.CONCEPT, label="", attributes={})).type in {EntityType.CONCEPT, EntityType.RESEARCH_PROBLEM, EntityType.METHOD, EntityType.TECHNIQUE, EntityType.BENCHMARK}:
            targets.add(e.source)
    return targets


def _citation_degree(paper_id: str, edges: List[Edge]) -> int:
    count = 0
    for e in edges:
        if e.relation in {RelationType.CITES, RelationType.CITED_BY} and (e.source == paper_id or e.target == paper_id):
            count += 1
    return count


def _temporal_relevance(year: int | None) -> float:
    if year is None: return 0.0
    if year >= 2024: return 1.0
    if year >= 2022: return 0.8
    if year >= 2019: return 0.5
    return 0.2


def _feature_sets(matched_ids: Set[str], by_id: Dict[str, Entity]) -> Dict[EntityType, Set[str]]:
    out: Dict[EntityType, Set[str]] = defaultdict(set)
    for mid in matched_ids:
        e = by_id.get(mid)
        if e:
            out[e.type].add(mid)
    return out


def _proportion(actual: Set[str], universe: Set[str]) -> float:
    if not universe: return 0.0
    return len(actual & universe) / len(universe)


def _shortest_distance(start: str, target: str, adjacency: Dict[str, Set[str]], max_hops: int = 3) -> Optional[int]:
    if start == target: return 0
    seen = {start}; q = deque([(start, 0)])
    while q:
        node, d = q.popleft()
        if d >= max_hops: continue
        for nxt in adjacency.get(node, set()):
            if nxt == target:
                return d + 1
            if nxt not in seen:
                seen.add(nxt); q.append((nxt, d + 1))
    return None


def _evidence_for_paper_entity(paper_id: str, targets: Set[str], edges: List[Edge]) -> List[EvidenceItem]:
    items: List[EvidenceItem] = []
    for e in edges:
        if e.source == paper_id and e.target in targets:
            items.append(EvidenceItem(basis="RULE_DERIVED" if e.provenance.type.value == "RULE_DERIVED" else "DIRECTLY_SUPPORTED", edge_id=e.edge_id, paper_id=paper_id, source_field=e.provenance.source_field.value if e.provenance.source_field else None, rule_id=e.provenance.rule_id, fragment=e.provenance.evidence))
        elif e.target == paper_id and e.source in targets:
            items.append(EvidenceItem(basis="RULE_DERIVED" if e.provenance.type.value == "RULE_DERIVED" else "DIRECTLY_SUPPORTED", edge_id=e.edge_id, paper_id=paper_id, source_field=e.provenance.source_field.value if e.provenance.source_field else None, rule_id=e.provenance.rule_id, fragment=e.provenance.evidence))
    return items


def analyze_proposal(raw_text: str, state: KnowledgeState, vocab: VocabularyFile, request_id: str = "req_001") -> RuntimeOutput:
    by_id, outgoing, adjacency = graph_index(state)
    grounding = ground_proposal(raw_text, vocab)
    matched_ids = set(grounding.matched_concepts)
    facet_ids_by_type = _feature_sets(matched_ids, by_id)
    candidates: Dict[str, Set[str]] = defaultdict(set)
    for e in state.relationships:
        if e.source in {p.id for p in _paper_entities(by_id)} and e.target in matched_ids:
            candidates[e.source].add(e.target)
        if e.target in {p.id for p in _paper_entities(by_id)} and e.source in matched_ids:
            candidates[e.target].add(e.source)

    max_degree = max((_citation_degree(p.id, state.relationships) for p in _paper_entities(by_id)), default=1)
    scored: List[Dict[str, Any]] = []
    for paper_id, direct_targets in candidates.items():
        concept_overlap = _proportion(direct_targets, facet_ids_by_type[EntityType.CONCEPT])
        method_overlap = _proportion(direct_targets, facet_ids_by_type[EntityType.METHOD])
        problem_overlap = _proportion(direct_targets, facet_ids_by_type[EntityType.RESEARCH_PROBLEM])
        benchmark_overlap = _proportion(direct_targets, facet_ids_by_type[EntityType.BENCHMARK])
        distances = []
        for target in matched_ids:
            d = _shortest_distance(target, paper_id, adjacency)
            if d is not None: distances.append(d)
        graph_proximity = max((1 / d for d in distances), default=0.0)
        citation_connectivity = _citation_degree(paper_id, state.relationships) / max_degree if max_degree else 0.0
        paper = by_id[paper_id]
        temporal = _temporal_relevance(paper.attributes.get("year"))
        score = (0.30 * concept_overlap + 0.20 * method_overlap + 0.15 * problem_overlap + 0.10 * benchmark_overlap + 0.10 * graph_proximity + 0.10 * citation_connectivity + 0.05 * temporal)
        evidence = _evidence_for_paper_entity(paper_id, matched_ids, state.relationships)
        scored.append({"paper": paper, "direct_targets": direct_targets, "evidence": evidence, "features": {
            "concept_overlap": concept_overlap, "method_overlap": method_overlap, "problem_overlap": problem_overlap, "benchmark_overlap": benchmark_overlap,
            "graph_proximity": graph_proximity, "citation_connectivity": citation_connectivity, "temporal_relevance": temporal,
        }, "score": score})
    scored.sort(key=lambda x: (-x["score"], x["paper"].id))

    prior_work: List[PriorWorkItem] = []
    for item in scored[:10]:
        paper = item["paper"]
        direct = item["direct_targets"]
        confidence = EvidenceSufficiency.HIGH if item["score"] >= 0.65 and len(item["evidence"]) >= 2 else (EvidenceSufficiency.MEDIUM if item["score"] >= 0.4 else EvidenceSufficiency.LOW)
        prior_work.append(PriorWorkItem(
            paper_id=paper.id,
            score=round(item["score"], 4),
            shared_concepts=tuple(sorted(t for t in direct if by_id[t].type == EntityType.CONCEPT)),
            shared_methods=tuple(sorted(t for t in direct if by_id[t].type == EntityType.METHOD)),
            evidence=tuple(item["evidence"]),
            confidence=confidence,
        ))

    reading_path: List[ReadingPathItem] = []
    for rank, item in enumerate(scored[:7], start=1):
        paper = item["paper"]
        shared = sorted(item["direct_targets"])
        concepts = tuple(sorted(t for t in shared if by_id[t].type in {EntityType.CONCEPT, EntityType.RESEARCH_PROBLEM, EntityType.METHOD, EntityType.TECHNIQUE}))
        reading_path.append(ReadingPathItem(
            rank=rank,
            paper_id=paper.id,
            reason=f"shares {len(shared)} grounded vocabulary entries with proposal",
            concepts_learned=concepts,
            prerequisites=(),
            relationship_to_proposal=f"Useful because it has typed edges to {', '.join(sorted(shared)) or 'no matched concepts'}",
        ))

    # Positioning at facet level.
    direct_candidates = len(scored)
    full_coverage = 0.0
    if matched_ids and scored:
        full_coverage = max(len(item["direct_targets"]) / len(matched_ids) for item in scored)
    top_score = scored[0]["score"] if scored else 0.0
    if not matched_ids:
        label = PositioningLabel.UNKNOWN
        ev = EvidenceSufficiency.INSUFFICIENT
    elif direct_candidates == 0:
        label = PositioningLabel.UNKNOWN
        ev = EvidenceSufficiency.INSUFFICIENT
    elif top_score >= 0.65 and full_coverage >= 0.6:
        label = PositioningLabel.WELL_EXPLORED
        ev = EvidenceSufficiency.HIGH if len(scored) >= 2 else EvidenceSufficiency.MEDIUM
    elif full_coverage < 1.0 and direct_candidates <= 2:
        label = PositioningLabel.UNDERREPRESENTED
        ev = EvidenceSufficiency.LOW if direct_candidates == 1 else EvidenceSufficiency.MEDIUM
    elif top_score >= 0.40:
        label = PositioningLabel.PARTIALLY_EXPLORED
        ev = EvidenceSufficiency.MEDIUM
    else:
        label = PositioningLabel.UNKNOWN
        ev = EvidenceSufficiency.LOW

    all_evidence: List[EvidenceItem] = []
    for item in scored[:5]:
        all_evidence.extend(item["evidence"][:3])
    positions = [FacetPositioning(facet_id=grounding.facets[0].facet_id, facet_text=grounding.facets[0].facet_text, label=label, abstain=(ev == EvidenceSufficiency.INSUFFICIENT), confidence_score=round(top_score, 4), evidence_sufficiency=ev, evidence=tuple(all_evidence[:10]))]

    tensions: List[Tension] = []
    claim_groups: Dict[str, Dict[str, List[Edge]]] = defaultdict(lambda: defaultdict(list))
    for e in state.relationships:
        if e.relation in {RelationType.SUPPORTS, RelationType.CHALLENGES} and by_id.get(e.target, Entity(id=e.target, type=EntityType.CLAIM, label="", attributes={})).type == EntityType.CLAIM:
            claim_groups[e.target][e.relation.value].append(e)
    if claim_groups:
        for claim_id, groups in claim_groups.items():
            sup = groups.get("SUPPORTS", [])
            cha = groups.get("CHALLENGES", [])
            if sup and cha and len({e.provenance.source_paper_id for e in sup+cha if e.provenance.source_paper_id}) >= 2:
                tensions.append(Tension(facet_id=grounding.facets[0].facet_id, claim_id=claim_id, status=TensionStatus.CONFLICTING, supporting_evidence=tuple(EvidenceItem(basis="DIRECTLY_SUPPORTED", paper_id=e.provenance.source_paper_id, source_field=e.provenance.source_field.value if e.provenance.source_field else None, fragment=e.provenance.evidence) for e in sup), challenging_evidence=tuple(EvidenceItem(basis="DIRECTLY_SUPPORTED", paper_id=e.provenance.source_paper_id, source_field=e.provenance.source_field.value if e.provenance.source_field else None, fragment=e.provenance.evidence) for e in cha)))
            else:
                tensions.append(Tension(facet_id=grounding.facets[0].facet_id, claim_id=claim_id, status=TensionStatus.INSUFFICIENT_EVIDENCE, supporting_evidence=(), challenging_evidence=()))
    else:
        tensions.append(Tension(facet_id=grounding.facets[0].facet_id, claim_id=None, status=TensionStatus.INSUFFICIENT_EVIDENCE))

    limitations: List[LimitationReport] = []
    for e in state.relationships:
        if e.relation != RelationType.REPORTS_LIMITATION:
            continue
        limitations.append(LimitationReport(method_id=e.source, limitation_id=e.target, reported_by=e.provenance.source_paper_id or "", attribution=e.provenance.attribution.value if e.provenance.attribution else "", evidence=(EvidenceItem(basis="RULE_DERIVED", paper_id=e.provenance.source_paper_id or "", source_field=e.provenance.source_field.value if e.provenance.source_field else None, fragment=e.provenance.evidence, rule_id=e.provenance.rule_id),)))

    top_ev = ev
    warnings: List[str] = []
    if top_ev == EvidenceSufficiency.INSUFFICIENT:
        warnings.append("Insufficient evidence in the indexed corpus.")
    if not matched_ids:
        warnings.append("No controlled vocabulary term matched; cannot ground the proposal.")
    if grounding.ambiguous_concepts:
        warnings.append(f"Ambiguous matched terms: {', '.join(a.input for a in grounding.ambiguous_concepts)}")

    return RuntimeOutput(
        request_id=request_id,
        proposal=grounding,
        prior_work=tuple(prior_work),
        reading_path=tuple(reading_path),
        positioning=tuple(positions),
        tensions=tuple(tensions),
        limitations=tuple(limitations),
        evidence_sufficiency=top_ev,
        warnings=tuple(warnings),
    )


def output_to_json(out: RuntimeOutput) -> str:
    return out.model_dump_json(indent=2)
