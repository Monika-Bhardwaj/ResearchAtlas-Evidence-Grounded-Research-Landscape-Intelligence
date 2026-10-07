"""Ontology loader and validator.

Invalid ontology states FAIL (OntologyError). Nothing is silently repaired or defaulted.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, FrozenSet, List, Optional

import yaml
from pydantic import ValidationError

from src.errors import OntologyError
from src.ids import split_id
from src.ontology.enums import (
    EntityType,
    ProvenanceType,
    RelationStatus,
    RelationType,
)
from src.ontology.spec import OntologySpec, RelationSpec

DEFAULT_ONTOLOGY_PATH = Path(__file__).with_name("ontology.yaml")


@dataclass(frozen=True)
class Ontology:
    spec: OntologySpec

    @property
    def version(self) -> str:
        return self.spec.ontology_version

    @property
    def schema_version(self) -> str:
        return self.spec.schema_version

    def relation(self, rel: RelationType) -> RelationSpec:
        return self.spec.relations[rel.value]

    def domain_types(self, rel: RelationType) -> FrozenSet[EntityType]:
        return frozenset(EntityType(n) for n in self.relation(rel).domain if n in EntityType._value2member_map_)

    def range_types(self, rel: RelationType) -> FrozenSet[EntityType]:
        return frozenset(EntityType(n) for n in self.relation(rel).range if n in EntityType._value2member_map_)

    def prefix_to_type(self) -> Dict[str, EntityType]:
        return {spec.id_prefix: EntityType(name) for name, spec in self.spec.entities.items()}

    def type_of_id(self, entity_id: str) -> Optional[EntityType]:
        """Entity type implied by an id's prefix, or None if the prefix is unknown/malformed."""
        try:
            prefix, _ = split_id(entity_id)
        except ValueError:
            return None
        return self.prefix_to_type().get(prefix)

    def storable_relations(self) -> List[RelationType]:
        return [RelationType(k) for k, v in self.spec.relations.items() if v.status == RelationStatus.ACTIVE]


