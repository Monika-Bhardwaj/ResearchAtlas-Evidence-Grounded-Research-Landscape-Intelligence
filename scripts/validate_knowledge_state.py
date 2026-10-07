"""Validate a knowledge-state file against the ontology. Fails fast; nothing is repaired.

Exit codes: 0 valid, 1 invalid or corrupt, 2 file not found (no build exists yet).
"""
import argparse
import sys
from pathlib import Path

import _bootstrap  # noqa: F401
from _bootstrap import ROOT

from src.errors import KnowledgeStateCorruptError, OntologyError, Severity
from src.knowledge.io import load_knowledge_state
from src.knowledge.validation import validate_knowledge_state
from src.ontology.loader import load_ontology


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("path", nargs="?", default=str(ROOT / "knowledge" / "knowledge_state.json"))
    args = ap.parse_args()
    path = Path(args.path)
    if not path.exists():
        print(f"No knowledge state at {path}. It is built at Milestone 3.", file=sys.stderr)
        return 2
    try:
        onto = load_ontology()
        state = load_knowledge_state(path)
    except (OntologyError, KnowledgeStateCorruptError) as exc:
        print(f"INVALID: {exc}", file=sys.stderr)
        return 1
    issues = validate_knowledge_state(state, onto)
    errors = [i for i in issues if i.severity == Severity.ERROR]
    for i in issues:
        print(i, file=sys.stderr if i.severity == Severity.ERROR else sys.stdout)
    if errors:
        print(f"INVALID: {len(errors)} error(s).", file=sys.stderr)
        return 1
    print(f"OK: {len(state.entities)} entities, {len(state.relationships)} relationships, "
          f"ontology {state.ontology_version}, integrity verified.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
