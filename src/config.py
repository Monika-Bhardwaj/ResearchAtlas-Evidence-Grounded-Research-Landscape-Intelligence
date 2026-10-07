"""Configuration management (Section 41): no magic constants scattered through the code."""
from __future__ import annotations

from pathlib import Path
from typing import Optional, Tuple

import yaml
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from src.errors import ConfigError

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CONFIG_PATH = REPO_ROOT / "config" / "default.yaml"


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class TraversalSettings(_Frozen):
    max_hops: int = Field(ge=1, le=6)
    max_nodes: int = Field(ge=1)


class ReadingPathSettings(_Frozen):
    max_papers: int = Field(ge=1, le=10)


class ScoringWeights(_Frozen):
    concept_overlap: float = Field(ge=0.0, le=1.0)
    method_overlap: float = Field(ge=0.0, le=1.0)
    problem_overlap: float = Field(ge=0.0, le=1.0)
    benchmark_overlap: float = Field(ge=0.0, le=1.0)
    graph_proximity: float = Field(ge=0.0, le=1.0)
    citation_connectivity: float = Field(ge=0.0, le=1.0)
    temporal_relevance: float = Field(ge=0.0, le=1.0)

    @model_validator(mode="after")
    def _sum_to_one(self) -> "ScoringWeights":
        total = sum(self.model_dump().values())
        if abs(total - 1.0) > 1e-9:
            raise ValueError(f"scoring weights must sum to 1.0, got {total}")
        return self


class GoldSettings(_Frozen):
    facets_min: int = Field(ge=1)
    facets_max: int = Field(ge=1)
    require_combination_facet: bool
    min_facet_words: int = Field(ge=1)
    label_hint_terms: Tuple[str, ...]

    @model_validator(mode="after")
    def _range(self) -> "GoldSettings":
        if self.facets_min > self.facets_max:
            raise ValueError("facets_min must be <= facets_max")
        return self


class Settings(_Frozen):
    schema_version: str
    ontology_version: str
    traversal: TraversalSettings
    reading_path: ReadingPathSettings
    scoring_weights: ScoringWeights
    gold: GoldSettings


def load_settings(path: Optional[Path] = None) -> Settings:
    path = Path(path) if path else DEFAULT_CONFIG_PATH
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise ConfigError(f"config file not found: {path}") from exc
    except (UnicodeDecodeError, OSError) as exc:
        raise ConfigError(f"config file is unreadable: {path}: {exc}") from exc
    except yaml.YAMLError as exc:
        raise ConfigError(f"config file is not valid YAML: {path}: {exc}") from exc
    try:
        return Settings.model_validate(raw)
    except ValidationError as exc:
        raise ConfigError(f"invalid configuration in {path}:\n{exc}") from exc