def _validate(spec: OntologySpec) -> List[str]:
    p: List[str] = []
    entity_names = set(spec.entities)
    expected_entities = {e.value for e in EntityType}
    if entity_names != expected_entities:
        p.append(f"entity keys must be exactly the closed vocabulary; missing={sorted(expected_entities - entity_names)}, extra={sorted(entity_names - expected_entities)}")
    rel_names = set(spec.relations)
    expected_rels = {r.value for r in RelationType}
    if rel_names != expected_rels:
        p.append(f"relation keys must be exactly the {len(expected_rels)} Section 7 relations; missing={sorted(expected_rels - rel_names)}, extra={sorted(rel_names - expected_rels)}")

    prefixes = [s.id_prefix for s in spec.entities.values()]
    if len(prefixes) != len(set(prefixes)):
        p.append("entity id_prefix values must be unique")
    if "Paper" in spec.entities and "title" not in spec.entities["Paper"].required_attributes:
        p.append("Paper must require the 'title' attribute")

    for name in spec.non_relations:
        if name in rel_names:
            p.append(f"'{name}' is declared a non-relation but also appears as a relation key")
    for name in list(spec.deferred_entities) + list(spec.excluded_entities):
        if name in entity_names:
            p.append(f"'{name}' is both an active entity and deferred/excluded")

    deferred = set(spec.deferred_entities)
    for rname, r in spec.relations.items():
        where = f"relation {rname}"
        referenced = set(r.domain) | set(r.range)
        if r.status == RelationStatus.DEFERRED:
            unknown = referenced - entity_names - deferred
            if unknown:
                p.append(f"{where}: unknown entity types {sorted(unknown)}")
            if not (referenced & deferred):
                p.append(f"{where}: a DEFERRED relation must reference a deferred entity")
            if r.allowed_provenance:
                p.append(f"{where}: DEFERRED relations must have empty allowed_provenance")
        else:
            unknown = referenced - entity_names
            if unknown:
                p.append(f"{where}: domain/range reference unknown or inactive entity types {sorted(unknown)}")

        if r.status == RelationStatus.ACTIVE:
            if not r.allowed_provenance:
                p.append(f"{where}: ACTIVE relations need at least one allowed provenance type")
            if r.primary_source not in {t.value for t in r.allowed_provenance}:
                p.append(f"{where}: primary_source '{r.primary_source}' must be one of allowed_provenance")
            if r.inverse_of is not None:
                p.append(f"{where}: ACTIVE relations cannot declare inverse_of")
        else:
            if r.primary_source != "NONE":
                p.append(f"{where}: non-storable relations must have primary_source NONE")
            if r.allowed_provenance:
                p.append(f"{where}: non-storable relations must have empty allowed_provenance")

        if r.status == RelationStatus.DERIVED_INVERSE:
            inv = spec.relations.get(r.inverse_of.value) if r.inverse_of else None
            if inv is None:
                p.append(f"{where}: DERIVED_INVERSE requires a valid inverse_of")
            else:
                if inv.status != RelationStatus.ACTIVE:
                    p.append(f"{where}: inverse_of must point to an ACTIVE relation")
                if set(r.domain) != set(inv.range) or set(r.range) != set(inv.domain):
                    p.append(f"{where}: domain/range must be the swap of {r.inverse_of.value}")
        elif r.inverse_of is not None:
            p.append(f"{where}: only DERIVED_INVERSE relations may declare inverse_of")

        if r.symmetric and set(r.domain) != set(r.range):
            p.append(f"{where}: symmetric relations need identical domain and range")
        if r.mirror_of is not None:
            m = spec.relations.get(r.mirror_of.value)
            if m is None or m.status != RelationStatus.ACTIVE:
                p.append(f"{where}: mirror_of must point to an ACTIVE relation")
            elif set(m.domain) != set(r.domain) or set(m.range) != set(r.range):
                p.append(f"{where}: mirror_of relation must have identical domain and range")
        if r.status != RelationStatus.ACTIVE and (r.requires_source_paper or r.requires_evidence or r.requires_attribution):
            p.append(f"{where}: requires_* flags apply to ACTIVE relations only")
        if r.requires_attribution and not (r.requires_source_paper and r.requires_evidence):
            p.append(f"{where}: requires_attribution implies requires_source_paper and requires_evidence")

        if r.range_extension:
            covered = set(r.range_semantics or {})
            if len(r.range) < 2:
                p.append(f"{where}: range_extension needs a multi-type range")
            if covered != set(r.range):
                p.append(f"{where}: a range-extended relation needs range_semantics defining every range type precisely; missing={sorted(set(r.range) - covered)}, extra={sorted(covered - set(r.range))}")
        elif r.range_semantics:
            p.append(f"{where}: range_semantics is only allowed on range-extended relations")

        # Estimate coherence with provenance
        prov = set(r.allowed_provenance)
        if prov == {ProvenanceType.MANUALLY_CURATED} and r.estimate.curated_edges != r.estimate.edges:
            p.append(f"{where}: a purely curated relation must estimate curated_edges == edges")
        if ProvenanceType.MANUALLY_CURATED not in prov and r.estimate.curated_edges != (0, 0):
            p.append(f"{where}: relation does not allow curation but estimates curated edges")
    return p


def load_ontology(path: Optional[Path] = None) -> Ontology:
    path = Path(path) if path else DEFAULT_ONTOLOGY_PATH
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise OntologyError([f"ontology file not found: {path}"]) from exc
    except (UnicodeDecodeError, OSError) as exc:
        raise OntologyError([f"ontology file is unreadable: {exc}"]) from exc
    except yaml.YAMLError as exc:
        raise OntologyError([f"ontology file is not valid YAML: {exc}"]) from exc
    try:
        spec = OntologySpec.model_validate(raw)
    except ValidationError as exc:
        raise OntologyError([f"structure error: {e['loc']}: {e['msg']}" for e in exc.errors()]) from exc
    problems = _validate(spec)
    if problems:
        raise OntologyError(problems)
    return Ontology(spec)
