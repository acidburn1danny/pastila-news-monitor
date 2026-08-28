"""V1.2 host transport with durable byte-exact stdout/stderr evidence."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from pastila_scout.wsl_execution_v1 import WslExecutionResultV1, canonical_receipt_bytes_v1
from pastila_scout.wsl_execution_v1_1 import WslExecutionBoundaryV1_1

from .stage_p_construction_obligation_v2_generation_wsl_host_executor_v1_1 import (
    _canonical,
    _linux_receipt,
    _publish,
)
from .stage_p_construction_obligation_v2_generation_wsl_invocation_binding_v1_1 import (
    OUTER_TIMEOUT_SECONDS,
    PreparedGenerationWslInvocationV1,
)

GENERATION_WSL_HOST_EXECUTOR_IDENTITY_FIELDS = (
    "construction-obligation-v2-generation-wsl-host-executor-v1.2",
    "transport-boundary:wsl-v1.1",
    "raw-streams:stdout-then-stderr-before-receipts",
    "retry-fallback-repair-selection:0",
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


def execute_generation_wsl_host_v1_2(
    *, prepared: PreparedGenerationWslInvocationV1, boundary: WslExecutionBoundaryV1_1,
) -> GenerationWslHostExecutionOutcomeV1_2:
    """Execute once; persist both captured streams before derived receipts."""
    if type(prepared) is not PreparedGenerationWslInvocationV1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_PREPARED_WSL_INVOCATION_REQUIRED")
    if type(boundary) is not WslExecutionBoundaryV1_1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_CANONICAL_WSL_V1_1_REQUIRED")
    if prepared.invocation.profile_identity != boundary.profile.identity:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_WSL_PROFILE_IDENTITY_MISMATCH")
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
            linux_identity, linux_status = _linux_receipt(
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


def _reconciliation(prepared, status, stdout_sha, stderr_sha, receipt_sha,
                    linux_identity, failure_type):
    value = {
        "schema_name": "pastila-construction-obligation-v2-generation-host-reconciliation",
        "schema_version": "1.2.0",
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


__all__ = (
    "GENERATION_WSL_HOST_EXECUTOR_IDENTITY",
    "GENERATION_WSL_HOST_EXECUTOR_IDENTITY_FIELDS",
    "GenerationWslHostExecutionOutcomeV1_2",
    "execute_generation_wsl_host_v1_2",
)
