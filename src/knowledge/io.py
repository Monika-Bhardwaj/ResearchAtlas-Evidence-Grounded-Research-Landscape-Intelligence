"""Knowledge-state serialization, integrity hash, and fail-fast loading (Sections 16, 27, 41)."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict

from pydantic import ValidationError

from src.errors import KnowledgeStateCorruptError
from src.knowledge.models import Integrity, KnowledgeState
from src.serialization import canonical_dumps, canonical_json_bytes, sha256_hex

_HASHED_KEYS = (
    "schema_version", "ontology_version", "corpus_version", "knowledge_build_version",
    "entities", "relationships", "ambiguities",
)


def _content_payload(state: KnowledgeState) -> Dict[str, Any]:
    d = state.model_dump(mode="json")
    payload = {k: d[k] for k in _HASHED_KEYS}
    payload["entities"] = sorted(payload["entities"], key=lambda e: e["id"])
    payload["relationships"] = sorted(payload["relationships"], key=lambda e: e["edge_id"])
    payload["ambiguities"] = sorted(payload["ambiguities"], key=lambda a: a["input"])
    return payload


def compute_content_hash(state: KnowledgeState) -> str:
    """Hash of the semantic content only. Build metadata is excluded so rebuilds can match."""
    return sha256_hex(canonical_json_bytes(_content_payload(state)))


def with_integrity(state: KnowledgeState) -> KnowledgeState:
    return state.model_copy(update={"integrity": Integrity(content_sha256=compute_content_hash(state))})


def to_canonical_dict(state: KnowledgeState) -> Dict[str, Any]:
    d = state.model_dump(mode="json")
    d["entities"] = sorted(d["entities"], key=lambda e: e["id"])
    d["relationships"] = sorted(d["relationships"], key=lambda e: e["edge_id"])
    d["ambiguities"] = sorted(d["ambiguities"], key=lambda a: a["input"])
    return d


def canonicalize(state: KnowledgeState) -> KnowledgeState:
    """Return the same content with entities, relationships and ambiguities in canonical order."""
    return state.model_copy(update={
        "entities": tuple(sorted(state.entities, key=lambda e: e.id)),
        "relationships": tuple(sorted(state.relationships, key=lambda e: e.edge_id)),
        "ambiguities": tuple(sorted(state.ambiguities, key=lambda a: a.input)),
    })


def save_knowledge_state(state: KnowledgeState, path: Path) -> KnowledgeState:
    """Write canonical JSON with a freshly computed integrity hash. Returns the saved (canonical) state."""
    state = canonicalize(with_integrity(state))
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(canonical_dumps(to_canonical_dict(state)), encoding="utf-8")
    return state


def load_knowledge_state(path: Path) -> KnowledgeState:
    """Parse a knowledge-state file. Corrupt or malformed input raises KnowledgeStateCorruptError."""
    path = Path(path)
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError as exc:
        raise KnowledgeStateCorruptError(f"knowledge state not found: {path}") from exc
    except (UnicodeDecodeError, OSError) as exc:
        raise KnowledgeStateCorruptError(f"{path} is unreadable (not valid UTF-8 text): {exc}") from exc
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise KnowledgeStateCorruptError(f"{path} is not valid JSON: {exc}") from exc
    try:
        return KnowledgeState.model_validate(raw)
    except ValidationError as exc:
        raise KnowledgeStateCorruptError(f"{path} does not match the knowledge-state schema:\n{exc}") from exc
