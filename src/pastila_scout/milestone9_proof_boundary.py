"""Stable phase and capability policy for the Core V2 Milestone 9 proof chain."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from pathlib import Path
from typing import Mapping


SCHEDULE_RULE = "FIRST_UTC_HOUR_AT_LEAST_12_HOURS_AFTER_REPLACEMENT_FREEZE"
ARTIFACT_RETENTION_DAYS = 30
SCHEDULER_DELAY_HOURS = 24


class Phase(Enum):
    FREEZE = "freeze"
    PRE_REQUEST = "pre_request_validation"
    TRANSPORT = "rfc3161_transport"
    POST_RESPONSE = "post_response_verification"
    ACTIVATION = "attestation_only_activation"


@dataclass(frozen=True)
class CapabilityPolicy:
    network_targets: tuple[str, ...]
    may_verify_rfc3161: bool = False
    may_submit_rfc3161: bool = False
    may_acquire_metadata: bool = False
    may_request_sigstore: bool = False


POLICY = {
    Phase.FREEZE: CapabilityPolicy(()),
    Phase.PRE_REQUEST: CapabilityPolicy((), may_verify_rfc3161=True),
    Phase.TRANSPORT: CapabilityPolicy(
        ("http://timestamp.digicert.com",), may_submit_rfc3161=True
    ),
    Phase.POST_RESPONSE: CapabilityPolicy((), may_verify_rfc3161=True),
    Phase.ACTIVATION: CapabilityPolicy(
        ("github-oidc", "fulcio", "rekor"), may_request_sigstore=True
    ),
}


def assert_phase_policy() -> None:
    """Fail closed if a phase gains a conflicting or metadata capability."""
    if set(POLICY) != set(Phase):
        raise ValueError("incomplete Milestone 9 phase policy")
    for phase, policy in POLICY.items():
        if policy.may_acquire_metadata:
            raise ValueError(f"metadata acquisition reachable in {phase.value}")
        if policy.may_verify_rfc3161 and policy.network_targets:
            raise ValueError(f"RFC-3161 verification is not offline in {phase.value}")
        if policy.may_submit_rfc3161 != (phase is Phase.TRANSPORT):
            raise ValueError("RFC-3161 transport capability escaped its phase")
        if policy.may_request_sigstore != (phase is Phase.ACTIVATION):
            raise ValueError("Sigstore capability escaped activation")


assert_phase_policy()


def validate_policy_record(value: Mapping[str, object]) -> None:
    """Validate the committed policy without accepting extra capabilities."""
    expected_phases = {
        phase.value: {
            "network_targets": list(policy.network_targets),
            "may_verify_rfc3161": policy.may_verify_rfc3161,
            "may_submit_rfc3161": policy.may_submit_rfc3161,
            "may_acquire_metadata": policy.may_acquire_metadata,
            "may_request_sigstore": policy.may_request_sigstore,
        }
        for phase, policy in POLICY.items()
    }
    expected = {
        "schema": "PASTILA_MILESTONE_9_PHASE_POLICY_V1",
        "schedule_rule": SCHEDULE_RULE,
        "scheduler_delay_hours": SCHEDULER_DELAY_HOURS,
        "artifact_retention_days": ARTIFACT_RETENTION_DAYS,
        "phases": expected_phases,
    }
    if value != expected:
        raise ValueError("Milestone 9 phase-policy mismatch")


def load_policy_record(path: Path) -> Mapping[str, object]:
    if path.is_symlink():
        raise ValueError("Milestone 9 phase-policy symlink")
    raw = path.read_bytes()
    if not raw.endswith(b"\n") or raw.count(b"\n") != 1:
        raise ValueError("Milestone 9 phase-policy serialization")
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise ValueError("Milestone 9 phase-policy schema")
    validate_policy_record(value)
    return value
