"""Injected, source-only Linux generation supervisor candidate.

The candidate owns ordering and reconciliation only.  Child process mechanics
and durable persistence are injected; this module has no entry point, process
constructor, filesystem writer, WSL binding, or runtime import.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Callable

from .stage_p_construction_obligation_v2_generation_authority_contract_v1 import (
    parse_generation_authority_v1,
)
from .stage_p_construction_obligation_v2_generation_execution_policy_gate_v1 import (
    canonical_observed_generation_execution_policy_v1,
    validate_generation_execution_policy_gate_v1,
)
from .stage_p_construction_obligation_v2_injected_generation_supervisor_v1 import (
    InjectedGenerationSupervisorResultV1,
)
from .stage_p_construction_obligation_v2_runner_protocol_cleanup_extension_v1_1 import (
    build_cleanup_receipt_v1_1,
    build_result_envelope_v1_1,
)
from .stage_p_construction_obligation_v2_runner_protocol_codec_v1 import (
    build_runner_result_v1,
    parse_runner_request_v1,
)


SUPERVISOR_CANDIDATE_IDENTITY = "ce43ed32836005bcd471da40f9003e3d9ba66e090e57fbf66cdf77d0c8b95391"
SYSTEM_PROMPT_SHA256 = "111bc2734343c67aab4e1a04003199b98d4955fe9579e445cd7b5d6805a9da17"


@dataclass(frozen=True, slots=True)
class LinuxGenerationChildInvocationV1:
    raw_runner_request: bytes
    system_prompt: str
    authority_receipt_identity: str


@dataclass(frozen=True, slots=True)
class InjectedChildProcessOperationsV1:
    start: Callable[[LinuxGenerationChildInvocationV1], object]
    join: Callable[[object, float], None]
    is_alive: Callable[[object], bool]
    terminate: Callable[[object], None]
    kill: Callable[[object], None]
    exit_code: Callable[[object], int | None]
    collect_result: Callable[[object], InjectedGenerationSupervisorResultV1 | None]


@dataclass(frozen=True, slots=True)
class InjectedDurableSinkV1:
    persist: Callable[[str, bytes], None]


@dataclass(frozen=True, slots=True)
class LinuxGenerationSupervisorOutcomeV1:
    status: str
    authority_receipt_identity: str
    persisted_artifact_sha256: tuple[tuple[str, str], ...]
    supervisor_receipt: bytes


def supervise_linux_generation_candidate_v1(
    *, raw_policy_receipt: bytes, raw_authority_receipt: bytes,
    raw_runner_request: bytes, system_prompt: str, timeout_seconds: float,
    child_operations: InjectedChildProcessOperationsV1,
    durable_sink: InjectedDurableSinkV1,
) -> LinuxGenerationSupervisorOutcomeV1:
    """Validate first, then coordinate exactly one injected child."""
    if type(child_operations) is not InjectedChildProcessOperationsV1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_CHILD_OPERATIONS_EXACT_TYPE_REQUIRED")
    if type(durable_sink) is not InjectedDurableSinkV1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_DURABLE_SINK_EXACT_TYPE_REQUIRED")
    if type(timeout_seconds) is not float or not 1.0 <= timeout_seconds <= 1200.0:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_SUPERVISOR_TIMEOUT_INVALID")
    expected_policy = validate_generation_execution_policy_gate_v1(
        observed=canonical_observed_generation_execution_policy_v1())
    if raw_policy_receipt != expected_policy:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_GENERATION_POLICY_RECEIPT_MISMATCH")
    request = parse_runner_request_v1(raw_request=raw_runner_request)
    if (type(system_prompt) is not str
            or hashlib.sha256(system_prompt.encode("utf-8")).hexdigest() != SYSTEM_PROMPT_SHA256):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_SYSTEM_PROMPT_IDENTITY_MISMATCH")
    authority = parse_generation_authority_v1(
        raw_receipt=raw_authority_receipt,
        expected_generation_candidate_identity=SUPERVISOR_CANDIDATE_IDENTITY,
        expected_host_payload_sha256=request.host_payload_sha256,
        expected_provider_request_id=request.provider_request_id,
        expected_source_context_identity=request.source_context_identity,
    )

    invocation = LinuxGenerationChildInvocationV1(
        raw_runner_request, system_prompt, authority.authority_receipt_identity)
    handle = child_operations.start(invocation)
    if handle is None:
        raise RuntimeError("CONSTRUCTION_OBLIGATION_V2_CHILD_HANDLE_MISSING")
    child_operations.join(handle, timeout_seconds)
    timed_out = child_operations.is_alive(handle)
    termination = None
    if timed_out:
        child_operations.terminate(handle)
        child_operations.join(handle, 10.0)
        termination = "TERMINATED"
        if child_operations.is_alive(handle):
            child_operations.kill(handle)
            child_operations.join(handle, 10.0)
            termination = "KILLED"
    if child_operations.is_alive(handle):
        raise RuntimeError("CONSTRUCTION_OBLIGATION_V2_CHILD_TERMINATION_UNCONFIRMED")

    exit_code = child_operations.exit_code(handle)
    child_result = child_operations.collect_result(handle)
    if timed_out:
        child_result = None
        failure_code = "CHILD_TIMEOUT_" + (termination or "UNCONFIRMED")
    elif exit_code != 0 or type(child_result) is not InjectedGenerationSupervisorResultV1:
        child_result = None
        failure_code = "CHILD_NONZERO_OR_RESULT_MISSING"
    else:
        failure_code = None

    artifacts = _reconcile_artifacts(
        request=request, child_result=child_result, failure_code=failure_code)
    persisted: list[tuple[str, str]] = []
    for label, raw in artifacts:
        if any(existing == label for existing, _ in persisted):
            raise RuntimeError("CONSTRUCTION_OBLIGATION_V2_DURABLE_LABEL_DUPLICATE")
        try:
            durable_sink.persist(label, raw)
        except Exception as exc:
            raise RuntimeError("CONSTRUCTION_OBLIGATION_V2_DURABLE_PERSISTENCE_FAILED") from exc
        persisted.append((label, hashlib.sha256(raw).hexdigest()))
    status = (
        child_result.status if child_result is not None
        else "EXECUTION_FAILURE"
    )
    receipt = _supervisor_receipt(
        status=status, authority_identity=authority.authority_receipt_identity,
        exit_code=exit_code, timed_out=timed_out, termination=termination,
        artifacts=tuple(persisted))
    try:
        durable_sink.persist("supervisor-receipt.json", receipt)
    except Exception as exc:
        raise RuntimeError("CONSTRUCTION_OBLIGATION_V2_DURABLE_PERSISTENCE_FAILED") from exc
    persisted.append(("supervisor-receipt.json", hashlib.sha256(receipt).hexdigest()))
    return LinuxGenerationSupervisorOutcomeV1(
        status, authority.authority_receipt_identity, tuple(persisted), receipt)


def _reconcile_artifacts(*, request, child_result, failure_code):
    artifacts: list[tuple[str, bytes]] = []
    if child_result is None:
        terminal_event = _failure_event(request.provider_request_id, failure_code)
        terminal_identity = json.loads(terminal_event)["event_identity"]
        base_result = build_runner_result_v1(
            request=request, status="EXECUTION_FAILURE",
            lifecycle_terminal_event_identity=terminal_identity,
            execution_failure_code=failure_code)
        cleanup = build_cleanup_receipt_v1_1(
            provider_request_id=request.provider_request_id,
            source_context_identity=request.source_context_identity,
            worker_terminal_event_identity=terminal_identity,
            cleanup_status="CLEANUP_FAILED",
            cleanup_failure_code="CHILD_CLEANUP_UNCONFIRMED")
        envelope = build_result_envelope_v1_1(
            raw_base_runner_result=base_result,
            raw_cleanup_receipt=cleanup, raw_partial_output=None)
        return [
            ("lifecycle-00001-execution-failed.json", terminal_event),
            ("runner-result.json", base_result),
            ("cleanup-receipt-v1-1.json", cleanup),
            ("result-envelope-v1-1.json", envelope),
        ]

    if not child_result.lifecycle_events:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_CHILD_LIFECYCLE_REQUIRED")
    for sequence, raw in enumerate(child_result.lifecycle_events, 1):
        value = json.loads(raw)
        if value.get("sequence") != sequence - 1:
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_CHILD_LIFECYCLE_SEQUENCE_INVALID")
        artifacts.append((f"lifecycle-{sequence:05d}-{value['event'].lower()}.json", raw))
    terminal = json.loads(child_result.lifecycle_events[-1])
    base = json.loads(child_result.runner_result)
    if (
        base.get("provider_request_id") != request.provider_request_id
        or base.get("source_context_identity") != request.source_context_identity
        or base.get("lifecycle_terminal_event_identity") != terminal.get("event_identity")
    ):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_CHILD_RESULT_BINDING_MISMATCH")
    old_cleanup = _validate_child_cleanup_receipt(
        child_result.cleanup_receipt, terminal["event_identity"])
    cleanup_status = old_cleanup["cleanup_status"]
    cleanup_failure = None if cleanup_status == "CLEANUP_COMPLETED" else "CHILD_CLEANUP_FAILED"
    cleanup = build_cleanup_receipt_v1_1(
        provider_request_id=request.provider_request_id,
        source_context_identity=request.source_context_identity,
        worker_terminal_event_identity=terminal["event_identity"],
        cleanup_status=cleanup_status, cleanup_failure_code=cleanup_failure)
    envelope = build_result_envelope_v1_1(
        raw_base_runner_result=child_result.runner_result,
        raw_cleanup_receipt=cleanup,
        raw_partial_output=child_result.raw_partial_output)
    if child_result.raw_output is not None:
        artifacts.append(("raw-output.bin", child_result.raw_output))
    if child_result.raw_partial_output is not None:
        artifacts.append(("raw-partial-output.bin", child_result.raw_partial_output))
    if child_result.compatibility_receipt is not None:
        artifacts.append(("adapter-compatibility-receipt.json", child_result.compatibility_receipt))
    artifacts.extend((
        ("runner-result.json", child_result.runner_result),
        ("cleanup-receipt-v1-1.json", cleanup),
        ("result-envelope-v1-1.json", envelope),
    ))
    return artifacts


def _validate_child_cleanup_receipt(raw, terminal_identity):
    try:
        value = json.loads(raw.decode("utf-8", errors="strict"))
    except Exception as exc:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_CHILD_CLEANUP_RECEIPT_INVALID") from exc
    expected = hashlib.sha256(_canonical(
        {key: item for key, item in value.items() if key != "receipt_identity"}
    )).hexdigest()
    if (
        raw != _canonical(value)
        or value.get("receipt_identity") != expected
        or value.get("worker_terminal_event_identity") != terminal_identity
        or value.get("cleanup_status") not in {"CLEANUP_COMPLETED", "CLEANUP_FAILED"}
    ):
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_CHILD_CLEANUP_RECEIPT_MISMATCH")
    return value


def _failure_event(provider_request_id, failure_code):
    value = {
        "schema_name": "pastila-semantic-admission-v2-construction-obligation-v2-linux-supervisor-event",
        "schema_version": "1.0.0",
        "supervisor_candidate_identity": SUPERVISOR_CANDIDATE_IDENTITY,
        "provider_request_id": provider_request_id,
        "sequence": 0, "event": "EXECUTION_FAILED",
        "failure_code": failure_code, "event_identity": "",
    }
    value["event_identity"] = hashlib.sha256(_canonical(
        {key: item for key, item in value.items() if key != "event_identity"}
    )).hexdigest()
    return _canonical(value)


def _supervisor_receipt(*, status, authority_identity, exit_code, timed_out,
                        termination, artifacts):
    value = {
        "schema_name": "pastila-semantic-admission-v2-construction-obligation-v2-linux-generation-supervisor-receipt",
        "schema_version": "1.0.0",
        "supervisor_candidate_identity": SUPERVISOR_CANDIDATE_IDENTITY,
        "authority_receipt_identity": authority_identity,
        "status": status, "child_exit_code": exit_code,
        "timed_out": timed_out, "termination": termination,
        "persisted_artifacts": [
            {"label": label, "sha256": sha256} for label, sha256 in artifacts],
        "retry_count": 0, "receipt_identity": "",
    }
    value["receipt_identity"] = hashlib.sha256(_canonical(
        {key: item for key, item in value.items() if key != "receipt_identity"}
    )).hexdigest()
    return _canonical(value)


def _canonical(value: dict[str, object]) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


__all__ = (
    "InjectedChildProcessOperationsV1", "InjectedDurableSinkV1",
    "LinuxGenerationChildInvocationV1", "LinuxGenerationSupervisorOutcomeV1",
    "SUPERVISOR_CANDIDATE_IDENTITY", "supervise_linux_generation_candidate_v1",
)
