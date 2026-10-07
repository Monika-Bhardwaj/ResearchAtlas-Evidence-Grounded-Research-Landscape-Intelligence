"""Filesystem cache for raw acquisition responses."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Union

from src.config import REPO_ROOT


CACHE_ROOT = REPO_ROOT / "data" / "cache"
RAW_ROOT = REPO_ROOT / "data" / "raw"


def _sha256(payload: Union[bytes, str]) -> str:
    data = payload.encode("utf-8") if isinstance(payload, str) else payload
    return hashlib.sha256(data).hexdigest()


def write_raw_json(source: str, endpoint: str, payload: Any, name: str) -> Path:
    path = RAW_ROOT / source / f"{endpoint}_{name}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True)
    path.write_text(text + "\n", encoding="utf-8")
    return path


def write_raw_bytes(source: str, endpoint: str, payload: bytes, name: str, suffix: str) -> Path:
    path = RAW_ROOT / source / f"{endpoint}_{name}.{suffix}"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return path


def cache_metadata(path: Path) -> dict:
    return {"raw_path": str(path.relative_to(REPO_ROOT)), "raw_sha256": _sha256(path.read_bytes())}


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))
