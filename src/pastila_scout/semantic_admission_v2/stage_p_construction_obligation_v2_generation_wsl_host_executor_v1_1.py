"""Host execution and receipt reconciliation for V2 generation over WSL."""

from __future__ import annotations

import hashlib
import json
import os
import uuid
from dataclasses import dataclass
from pathlib import Path

from pastila_scout.wsl_execution_v1 import (
    WslExecutionResultV1,
    canonical_receipt_bytes_v1,
)
from pastila_scout.wsl_execution_v1_1 import WslExecutionBoundaryV1_1

from .stage_p_construction_obligation_v2_generation_wsl_invocation_binding_v1_1 import (
    OUTER_TIMEOUT_SECONDS,
    PreparedGenerationWslInvocationV1,
)
from .stage_p_construction_obligation_v2_linux_generation_supervisor_candidate_v1_1 import (
    SUPERVISOR_CANDIDATE_IDENTITY,
)

GENERATION_WSL_HOST_EXECUTOR_IDENTITY = (
    "7749b2b075c7db788927130505edbaafa1c7cfbd398b1132b01b396f94d97942"
)


@dataclass(frozen=True, slots=True)
class GenerationWslHostExecutionOutcomeV1:
    status: str
    transport_result: WslExecutionResultV1
    wsl_receipt_sha256: str
    reconciliation_identity: str
    linux_supervisor_receipt_identity: str | None


def execute_generation_wsl_host_v1_1(
    *,
    prepared: PreparedGenerationWslInvocationV1,
    boundary: WslExecutionBoundaryV1_1,
) -> GenerationWslHostExecutionOutcomeV1:
    """Cross the single WSL execution edge and seal transport evidence."""
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
    result = boundary.execute(
        prepared.invocation, timeout_seconds=OUTER_TIMEOUT_SECONDS
    )
    if type(result) is not WslExecutionResultV1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_WSL_RESULT_EXACT_TYPE_REQUIRED")
    raw_wsl_receipt = canonical_receipt_bytes_v1(result.receipt)
    _publish(outer / "wsl-execution-receipt.json", raw_wsl_receipt)
    wsl_sha = hashlib.sha256(raw_wsl_receipt).hexdigest()

    linux_identity = None
    if result.succeeded:
        try:
            linux_identity, linux_status = _linux_receipt(
                prepared.linux_evidence_root / "supervisor-receipt.json",
                prepared.authority_receipt_identity,
            )
            status = "RECONCILED:" + linux_status
        except Exception as exc:
            status = "LINUX_EVIDENCE_RECONCILIATION_FAILURE"
            reconciliation = _reconciliation(
                prepared=prepared,
                status=status,
                wsl_sha=wsl_sha,
                linux_identity=None,
                failure_type=type(exc).__name__,
            )
            _publish(outer / "host-reconciliation.json", reconciliation)
            raise RuntimeError(
                "CONSTRUCTION_OBLIGATION_V2_LINUX_EVIDENCE_RECONCILIATION_FAILED"
            ) from exc
    else:
        status = "TRANSPORT_FAILURE"
    reconciliation = _reconciliation(
        prepared=prepared,
        status=status,
        wsl_sha=wsl_sha,
        linux_identity=linux_identity,
        failure_type=None,
    )
    _publish(outer / "host-reconciliation.json", reconciliation)
    reconciliation_identity = json.loads(reconciliation)["reconciliation_identity"]
    return GenerationWslHostExecutionOutcomeV1(
        status, result, wsl_sha, reconciliation_identity, linux_identity
    )


def _linux_receipt(path: Path, authority_identity: str) -> tuple[str, str]:
    raw = path.read_bytes()
    value = json.loads(raw.decode("utf-8", errors="strict"))
    required = {
        "schema_name",
        "schema_version",
        "supervisor_candidate_identity",
        "authority_receipt_identity",
        "status",
        "child_exit_code",
        "timed_out",
        "termination",
        "persisted_artifacts",
        "retry_count",
        "receipt_identity",
    }
    if type(value) is not dict or set(value) != required:
        raise ValueError("LINUX_SUPERVISOR_RECEIPT_SHAPE_INVALID")
    if (
        value["schema_name"]
        != "pastila-semantic-admission-v2-construction-obligation-v2-linux-generation-supervisor-receipt"
        or value["schema_version"] != "1.0.0"
        or value["supervisor_candidate_identity"] != SUPERVISOR_CANDIDATE_IDENTITY
        or value["authority_receipt_identity"] != authority_identity
        or value["retry_count"] != 0
        or type(value["status"]) is not str
        or not value["status"]
    ):
        raise ValueError("LINUX_SUPERVISOR_RECEIPT_BINDING_INVALID")
    body = {key: item for key, item in value.items() if key != "receipt_identity"}
    expected = hashlib.sha256(_canonical(body)).hexdigest()
    if value["receipt_identity"] != expected or raw != _canonical(value):
        raise ValueError("LINUX_SUPERVISOR_RECEIPT_SEAL_INVALID")
    return expected, value["status"]


def _reconciliation(*, prepared, status, wsl_sha, linux_identity, failure_type):
    value = {
        "schema_name": "pastila-construction-obligation-v2-generation-host-reconciliation",
        "schema_version": "1.0.0",
        "host_executor_identity": GENERATION_WSL_HOST_EXECUTOR_IDENTITY,
        "invocation_binding_identity": prepared.binding_identity,
        "command_identity": prepared.invocation.command_identity,
        "authority_receipt_identity": prepared.authority_receipt_identity,
        "runner_request_sha256": prepared.runner_request_sha256,
        "wsl_execution_receipt_sha256": wsl_sha,
        "linux_supervisor_receipt_identity": linux_identity,
        "status": status,
        "failure_type": failure_type,
        "retry_count": 0,
        "reconciliation_identity": "",
    }
    value["reconciliation_identity"] = hashlib.sha256(
        _canonical(
            {
                key: item
                for key, item in value.items()
                if key != "reconciliation_identity"
            }
        )
    ).hexdigest()
    return _canonical(value)


def _publish(target: Path, raw: bytes) -> None:
    if target.exists() or target.is_symlink():
        raise FileExistsError("CONSTRUCTION_OBLIGATION_V2_HOST_RECEIPT_EXISTS")
    pending = target.parent / (".pending-" + uuid.uuid4().hex)
    descriptor = None
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
        descriptor = os.open(pending, flags, 0o600)
        written = 0
        while written < len(raw):
            count = os.write(descriptor, raw[written:])
            if count <= 0:
                raise OSError("CONSTRUCTION_OBLIGATION_V2_HOST_RECEIPT_SHORT_WRITE")
            written += count
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.link(pending, target)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        pending.unlink(missing_ok=True)


def _canonical(value: dict[str, object]) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode()


__all__ = (
    "GENERATION_WSL_HOST_EXECUTOR_IDENTITY",
    "GenerationWslHostExecutionOutcomeV1",
    "execute_generation_wsl_host_v1_1",
)
