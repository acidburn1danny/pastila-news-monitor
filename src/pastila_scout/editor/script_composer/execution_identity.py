"""Deterministic identities for provider-neutral Phase 3 artifacts."""

from .identity import derive_identity


def _identity(kind: str, artifact, identity_field: str) -> str:
    seed = artifact.model_dump(mode="python", exclude={identity_field})
    return derive_identity(kind, seed)


def execution_intent_identity(value) -> str:
    return _identity("generation-execution-intent", value, "execution_intent_id")


def execution_plan_identity(value) -> str:
    ordinals = {
        item.execution_unit_id: item.ordinal for item in value.ordered_execution_units
    }
    units = []
    for item in value.ordered_execution_units:
        unit = item.model_dump(
            mode="python",
            exclude={
                "execution_unit_id",
                "execution_plan_reference",
                "dependency_unit_references",
                "capability_set_reference",
                "semantic_fingerprint",
            },
        )
        unit["dependency_ordinals"] = tuple(
            ordinals.get(reference, reference)
            for reference in item.dependency_unit_references
        )
        units.append(unit)
    bindings = tuple(
        {
            **item.model_dump(
                mode="python",
                exclude={"output_binding_id", "unit_reference", "semantic_fingerprint"},
            ),
            "unit_ordinal": ordinals.get(item.unit_reference, item.unit_reference),
        }
        for item in value.expected_output_bindings
    )
    dependency_declarations = tuple(
        (
            ordinals.get(item.source_unit_reference, item.source_unit_reference),
            ordinals.get(
                item.dependency_unit_reference, item.dependency_unit_reference
            ),
        )
        for item in value.dependency_declarations
    )
    seed = {
        "contract_version": value.contract_version,
        "execution_intent_reference": value.execution_intent_reference,
        "execution_intent_fingerprint": value.execution_intent_fingerprint,
        "normalized_input_fingerprint": value.normalized_input_fingerprint,
        "units": tuple(units),
        "bindings": bindings,
        "dependency_declarations": dependency_declarations,
        "policy_references": value.policy_references,
        "authority_references": value.authority_references,
        "evidence_references": value.evidence_references,
        "retry_policy": value.retry_policy.model_dump(
            mode="python",
            exclude={"retry_policy_id", "semantic_fingerprint"},
        ),
        "failure_policy": {
            **value.failure_policy.model_dump(
                mode="python",
                exclude={
                    "failure_policy_id",
                    "semantic_fingerprint",
                    "required_output_binding_references",
                    "optional_output_binding_references",
                },
            ),
            "required_output_binding_references": tuple(
                sorted(set(value.failure_policy.required_output_binding_references))
            ),
            "optional_output_binding_references": tuple(
                sorted(set(value.failure_policy.optional_output_binding_references))
            ),
        },
        "capability_sets": value.capability_sets,
    }
    return derive_identity("generation-execution-plan", seed)


def execution_unit_identity(value) -> str:
    seed = value.model_dump(
        mode="python",
        exclude={
            "execution_unit_id",
            "semantic_fingerprint",
        },
    )
    return derive_identity("generation-execution-unit", seed)


def execution_request_identity(value) -> str:
    return _identity("generation-execution-request", value, "execution_request_id")


def execution_outcome_identity(value) -> str:
    return _identity("generation-execution-outcome", value, "execution_outcome_id")


def state_observation_identity(value) -> str:
    return _identity("generation-state-observation", value, "state_observation_id")


def capability_set_identity(value) -> str:
    return _identity("generation-capability-set", value, "capability_set_id")


def output_binding_identity(value) -> str:
    seed = value.model_dump(
        mode="python",
        exclude={"output_binding_id", "unit_reference", "semantic_fingerprint"},
    )
    return derive_identity("generation-output-binding", seed)


def retry_policy_identity(value) -> str:
    return _identity("generation-retry-policy", value, "retry_policy_id")


def failure_policy_identity(value) -> str:
    return _identity("generation-failure-policy", value, "failure_policy_id")


__all__ = tuple(
    name
    for name in globals()
    if name.endswith("_identity") and not name.startswith("_")
)
