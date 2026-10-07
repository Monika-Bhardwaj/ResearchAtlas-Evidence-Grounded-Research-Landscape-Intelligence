from pathlib import Path

import pytest
import yaml
from pydantic import ValidationError

from src.errors import SealMismatchError, Severity
from src.evaluation.gold import GoldSet, seal_file, validate_gold_set, verify_seal
from src.knowledge.curation import (
    Approval, CuratedEdge, CurationFile, VocabularyFile, approved_curated_edges, approved_vocabulary,
    validate_curation, validate_vocabulary,
)
from src.config import REPO_ROOT

TEMPLATES = REPO_ROOT / "data"


def load(model, rel):
    return model.model_validate(yaml.safe_load((TEMPLATES / rel).read_text(encoding="utf-8")))


def errs(issues):
    return {i.code for i in issues if i.severity == Severity.ERROR}


def warns(issues):
    return {i.code for i in issues if i.severity == Severity.WARNING}


APPROVED = {"status": "APPROVED", "approved_by": "researcher", "approved_on": "2026-01-01"}


# ---------------------------------------------------------------- blank templates are valid and empty
def test_blank_templates_validate_and_contain_no_content(ontology, settings):
    assert load(VocabularyFile, "curation/vocabulary.template.yaml").entries == ()
    assert load(CurationFile, "curation/curation.template.yaml").edges == ()
    for split in ("dev", "test"):
        gs = load(GoldSet, f"evaluation/gold_{split}.template.yaml")
        assert gs.proposals == ()
        assert validate_gold_set(gs, settings, ontology) == []


# ---------------------------------------------------------------- approval
def test_approved_requires_who_and_when():
    with pytest.raises(ValidationError, match="approved_by"):
        Approval(status="APPROVED")
    assert Approval(**APPROVED)


def vocab(*entries, ambiguous=()):
    return VocabularyFile(vocabulary_version="t", entries=entries, ambiguous_terms=ambiguous)


def v(id_, type_, label, aliases=(), approval=None):
    return dict(id=id_, type=type_, label=label, aliases=aliases, definition="d", approval=approval or APPROVED)


def test_vocabulary_rejects_paper_entries_and_prefix_mismatch(ontology):
    assert "VOCAB_WRONG_SOURCE" in errs(validate_vocabulary(vocab(v("paper:x", "Paper", "x")), ontology))
    assert "VOCAB_PREFIX_MISMATCH" in errs(validate_vocabulary(vocab(v("method:x", "Concept", "x")), ontology))


def test_vocabulary_ambiguity_must_be_declared_never_silently_resolved(ontology):
    a = v("concept:forget_select", "Concept", "selective forgetting", ("forgetting",))
    b = v("concept:forget_prune", "Concept", "memory pruning", ("forgetting",))
    assert "VOCAB_UNDECLARED_AMBIGUITY" in errs(validate_vocabulary(vocab(a, b), ontology))
    declared = vocab(a, b, ambiguous=({"input": "forgetting", "candidates": ("concept:forget_select", "concept:forget_prune")},))
    assert errs(validate_vocabulary(declared, ontology)) == set()


def test_draft_entries_warn_and_are_not_applied(ontology):
    draft = vocab(v("concept:x", "Concept", "x", approval={"status": "DRAFT"}), v("concept:y", "Concept", "y"))
    assert "VOCAB_DRAFT" in warns(validate_vocabulary(draft, ontology))
    assert [e.id for e in approved_vocabulary(draft)] == ["concept:y"]


# ---------------------------------------------------------------- curation
def cur(**kw):
    base = dict(curation_id="cur_0001", source="concept:a", relation="PREREQUISITE_FOR", target="method:b",
                rationale="because", authorship="HUMAN", curated_by="researcher", approval=APPROVED)
    base.update(kw)
    return base


def curation(*edges):
    return CurationFile(curation_version="t", curator="researcher", edges=tuple(CuratedEdge(**e) for e in edges))


