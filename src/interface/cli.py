"""CLI for a new research proposal against the frozen knowledge state."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

from src.config import REPO_ROOT
from src.knowledge.curation import VocabularyFile, approved_vocabulary
from src.knowledge.io import load_knowledge_state
from src.knowledge.validation import assert_valid
from src.ontology.loader import load_ontology
from src.output.models import INSUFFICIENT_MESSAGE, RuntimeOutput
from src.reasoning.engine import analyze_proposal, output_to_json


def _read_proposal(args) -> str:
    if args.proposal is not None:
        return args.proposal
    if not sys.stdin.isatty():
        return sys.stdin.read()
    print("Enter research proposal:", file=sys.stderr)
    return sys.stdin.readline().strip()


def _print_human(out: RuntimeOutput, verbose: bool) -> None:
    print("PROPOSAL GROUNDING")
    print("------------------")
    if out.proposal.matched_concepts:
        print("Matched:", ", ".join(out.proposal.matched_concepts))
    else:
        print("Matched: none")
    if out.proposal.ambiguous_concepts:
        print("Ambiguous:", "; ".join(f"{a.input} -> {', '.join(a.candidates)}" for a in out.proposal.ambiguous_concepts))
    if out.proposal.unknown_concepts:
        print("Unknown:", ", ".join(out.proposal.unknown_concepts))

    print("\nCLOSEST PRIOR WORK")
    print("----------------------")
    if not out.prior_work:
        print("No directly supported prior work found in the indexed corpus.")
    for item in out.prior_work:
        print(f"- {item.paper_id}: {item.score:.3f} [{item.confidence.value}]")
        if item.shared_concepts or item.shared_methods:
            print(f"  overlap: {', '.join(item.shared_concepts + item.shared_methods)}")
        if verbose and item.evidence:
            e = item.evidence[0]
            print(f"  evidence: edge={e.edge_id} field={e.source_field} rule={e.rule_id}")

    print("\nRECOMMENDED READING ORDER")
    print("--------------------------")
    for step in out.reading_path:
        print(f"{step.rank}. {step.paper_id}: {step.relationship_to_proposal}")

    print("\nLITERATURE TENSIONS")
    print("-------------------")
    for t in out.tensions:
        if t.status.value == "CONFLICTING":
            print(f"- {t.claim_id}: CONFLICTING; support/challenge evidence present")
        else:
            print(f"- {t.claim_id or 'facet'}: INSUFFICIENT_EVIDENCE")

    print("\nPOSITIONING")
    print("------------")
    for p in out.positioning:
        print(f"- {p.label.value}: confidence_score={p.confidence_score:.3f}; sufficiency={p.evidence_sufficiency.value}; abstain={p.abstain}")

    print("\nLIMITATIONS")
    print("------------")
    if not out.limitations:
        print("No attributed limitation edges found in the indexed corpus.")
    for lim in out.limitations[:10]:
        print(f"- {lim.method_id} -> {lim.limitation_id} (reported_by={lim.reported_by}, attribution={lim.attribution})")

    print("\nUNCERTAINTY / WARNINGS")
    print("-----------------------")
    print(f"Evidence sufficiency: {out.evidence_sufficiency.value}")
    for w in out.warnings:
        print(f"- {w}")
    if out.evidence_sufficiency.value == "INSUFFICIENT":
        print(f"- {INSUFFICIENT_MESSAGE}")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--proposal", default=None)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--knowledge-state", default=str(REPO_ROOT / "knowledge" / "knowledge_state.json"))
    ap.add_argument("--vocabulary", default=str(REPO_ROOT / "data" / "curation" / "vocabulary.yaml"))
    args = ap.parse_args()
    proposal = _read_proposal(args)
    try:
        state = load_knowledge_state(Path(args.knowledge_state))
        assert_valid(state, load_ontology())
        vocab = VocabularyFile.model_validate(yaml.safe_load(Path(args.vocabulary).read_text(encoding="utf-8")))
        out = analyze_proposal(proposal, state, vocab)
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    if args.json:
        print(output_to_json(out))
    else:
        _print_human(out, args.verbose)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
