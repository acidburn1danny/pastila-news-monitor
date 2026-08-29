"""V1.2.1 host transport with durable byte-exact stdout/stderr evidence."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from pastila_scout.wsl_execution_v1 import WslExecutionResultV1, canonical_receipt_bytes_v1
from pastila_scout.wsl_execution_v1_1 import WslExecutionBoundaryV1_1

from .stage_p_construction_obligation_v2_generation_wsl_host_executor_v1_1 import (
    _canonical,
    _publish,
)
from .stage_p_construction_obligation_v2_generation_wsl_invocation_binding_v1_1 import (
    OUTER_TIMEOUT_SECONDS, SYSTEM_PROMPT_SHA256, _file,
)
from .stage_p_construction_obligation_v2_generation_execution_policy_gate_v1 import (
    canonical_observed_generation_execution_policy_v1,
    validate_generation_execution_policy_gate_v1,
)
from .stage_p_construction_obligation_v2_generation_wsl_invocation_binding_v1_2_1 import (
    GENERATION_WSL_INVOCATION_BINDING_IDENTITY, RUNNER_MODULE,
    PreparedGenerationWslInvocationV1_2_1, _validate_packet_manifest_v1_2_1,
    _derive_packet_plan_identity,
)
from .stage_p_construction_obligation_v2_generation_authority_preload_v1_2_1 import (
    AUTHORITY_PRELOAD_IDENTITY, parse_generation_authority_v1_2_1,
)
from .stage_p_construction_obligation_v2_runner_protocol_codec_v1 import parse_runner_request_v1
from pastila_scout.wsl_execution_v1 import windows_path_to_wsl_v1
from .stage_p_construction_obligation_v2_linux_generation_supervisor_candidate_v1_2_1 import SUPERVISOR_CANDIDATE_IDENTITY

GENERATION_WSL_HOST_EXECUTOR_IDENTITY_FIELDS = (
    "construction-obligation-v2-generation-wsl-host-executor-v1.2.1",
    "transport-boundary:wsl-v1.1",
    "raw-streams:stdout-then-stderr-before-receipts",
    "retry-fallback-repair-selection:0",
    "prepared-invocation:v1.2.1-exact-type",
    "pre-execute:independent-canonical-revalidation",
    "pre-execute:packet-manifest-and-file-set-revalidation",
    "pre-execute:authority-packet-command-plan-revalidation",
    "evidence-domain:progress-state-machine-bound",
)
GENERATION_WSL_HOST_EXECUTOR_IDENTITY = hashlib.sha256(
    "\n".join(GENERATION_WSL_HOST_EXECUTOR_IDENTITY_FIELDS).encode()
).hexdigest()


@dataclass(frozen=True, slots=True)
class GenerationWslHostExecutionOutcomeV1_2:
    status: str
    transport_result: WslExecutionResultV1
    stdout_sha256: str
    stderr_sha256: str
    wsl_receipt_sha256: str
    reconciliation_identity: str
    linux_supervisor_receipt_identity: str | None


def execute_generation_wsl_host_v1_2_1(
    *, prepared: PreparedGenerationWslInvocationV1_2_1, boundary: WslExecutionBoundaryV1_1,
) -> GenerationWslHostExecutionOutcomeV1_2:
    """Execute once; persist both captured streams before derived receipts."""
    if type(prepared) is not PreparedGenerationWslInvocationV1_2_1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_PREPARED_WSL_INVOCATION_V1_2_1_REQUIRED")
    if type(boundary) is not WslExecutionBoundaryV1_1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_CANONICAL_WSL_V1_1_REQUIRED")
    _revalidate_prepared_v1_2_1(prepared, boundary)
    outer = prepared.outer_evidence_root
    if outer.exists() or outer.is_symlink():
        raise FileExistsError("CONSTRUCTION_OBLIGATION_V2_OUTER_ROOT_ALREADY_EXISTS")
    if outer.parent.resolve(strict=True) != outer.parent:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_OUTER_ROOT_PARENT_INVALID")
    outer.mkdir(mode=0o700, parents=False, exist_ok=False)
    result = boundary.execute(prepared.invocation, timeout_seconds=OUTER_TIMEOUT_SECONDS)
    if type(result) is not WslExecutionResultV1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_WSL_RESULT_EXACT_TYPE_REQUIRED")
    stdout = result.stdout.encode("utf-8", errors="strict")
    stderr = result.stderr.encode("utf-8", errors="strict")
    _publish(outer / "wsl-stdout.bin", stdout)
    _publish(outer / "wsl-stderr.bin", stderr)
    stdout_sha = hashlib.sha256(stdout).hexdigest()
    stderr_sha = hashlib.sha256(stderr).hexdigest()
    if (stdout_sha != result.receipt.stdout_sha256
            or stderr_sha != result.receipt.stderr_sha256):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_WSL_STREAM_RECEIPT_MISMATCH")
    raw_receipt = canonical_receipt_bytes_v1(result.receipt)
    _publish(outer / "wsl-execution-receipt.json", raw_receipt)
    receipt_sha = hashlib.sha256(raw_receipt).hexdigest()
    linux_identity = None
    failure_type = None
    if result.succeeded:
        try:
            linux_identity, linux_status = _linux_receipt_v1_2_1(
                prepared.linux_evidence_root / "supervisor-receipt.json",
                prepared.authority_receipt_identity,
            )
            status = "RECONCILED:" + linux_status
        except Exception as exc:
            status = "LINUX_EVIDENCE_RECONCILIATION_FAILURE"
            failure_type = type(exc).__name__
    else:
        status = "TRANSPORT_FAILURE"
    reconciliation = _reconciliation(
        prepared, status, stdout_sha, stderr_sha, receipt_sha,
        linux_identity, failure_type,
    )
    _publish(outer / "host-reconciliation-v1-2.json", reconciliation)
    reconciliation_identity = json.loads(reconciliation)["reconciliation_identity"]
    if status == "LINUX_EVIDENCE_RECONCILIATION_FAILURE":
        raise RuntimeError("CONSTRUCTION_OBLIGATION_V2_LINUX_EVIDENCE_RECONCILIATION_FAILED")
    return GenerationWslHostExecutionOutcomeV1_2(
        status, result, stdout_sha, stderr_sha, receipt_sha,
        reconciliation_identity, linux_identity,
    )


def _revalidate_prepared_v1_2_1(prepared, boundary):
    if (prepared.binding_identity != GENERATION_WSL_INVOCATION_BINDING_IDENTITY
            or prepared.wsl_binding_identity != GENERATION_WSL_INVOCATION_BINDING_IDENTITY
            or prepared.authority_preload_identity != AUTHORITY_PRELOAD_IDENTITY
            or prepared.timeout_seconds != OUTER_TIMEOUT_SECONDS):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_V1_2_1_IDENTITY_MISMATCH")
    policy = _file(prepared.policy_receipt_path, "POLICY")
    authority_path = _file(prepared.authority_receipt_path, "AUTHORITY")
    request_path = _file(prepared.runner_request_path, "RUNNER_REQUEST")
    prompt = _file(prepared.system_prompt_path, "SYSTEM_PROMPT")
    expected_policy = validate_generation_execution_policy_gate_v1(
        observed=canonical_observed_generation_execution_policy_v1())
    if policy.read_bytes() != expected_policy:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_GENERATION_POLICY_RECEIPT_MISMATCH")
    if hashlib.sha256(prompt.read_bytes()).hexdigest() != SYSTEM_PROMPT_SHA256:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_SYSTEM_PROMPT_IDENTITY_MISMATCH")
    raw_request = request_path.read_bytes()
    request = parse_runner_request_v1(raw_request=raw_request)
    request_sha = hashlib.sha256(raw_request).hexdigest()
    arguments = ("-m", RUNNER_MODULE,
                 windows_path_to_wsl_v1(prepared.policy_receipt_path),
                 windows_path_to_wsl_v1(prepared.authority_receipt_path),
                 windows_path_to_wsl_v1(prepared.runner_request_path),
                 windows_path_to_wsl_v1(prepared.system_prompt_path),
                 windows_path_to_wsl_v1(prepared.linux_evidence_root))
    command_plan = boundary.build_invocation(
        consumer_id="construction-obligation-v2-generation-v1-2-1",
        authority_reference="0" * 64, arguments=arguments)
    packet_plan_identity = _derive_packet_plan_identity(
        manifest_path=_file(prepared.packet_manifest_path, "PACKET_MANIFEST"),
        command_plan_identity=command_plan.command_identity,
        source_context_identity=request.source_context_identity,
        outer_evidence_root=prepared.outer_evidence_root)
    authority = parse_generation_authority_v1_2_1(
        raw_receipt=authority_path.read_bytes(),
        expected_host_payload_sha256=request.host_payload_sha256,
        expected_runner_request_sha256=request_sha,
        expected_provider_request_id=request.provider_request_id,
        expected_source_context_identity=request.source_context_identity,
        expected_packet_plan_identity=packet_plan_identity,
        expected_command_plan_identity=command_plan.command_identity,
    )
    expected = boundary.build_invocation(
        consumer_id="construction-obligation-v2-generation-v1-2-1",
        authority_reference=authority.authority_receipt_identity,
        arguments=arguments,
    )
    material = (
        "STAGE_P_CONSTRUCTION_OBLIGATION_V2_GENERATION_WSL_INVOCATION_INSTANCE_V1_2_1",
        GENERATION_WSL_INVOCATION_BINDING_IDENTITY, expected.command_identity,
        authority.authority_receipt_identity, request_sha, prepared.packet_identity,
        request.provider_request_id, request.source_context_identity,
        prepared.evidence_root_identity, str(prepared.outer_evidence_root),
        str(prepared.policy_receipt_path), str(prepared.authority_receipt_path),
        str(prepared.runner_request_path), str(prepared.packet_manifest_path),
        str(prepared.system_prompt_path),
        str(OUTER_TIMEOUT_SECONDS),
    )
    instance = hashlib.sha256("\n".join(material).encode()).hexdigest()
    evidence_identity = hashlib.sha256("\n".join((
        "STAGE_P_CONSTRUCTION_OBLIGATION_V2_CASE01_V1_2_1_PROGRESS_STATE_MACHINE_BOUND_EVIDENCE_ROOT",
        request.source_context_identity, expected.command_identity,
        str(prepared.outer_evidence_root),
    )).encode()).hexdigest()
    packet_identity = _validate_packet_manifest_v1_2_1(
        manifest_path=_file(prepared.packet_manifest_path, "PACKET_MANIFEST"),
        invocation=expected, authority_identity=authority.authority_receipt_identity,
        authority_path=authority_path, request_path=request_path,
        packet_plan_identity=packet_plan_identity,
        command_plan_identity=command_plan.command_identity,
        source_context_identity=request.source_context_identity,
        evidence_root_identity=evidence_identity,
        outer_evidence_root=prepared.outer_evidence_root,
    )
    if (type(prepared.invocation) is not type(expected) or prepared.invocation != expected
            or prepared.command_identity != expected.command_identity
            or prepared.invocation_instance_identity != instance
            or prepared.authority_receipt_identity != authority.authority_receipt_identity
            or prepared.runner_request_sha256 != request_sha
            or prepared.provider_request_id != request.provider_request_id
            or prepared.source_context_identity != request.source_context_identity
            or prepared.packet_identity != packet_identity
            or prepared.evidence_root_identity != evidence_identity
            or prepared.linux_evidence_root != prepared.outer_evidence_root / "linux-generation"):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_V1_2_1_EXECUTION_PLAN_DRIFT")


def _reconciliation(prepared, status, stdout_sha, stderr_sha, receipt_sha,
                    linux_identity, failure_type):
    value = {
        "schema_name": "pastila-construction-obligation-v2-generation-host-reconciliation",
        "schema_version": "1.2.1",
        "host_executor_identity": GENERATION_WSL_HOST_EXECUTOR_IDENTITY,
        "invocation_binding_identity": prepared.binding_identity,
        "command_identity": prepared.invocation.command_identity,
        "authority_receipt_identity": prepared.authority_receipt_identity,
        "runner_request_sha256": prepared.runner_request_sha256,
        "wsl_stdout_sha256": stdout_sha,
        "wsl_stderr_sha256": stderr_sha,
        "wsl_execution_receipt_sha256": receipt_sha,
        "linux_supervisor_receipt_identity": linux_identity,
        "status": status,
        "failure_type": failure_type,
        "retry_count": 0,
        "reconciliation_identity": "",
    }
    value["reconciliation_identity"] = hashlib.sha256(_canonical({
        key: item for key, item in value.items() if key != "reconciliation_identity"
    })).hexdigest()
    return _canonical(value)


def _linux_receipt_v1_2_1(path, authority_identity):
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8", errors="strict"))
    required = {
        "schema_name", "schema_version", "supervisor_candidate_identity",
        "authority_receipt_identity", "status", "child_exit_code", "timed_out",
        "termination", "persisted_artifacts", "retry_count", "receipt_identity",
    }
    if type(value) is not dict or set(value) != required:
        raise ValueError("LINUX_SUPERVISOR_V1_2_RECEIPT_SHAPE_INVALID")
    if (value["supervisor_candidate_identity"] != SUPERVISOR_CANDIDATE_IDENTITY
            or value["authority_receipt_identity"] != authority_identity
            or value["retry_count"] != 0):
        raise ValueError("LINUX_SUPERVISOR_V1_2_RECEIPT_BINDING_INVALID")
    body = {key: item for key, item in value.items() if key != "receipt_identity"}
    expected = hashlib.sha256(_canonical(body)).hexdigest()
    if value["receipt_identity"] != expected or raw != _canonical(value):
        raise ValueError("LINUX_SUPERVISOR_V1_2_RECEIPT_SEAL_INVALID")
    return expected, value["status"]


__all__ = (
    "GENERATION_WSL_HOST_EXECUTOR_IDENTITY",
    "GENERATION_WSL_HOST_EXECUTOR_IDENTITY_FIELDS",
    "GenerationWslHostExecutionOutcomeV1_2",
    "execute_generation_wsl_host_v1_2_1",
)