def test_curated_edges_must_be_human_authored():
    with pytest.raises(ValidationError):
        CuratedEdge(**cur(authorship="AI"))
    with pytest.raises(ValidationError):
        CuratedEdge(**{k: v for k, v in cur().items() if k != "authorship"})


def test_valid_entity_level_curated_edge_passes(ontology):
    assert errs(validate_curation(curation(cur()), ontology)) == set()


def test_curation_domain_range_and_curatable_checks(ontology):
    assert "CUR_DOMAIN" in errs(validate_curation(curation(cur(source="paper:a")), ontology))
    assert "CUR_RANGE" in errs(validate_curation(curation(cur(target="limitation:b")), ontology))
    assert "CUR_NOT_CURATABLE" in errs(validate_curation(curation(cur(relation="CITES", source="paper:a", target="paper:b")), ontology))
    assert "CUR_RELATION_NOT_STORABLE" in errs(validate_curation(curation(cur(relation="CITED_BY", source="paper:a", target="paper:b")), ontology))


def test_curation_symmetric_and_mirror_rules(ontology):
    assert "CUR_SYMMETRIC_ORDER" in errs(validate_curation(curation(cur(relation="COMBINES_WITH", source="concept:z", target="concept:a")), ontology))
    pair = curation(cur(curation_id="cur_0001", relation="GENERALIZES", source="concept:a", target="concept:b"),
                    cur(curation_id="cur_0002", relation="SPECIALIZES", source="concept:b", target="concept:a"))
    assert "CUR_MIRROR_CONFLICT" in errs(validate_curation(pair, ontology))


def test_paper_sourced_curated_edges_need_a_passage_from_that_paper(ontology):
    bare = cur(source="paper:a", relation="SUPPORTS", target="claim:k")
    assert "CUR_EVIDENCE_REQUIRED" in errs(validate_curation(curation(bare), ontology))
    ok = cur(source="paper:a", relation="SUPPORTS", target="claim:k",
             evidence=({"paper_id": "paper:a", "source_field": "abstract", "passage": "quoted passage"},))
    assert errs(validate_curation(curation(ok), ontology)) == set()


def test_reports_limitation_curation_needs_reporting_paper_and_attribution(ontology):
    base = cur(source="method:m", relation="REPORTS_LIMITATION", target="limitation:l")
    assert {"CUR_SOURCE_PAPER_REQUIRED", "CUR_ATTRIBUTION_REQUIRED"} <= errs(validate_curation(curation(base), ontology))
    good = dict(base, attribution="THIRD_PARTY", evidence=({"paper_id": "paper:r", "passage": "p"},))
    assert errs(validate_curation(curation(good), ontology)) == set()
    assert "CUR_ATTRIBUTION_FORBIDDEN" in errs(validate_curation(curation(cur(attribution="THIRD_PARTY")), ontology))


def test_draft_curated_edges_warn_and_are_not_applied(ontology):
    c = curation(cur(approval={"status": "DRAFT"}), cur(curation_id="cur_0002", source="concept:c", target="method:d"))
    assert "CUR_DRAFT" in warns(validate_curation(c, ontology))
    assert [e.curation_id for e in approved_curated_edges(c)] == ["cur_0002"]


# ---------------------------------------------------------------- gold sets
def facet(pid, n, text="how an agent consolidates repeated experiences into lasting knowledge", **kw):
    base = dict(facet_id=f"{pid}.f{n}", facet_text=text, gold_label="WELL_EXPLORED", is_combination=False)
    base.update(kw)
    return base


def proposal(pid="dev-001", n_facets=4, combo=True, scope="IN_SCOPE", label="WELL_EXPLORED", **kw):
    facets = [facet(pid, i + 1, gold_label=label, is_combination=(combo and i == 0)) for i in range(n_facets)]
    base = dict(proposal_id=pid, split=pid.split("-")[0], scope=scope, raw_text="a proposal", facets=facets,
                expected_uncertainty="MEDIUM",
                annotation={"authorship": "HUMAN", "annotator": "researcher", "without_system_output": True})
    base.update(kw)
    return base


def gold(*props, split="dev"):
    return GoldSet.model_validate({"gold_version": "t", "split": split, "proposals": list(props)})


