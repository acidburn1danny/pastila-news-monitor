from __future__ import annotations

from dataclasses import replace
import pytest

from pastila_scout.humor_batch2_development_constructor_v5_3_3_release_path import FrozenSurfaceRoleRule
from pastila_scout.humor_batch2_development_constructor_v5_4_integration import (
    FrozenIntegratedAuthorityV54, QualifiedRuntimeBindingsV54, close_integrated_authority,
    conditional_integrated_emit, execute_zero_family_path,
)
from pastila_scout.humor_batch2_development_constructor_v5_4_semantic_licensing import (
    ProposedRelation, RuleOrigin, SemanticOperand, TrustedSemanticRule, semantic_rule_identity,
)


def frozen_authority() -> FrozenIntegratedAuthorityV54:
    operands = (
        SemanticOperand("timer", "TIMER", frozenset({"TRIGGER"}), frozenset({"FIRE"}), frozenset({"P"})),
        SemanticOperand("alarm", "ALARM", frozenset({"TRIGGERABLE"}), frozenset({"RING"}), frozenset({"P"})),
    )
    rule = TrustedSemanticRule("timer-rule", RuleOrigin.FROZEN_GENERIC_ONTOLOGY, "TRIGGERS",
        frozenset({"TIMER"}), frozenset({"ALARM"}), frozenset({"TRIGGER"}), frozenset({"TRIGGERABLE"}),
        frozenset({"FIRE"}), frozenset({"RING"}), "EVENT", frozenset({"RESULT"}), frozenset(), frozenset())
    relation = ProposedRelation("L1", None, "TRIGGERS", "timer", "alarm", "ringing", "timer-rule", True)
    roles = tuple(FrozenSurfaceRoleRule("L1", role, identity, form, (form,)) for role, identity, form in (
        ("ACTOR", "timer", "Timerul"), ("PREDICATE", "TRIGGERS", "pornește"),
        ("PATIENT", "alarm", "alarma"), ("PRODUCED", "ringing", "soneria")))
    return FrozenIntegratedAuthorityV54("authority", "implementation", "binding", "span", "denyset", "alignment",
        "contract", "provider", "observer", "emitter",
        operands, (relation,), (rule,), frozenset({semantic_rule_identity(rule)}), frozenset(), frozenset({"relations"}), roles)


def bindings() -> QualifiedRuntimeBindingsV54:
    return QualifiedRuntimeBindingsV54("implementation", "provider", "observer", "emitter", "contract")


def test_integrated_zero_family_path_preserves_clause_only_byte_authority():
    closed = close_integrated_authority(frozen_authority(), bindings=bindings())
    surface, receipt = execute_zero_family_path(closed=closed,
        provider_payload={"clause": "Timerul pornește alarma și produce soneria."})
    assert surface.decode() == "Timerul pornește alarma și produce soneria."
    assert receipt.byte_receipt.semantic_conformance == "PASS_ACTUAL_SURFACE_SEMANTIC_CONFORMANCE"


@pytest.mark.parametrize("field", ["rules", "ontology", "roles", "affordances", "predicate_signatures", "necessity"])
def test_integration_rejects_planner_evidence_fields(field):
    with pytest.raises(ValueError, match="attempts to author"):
        close_integrated_authority(replace(frozen_authority(), planner_payload_keys=frozenset({field})), bindings=bindings())


def test_observer_mapping_must_match_independently_licensed_plan():
    authority = frozen_authority()
    bad = tuple(replace(item, semantic_identity="planner-role") if item.role == "ACTOR" else item
                for item in authority.role_rules)
    with pytest.raises(ValueError, match="drift"):
        close_integrated_authority(replace(authority, role_rules=bad), bindings=bindings())


def test_provider_remains_exactly_clause_only():
    closed = close_integrated_authority(frozen_authority(), bindings=bindings())
    with pytest.raises(ValueError, match="exactly"):
        execute_zero_family_path(closed=closed, provider_payload={"clause": "x", "roles": []})


@pytest.mark.parametrize("kind", ["PROPOSITION", "TEMPORAL_MOMENT", "STATUS", "LOG", "ABSTRACT_STATE"])
def test_p13_topology_changed_vocabulary_cannot_gain_agentive_affordance(kind):
    authority = frozen_authority()
    changed = replace(authority.authority_operands[0], entity_class=kind)
    with pytest.raises(ValueError, match="entity class"):
        close_integrated_authority(replace(authority, authority_operands=(changed, authority.authority_operands[1])), bindings=bindings())


def test_omitted_anchor_relation_fails_closed():
    authority = frozen_authority()
    with pytest.raises(ValueError, match="empty"):
        close_integrated_authority(replace(authority, proposed_relations=()), bindings=bindings())


def test_runtime_implementation_identity_skew_fails_before_provider():
    with pytest.raises(ValueError, match="identity skew"):
        close_integrated_authority(frozen_authority(), bindings=replace(bindings(), implementation_identity="stale"))


@pytest.mark.parametrize("field", ["provider_identity", "observer_identity", "emitter_identity", "contract_identity"])
def test_each_runtime_component_identity_is_exactly_bound(field):
    with pytest.raises(ValueError, match="identity skew"):
        close_integrated_authority(replace(frozen_authority(), **{field: "skew"}), bindings=bindings())


def test_receipt_from_different_licensed_closure_cannot_emit():
    closed = close_integrated_authority(frozen_authority(), bindings=bindings())
    surface, receipt = execute_zero_family_path(closed=closed,
        provider_payload={"clause": "Timerul pornește alarma și produce soneria."})
    other = replace(closed, closure_identity="different-closure")
    with pytest.raises(ValueError, match="licensed closure"):
        conditional_integrated_emit(closed=other, surface_bytes=surface, receipt=receipt)
