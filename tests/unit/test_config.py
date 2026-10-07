import pytest
import yaml

from src.config import DEFAULT_CONFIG_PATH, load_settings
from src.errors import ConfigError


def _write(tmp_path, mutate):
    raw = yaml.safe_load(DEFAULT_CONFIG_PATH.read_text(encoding="utf-8"))
    mutate(raw)
    p = tmp_path / "c.yaml"
    p.write_text(yaml.safe_dump(raw), encoding="utf-8")
    return p


def test_default_config_loads_and_matches_ontology_version(settings, ontology):
    assert settings.ontology_version == ontology.version
    assert settings.schema_version == ontology.schema_version


def test_scoring_weights_are_the_section_21_starting_points_and_sum_to_one(settings):
    w = settings.scoring_weights
    assert (w.concept_overlap, w.method_overlap, w.problem_overlap, w.benchmark_overlap,
            w.graph_proximity, w.citation_connectivity, w.temporal_relevance) == (0.30, 0.20, 0.15, 0.10, 0.10, 0.10, 0.05)
    assert abs(sum(w.model_dump().values()) - 1.0) < 1e-9
    assert all(v >= 0 for v in w.model_dump().values())      # no negative (sign-inverting) weights


def test_bad_weights_are_rejected(tmp_path):
    with pytest.raises(ConfigError, match="sum to 1.0"):
        load_settings(_write(tmp_path, lambda r: r["scoring_weights"].update(concept_overlap=0.5)))
    with pytest.raises(ConfigError):
        load_settings(_write(tmp_path, lambda r: r["scoring_weights"].update(concept_overlap=-0.1, method_overlap=0.6)))


def test_bad_gold_settings_and_unknown_keys_are_rejected(tmp_path):
    with pytest.raises(ConfigError, match="facets_min"):
        load_settings(_write(tmp_path, lambda r: r["gold"].update(facets_min=6)))
    with pytest.raises(ConfigError):
        load_settings(_write(tmp_path, lambda r: r.update(surprise=1)))


def test_missing_or_invalid_config(tmp_path):
    with pytest.raises(ConfigError, match="not found"):
        load_settings(tmp_path / "nope.yaml")
    bad = tmp_path / "bad.yaml"
    bad.write_text("a: [unclosed", encoding="utf-8")
    with pytest.raises(ConfigError, match="not valid YAML"):
        load_settings(bad)
