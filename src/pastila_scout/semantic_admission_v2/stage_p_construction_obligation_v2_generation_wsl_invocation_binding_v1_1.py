"""Build-only canonical WSL invocation for the V2 Linux generation runner."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from pastila_scout.wsl_execution_v1 import (
    WslInvocationV1,
    canonical_model_profile_v1,
    windows_path_to_wsl_v1,
)
from pastila_scout.wsl_execution_v1_1 import WslExecutionBoundaryV1_1

from .stage_p_construction_obligation_v2_generation_authority_preload_v1_1 import (
    parse_generation_authority_v1_1,
)
from .stage_p_construction_obligation_v2_generation_execution_policy_gate_v1 import (
    canonical_observed_generation_execution_policy_v1,
    validate_generation_execution_policy_gate_v1,
)
from .stage_p_construction_obligation_v2_runner_protocol_codec_v1 import (
    parse_runner_request_v1,
)

GENERATION_WSL_INVOCATION_BINDING_IDENTITY = (
    "c7a09557517e2a762d1d60738bc2c073be458533769bd0a968f25930fe3b6843"
)
RUNNER_IDENTITY = "ed9303593dea53b9375913e3cb1640cdb11f2e347299435532f7e3935bf755da"
RUNNER_RELATIVE = Path(
    "src/pastila_scout/semantic_admission_v2/"
    "stage_p_construction_obligation_v2_linux_generation_runner_v1_1.py"
)
RUNNER_MODULE = (
    "pastila_scout.semantic_admission_v2."
    "stage_p_construction_obligation_v2_linux_generation_runner_v1_1"
)
RUNNER_SOURCE_SHA256 = (
    "decf1a4aeccec35ef1d1f54cc714414f2348e11817ffc5d6eeddd844de4ed983"
)
CANONICAL_BRIDGE_PROFILE_IDENTITY = (
    "71f66b8bf20b3decb31cfe65d3d94720f9fd1d2c6500c9ef259197cbf94bc7f4"
)
SYSTEM_PROMPT_SHA256 = (
    "111bc2734343c67aab4e1a04003199b98d4955fe9579e445cd7b5d6805a9da17"
)
OUTER_TIMEOUT_SECONDS = 1260.0


@dataclass(frozen=True, slots=True)
class PreparedGenerationWslInvocationV1:
    binding_identity: str
    invocation: WslInvocationV1
    authority_receipt_identity: str
    provider_request_id: str
    source_context_identity: str
    runner_request_sha256: str
    outer_evidence_root: Path
    linux_evidence_root: Path


def build_generation_wsl_invocation_v1_1(
    *,
    project_root: Path,
    policy_receipt_path: Path,
    authority_receipt_path: Path,
    runner_request_path: Path,
    system_prompt_path: Path,
    outer_evidence_root: Path,
    boundary: WslExecutionBoundaryV1_1,
) -> PreparedGenerationWslInvocationV1:
    """Validate exact inputs and return one inert canonical invocation."""
    if type(boundary) is not WslExecutionBoundaryV1_1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_CANONICAL_WSL_V1_1_REQUIRED")
    profile = canonical_model_profile_v1(with_pydantic_bridge=True)
    if (
        boundary.profile != profile
        or boundary.profile.identity != CANONICAL_BRIDGE_PROFILE_IDENTITY
    ):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_WSL_PROFILE_IDENTITY_MISMATCH")
    root = project_root.resolve(strict=True)
    runner = root / RUNNER_RELATIVE
    if (
        not runner.is_file()
        or hashlib.sha256(runner.read_bytes()).hexdigest() != RUNNER_SOURCE_SHA256
    ):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_LINUX_RUNNER_SOURCE_DRIFT")
    policy = _file(policy_receipt_path, "POLICY")
    authority_path = _file(authority_receipt_path, "AUTHORITY")
    request_path = _file(runner_request_path, "RUNNER_REQUEST")
    prompt = _file(system_prompt_path, "SYSTEM_PROMPT")
    expected_policy = validate_generation_execution_policy_gate_v1(
        observed=canonical_observed_generation_execution_policy_v1()
    )
    if policy.read_bytes() != expected_policy:
        raise ValueError(
            "CONSTRUCTION_OBLIGATION_V2_GENERATION_POLICY_RECEIPT_MISMATCH"
        )
    if hashlib.sha256(prompt.read_bytes()).hexdigest() != SYSTEM_PROMPT_SHA256:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_SYSTEM_PROMPT_IDENTITY_MISMATCH")
    raw_request = request_path.read_bytes()
    request = parse_runner_request_v1(raw_request=raw_request)
    authority = parse_generation_authority_v1_1(
        raw_receipt=authority_path.read_bytes(),
        expected_host_payload_sha256=request.host_payload_sha256,
        expected_runner_request_sha256=hashlib.sha256(raw_request).hexdigest(),
        expected_provider_request_id=request.provider_request_id,
        expected_source_context_identity=request.source_context_identity,
    )
    outer = _new_root(outer_evidence_root)
    linux = outer / "linux-generation"
    invocation = boundary.build_invocation(
        consumer_id="construction-obligation-v2-generation-v1-1",
        authority_reference=authority.authority_receipt_identity,
        arguments=(
            "-m",
            RUNNER_MODULE,
            windows_path_to_wsl_v1(policy),
            windows_path_to_wsl_v1(authority_path),
            windows_path_to_wsl_v1(request_path),
            windows_path_to_wsl_v1(prompt),
            windows_path_to_wsl_v1(linux),
        ),
    )
    material = (
        "STAGE_P_CONSTRUCTION_OBLIGATION_V2_GENERATION_WSL_INVOCATION_INSTANCE_V1_1",
        GENERATION_WSL_INVOCATION_BINDING_IDENTITY,
        invocation.command_identity,
        authority.authority_receipt_identity,
        hashlib.sha256(raw_request).hexdigest(),
        request.provider_request_id,
        request.source_context_identity,
        str(outer),
    )
    return PreparedGenerationWslInvocationV1(
        hashlib.sha256("\n".join(material).encode()).hexdigest(),
        invocation,
        authority.authority_receipt_identity,
        request.provider_request_id,
        request.source_context_identity,
        hashlib.sha256(raw_request).hexdigest(),
        outer,
        linux,
    )


def _file(path: Path, label: str) -> Path:
    if not isinstance(path, Path) or not path.is_absolute():
        raise ValueError(f"CONSTRUCTION_OBLIGATION_V2_{label}_ABSOLUTE_PATH_REQUIRED")
    resolved = path.resolve(strict=True)
    if resolved != path or not resolved.is_file():
        raise ValueError(f"CONSTRUCTION_OBLIGATION_V2_{label}_CANONICAL_FILE_REQUIRED")
    return resolved


def _new_root(path: Path) -> Path:
    if not isinstance(path, Path) or not path.is_absolute():
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_OUTER_ROOT_ABSOLUTE_PATH_REQUIRED")
    if path.exists() or path.is_symlink():
        raise FileExistsError("CONSTRUCTION_OBLIGATION_V2_OUTER_ROOT_ALREADY_EXISTS")
    if path.parent.resolve(strict=True) != path.parent:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_OUTER_ROOT_PARENT_INVALID")
    return path


__all__ = (
    "GENERATION_WSL_INVOCATION_BINDING_IDENTITY",
    "OUTER_TIMEOUT_SECONDS",
    "RUNNER_MODULE",
    "RUNNER_RELATIVE",
    "RUNNER_SOURCE_SHA256",
    "PreparedGenerationWslInvocationV1",
    "build_generation_wsl_invocation_v1_1",
)
