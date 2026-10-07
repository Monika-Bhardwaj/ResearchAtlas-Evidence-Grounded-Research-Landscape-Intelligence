#!/usr/bin/env python3
"""Inspect the serialized knowledge state without depending on runtime code."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import _bootstrap  # noqa: F401
from _bootstrap import ROOT

from src.knowledge.io import load_knowledge_state
from src.knowledge.models import KnowledgeState
from src.ontology.loader import load_ontology


def _find_edges(state: KnowledgeState, relation: str | None = None, src: str | None = None, target: str | None = None):
    for e in state.relationships:
        if relation and e.relation.value != relation:
            continue
        if src and e.source != src and e.target != src:
            continue
        if target and e.source != target and e.target != target:
            continue
        yield e


def _print_entity(state: KnowledgeState, entity_id: str) -> int:
    for e in state.entities:
        if e.id == entity_id:
            print(f"ENTITY {e.id} [{e.type.value}] {e.label}")
            for k, v in e.attributes.items():
                print(f"  {k}: {v}")
            print("  edges:")
            for edge in _find_edges(state, src=entity_id):
                print(f"    {edge.edge_id}: {edge.source} --{edge.relation.value}--> {edge.target}")
            return 0
    print(f"No entity {entity_id}", file=sys.stderr)
    return 1


def _print_relation(state: KnowledgeState, relation: str) -> int:
    edges = list(_find_edges(state, relation=relation))
    print(f"RELATION {relation}: {len(edges)} edges")
    for e in edges[:50]:
        print(f"  {e.source} -> {e.target} (edge={e.edge_id}, confidence={e.confidence})")
    return 0 if edges else 1


def _print_neighbors(state: KnowledgeState, node_id: str) -> int:
    print(f"NEIGHBORS OF {node_id}")
    count = 0
    for e in state.relationships:
        if e.source == node_id:
            print(f"  -> {e.relation.value} -> {e.target}")
            count += 1
        elif e.target == node_id:
            print(f"  <- {e.relation.value} <- {e.source}")
            count += 1
    print(f"count: {count}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--knowledge-state", default=str(ROOT / "knowledge" / "knowledge_state.json"))
    ap.add_argument("--entity")
    ap.add_argument("--paper")
    ap.add_argument("--relation")
    ap.add_argument("--neighbors")
    ap.add_argument("--stats", action="store_true")
    args = ap.parse_args()
    try:
        state = load_knowledge_state(Path(args.knowledge_state))
        # load enough ontology metadata to fail fast if version drift
        _ = load_ontology()
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.stats:
        from collections import Counter
        rel = Counter(e.relation.value for e in state.relationships)
        ent = Counter(e.type.value for e in state.entities)
        print(f"entities: {len(state.entities)}")
        print(f"relationships: {len(state.relationships)}")
        print(f"entity_types: {dict(ent)}")
        print(f"relation_types: {dict(rel)}")
        return 0
    if args.entity:
        return _print_entity(state, args.entity)
    if args.paper:
        return _print_entity(state, args.paper if args.paper.startswith("paper:") else f"paper:{args.paper}")
    if args.relation:
        return _print_relation(state, args.relation)
    if args.neighbors:
        return _print_neighbors(state, args.neighbors)
    # default: stats
    print(f"Loaded {len(state.entities)} entities and {len(state.relationships)} relationships.")
    print("Use --stats, --entity, --paper, --relation, or --neighbors.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
