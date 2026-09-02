"""Design-only validator for the source-blind V2 relation contract.

It admits and activates nothing.  It exists so the frozen design can prove
that candidate-specific evidence is required and that relation-class switching
cannot weaken the applicable checks.
"""
from __future__ import annotations

RELATIONS = {
    "CAUSAL": ("causal_dependency", "exact_result"),
    "TRIGGER": ("causal_dependency", "exact_result"),
    "PHYSICAL_ACTION": ("semantic_authority", "exact_result"),
    "STATE_TRANSITION": ("causal_dependency", "exact_result"),
    "PROCEDURAL": ("procedure_authority", "exact_result"),
    "NORMATIVE_AUTHORIZATION": ("normative_authority", "normative_authority"),
    "NORMATIVE_OBLIGATION": ("normative_authority", "normative_authority"),
    "LOGICAL_INFERENCE": ("inference_rule", "premise"),
    "REPRESENTATIONAL": ("representation_convention", "referential"),
    "RECORDING_EVIDENTIARY": ("evidentiary_provenance", "evidentiary"),
    "MEASUREMENT": ("measurement_method", "evidentiary"),
    "CLASSIFICATION_CONSTITUTIVE": ("classification_criterion", "criterion"),
    "INFORMATION_TRANSFER": ("transfer_provenance", "content_channel"),
    "TEMPORAL": ("temporal_ordering", "temporal_reference"),
    "MOVEMENT_LOCATION": ("semantic_authority", "exact_result"),
    "OBSERVATION_PERCEPTION": ("evidentiary_provenance", "evidentiary"),
    "COMPARISON_VERIFICATION": ("classification_criterion", "criterion"),
}

P13_NEGATIVE_CODES = {
    "PROPOSITION_ACTIVATES_TIME": "OPERAND_AFFORDANCE_MISMATCH",
    "ELIGIBILITY_WITHOUT_AUTHORITY": "AUTHORITY_PROVENANCE_MISSING",
    "RECORD_CREATES_OBLIGATION": "NORMATIVE_AUTHORITY_MISSING",
    "LEXICAL_CONTINUITY_AS_CAUSALITY": "CAUSAL_DEPENDENCY_MISSING",
    "PLANNER_AUTHORED_LICENSE": "TRUST_DOMAIN_SELF_AUTHORIZATION",
    "SELF_VALIDATING_NECESSITY": "EVIDENCE_DEPENDS_ON_CANDIDATE",
    "ARBITRARY_TERMINAL": "TERMINAL_LICENSE_MISSING",
}

def validate_design_witness(witness: dict) -> tuple[str, ...]:
    """Return candidate-specific blockers; empty means design-satisfiable only."""
    blockers: list[str] = []
    relation = witness.get("relation_class")
    if relation not in RELATIONS:
        return ("UNKNOWN_RELATION_CLASS",)
    evidence_kind, continuity = RELATIONS[relation]
    evidence = witness.get("evidence", {})
    if evidence.get("relation_class") != relation:
        blockers.append("EVIDENCE_RELATION_CLASS_BINDING_MISMATCH")
    if evidence.get("kind") != evidence_kind:
        blockers.append("RELATION_CLASS_EVIDENCE_MISMATCH")
    if not evidence.get("identity") or not evidence.get("provenance_identity"):
        blockers.append("EVIDENCE_PROVENANCE_MISSING")
    if evidence.get("owner") in {"RULE_AUTHOR", "PLANNER"}:
        blockers.append("TRUST_DOMAIN_SELF_AUTHORIZATION")
    if evidence.get("depends_on_candidate") is not False:
        blockers.append("EVIDENCE_DEPENDS_ON_CANDIDATE")
    if witness.get("continuity", {}).get("kind") != continuity:
        blockers.append("RELATION_CLASS_CONTINUITY_MISMATCH")
    if not witness.get("operands_typed") or not witness.get("roles_compatible"):
        blockers.append("OPERAND_OR_ROLE_INVALID")
    if not witness.get("claimed_result_licensed"):
        blockers.append("CLAIMED_RESULT_NOT_LICENSED")
    # Multiple results are allowed; the selected one still needs a contrast test.
    if not witness.get("arbitrary_substitution_rejected"):
        blockers.append("ARBITRARY_SUBSTITUTION_NOT_REJECTED")
    terminal = witness.get("terminal")
    if terminal and not all(terminal.get(k) for k in ("authority", "continuity", "licensed_result", "non_arbitrary")):
        blockers.append("TERMINAL_LICENSE_MISSING")
    return tuple(dict.fromkeys(blockers))

def detect_universal_rejection(results: dict[str, tuple[str, ...]]) -> bool:
    """True when every supported positive witness is rejected."""
    return set(results) == set(RELATIONS) and all(results.values())