def test_valid_gold_proposal_passes(ontology, settings):
    assert [i for i in validate_gold_set(gold(proposal()), settings, ontology) if i.severity == Severity.ERROR] == []


def test_facet_count_and_combination_rules(ontology, settings):
    assert "GOLD_FACET_COUNT" in errs(validate_gold_set(gold(proposal(n_facets=2)), settings, ontology))
    assert "GOLD_FACET_COUNT" in errs(validate_gold_set(gold(proposal(n_facets=6)), settings, ontology))
    assert "GOLD_NO_COMBINATION" in errs(validate_gold_set(gold(proposal(combo=False)), settings, ontology))


def test_out_of_scope_rules(ontology, settings):
    bad = gold(proposal(scope="OUT_OF_SCOPE", combo=False, label="WELL_EXPLORED"))
    assert "GOLD_OOS_LABEL" in errs(validate_gold_set(bad, settings, ontology))
    ok = gold(proposal(scope="OUT_OF_SCOPE", combo=False, label="UNKNOWN"))
    assert errs(validate_gold_set(ok, settings, ontology)) == set()
    with_rel = gold(proposal(scope="OUT_OF_SCOPE", combo=False, label="UNKNOWN", relevant_papers=[{"paper_id": "paper:a", "relevance": 2}]))
    assert "GOLD_OOS_RELEVANT" in errs(validate_gold_set(with_rel, settings, ontology))


def test_rule_9_facet_text_checks(ontology, settings):
    def with_text(text):
        p = proposal()
        p["facets"][1]["facet_text"] = text
        return gold(p)
    assert "GOLD_FACET_SHORT" in errs(validate_gold_set(with_text("too short here"), settings, ontology))
    assert "GOLD_ONTOLOGY_LEAK" in errs(validate_gold_set(with_text("whether concept:episodic_memory helps an agent reason over time"), settings, ontology))
    assert "GOLD_ONTOLOGY_LEAK" in errs(validate_gold_set(with_text("whether episodic_memory helps an agent reason over time"), settings, ontology))
    assert "GOLD_LABEL_HINT" in warns(validate_gold_set(with_text("an underexplored way for agents to retain long conversations"), settings, ontology))


def test_gold_concept_ids_and_tension_checks(ontology, settings):
    p = proposal()
    p["facets"][0]["gold_concepts"] = ["method:oops"]
    assert "GOLD_CONCEPT_ID" in errs(validate_gold_set(gold(p), settings, ontology))
    p2 = proposal(gold_tensions=[{"facet_id": "dev-001.f9", "status": "INSUFFICIENT_EVIDENCE"}])
    assert "GOLD_TENSION_FACET" in errs(validate_gold_set(gold(p2), settings, ontology))
    p3 = proposal(gold_tensions=[{"facet_id": "dev-001.f1", "claim_id": "claim:k", "status": "CONFLICTING", "supporting": ["paper:a"], "challenging": []}])
    assert "GOLD_TENSION_CONFLICTING" in errs(validate_gold_set(gold(p3), settings, ontology))


def test_gold_schema_enforces_split_ids_and_human_attestation():
    with pytest.raises(ValidationError, match="split"):
        gold(proposal("test-001"), split="dev")
    with pytest.raises(ValidationError, match="unique"):
        gold(proposal("dev-001"), proposal("dev-001"))
    p = proposal(annotation={"authorship": "AI", "annotator": "x", "without_system_output": True})
    with pytest.raises(ValidationError):
        gold(p)
    p = proposal(annotation={"authorship": "HUMAN", "annotator": "x", "without_system_output": False})
    with pytest.raises(ValidationError):
        gold(p)


def test_seal_detects_any_change(tmp_path):
    f = tmp_path / "gold_test.yaml"
    f.write_text("proposals: []\n", encoding="utf-8")
    digest = seal_file(f)
    verify_seal(f, digest)
    f.write_text("proposals: []\n# edited\n", encoding="utf-8")
    with pytest.raises(SealMismatchError):
        verify_seal(f, digest)
