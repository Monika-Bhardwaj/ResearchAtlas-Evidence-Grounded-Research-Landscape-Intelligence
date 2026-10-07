"""Render docs/ontology.md and docs/relation_source_inventory.md from ontology.yaml."""
import argparse
import sys

import _bootstrap  # noqa: F401
from _bootstrap import ROOT

from src.docs_render import render_inventory_md, render_ontology_md
from src.ontology.loader import load_ontology


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="exit 1 if the checked-in docs are stale")
    args = ap.parse_args()
    onto = load_ontology()
    targets = {
        ROOT / "docs" / "ontology.md": render_ontology_md(onto),
        ROOT / "docs" / "relation_source_inventory.md": render_inventory_md(onto),
    }
    stale = []
    for path, text in targets.items():
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(path.name)
        else:
            path.write_text(text, encoding="utf-8")
            print(f"wrote {path.relative_to(ROOT)}")
    if stale:
        print("stale docs: " + ", ".join(stale), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
