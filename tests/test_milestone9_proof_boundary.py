from pastila_scout.milestone9_proof_boundary import (
    ARTIFACT_RETENTION_DAYS,
    POLICY,
    SCHEDULE_RULE,
    SCHEDULER_DELAY_HOURS,
    Phase,
    assert_phase_policy,
    load_policy_record,
    validate_policy_record,
)
from pathlib import Path
import copy
import pytest


def test_owner_governance_is_stable():
    assert SCHEDULE_RULE == "FIRST_UTC_HOUR_AT_LEAST_12_HOURS_AFTER_REPLACEMENT_FREEZE"
    assert ARTIFACT_RETENTION_DAYS == 30
    assert SCHEDULER_DELAY_HOURS == 24


def test_rfc3161_verification_and_transport_are_separate():
    assert POLICY[Phase.PRE_REQUEST].network_targets == ()
    assert POLICY[Phase.PRE_REQUEST].may_verify_rfc3161
    assert POLICY[Phase.POST_RESPONSE].network_targets == ()
    assert POLICY[Phase.POST_RESPONSE].may_verify_rfc3161
    assert POLICY[Phase.TRANSPORT].may_submit_rfc3161
    assert not POLICY[Phase.TRANSPORT].may_verify_rfc3161


def test_activation_cannot_submit_or_acquire_metadata():
    activation = POLICY[Phase.ACTIVATION]
    assert activation.may_request_sigstore
    assert not activation.may_submit_rfc3161
    assert not activation.may_acquire_metadata
    assert all(not policy.may_acquire_metadata for policy in POLICY.values())
    assert_phase_policy()


def test_committed_policy_matches_executable_policy():
    root = Path(__file__).parents[1]
    value = load_policy_record(root / "deployment/milestone-9-phase-policy.json")
    assert value["artifact_retention_days"] == 30


def test_policy_rejects_capability_expansion():
    root = Path(__file__).parents[1]
    value = copy.deepcopy(load_policy_record(root / "deployment/milestone-9-phase-policy.json"))
    value["phases"]["attestation_only_activation"]["may_acquire_metadata"] = True
    with pytest.raises(ValueError, match="phase-policy mismatch"):
        validate_policy_record(value)
