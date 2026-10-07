#!/usr/bin/env python3
from __future__ import annotations

import sys
from pathlib import Path

import _bootstrap  # noqa: F401
from _bootstrap import ROOT

if __name__ == "__main__":
    argv = list(sys.argv)
    from src.knowledge.builder import main
    raise SystemExit(main())
