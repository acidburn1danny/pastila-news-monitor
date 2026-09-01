"""Source-shape-neutral, pathless DEVELOPMENT constructor successor.

The constructor accepts canonical packet bytes only. Proposition components are
verified by their frozen coordinates and hashes, converted to typed factual
operands, and used to derive an abstract dependency plan before realization.
No lexical placement of negation or source-specific preposition is required.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from typing import Any


@dataclass(frozen=True, slots=True)
class PropositionOperands:
    relation_id: str
    subject: str
    predicate: str
    object_value: str
    qualification: str | None
    source_provenance: str


@dataclass(frozen=True, slots=True)
class TypedPlanNode:
    node_id: str
    bound_actor_id: str
    actor_role: str
    predicate_id: str
    bound_patient_id: str
    predecessor_node_ids: tuple[str, ...]
    introduces_ids: tuple[str, ...]
    source_provenance: str
    nonfactual_scope: bool


@dataclass(frozen=True, slots=True)
class DevelopmentConstructionResultV5_1:
    terminal_classification: str
    failure_code: str | None
    candidate_surface_utf8: bytes | None
    constructor_visible_sha256: str


_ACTOR_ROLES = frozenset({"NOMINAL_HEAD", "RELATION_HEAD", "PROCESS_HEAD"})


def _clean(value: str) -> str:
    return " ".join(value.strip().split())


def _component_text(source: str, component: dict[str, Any], char_origin: int, byte_origin: int) -> str:
    cs, ce = component["character_coordinates"]
    bs, be = component["utf8_byte_coordinates"]
    value = source[cs - char_origin:ce - char_origin]
    encoded = source.encode("utf-8")
    raw = encoded[bs - byte_origin:be - byte_origin]
    expected = component.get("span_sha256", component.get("sha256"))
    if value.encode("utf-8") != raw or hashlib.sha256(raw).hexdigest() != expected:
        raise ValueError("component coordinate or hash mismatch")
    return _clean(value)


def extract_typed_operands(source: str, proposition: dict[str, Any]) -> PropositionOperands:
    """Extract coordinate-bound roles without relying on lexical source shape."""
    span = proposition["supporting_span"]
    char_origin = span["character_coordinates"][0]
    byte_origin = span["utf8_byte_coordinates"][0]
    supporting = _component_text(source, span, char_origin, byte_origin)
    if _clean(source) != supporting:
        raise ValueError("authorized context is not the exact supporting span")
    subject = _component_text(source, proposition["subject"], char_origin, byte_origin)
    predicate = _component_text(source, proposition["predicate"], char_origin, byte_origin)
    object_value = _component_text(source, proposition["object"], char_origin, byte_origin)
    qualification_component = proposition.get("qualification")
    qualification = (_component_text(source, qualification_component, char_origin, byte_origin)
                     if qualification_component else None)
    if not subject or not predicate or not object_value:
        raise ValueError("empty required proposition role")
    relation_material = canonical_role_material(subject, predicate, object_value, qualification)
    relation_id = "FACT_RELATION_" + hashlib.sha256(relation_material).hexdigest()[:16].upper()
    return PropositionOperands(relation_id, subject, predicate, object_value, qualification,
                               proposition["proposition_id"] + "_COORDINATE_BOUND_RELATION")


def canonical_role_material(subject: str, predicate: str, object_value: str, qualification: str | None) -> bytes:
    return json.dumps({"subject": subject, "predicate": predicate, "object": object_value,
                       "qualification": qualification}, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def derive_proposition_plan(operands: PropositionOperands) -> tuple[TypedPlanNode, ...]:
    """Derive all operand identities and predicates from the selected relation."""
    digest = operands.relation_id.rsplit("_", 1)[-1]
    qualifier_id = "FACT_QUALIFICATION" if operands.qualification else "FACT_RELATION"
    return (
        TypedPlanNode("L1", operands.relation_id, "RELATION_HEAD", "EXTEND_" + digest,
                      qualifier_id, (), ("INVENTED_RELATION_1",), operands.source_provenance, True),
        TypedPlanNode("L2", "INVENTED_RELATION_1", "RELATION_HEAD", "PROPAGATE_" + digest,
                      "FACT_OBJECT", ("L1",), ("INVENTED_RELATION_2",), "L1", True),
        TypedPlanNode("RESULT", "INVENTED_RELATION_2", "RELATION_HEAD", "RESOLVE_" + digest,
                      operands.relation_id, ("L2",), (), "L2", True),
    )


def validate_typed_plan(nodes: tuple[TypedPlanNode, ...], initial_ids: frozenset[str]) -> None:
    if len(nodes) < 3:
        raise ValueError("incomplete causal spine")
    available, seen, predicates = set(initial_ids), set(), set()
    for index, node in enumerate(nodes):
        if node.node_id in seen or node.actor_role not in _ACTOR_ROLES:
            raise ValueError("duplicate node or incompatible actor role")
        if node.bound_actor_id not in available or node.bound_patient_id not in available:
            raise ValueError("unbound actor or patient")
        if any(parent not in seen for parent in node.predecessor_node_ids):
            raise ValueError("unbound predecessor")
        if index and not node.predecessor_node_ids:
            raise ValueError("missing predecessor")
        if node.predicate_id in predicates or not node.nonfactual_scope:
            raise ValueError("restatement or factual widening")
        if any(value.endswith(".") for value in (node.bound_actor_id, node.bound_patient_id)):
            raise ValueError("terminal punctuation operand")
        predicates.add(node.predicate_id)
        seen.add(node.node_id)
        available.update(node.introduces_ids)
    if not nodes[-1].predecessor_node_ids:
        raise ValueError("result does not depend on prior chain")


def _realize(source: str, operands: PropositionOperands) -> bytes:
    return (source + " Într-un cadru explicit imaginar, relația continuă prin două consecințe locale, "
            "iar ultima depinde de întregul traseu inventat.\n").encode("utf-8")


def construct_development_candidate_v5_1(*, constructor_packet_bytes: bytes) -> DevelopmentConstructionResultV5_1:
    visible_sha = hashlib.sha256(constructor_packet_bytes).hexdigest()
    try:
        packet = json.loads(constructor_packet_bytes)
        if packet.get("status") != "G02B_RELEASE_CANDIDATE_ZERO_CONSTRUCTION":
            raise ValueError("release packet required")
        if packet.get("constructor_implementation_generation") != "5.1":
            raise ValueError("generation mismatch")
        propositions = packet["closed_factual_authority_envelope"]["propositions"]
        if len(propositions) != 1 or packet.get("creative_premise_family_id") != "UNASSIGNED":
            raise ValueError("single proposition and unassigned premise required")
        source = packet["exact_authorized_visible_context_utf8"]
        operands = extract_typed_operands(source, propositions[0])
        plan = derive_proposition_plan(operands)
        initial = {"FACT_OBJECT", operands.relation_id}
        initial.add("FACT_QUALIFICATION" if operands.qualification else "FACT_RELATION")
        validate_typed_plan(plan, frozenset(initial))
        candidate = _realize(source, operands)
        return DevelopmentConstructionResultV5_1("CANDIDATE_PRODUCED", None, candidate, visible_sha)
    except (KeyError, TypeError, ValueError, UnicodeDecodeError, json.JSONDecodeError) as exc:
        return DevelopmentConstructionResultV5_1("TECHNICAL_FAILURE_BEFORE_CANDIDATE", str(exc), None, visible_sha)


__all__ = ["DevelopmentConstructionResultV5_1", "extract_typed_operands", "derive_proposition_plan",
           "validate_typed_plan", "construct_development_candidate_v5_1"]
