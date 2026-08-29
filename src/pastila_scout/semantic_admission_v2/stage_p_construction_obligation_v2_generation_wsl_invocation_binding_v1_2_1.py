"""Build-only WSL invocation binding for the V1.2.1 Linux runner."""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

from pastila_scout.wsl_execution_v1 import WslInvocationV1, canonical_model_profile_v1, windows_path_to_wsl_v1
from pastila_scout.wsl_execution_v1_1 import WslExecutionBoundaryV1_1

from .stage_p_construction_obligation_v2_generation_authority_preload_v1_2_1 import AUTHORITY_PRELOAD_IDENTITY, parse_generation_authority_v1_2_1
from .stage_p_construction_obligation_v2_generation_execution_policy_gate_v1 import canonical_observed_generation_execution_policy_v1, validate_generation_execution_policy_gate_v1
from .stage_p_construction_obligation_v2_generation_wsl_invocation_binding_v1_1 import CANONICAL_BRIDGE_PROFILE_IDENTITY, OUTER_TIMEOUT_SECONDS, SYSTEM_PROMPT_SHA256, _file, _new_root
from .stage_p_construction_obligation_v2_linux_generation_runner_v1_2_1 import LINUX_GENERATION_RUNNER_IDENTITY
from .stage_p_construction_obligation_v2_runner_protocol_codec_v1 import parse_runner_request_v1

GENERATION_WSL_INVOCATION_BINDING_IDENTITY_FIELDS = (
    "construction-obligation-v2-generation-wsl-invocation-binding-v1.2.1",
    "runner-identity:" + LINUX_GENERATION_RUNNER_IDENTITY,
    "host-executor:v1.2.1",
    "prepared-invocation-type:v1.2.1",
    "authority-parser:v1.2.1-only",
    "execution-plan:canonical-byte-bound",
    "outer-timeout:1260",
)
GENERATION_WSL_INVOCATION_BINDING_IDENTITY = hashlib.sha256(
    "\n".join(GENERATION_WSL_INVOCATION_BINDING_IDENTITY_FIELDS).encode()
).hexdigest()
RUNNER_RELATIVE = Path("src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_linux_generation_runner_v1_2_1.py")
RUNNER_MODULE = "pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_linux_generation_runner_v1_2_1"
RUNNER_SOURCE_SHA256 = "8ec2679d84b11ba3f39598473a1fb9264741683bbbfc9e2736c889b09e851853"


@dataclass(frozen=True, slots=True)
class PreparedGenerationWslInvocationV1_2_1:
    binding_identity: str
    invocation_instance_identity: str
    invocation: WslInvocationV1
    authority_preload_identity: str
    authority_receipt_identity: str
    wsl_binding_identity: str
    command_identity: str
    packet_identity: str
    provider_request_id: str
    source_context_identity: str
    runner_request_sha256: str
    policy_receipt_path: Path
    authority_receipt_path: Path
    runner_request_path: Path
    system_prompt_path: Path
    outer_evidence_root: Path
    linux_evidence_root: Path
    evidence_root_identity: str
    timeout_seconds: float


