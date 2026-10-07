import json
import random

import pytest

from src.errors import KnowledgeStateCorruptError
from src.knowledge.io import compute_content_hash, load_knowledge_state, save_knowledge_state, to_canonical_dict
from src.knowledge.models import BuildMetadata
from src.serialization import canonical_dumps, canonical_json_bytes
from tests.helpers import base_edges, base_entities, make_state


def test_canonical_json_is_order_independent():
    assert canonical_json_bytes({"b": 1, "a": [1, 2]}) == canonical_json_bytes({"a": [1, 2], "b": 1})
    assert canonical_dumps({"b": 1, "a": 2}).endswith("\n")


def test_content_hash_ignores_input_order():
    ents, eds = list(base_entities()), list(base_edges())
    h1 = compute_content_hash(make_state(ents, eds))
    random.Random(7).shuffle(ents)
    random.Random(8).shuffle(eds)
    assert compute_content_hash(make_state(ents, eds)) == h1


def test_content_hash_changes_with_content_but_not_build_metadata():
    base = make_state()
    changed = make_state(edges=list(base_edges())[:-1])
    assert compute_content_hash(base) != compute_content_hash(changed)
    other_meta = base.model_copy(update={"build_metadata": BuildMetadata(generator="elsewhere", git_sha="abc123")})
    assert compute_content_hash(other_meta) == compute_content_hash(base)


def test_save_load_round_trip_is_byte_stable(tmp_path):
    st = make_state()
    p1, p2 = tmp_path / "a.json", tmp_path / "b.json"
    saved = save_knowledge_state(st, p1)
    again = save_knowledge_state(load_knowledge_state(p1), p2)
    assert p1.read_bytes() == p2.read_bytes()
    assert load_knowledge_state(p1) == saved == again


def test_saved_file_is_sorted_and_hash_is_embedded(tmp_path):
    st = make_state(entities=list(reversed(base_entities())))
    p = tmp_path / "ks.json"
    save_knowledge_state(st, p)
    raw = json.loads(p.read_text(encoding="utf-8"))
    ids = [e["id"] for e in raw["entities"]]
    assert ids == sorted(ids)
    assert raw["integrity"]["content_sha256"] == compute_content_hash(st)


def test_corrupt_inputs_fail_with_clear_errors(tmp_path):
    with pytest.raises(KnowledgeStateCorruptError, match="not found"):
        load_knowledge_state(tmp_path / "missing.json")
    bad = tmp_path / "bad.json"
    bad.write_text("{not json", encoding="utf-8")
    with pytest.raises(KnowledgeStateCorruptError, match="not valid JSON"):
        load_knowledge_state(bad)
    wrong = tmp_path / "wrong.json"
    wrong.write_text(json.dumps({"schema_version": "0.1.0"}), encoding="utf-8")
    with pytest.raises(KnowledgeStateCorruptError, match="schema"):
        load_knowledge_state(wrong)
