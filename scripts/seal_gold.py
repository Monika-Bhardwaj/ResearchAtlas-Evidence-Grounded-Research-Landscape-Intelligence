"""Seal or verify a gold file by SHA-256 (49.9). The hash is committed; the sealed file is not.

  python scripts/seal_gold.py data/evaluation/gold_test.yaml             # write <file>.sha256
  python scripts/seal_gold.py data/evaluation/gold_test.yaml --verify    # check against the seal
"""
import argparse
import sys
from pathlib import Path

import _bootstrap  # noqa: F401

from src.errors import SealMismatchError
from src.evaluation.gold import seal_file, verify_seal


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("path")
    ap.add_argument("--verify", action="store_true")
    args = ap.parse_args()
    path = Path(args.path)
    seal_path = path.with_name(path.name + ".sha256")
    if args.verify:
        expected = seal_path.read_text(encoding="utf-8").split()[0]
        try:
            verify_seal(path, expected)
        except SealMismatchError as exc:
            print(f"SEAL MISMATCH: {exc}", file=sys.stderr)
            return 1
        print("seal verified")
        return 0
    digest = seal_file(path)
    seal_path.write_text(f"{digest}  {path.name}\n", encoding="utf-8")
    print(f"sealed {path.name}: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
