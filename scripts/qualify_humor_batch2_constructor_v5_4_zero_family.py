"""Execute the V5.4 path with a synthetic, non-family authority and clause."""
from __future__ import annotations

import json

from pastila_scout.humor_batch2_development_constructor_v5_3_3_release_path import FrozenSurfaceRoleRule
from pastila_scout.humor_batch2_development_constructor_v5_4_integration import (
    FrozenIntegratedAuthorityV54, QualifiedRuntimeBindingsV54,
    close_integrated_authority, execute_zero_family_path,
)
from pastila_scout.humor_batch2_development_constructor_v5_4_semantic_licensing import (
    ProposedRelation, RuleOrigin, SemanticOperand, TrustedSemanticRule, semantic_rule_identity,
)


def qualify() -> dict[str, object]:
    operands = (
        SemanticOperand("timer", "TIMER", frozenset({"TRIGGER"}), frozenset({"FIRE"}), frozenset({"SYNTHETIC"})),
        SemanticOperand("alarm", "ALARM", frozenset({"TRIGGERABLE"}), frozenset({"RING"}), frozenset({"SYNTHETIC"})),
    )
    rule = TrustedSemanticRule("timer-triggers-alarm", RuleOrigin.FROZEN_GENERIC_ONTOLOGY, "TRIGGERS",
        frozenset({"TIMER"}), frozenset({"ALARM"}), frozenset({"TRIGGER"}), frozenset({"TRIGGERABLE"}),
        frozenset({"FIRE"}), frozenset({"RING"}), "RINGING_EVENT", frozenset({"RESULT"}),
        frozenset(), frozenset())
    relation = ProposedRelation("S1", None, "TRIGGERS", "timer", "alarm", "ringing",
                                "timer-triggers-alarm", True)
    forms = (("ACTOR", "timer", "Cronometrul"), ("PREDICATE", "TRIGGERS", "declanșează"),
             ("PATIENT", "alarm", "alarma"), ("PRODUCED", "ringing", "semnalul"))
    roles = tuple(FrozenSurfaceRoleRule("S1", role, identity, form, (form,))
                  for role, identity, form in forms)
    authority = FrozenIntegratedAuthorityV54(
        "synthetic-authority", "v5.4-qualified-implementation", "synthetic-binding", "synthetic-span",
        "synthetic-denyset", "frozen-alignment", "v5.4-contract", "clause-provider",
        "byte-observer", "conditional-emitter", operands, (relation,), (rule,),
        frozenset({semantic_rule_identity(rule)}), frozenset(), frozenset({"relations"}), roles)
    bindings = QualifiedRuntimeBindingsV54("v5.4-qualified-implementation", "clause-provider",
                                           "byte-observer", "conditional-emitter", "v5.4-contract")
    closed = close_integrated_authority(authority, bindings=bindings)
    surface, receipt = execute_zero_family_path(closed=closed,
        provider_payload={"clause": "Cronometrul declanșează alarma și produce semnalul."})
    return {
        "verdict": "PASS_SYNTHETIC_ZERO_FAMILY_EXECUTABLE_PATH",
        "closure_identity": closed.closure_identity,
        "rule_identity": semantic_rule_identity(rule),
        "surface_sha256": receipt.byte_receipt.surface_sha256,
        "surface_byte_length": len(surface),
        "observed_roles": len(receipt.byte_receipt.observed_roles),
        "trusted_receipt_identity": receipt.receipt_identity,
        "provider_fields": ["clause"],
        "real_family": False,
        "model_visible": False,
        "positive_coverage": False,
    }


if __name__ == "__main__":
    print(json.dumps(qualify(), sort_keys=True, separators=(",", ":")))