def build_generation_wsl_invocation_v1_2_1(
    *, project_root: Path, policy_receipt_path: Path, authority_receipt_path: Path,
    runner_request_path: Path, system_prompt_path: Path,
    outer_evidence_root: Path, packet_identity: str, evidence_root_identity: str,
    boundary: WslExecutionBoundaryV1_1,
) -> PreparedGenerationWslInvocationV1_2_1:
    if type(boundary) is not WslExecutionBoundaryV1_1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_CANONICAL_WSL_V1_1_REQUIRED")
    profile = canonical_model_profile_v1(with_pydantic_bridge=True)
    if boundary.profile != profile or boundary.profile.identity != CANONICAL_BRIDGE_PROFILE_IDENTITY:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_WSL_PROFILE_IDENTITY_MISMATCH")
    root = project_root.resolve(strict=True)
    runner = root / RUNNER_RELATIVE
    if not runner.is_file() or hashlib.sha256(runner.read_bytes()).hexdigest() != RUNNER_SOURCE_SHA256:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_LINUX_RUNNER_V1_2_SOURCE_DRIFT")
    policy = _file(policy_receipt_path, "POLICY")
    authority_path = _file(authority_receipt_path, "AUTHORITY")
    request_path = _file(runner_request_path, "RUNNER_REQUEST")
    prompt = _file(system_prompt_path, "SYSTEM_PROMPT")
    expected = validate_generation_execution_policy_gate_v1(observed=canonical_observed_generation_execution_policy_v1())
    if policy.read_bytes() != expected:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_GENERATION_POLICY_RECEIPT_MISMATCH")
    if hashlib.sha256(prompt.read_bytes()).hexdigest() != SYSTEM_PROMPT_SHA256:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_SYSTEM_PROMPT_IDENTITY_MISMATCH")
    raw_request = request_path.read_bytes()
    request = parse_runner_request_v1(raw_request=raw_request)
    if not _identity(packet_identity) or not _identity(evidence_root_identity):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_PACKET_OR_EVIDENCE_IDENTITY_INVALID")
    authority = parse_generation_authority_v1_2_1(
        raw_receipt=authority_path.read_bytes(),
        expected_host_payload_sha256=request.host_payload_sha256,
        expected_runner_request_sha256=hashlib.sha256(raw_request).hexdigest(),
        expected_provider_request_id=request.provider_request_id,
        expected_source_context_identity=request.source_context_identity,
    )
    outer = _new_root(outer_evidence_root)
    linux = outer / "linux-generation"
    invocation = boundary.build_invocation(
        consumer_id="construction-obligation-v2-generation-v1-2-1",
        authority_reference=authority.authority_receipt_identity,
        arguments=("-m", RUNNER_MODULE, windows_path_to_wsl_v1(policy),
                   windows_path_to_wsl_v1(authority_path), windows_path_to_wsl_v1(request_path),
                   windows_path_to_wsl_v1(prompt), windows_path_to_wsl_v1(linux)),
    )
    expected_evidence_identity = hashlib.sha256("\n".join((
        "STAGE_P_CONSTRUCTION_OBLIGATION_V2_CASE01_V1_2_1_IDENTITY_ISOLATED_EVIDENCE_ROOT",
        request.source_context_identity, invocation.command_identity, str(outer),
    )).encode()).hexdigest()
    if evidence_root_identity != expected_evidence_identity:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_EVIDENCE_ROOT_IDENTITY_MISMATCH")
    material = (
        "STAGE_P_CONSTRUCTION_OBLIGATION_V2_GENERATION_WSL_INVOCATION_INSTANCE_V1_2_1",
        GENERATION_WSL_INVOCATION_BINDING_IDENTITY, invocation.command_identity,
        authority.authority_receipt_identity, hashlib.sha256(raw_request).hexdigest(),
        packet_identity, request.provider_request_id, request.source_context_identity,
        evidence_root_identity, str(outer), str(policy), str(authority_path),
        str(request_path), str(prompt), str(OUTER_TIMEOUT_SECONDS),
    )
    instance_identity = hashlib.sha256("\n".join(material).encode()).hexdigest()
    return PreparedGenerationWslInvocationV1_2_1(
        GENERATION_WSL_INVOCATION_BINDING_IDENTITY, instance_identity, invocation,
        AUTHORITY_PRELOAD_IDENTITY,
        authority.authority_receipt_identity, GENERATION_WSL_INVOCATION_BINDING_IDENTITY,
        invocation.command_identity, packet_identity, request.provider_request_id,
        request.source_context_identity, hashlib.sha256(raw_request).hexdigest(),
        policy, authority_path, request_path, prompt, outer, linux,
        evidence_root_identity, OUTER_TIMEOUT_SECONDS,
    )


def _identity(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


__all__ = (
    "GENERATION_WSL_INVOCATION_BINDING_IDENTITY",
    "GENERATION_WSL_INVOCATION_BINDING_IDENTITY_FIELDS", "OUTER_TIMEOUT_SECONDS",
    "RUNNER_MODULE", "RUNNER_RELATIVE", "RUNNER_SOURCE_SHA256",
    "PreparedGenerationWslInvocationV1_2_1",
    "build_generation_wsl_invocation_v1_2_1",
)
