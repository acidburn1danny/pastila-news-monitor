"""Coordinate-bound semantic-role alignment successor for Constructor V5.3.

This module does not realize or emit text.  It distinguishes an absent role
from a role whose exact surface bytes carry a narrowly licensed Romanian case
inflection.  Every accepted witness remains bound to both character and UTF-8
byte coordinates in the actual surface.
"""

from __future__ import annotations

from dataclasses import dataclass
import unicodedata

from pastila_scout.humor_batch2_development_constructor_v5_1 import TypedPlanNode


@dataclass(frozen=True, slots=True)
class CoordinateBoundRoleWitness:
    node_id: str
    role: str
    operand_or_predicate_id: str
    character_start: int
    character_end: int
    utf8_byte_start: int
    utf8_byte_end: int
    surface_form: str
    canonical_form: str
    alignment_rule: str


def _norm(value: str) -> str:
    return " ".join(unicodedata.normalize("NFKC", value).casefold().split())


def _licensed_alignment(canonical: str, surface: str, rule: str) -> bool:
    canonical_norm, surface_norm = _norm(canonical), _norm(surface)
    if rule == "EXACT_NFKC_CASEFOLD":
        return canonical_norm == surface_norm
    if rule == "ROMANIAN_AMBELE_AMBELOR_CASE_INFLECTION":
        canonical_words, surface_words = canonical_norm.split(), surface_norm.split()
        return (
            len(canonical_words) == len(surface_words)
            and canonical_words[:1] == ["ambele"]
            and surface_words[:1] == ["ambelor"]
            and canonical_words[1:] == surface_words[1:]
        )
    return False


def validate_coordinate_bound_role_witness(surface: str, witness: CoordinateBoundRoleWitness) -> None:
    """Require actual coordinate evidence and a deterministic alignment rule."""
    if witness.role not in {"ACTOR", "PREDICATE", "PATIENT"}:
        raise ValueError("unknown semantic role")
    if not (0 <= witness.character_start < witness.character_end <= len(surface)):
        raise ValueError("semantic role genuinely missing: invalid character coordinates")
    raw = surface.encode("utf-8")
    if not (0 <= witness.utf8_byte_start < witness.utf8_byte_end <= len(raw)):
        raise ValueError("semantic role genuinely missing: invalid byte coordinates")
    character_evidence = surface[witness.character_start:witness.character_end]
    byte_evidence = raw[witness.utf8_byte_start:witness.utf8_byte_end]
    if character_evidence != witness.surface_form or byte_evidence != witness.surface_form.encode("utf-8"):
        raise ValueError("semantic role genuinely missing: coordinates do not bind surface bytes")
    if not _licensed_alignment(witness.canonical_form, witness.surface_form, witness.alignment_rule):
        raise ValueError("surface-form mismatch is not deterministically licensed")


def validate_node_role_alignment(
    *, surface: str, typed_plan: tuple[TypedPlanNode, ...],
    witnesses: tuple[CoordinateBoundRoleWitness, ...],
) -> None:
    """Require independent actor, predicate, and patient evidence for every node."""
    indexed = {(item.node_id, item.role): item for item in witnesses}
    expected = {(node.node_id, role) for node in typed_plan for role in ("ACTOR", "PREDICATE", "PATIENT")}
    if len(indexed) != len(witnesses) or set(indexed) != expected:
        raise ValueError("semantic role genuinely missing: N x actor/predicate/patient coverage required")
    for node in typed_plan:
        expected_ids = {
            "ACTOR": node.bound_actor_id,
            "PREDICATE": node.predicate_id,
            "PATIENT": node.bound_patient_id,
        }
        for role, expected_id in expected_ids.items():
            witness = indexed[(node.node_id, role)]
            if witness.operand_or_predicate_id != expected_id:
                raise ValueError("typed semantic-role identity mismatch")
            validate_coordinate_bound_role_witness(surface, witness)


__all__ = ["CoordinateBoundRoleWitness", "validate_coordinate_bound_role_witness",
           "validate_node_role_alignment"]
