import pytest
from pydantic import ValidationError

from src.ontology.enums import RelationType
from src.output.models import (
    INSUFFICIENT_MESSAGE, EvidenceItem, Facet, FacetPositioning, PositioningLabel, ProposalGrounding,
    ReadingPathItem, RuntimeOutput, Tension, TensionStatus,
)

EV = EvidenceItem(basis="DIRECTLY_SUPPORTED", edge_id="edge_0001", paper_id="paper:s2_a")


def output(**kw):
    facets = (Facet(facet_id="f1", facet_text="a facet about consolidation"), Facet(facet_id="f2", facet_text="a facet about forgetting"))
    base = dict(
        request_id="r1",
        proposal=ProposalGrounding(raw_text="p", facets=facets),
        positioning=tuple(FacetPositioning(facet_id=f.facet_id, facet_text=f.facet_text, label=PositioningLabel.UNKNOWN,
                                           abstain=True, confidence_score=0.1, evidence_sufficiency="INSUFFICIENT") for f in facets),
        evidence_sufficiency="HIGH",
    )
    base.update(kw)
    return RuntimeOutput(**base)


def rp(rank, pid):
    return ReadingPathItem(rank=rank, paper_id=pid, reason="why", relationship_to_proposal="how")


def test_valid_output():
    assert output().evidence_sufficiency.value == "HIGH"


def test_unknown_is_a_class_and_abstain_is_a_separate_flag():
    p = output().positioning[0]
    assert p.label == PositioningLabel.UNKNOWN and p.abstain is True
    assert PositioningLabel("UNKNOWN") and "ABSTAIN" not in {l.value for l in PositioningLabel}


def test_reading_path_ranks_must_be_contiguous_and_unique():
    output(reading_path=(rp(1, "paper:a"), rp(2, "paper:b")))
    with pytest.raises(ValidationError, match="ranks"):
        output(reading_path=(rp(1, "paper:a"), rp(3, "paper:b")))
    with pytest.raises(ValidationError, match="repeat"):
        output(reading_path=(rp(1, "paper:a"), rp(2, "paper:a")))


def test_positioning_must_cover_exactly_the_facets():
    facets = (Facet(facet_id="f1", facet_text="t"),)
    with pytest.raises(ValidationError, match="cover exactly"):
        RuntimeOutput(request_id="r", proposal=ProposalGrounding(raw_text="p", facets=facets), positioning=(), evidence_sufficiency="LOW")


def test_insufficient_output_carries_the_required_message():
    with pytest.raises(ValidationError, match="INSUFFICIENT"):
        output(evidence_sufficiency="INSUFFICIENT")
    assert output(evidence_sufficiency="INSUFFICIENT", warnings=(INSUFFICIENT_MESSAGE,))


@pytest.mark.parametrize("text", ["This proposal is novel.", "your research appears highly novel", "No prior work exists on this."])
def test_novelty_claims_are_rejected(text):
    with pytest.raises(ValidationError, match="novelty"):
        output(warnings=(text,))


def test_neutral_wording_is_accepted():
    assert output(warnings=("No close prior work was found in the indexed corpus.",))


def test_conflicting_tension_needs_both_sides_and_two_papers():
    sup = (EvidenceItem(basis="DIRECTLY_SUPPORTED", edge_id="edge_0007", paper_id="paper:s2_b"),)
    chal = (EvidenceItem(basis="DIRECTLY_SUPPORTED", edge_id="edge_0008", paper_id="paper:s2_a"),)
    assert Tension(facet_id="f1", claim_id="claim:k1", status=TensionStatus.CONFLICTING, supporting_evidence=sup, challenging_evidence=chal)
    with pytest.raises(ValidationError, match="both"):
        Tension(facet_id="f1", claim_id="claim:k1", status=TensionStatus.CONFLICTING, supporting_evidence=sup)
    same = (EvidenceItem(basis="DIRECTLY_SUPPORTED", edge_id="edge_0009", paper_id="paper:s2_b"),)
    with pytest.raises(ValidationError, match="two distinct"):
        Tension(facet_id="f1", claim_id="claim:k1", status=TensionStatus.CONFLICTING, supporting_evidence=sup, challenging_evidence=same)
    assert Tension(facet_id="f1", claim_id=None, status=TensionStatus.INSUFFICIENT_EVIDENCE)


def test_tension_status_is_not_an_ontology_relation():
    assert {s.value for s in TensionStatus}.isdisjoint({r.value for r in RelationType})


def test_evidence_with_a_supported_basis_must_be_traceable():
    with pytest.raises(ValidationError, match="must reference"):
        EvidenceItem(basis="RULE_DERIVED")
    assert EvidenceItem(basis="INSUFFICIENT_EVIDENCE")
    assert EvidenceItem(basis="USER_PROVIDED")


def test_score_range_and_extra_fields():
    from src.output.models import PriorWorkItem
    with pytest.raises(ValidationError):
        PriorWorkItem(paper_id="paper:a", score=1.2, confidence="HIGH")
    with pytest.raises(ValidationError):
        output(novelty_score=0.9)
