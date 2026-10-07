import re

from src.config import REPO_ROOT

CONTRACT = (REPO_ROOT / "docs" / "research_contract.md").read_text(encoding="utf-8")

REQUIRED_ARTIFACTS = {
    "src/ontology/ontology.yaml", "src/ontology/loader.py", "src/knowledge/models.py", "src/knowledge/validation.py",
    "src/knowledge/io.py", "src/knowledge/curation.py", "src/evaluation/gold.py", "src/output/models.py",
    "config/default.yaml", "schemas/knowledge_state.schema.json", "docs/relation_source_inventory.md",
    "scripts/validate_knowledge_state.py", "scripts/seal_gold.py",
}


def _traceability_paths():
    section = CONTRACT[CONTRACT.index("## 2.6 M1 traceability"):]
    return set(re.findall(r"^\| `([^`]+)` \|", section, flags=re.MULTILINE))


def test_every_m1_artifact_is_mapped_to_the_contract_and_exists():
    paths = _traceability_paths()
    assert REQUIRED_ARTIFACTS <= paths, f"unmapped M1 artifacts: {REQUIRED_ARTIFACTS - paths}"
    missing = [p for p in paths if not (REPO_ROOT / p).exists()]
    assert not missing, f"traceability rows point at missing files: {missing}"


def test_contract_contains_the_frozen_structure():
    for needle in ("H1 (primary, accuracy; the ONLY confirmatory hypothesis)", "H1b", "H2 (structure matters", "H3 (calibration",
                   "## 49.5b Ranking→positioning adapter and fairness rules", "## 49.12 Parameters", "LOWER IS BETTER",
                   "never stored in the knowledge state", "Status: PROPOSED", "FROZEN AT MILESTONE 1 APPROVAL"):
        assert needle in CONTRACT, needle


def test_contract_does_not_use_the_wrong_aurc_direction():
    assert "L3 ≥ L2" not in CONTRACT


def test_all_twelve_adrs_exist_with_the_required_sections():
    adrs = sorted((REPO_ROOT / "docs" / "decisions").glob("ADR-*.md"))
    assert len(adrs) == 12
    for p in adrs:
        text = p.read_text(encoding="utf-8")
        for h in ("## Decision", "## Alternatives considered", "## Rationale", "## Consequences", "## Rejected alternatives"):
            assert h in text, (p.name, h)


def test_no_premature_implementation_only_placeholders_in_later_milestone_packages():
    for pkg in ("ingestion", "corpus", "reasoning", "interface"):
        files = [p.name for p in (REPO_ROOT / "src" / pkg).iterdir() if p.is_file() and p.suffix == ".py"]
        assert files == ["__init__.py"], (pkg, files)
        assert "Placeholder" in (REPO_ROOT / "src" / pkg / "__init__.py").read_text(encoding="utf-8")


def test_data_directory_holds_only_blank_templates_and_empty_dirs():
    for p in (REPO_ROOT / "data").rglob("*"):
        if p.is_file():
            assert p.name.endswith(".template.yaml"), f"unexpected data file: {p}"
