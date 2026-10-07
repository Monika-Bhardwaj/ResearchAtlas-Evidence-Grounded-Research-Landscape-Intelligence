import subprocess
import sys

from src.config import REPO_ROOT
from src.knowledge.io import save_knowledge_state
from tests.helpers import base_edges, make_state


def run(*args):
    return subprocess.run([sys.executable, *args], cwd=REPO_ROOT, capture_output=True, text=True)


def test_validate_script_exit_codes(tmp_path):
    missing = run("scripts/validate_knowledge_state.py", str(tmp_path / "none.json"))
    assert missing.returncode == 2 and "Milestone 3" in missing.stderr

    good = tmp_path / "ks.json"
    save_knowledge_state(make_state(), good)
    ok = run("scripts/validate_knowledge_state.py", str(good))
    assert ok.returncode == 0 and "integrity verified" in ok.stdout

    bad = tmp_path / "bad.json"
    bad.write_text(good.read_text(encoding="utf-8").replace('"confidence": 0.9', '"confidence": 0.8', 1), encoding="utf-8")
    broken = run("scripts/validate_knowledge_state.py", str(bad))
    assert broken.returncode == 1 and "KS_INTEGRITY" in broken.stderr

    junk = tmp_path / "junk.json"
    junk.write_text("not json", encoding="utf-8")
    assert run("scripts/validate_knowledge_state.py", str(junk)).returncode == 1


def test_validate_script_reports_every_semantic_error(tmp_path):
    from src.ontology.enums import RelationType
    from tests.helpers import edge, prov_rule
    st = make_state(edges=list(base_edges()) + [edge(50, "method:m2", RelationType.PROPOSES, "method:m1", prov_rule())])
    p = tmp_path / "ks.json"
    save_knowledge_state(st, p)
    r = run("scripts/validate_knowledge_state.py", str(p))
    assert r.returncode == 1 and "EDGE_DOMAIN" in r.stderr


def test_generated_artifacts_are_up_to_date():
    assert run("scripts/export_schemas.py", "--check").returncode == 0
    assert run("scripts/render_docs.py", "--check").returncode == 0


def test_seal_script_round_trip_and_tamper_detection(tmp_path):
    f = tmp_path / "gold_test.yaml"
    f.write_text("proposals: []\n", encoding="utf-8")
    assert run("scripts/seal_gold.py", str(f)).returncode == 0
    assert (tmp_path / "gold_test.yaml.sha256").exists()
    assert run("scripts/seal_gold.py", str(f), "--verify").returncode == 0
    f.write_text("proposals: [edited]\n", encoding="utf-8")
    r = run("scripts/seal_gold.py", str(f), "--verify")
    assert r.returncode == 1 and "SEAL MISMATCH" in r.stderr
