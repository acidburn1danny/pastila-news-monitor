"""Build-only WSL invocation binding for the V1.2.1 Linux runner."""
from __future__ import annotations

import hashlib
import json
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
    "packet-manifest:canonical-file-set-bound",
    "authority:non-circular-packet-command-plan-bound",
    "evidence-domain:source-context-reconstruction-bound",
    "outer-timeout:1260",
)
GENERATION_WSL_INVOCATION_BINDING_IDENTITY = hashlib.sha256(
    "\n".join(GENERATION_WSL_INVOCATION_BINDING_IDENTITY_FIELDS).encode()
).hexdigest()
RUNNER_RELATIVE = Path("src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_linux_generation_runner_v1_2_1.py")
RUNNER_MODULE = "pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_linux_generation_runner_v1_2_1"
RUNNER_SOURCE_SHA256 = "ce363e906555177c7ca17aad7f80f117309e3a3e13a24d463d65fe6c3168cea0"


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
    packet_manifest_path: Path
    system_prompt_path: Path
    outer_evidence_root: Path
    linux_evidence_root: Path
    evidence_root_identity: str
    timeout_seconds: float


def build_generation_wsl_invocation_v1_2_1(
    *, project_root: Path, policy_receipt_path: Path, authority_receipt_path: Path,
    runner_request_path: Path, system_prompt_path: Path,
    packet_manifest_path: Path, outer_evidence_root: Path,
    evidence_root_identity: str,
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
    manifest_path = _file(packet_manifest_path, "PACKET_MANIFEST")
    prompt = _file(system_prompt_path, "SYSTEM_PROMPT")
    expected = validate_generation_execution_policy_gate_v1(observed=canonical_observed_generation_execution_policy_v1())
    if policy.read_bytes() != expected:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_GENERATION_POLICY_RECEIPT_MISMATCH")
    if hashlib.sha256(prompt.read_bytes()).hexdigest() != SYSTEM_PROMPT_SHA256:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_SYSTEM_PROMPT_IDENTITY_MISMATCH")
    raw_request = request_path.read_bytes()
    request = parse_runner_request_v1(raw_request=raw_request)
    if not _identity(evidence_root_identity):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_EVIDENCE_IDENTITY_INVALID")
    outer = _new_root(outer_evidence_root)
    linux = outer / "linux-generation"
    arguments = ("-m", RUNNER_MODULE, windows_path_to_wsl_v1(policy),
                 windows_path_to_wsl_v1(authority_path), windows_path_to_wsl_v1(request_path),
                 windows_path_to_wsl_v1(prompt), windows_path_to_wsl_v1(linux))
    command_plan = boundary.build_invocation(
        consumer_id="construction-obligation-v2-generation-v1-2-1",
        authority_reference="0" * 64, arguments=arguments)
    packet_plan_identity = _derive_packet_plan_identity(
        manifest_path=manifest_path, command_plan_identity=command_plan.command_identity,
        source_context_identity=request.source_context_identity,
        outer_evidence_root=outer)
    authority = parse_generation_authority_v1_2_1(
        raw_receipt=authority_path.read_bytes(),
        expected_host_payload_sha256=request.host_payload_sha256,
        expected_runner_request_sha256=hashlib.sha256(raw_request).hexdigest(),
        expected_provider_request_id=request.provider_request_id,
        expected_source_context_identity=request.source_context_identity,
        expected_packet_plan_identity=packet_plan_identity,
        expected_command_plan_identity=command_plan.command_identity,
    )
    invocation = boundary.build_invocation(
        consumer_id="construction-obligation-v2-generation-v1-2-1",
        authority_reference=authority.authority_receipt_identity,
        arguments=arguments,
    )
    expected_evidence_identity = hashlib.sha256("\n".join((
        "STAGE_P_CONSTRUCTION_OBLIGATION_V2_CASE01_V1_2_1_SOURCE_CONTEXT_RECONSTRUCTION_BOUND_EVIDENCE_ROOT",
        request.source_context_identity, invocation.command_identity, str(outer),
    )).encode()).hexdigest()
    if evidence_root_identity != expected_evidence_identity:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_EVIDENCE_ROOT_IDENTITY_MISMATCH")
    packet_identity = _validate_packet_manifest_v1_2_1(
        manifest_path=manifest_path, invocation=invocation,
        authority_identity=authority.authority_receipt_identity,
        authority_path=authority_path, request_path=request_path,
        packet_plan_identity=packet_plan_identity,
        command_plan_identity=command_plan.command_identity,
        source_context_identity=request.source_context_identity,
        evidence_root_identity=evidence_root_identity, outer_evidence_root=outer,
    )
    material = (
        "STAGE_P_CONSTRUCTION_OBLIGATION_V2_GENERATION_WSL_INVOCATION_INSTANCE_V1_2_1",
        GENERATION_WSL_INVOCATION_BINDING_IDENTITY, invocation.command_identity,
        authority.authority_receipt_identity, hashlib.sha256(raw_request).hexdigest(),
        packet_identity, request.provider_request_id, request.source_context_identity,
        evidence_root_identity, str(outer), str(policy), str(authority_path),
        str(request_path), str(manifest_path), str(prompt), str(OUTER_TIMEOUT_SECONDS),
    )
    instance_identity = hashlib.sha256("\n".join(material).encode()).hexdigest()
    return PreparedGenerationWslInvocationV1_2_1(
        GENERATION_WSL_INVOCATION_BINDING_IDENTITY, instance_identity, invocation,
        AUTHORITY_PRELOAD_IDENTITY,
        authority.authority_receipt_identity, GENERATION_WSL_INVOCATION_BINDING_IDENTITY,
        invocation.command_identity, packet_identity, request.provider_request_id,
        request.source_context_identity, hashlib.sha256(raw_request).hexdigest(),
        policy, authority_path, request_path, manifest_path, prompt, outer, linux,
        evidence_root_identity, OUTER_TIMEOUT_SECONDS,
    )


def _identity(value: object) -> bool:
    return type(value) is str and len(value) == 64 and all(c in "0123456789abcdef" for c in value)


def _validate_packet_manifest_v1_2_1(
    *, manifest_path: Path, invocation: WslInvocationV1, authority_identity: str,
    authority_path: Path, request_path: Path, source_context_identity: str,
    packet_plan_identity: str, command_plan_identity: str,
    evidence_root_identity: str,
    outer_evidence_root: Path,
) -> str:
    raw = manifest_path.read_bytes()
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"))
    except Exception as exc:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_PACKET_MANIFEST_JSON_INVALID") from exc
    required = {
        "schema_name", "schema_version", "case_id", "source_context_identity",
        "historical_request_reused", "receipt_status", "attempts",
        "proposed_evidence_root", "evidence_root_identity",
        "evidence_root_exclusive_at_materialization", "command", "command_identity",
        "command_plan_identity", "packet_plan_identity",
        "authority_reference_if_issued", "file_sha256", "limits", "execution",
        "packet_identity",
    }
    if type(value) is not dict or set(value) != required or raw != _canonical(value):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_PACKET_MANIFEST_SHAPE_OR_BYTES_INVALID")
    body = {key: item for key, item in value.items() if key != "packet_identity"}
    packet_identity = hashlib.sha256(_canonical(body)).hexdigest()
    if value["packet_identity"] != packet_identity:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_PACKET_MANIFEST_SEAL_INVALID")
    expected_files = {
        "application-provider-request.json", "authority-receipt-candidate.json",
        "host-payload.json", "rendered-prompt.json", "runner-request.json",
        "static-executor-binding.json",
    }
    hashes = value["file_sha256"]
    if type(hashes) is not dict or set(hashes) != expected_files:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_PACKET_FILE_SET_INVALID")
    packet_root = manifest_path.parent
    allowed_names = expected_files | {
        "manifest.json", "authority-receipt-issued.json",
    }
    actual_names = {path.name for path in packet_root.iterdir()}
    if actual_names != allowed_names:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_PACKET_DIRECTORY_FILE_SET_INVALID")
    for name, expected_sha in hashes.items():
        path = _file(packet_root / name, "PACKET_FILE")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected_sha:
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_PACKET_FILE_HASH_MISMATCH")
    candidate_raw = (packet_root / "authority-receipt-candidate.json").read_bytes()
    candidate = json.loads(candidate_raw)
    issued = json.loads(authority_path.read_bytes())
    issued_body = {key: item for key, item in issued.items()
                   if key != "authority_receipt_identity"}
    fixed = (
        value["schema_name"] == "pastila-construction-obligation-v2-case01-issuance-packet"
        and value["schema_version"] == "1.2.1" and value["case_id"] == "HMCV1-SASC-01"
        and value["receipt_status"] == "UNISSUED"
        and value["attempts"] == {"completed": 0, "ceiling": 1}
        and all(flag is False for flag in value["execution"].values())
        and value["command"] == list(invocation.command)
        and value["command_identity"] == invocation.command_identity
        and value["command_plan_identity"] == command_plan_identity
        and value["packet_plan_identity"] == packet_plan_identity
        and value["authority_reference_if_issued"] == authority_identity
        and candidate.get("proposed_receipt_identity") == authority_identity
        and candidate.get("receipt_status") == "UNISSUED"
        and candidate.get("authority_receipt_identity") is None
        and candidate_raw == _canonical(candidate)
        and candidate.get("authority_body") == issued_body
        and value["source_context_identity"] == source_context_identity
        and value["evidence_root_identity"] == evidence_root_identity
        and value["proposed_evidence_root"] == str(outer_evidence_root)
        and authority_path == packet_root / "authority-receipt-issued.json"
        and request_path == packet_root / "runner-request.json"
    )
    if not fixed:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_PACKET_BINDING_MISMATCH")
    return packet_identity


def _derive_packet_plan_identity(
    *, manifest_path: Path, command_plan_identity: str,
    source_context_identity: str, outer_evidence_root: Path,
) -> str:
    packet_root = manifest_path.parent
    plan_names = {
        "application-provider-request.json", "host-payload.json",
        "rendered-prompt.json", "runner-request.json", "static-executor-binding.json",
    }
    hashes = {name: hashlib.sha256(_file(packet_root / name, "PACKET_PLAN_FILE").read_bytes()).hexdigest()
              for name in sorted(plan_names)}
    value = {
        "schema": "STAGE_P_CONSTRUCTION_OBLIGATION_V2_PACKET_PLAN_V1_2_1",
        "packet_root": str(packet_root), "evidence_root": str(outer_evidence_root),
        "source_context_identity": source_context_identity,
        "wsl_binding_identity": GENERATION_WSL_INVOCATION_BINDING_IDENTITY,
        "command_plan_identity": command_plan_identity,
        "plan_file_sha256": hashes,
    }
    return hashlib.sha256(_canonical(value)).hexdigest()


def _canonical(value: dict[str, object]) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


__all__ = (
    "GENERATION_WSL_INVOCATION_BINDING_IDENTITY",
    "GENERATION_WSL_INVOCATION_BINDING_IDENTITY_FIELDS", "OUTER_TIMEOUT_SECONDS",
    "RUNNER_MODULE", "RUNNER_RELATIVE", "RUNNER_SOURCE_SHA256",
    "PreparedGenerationWslInvocationV1_2_1",
    "build_generation_wsl_invocation_v1_2_1",
)
