"""Gold-set schema and structural validators (Sections 31, 49.5b rules 8-10, 49.9).

The coding agent supplies only the SCHEMA and these validators. Gold content is authored by the
human researcher, without viewing any system output, and the frozen test file is sealed by hash.
"""
from __future__ import annotations

import re
from enum import Enum
from pathlib import Path
from typing import List, Literal, Optional, Set, Tuple

from pydantic import BaseModel, ConfigDict, Field, model_validator

from src.config import Settings
from src.errors import Issue, SealMismatchError, Severity
from src.ids import PAPER_ID_PATTERN
from src.ontology.loader import Ontology
from src.output.models import EvidenceSufficiency, PositioningLabel, TensionStatus
from src.serialization import sha256_file


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class Split(str, Enum):
    DEV = "dev"
    TEST = "test"


class Scope(str, Enum):
    IN_SCOPE = "IN_SCOPE"
    OUT_OF_SCOPE = "OUT_OF_SCOPE"


class GoldFacet(_Frozen):
    facet_id: str = Field(pattern=r"^(dev|test)-[0-9]{3}\.f[1-9][0-9]*$")
    facet_text: str = Field(min_length=1)
    gold_concepts: Tuple[str, ...] = ()
    gold_ambiguous: Tuple[str, ...] = ()
    gold_unknown: Tuple[str, ...] = ()
    gold_label: PositioningLabel
    is_combination: bool = False


class RelevantPaper(_Frozen):
    """Only papers a human judged relevant are listed; unlisted papers count as 0."""

    paper_id: str = Field(pattern=PAPER_ID_PATTERN)
    relevance: int = Field(ge=1, le=3)


class Prerequisite(_Frozen):
    before: str = Field(min_length=1)
    after: str = Field(min_length=1)


class GoldTension(_Frozen):
    facet_id: str = Field(min_length=1)
    claim_id: Optional[str] = None
    status: TensionStatus
    supporting: Tuple[str, ...] = ()
    challenging: Tuple[str, ...] = ()


class Annotation(_Frozen):
    authorship: Literal["HUMAN"]
    annotator: str = Field(min_length=1)
    without_system_output: Literal[True]   # attestation required by 49.9


class GoldProposal(_Frozen):
    proposal_id: str = Field(pattern=r"^(dev|test)-[0-9]{3}$")
    split: Split
    scope: Scope
    raw_text: str = Field(min_length=1)
    facets: Tuple[GoldFacet, ...] = Field(min_length=1)
    relevant_papers: Tuple[RelevantPaper, ...] = ()
    relevant_methods: Tuple[str, ...] = ()
    prerequisites: Tuple[Prerequisite, ...] = ()
    gold_tensions: Tuple[GoldTension, ...] = ()
    expected_uncertainty: EvidenceSufficiency
    annotation: Annotation


class GoldSet(_Frozen):
    gold_version: str = Field(min_length=1)
    split: Split
    proposals: Tuple[GoldProposal, ...] = ()

    @model_validator(mode="after")
    def _consistent(self) -> "GoldSet":
        pids = [p.proposal_id for p in self.proposals]
        if len(pids) != len(set(pids)):
            raise ValueError("proposal_id values must be unique")
        fids: List[str] = []
        for p in self.proposals:
            if p.split != self.split or not p.proposal_id.startswith(self.split.value + "-"):
                raise ValueError(f"proposal {p.proposal_id} does not belong to the {self.split.value} split")
            for f in p.facets:
                if not f.facet_id.startswith(p.proposal_id + "."):
                    raise ValueError(f"facet {f.facet_id} does not belong to proposal {p.proposal_id}")
                fids.append(f.facet_id)
        if len(fids) != len(set(fids)):
            raise ValueError("facet_id values must be unique")
        return self


def _e(code: str, msg: str, loc: str) -> Issue:
    return Issue(code, msg, loc, Severity.ERROR)


def validate_gold_set(gold: GoldSet, settings: Settings, onto: Ontology) -> List[Issue]:
    """Structural checks for rules 8-10 of 49.5b. Content quality remains the human's judgment."""
    g = settings.gold
    prefixes = "|".join(sorted(onto.prefix_to_type()))
    id_leak = re.compile(rf"\b(?:{prefixes}):[a-z0-9][a-z0-9_.\-]*", re.IGNORECASE)
    snake = re.compile(r"\b[a-z]+(?:_[a-z]+)+\b")
    issues: List[Issue] = []
    for p in gold.proposals:
        loc = f"proposal {p.proposal_id}"
        n = len(p.facets)
        if not g.facets_min <= n <= g.facets_max:
            issues.append(_e("GOLD_FACET_COUNT", f"{n} facets; required {g.facets_min}-{g.facets_max}", loc))
        if p.scope == Scope.IN_SCOPE and g.require_combination_facet and not any(f.is_combination for f in p.facets):
            issues.append(_e("GOLD_NO_COMBINATION", "in-scope proposals need at least one combination facet", loc))
        if p.scope == Scope.OUT_OF_SCOPE:
            if any(f.gold_label != PositioningLabel.UNKNOWN for f in p.facets):
                issues.append(_e("GOLD_OOS_LABEL", "out-of-scope proposals must label every facet UNKNOWN", loc))
            if p.relevant_papers:
                issues.append(_e("GOLD_OOS_RELEVANT", "out-of-scope proposals have no relevant papers (nDCG is undefined)", loc))
        facet_ids: Set[str] = {f.facet_id for f in p.facets}
        for f in p.facets:
            floc = f"facet {f.facet_id}"
            if len(f.facet_text.split()) < g.min_facet_words:
                issues.append(_e("GOLD_FACET_SHORT", f"facet_text needs >= {g.min_facet_words} words to be self-contained", floc))
            if id_leak.search(f.facet_text) or snake.search(f.facet_text):
                issues.append(_e("GOLD_ONTOLOGY_LEAK", "facet_text contains ontology-canonical identifiers; write natural researcher language (rule 9)", floc))
            low = f.facet_text.lower()
            for term in g.label_hint_terms:
                if term in low:
                    issues.append(Issue("GOLD_LABEL_HINT", f"facet_text contains {term!r}, which may hint at the gold label (rule 9)", floc, Severity.WARNING))
            for c in f.gold_concepts:
                if not c.startswith("concept:"):
                    issues.append(_e("GOLD_CONCEPT_ID", f"gold concept {c!r} must be a concept: id", floc))
        for t in p.gold_tensions:
            if t.facet_id not in facet_ids:
                issues.append(_e("GOLD_TENSION_FACET", f"tension references unknown facet {t.facet_id!r}", loc))
            if t.status == TensionStatus.CONFLICTING and (not t.supporting or not t.challenging or len(set(t.supporting) | set(t.challenging)) < 2):
                issues.append(_e("GOLD_TENSION_CONFLICTING", "CONFLICTING needs both sides and at least two distinct papers", loc))
    return issues


# ---------------------------------------------------------------- sealing (49.9)
def seal_file(path: Path) -> str:
    """SHA-256 of the file's bytes: the value committed in place of the sealed test gold."""
    return sha256_file(path)


def verify_seal(path: Path, expected_sha256: str) -> None:
    actual = sha256_file(path)
    if actual != expected_sha256:
        raise SealMismatchError(f"{path} hash {actual} does not match committed seal {expected_sha256}")
