"""Write JSON Schemas for every contract-bearing model into schemas/. Deterministic output."""
import argparse
import sys

import _bootstrap  # noqa: F401
from _bootstrap import ROOT

from src.schema_export import build_schemas
from src.serialization import canonical_dumps


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--check", action="store_true", help="exit 1 if checked-in schemas are stale")
    args = ap.parse_args()
    out_dir = ROOT / "schemas"
    out_dir.mkdir(exist_ok=True)
    stale = []
    for name, schema in build_schemas().items():
        path = out_dir / f"{name}.schema.json"
        text = canonical_dumps(schema)
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != text:
                stale.append(path.name)
        else:
            path.write_text(text, encoding="utf-8")
            print(f"wrote {path.relative_to(ROOT)}")
    if stale:
        print("stale schemas: " + ", ".join(stale), file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
