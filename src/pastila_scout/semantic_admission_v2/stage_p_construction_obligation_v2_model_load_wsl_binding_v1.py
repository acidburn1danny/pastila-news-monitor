"""Launch-forbidden canonical WSL binding for the load-only Linux supervisor."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from pastila_scout.wsl_execution_v1 import (
    WslInvocationV1, canonical_model_profile_v1,
    windows_path_to_wsl_v1,
)
from pastila_scout.wsl_execution_v1_1 import WslExecutionBoundaryV1_1

from .stage_p_construction_obligation_v2_model_load_authority_contract_v1 import (
    parse_load_only_authority_v1,
)
from .stage_p_construction_obligation_v2_model_load_only_candidate_v1_5 import (
    LOAD_ONLY_CANDIDATE_IDENTITY,
)
from .stage_p_construction_obligation_v2_model_load_policy_gate_v1 import (
    canonical_observed_model_load_policy_v1, validate_model_load_policy_gate_v1,
)


WSL_BINDING_IDENTITY = "ffbcad26400ed75d45d543258aaae54bf46291cb539a1f424aa7ce5dd2bdcfca"
SUPERVISOR_RELATIVE = Path("src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_model_load_linux_supervisor_v1.py")
SUPERVISOR_SOURCE_SHA256 = "4b118d5f74be59ea12f59cbad3c68f36a39c5fe6311e5895744d860bd9ae1531"


@dataclass(frozen=True, slots=True)
class PreparedLoadOnlyWslInvocationV1:
    invocation: WslInvocationV1
    authority_receipt_identity: str


def build_load_only_wsl_invocation_v1(
    *, project_root: Path, policy_receipt_path: Path,
    authority_receipt_path: Path, lifecycle_root: Path,
    boundary: WslExecutionBoundaryV1_1,
) -> PreparedLoadOnlyWslInvocationV1:
    if type(boundary) is not WslExecutionBoundaryV1_1 or boundary.profile != canonical_model_profile_v1(with_pydantic_bridge=True):
        raise TypeError("MODEL_LOAD_CANONICAL_WSL_BOUNDARY_REQUIRED")
    expected_policy = validate_model_load_policy_gate_v1(
        observed=canonical_observed_model_load_policy_v1())
    if policy_receipt_path.read_bytes() != expected_policy:
        raise ValueError("MODEL_LOAD_POLICY_RECEIPT_MISMATCH")
    authority = parse_load_only_authority_v1(
        raw_receipt=authority_receipt_path.read_bytes(),
        expected_load_candidate_identity=LOAD_ONLY_CANDIDATE_IDENTITY)
    supervisor = project_root.resolve(strict=True) / SUPERVISOR_RELATIVE
    if (not supervisor.is_file() or
            hashlib.sha256(supervisor.read_bytes()).hexdigest() != SUPERVISOR_SOURCE_SHA256):
        raise ValueError("MODEL_LOAD_SUPERVISOR_SOURCE_DRIFT")
    invocation = boundary.build_invocation(
        consumer_id="construction-obligation-v2-load-only-v1",
        authority_reference=authority.authority_receipt_identity,
        arguments=(windows_path_to_wsl_v1(supervisor),
                   windows_path_to_wsl_v1(policy_receipt_path.resolve(strict=True)),
                   windows_path_to_wsl_v1(authority_receipt_path.resolve(strict=True)),
                   windows_path_to_wsl_v1(lifecycle_root.resolve(strict=True))),
    )
    return PreparedLoadOnlyWslInvocationV1(invocation, authority.authority_receipt_identity)


__all__ = ("PreparedLoadOnlyWslInvocationV1", "SUPERVISOR_RELATIVE",
           "SUPERVISOR_SOURCE_SHA256",
           "WSL_BINDING_IDENTITY", "build_load_only_wsl_invocation_v1")
