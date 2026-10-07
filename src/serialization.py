"""Deterministic serialization helpers (Section 41)."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


def canonical_json_bytes(obj: Any) -> bytes:
    """Compact, key-sorted, UTF-8 JSON: the byte string that gets hashed."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def canonical_dumps(obj: Any) -> str:
    """Human-readable, key-sorted JSON with a trailing newline (for files)."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, indent=2) + "\n"


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_hex(Path(path).read_bytes())
