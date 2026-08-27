
import pytest

from pastila_scout.desktop_v1.voice_v2_composition import compose_voice_v2_production
from pastila_scout.voice_executor_v2 import (
    BOUNDED_INITIAL_PRODUCTION_ACTIVATION_POLICY_V1,
    DeterministicVoiceExecutorV2,
    finalize_activation_policy_v1,
)


def test_exact_owner_approved_policy_is_versioned_and_installed_model_free():
    policy = BOUNDED_INITIAL_PRODUCTION_ACTIVATION_POLICY_V1
    composition = compose_voice_v2_production()
    capability = composition.executor.inspect_capability()

    assert policy.schema_version == "1"
    assert policy.active_expression_count == 3
    assert policy.active_surface_count == 3
    assert capability.activation_policy_identity == policy.policy_identity
    assert composition.application.activation_policy == policy
    assert (capability.model_calls, capability.provider_calls, capability.model_loads) == (
        0,
        0,
        0,
    )


def test_policy_contains_only_exact_approved_tuples():
    policy = BOUNDED_INITIAL_PRODUCTION_ACTIVATION_POLICY_V1
    assert {
        (entry.expression_identity, entry.surface_identity)
        for entry in policy.entries
    } == {
        ("ro-expression-v1:65f9b0c32e8e886b8d0f", "SURFACE_BOUNDED_POOL_02_V1"),
        ("ro-expression-v1:1068794b4bf34c8914dc", "SURFACE_BOUNDED_POOL_01_V1"),
        ("ro-expression-v1:0e6562965022d3dd391f", "SURFACE_BOUNDED_POOL_03_V1"),
    }


@pytest.mark.parametrize(
    "field",
    ["eligibility_spec_identity", "relationship_scope_identity"],
)
def test_executor_rejects_governance_identity_drift(field):
    policy = BOUNDED_INITIAL_PRODUCTION_ACTIVATION_POLICY_V1
    first = policy.entries[0]
    changed = first.model_copy(update={field: "sha256:" + "f" * 64})
    drifted = finalize_activation_policy_v1(
        policy.model_copy(
            update={"entries": (changed,) + policy.entries[1:]}
        )
    )

    with pytest.raises(ValueError, match="governance identity mismatch"):
        DeterministicVoiceExecutorV2(activation_policy=drifted)


def test_policy_round_trip_preserves_identity_and_entry_order():
    policy = BOUNDED_INITIAL_PRODUCTION_ACTIVATION_POLICY_V1
    loaded = type(policy).model_validate_json(policy.model_dump_json())
    assert loaded == policy
    assert loaded.policy_identity == policy.policy_identity
