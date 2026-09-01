"""Pathless DEVELOPMENT constructor V5 with fail-closed typed-plan validation.

The module consumes canonical packet bytes only. It performs no filesystem,
environment, process, network, model, taxonomy, or repository access. Every
invented dependency is represented and validated as a typed abstract node
before any surface realization is permitted.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any


@dataclass(frozen=True, slots=True)
class DevelopmentConstructionResultV5:
    terminal_classification: str
    failure_code: str | None
    candidate_surface_utf8: bytes | None
    constructor_visible_sha256: str


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


_ACTOR_ROLES = frozenset({"NOMINAL_HEAD", "RELATION_HEAD", "PROCESS_HEAD"})
_PROHIBITED_ACTOR_ROLES = frozenset({"PREPOSITIONAL_PHRASE", "ADVERBIAL", "PURPOSE_PHRASE"})


def _failure(code: str, visible_sha: str) -> DevelopmentConstructionResultV5:
    return DevelopmentConstructionResultV5(
        "TECHNICAL_FAILURE_BEFORE_CANDIDATE", code, None, visible_sha
    )


def _clean(value: str) -> str:
    return " ".join(value.strip().split())


def _component_text(
    source: str,
    component: dict[str, Any],
    *,
    character_origin: int,
    byte_origin: int,
) -> str:
    start, end = component["character_coordinates"]
    start -= character_origin
    end -= character_origin
    value = source[start:end]
    byte_start, byte_end = component["utf8_byte_coordinates"]
    byte_start -= byte_origin
    byte_end -= byte_origin
    encoded = source.encode("utf-8")
    if value.encode("utf-8") != encoded[byte_start:byte_end]:
        raise ValueError("coordinate mismatch")
    expected = component.get("span_sha256", component.get("sha256"))
    if hashlib.sha256(value.encode("utf-8")).hexdigest() != expected:
        raise ValueError("component hash mismatch")
    return _clean(value)


def _validate_plan(nodes: tuple[TypedPlanNode, ...], initial_ids: frozenset[str]) -> None:
    if len(nodes) < 3:
        raise ValueError("at least two invented links and one result are required")
    available = set(initial_ids)
    seen_nodes: set[str] = set()
    distinct_predicates: set[str] = set()
    for index, node in enumerate(nodes):
        if node.node_id in seen_nodes:
            raise ValueError("duplicate plan node")
        if node.actor_role in _PROHIBITED_ACTOR_ROLES or node.actor_role not in _ACTOR_ROLES:
            raise ValueError("actor role incompatible")
        if node.bound_actor_id not in available or node.bound_patient_id not in available:
            raise ValueError("unbound actor or patient")
        if any(predecessor not in seen_nodes for predecessor in node.predecessor_node_ids):
            raise ValueError("unbound predecessor")
        if index and not node.predecessor_node_ids:
            raise ValueError("invented link lacks predecessor")
        if any(reference.endswith(".") for reference in (node.bound_actor_id, node.bound_patient_id)):
            raise ValueError("terminal punctuation in operand identity")
        if not node.nonfactual_scope:
            raise ValueError("invented node outside nonfactual scope")
        if node.predicate_id in distinct_predicates:
            raise ValueError("restatement cannot count as a distinct link")
        distinct_predicates.add(node.predicate_id)
        seen_nodes.add(node.node_id)
        available.update(node.introduces_ids)
    if len(distinct_predicates) < 3:
        raise ValueError("incomplete distinct causal spine")
    if not set(nodes[-1].predecessor_node_ids):
        raise ValueError("result does not depend on the chain")


def _derive_plan() -> tuple[TypedPlanNode, ...]:
    return (
        TypedPlanNode(
            "L1", "FACT_RELATION", "RELATION_HEAD", "RETURN_CHECK_TO_SUBJECT",
            "FACT_SUBJECT", (), ("CHECK_PROCESS",), "P5_RELATION", True,
        ),
        TypedPlanNode(
            "L2", "FACT_RELATION", "RELATION_HEAD", "REAPPLY_RELATION",
            "FACT_SUBJECT", ("L1",), (), "L1", True,
        ),
        TypedPlanNode(
            "RESULT", "CHECK_PROCESS", "PROCESS_HEAD", "CHECK_RELATION",
            "FACT_RELATION", ("L2",), (), "L2", True,
        ),
    )


def _choice(seed: bytes, offset: int, values: tuple[str, ...]) -> str:
    return values[seed[offset % len(seed)] % len(values)]


def _realize(source: str, subject: str, seed: bytes) -> bytes:
    scope = _choice(seed, 0, ("variantă", "ipoteză", "ramură"))
    fiction = _choice(seed, 1, ("inventată", "imaginară", "fictivă"))
    relation = _choice(seed, 2, (("regula", "regulii"), ("logica", "logicii"), ("procedura", "procedurii")))
    verb = _choice(seed, 3, ("trimite", "readuce", "întoarce"))
    process = _choice(seed, 4, ("verificarea", "controlul", "revizia"))
    atoms = [
        source, "Într-o", scope, fiction + ",", relation[0], verb, process, "spre", subject + ";",
        "de", "acolo,", relation[0], "se", "aplică", "din", "nou,", "iar", process,
        "ajunge", "să", "verifice", "chiar", relation[0] + ".",
    ]
    return " ".join(atoms).encode("utf-8") + b"\n"


def construct_development_candidate_v5(
    *, constructor_packet_bytes: bytes
) -> DevelopmentConstructionResultV5:
    """Perform one in-memory attempt only after the V5 typed plan closes."""
    visible_sha = hashlib.sha256(constructor_packet_bytes).hexdigest()
    try:
        packet: dict[str, Any] = json.loads(constructor_packet_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError):
        return _failure("CONSTRUCTOR_PACKET_INVALID", visible_sha)
    if packet.get("status") != "G02B_RELEASE_CANDIDATE_ZERO_CONSTRUCTION":
        return _failure("CONSTRUCTOR_PACKET_STATUS_INVALID", visible_sha)
    if packet.get("creative_premise_family_id") != "UNASSIGNED":
        return _failure("CREATIVE_PREMISE_PREASSIGNED", visible_sha)
    if packet.get("constructor_implementation_generation") != 5:
        return _failure("CONSTRUCTOR_IMPLEMENTATION_GENERATION_MISMATCH", visible_sha)
    source = packet.get("exact_authorized_visible_context_utf8")
    propositions = packet.get("closed_factual_authority_envelope", {}).get("propositions", [])
    if not isinstance(source, str) or len(propositions) != 1:
        return _failure("EXACT_SINGLE_PROPOSITION_CONTEXT_REQUIRED", visible_sha)
    proposition = propositions[0]
    try:
        supporting_span = proposition["supporting_span"]
        character_origin = supporting_span["character_coordinates"][0]
        byte_origin = supporting_span["utf8_byte_coordinates"][0]
        supporting = _component_text(source, supporting_span, character_origin=character_origin, byte_origin=byte_origin)
        subject = _component_text(source, proposition["subject"], character_origin=character_origin, byte_origin=byte_origin)
        predicate = _component_text(source, proposition["predicate"], character_origin=character_origin, byte_origin=byte_origin)
        object_value = _component_text(source, proposition["object"], character_origin=character_origin, byte_origin=byte_origin)
    except (KeyError, TypeError, ValueError):
        return _failure("PROPOSITION_BINDING_INVALID", visible_sha)
    if _clean(source) != supporting or not supporting.endswith("."):
        return _failure("AUTHORIZED_CONTEXT_NOT_EXACT_SUPPORTING_SPAN", visible_sha)
    if not proposition.get("qualification") or "nu" not in subject.casefold():
        return _failure("CONDITIONAL_SOURCE_RELATION_REQUIRED", visible_sha)
    if not re.search(r"\bpentru\b", object_value, flags=re.IGNORECASE):
        return _failure("FORWARD_RELATION_UNAVAILABLE", visible_sha)
    plan = _derive_plan()
    try:
        _validate_plan(plan, frozenset({"FACT_SUBJECT", "FACT_RELATION", "FACT_OBJECT"}))
    except ValueError:
        return _failure("TYPED_PLAN_CLOSURE_FAILED", visible_sha)
    seed = hashlib.sha256(source.encode("utf-8")).digest()
    candidate = _realize(supporting, subject, seed)
    return DevelopmentConstructionResultV5("CANDIDATE_PRODUCED", None, candidate, visible_sha)


__all__ = ["DevelopmentConstructionResultV5", "construct_development_candidate_v5"]
