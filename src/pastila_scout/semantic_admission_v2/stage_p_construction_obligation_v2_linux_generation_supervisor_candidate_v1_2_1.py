"""Injected, source-only Linux generation supervisor candidate.

The candidate owns ordering and reconciliation only.  Child process mechanics
and durable persistence are injected; this module has no entry point, process
constructor, filesystem writer, WSL binding, or runtime import.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import dataclass

from .stage_p_construction_obligation_v2_generation_authority_preload_v1_2_1 import (
    parse_generation_authority_v1_2_1,
)
from .stage_p_construction_obligation_v2_generation_execution_policy_gate_v1 import (
    canonical_observed_generation_execution_policy_v1,
    validate_generation_execution_policy_gate_v1,
)
from .stage_p_construction_obligation_v2_injected_generation_supervisor_v1_2_1 import (
    SUPERVISOR_IDENTITY, InjectedGenerationSupervisorResultV1,
)
from .stage_p_construction_obligation_v2_injected_generation_worker_v1_2_1 import (
    COMPATIBILITY_RECEIPT_IDENTITY, WORKER_IDENTITY,
    validate_compatibility_receipt_v1_2_1,
)
from .stage_p_construction_obligation_v2_runner_protocol_cleanup_extension_v1_1 import (
    build_cleanup_receipt_v1_1,
    build_result_envelope_v1_1,
)
from .stage_p_construction_obligation_v2_runner_protocol_codec_v1 import (
    build_runner_result_v1,
    parse_runner_request_v1,
)

SUPERVISOR_CANDIDATE_IDENTITY_FIELDS = (
    "construction-obligation-v2-linux-generation-supervisor-candidate-v1.2.1",
    "injected-supervisor:" + SUPERVISOR_IDENTITY,
    "timeout-progress:canonical-lifecycle-and-compatibility",
    "timeout-progress:exact-worker-schema-state-machine",
    "compatibility:ordered-load-completion-identity-bound",
    "timeout-terminal-event:chain-preserving",
    "retry-fallback-repair-selection:0",
)
SUPERVISOR_CANDIDATE_IDENTITY = hashlib.sha256(
    "\n".join(SUPERVISOR_CANDIDATE_IDENTITY_FIELDS).encode()).hexdigest()
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
    collect_progress: Callable[[object], tuple[tuple[str, bytes], ...]] = lambda handle: ()


@dataclass(frozen=True, slots=True)
class InjectedDurableSinkV1:
    persist: Callable[[str, bytes], None]


@dataclass(frozen=True, slots=True)
class LinuxGenerationSupervisorOutcomeV1:
    status: str
    authority_receipt_identity: str
    persisted_artifact_sha256: tuple[tuple[str, str], ...]
    supervisor_receipt: bytes


def supervise_linux_generation_candidate_v1_2_1(
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
    authority = parse_generation_authority_v1_2_1(
        raw_receipt=raw_authority_receipt,
        expected_host_payload_sha256=request.host_payload_sha256,
        expected_runner_request_sha256=hashlib.sha256(raw_runner_request).hexdigest(),
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
    child_progress = child_operations.collect_progress(handle)
    if (type(child_progress) is not tuple
            or any(type(item) is not tuple or len(item) != 2
                   or item[0] not in {"lifecycle", "compatibility"}
                   or type(item[1]) is not bytes for item in child_progress)):
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_CHILD_PROGRESS_EXACT_TYPE_REQUIRED")
    if timed_out:
        child_result = None
        failure_code = "CHILD_TIMEOUT_" + (termination or "UNCONFIRMED")
    elif exit_code != 0 or type(child_result) is not InjectedGenerationSupervisorResultV1:
        child_result = None
        failure_code = "CHILD_NONZERO_OR_RESULT_MISSING"
    else:
        failure_code = None

    artifacts = _reconcile_artifacts(
        request=request, child_result=child_result, failure_code=failure_code,
        child_progress=child_progress)
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


def _reconcile_artifacts(*, request, child_result, failure_code, child_progress=()):
    artifacts: list[tuple[str, bytes]] = []
    if child_result is None:
        progress, compatibility = _validated_timeout_progress(
            child_progress, request.provider_request_id)
        for raw in progress:
            value = json.loads(raw)
            artifacts.append((
                f"lifecycle-{value['sequence'] + 1:05d}-{value['event'].lower()}.json",
                raw,
            ))
        previous = json.loads(progress[-1])["event_identity"] if progress else None
        terminal_event = _failure_event(
            request.provider_request_id, failure_code, len(progress), previous)
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
        if compatibility:
            artifacts.append(("adapter-compatibility-receipt.json", compatibility[0]))
        return [
            *artifacts,
            (f"lifecycle-{len(progress) + 1:05d}-execution-failed.json", terminal_event),
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


def _validated_progress(values, provider_request_id):
    previous = None
    result = []
    observed_events = []
    for sequence, raw in enumerate(values):
        try:
            value = json.loads(raw.decode("utf-8", errors="strict"))
        except Exception as exc:
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_CHILD_PROGRESS_INVALID") from exc
        body = {key: item for key, item in value.items() if key != "event_identity"}
        expected = hashlib.sha256(_canonical(body)).hexdigest()
        event = value.get("event")
        detail = value.get("detail")
        if (raw != _canonical(value)
                or set(value) != {"schema_name", "schema_version", "worker_identity",
                                  "provider_request_id", "sequence", "event", "detail",
                                  "previous_event_identity", "event_identity"}
                or value.get("schema_name") != "pastila-semantic-admission-v2-construction-obligation-v2-injected-generation-event"
                or value.get("schema_version") != "1.0.0"
                or value.get("worker_identity") != WORKER_IDENTITY
                or value.get("provider_request_id") != provider_request_id
                or value.get("sequence") != sequence
                or value.get("previous_event_identity") != previous
                or value.get("event_identity") != expected
                or not _valid_event_transition(tuple(observed_events), event)
                or not _valid_event_detail(event, detail)):
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_CHILD_PROGRESS_BINDING_INVALID")
        previous = expected
        observed_events.append(event)
        result.append(raw)
    return tuple(result)


def _validated_timeout_progress(child_progress, provider_request_id):
    lifecycle = tuple(raw for label, raw in child_progress if label == "lifecycle")
    compatibility = tuple(raw for label, raw in child_progress if label == "compatibility")
    if len(compatibility) > 1:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_CHILD_COMPATIBILITY_DUPLICATE")
    progress = _validated_progress(lifecycle, provider_request_id)
    expected_records = []
    for raw in progress:
        value = json.loads(raw)
        if value["event"] == "MODEL_LOAD_COMPLETED":
            if not compatibility:
                raise ValueError("CONSTRUCTION_OBLIGATION_V2_CHILD_COMPATIBILITY_MISSING")
            validate_compatibility_receipt_v1_2_1(compatibility[0])
            if value["detail"]["compatibility_receipt_identity"] != json.loads(
                    compatibility[0])["receipt_identity"]:
                raise ValueError("CONSTRUCTION_OBLIGATION_V2_CHILD_COMPATIBILITY_BINDING_INVALID")
            expected_records.append(("compatibility", compatibility[0]))
        expected_records.append(("lifecycle", raw))
    if tuple(expected_records) != child_progress:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_CHILD_PROGRESS_ORDER_INVALID")
    return progress, compatibility


def _valid_event_transition(observed, event):
    if not observed:
        return event == "MODEL_LOAD_STARTED"
    previous = observed[-1]
    allowed = {
        "MODEL_LOAD_STARTED": {"MODEL_LOAD_COMPLETED", "EXECUTION_FAILED"},
        "MODEL_LOAD_COMPLETED": {"GENERATION_STARTED"},
        "GENERATION_STARTED": {"TERMINAL_EOS", "NO_LEGAL_TOKEN", "EXECUTION_FAILED"},
        "TERMINAL_EOS": {"CLEANUP_COMPLETED", "CLEANUP_FAILED"},
        "NO_LEGAL_TOKEN": {"CLEANUP_COMPLETED", "CLEANUP_FAILED"},
        "EXECUTION_FAILED": {"CLEANUP_COMPLETED", "CLEANUP_FAILED"},
        "CLEANUP_COMPLETED": set(),
        "CLEANUP_FAILED": set(),
    }
    return event in allowed.get(previous, set())


def _valid_event_detail(event, detail):
    if type(detail) is not dict:
        return False
    if event == "MODEL_LOAD_STARTED":
        return (set(detail) == {"prompt_token_count"}
                and type(detail["prompt_token_count"]) is int
                and 0 < detail["prompt_token_count"] <= 8192)
    if event == "MODEL_LOAD_COMPLETED":
        return detail == {"compatibility_receipt_identity": COMPATIBILITY_RECEIPT_IDENTITY}
    if event == "GENERATION_STARTED":
        return (set(detail) == {"maximum_output_tokens", "sole_callback"}
                and type(detail["maximum_output_tokens"]) is int
                and 0 < detail["maximum_output_tokens"] <= 3200
                and detail["sole_callback"] == "REQUEST_BOUND_PROJECTOR_V1_3")
    if event == "TERMINAL_EOS":
        return (set(detail) == {"generated_token_count", "output_sha256"}
                and type(detail["generated_token_count"]) is int
                and 0 < detail["generated_token_count"] <= 3200
                and _sha256_identity(detail["output_sha256"]))
    if event == "NO_LEGAL_TOKEN":
        return set(detail) == {"receipt_identity"} and _sha256_identity(detail["receipt_identity"])
    if event == "EXECUTION_FAILED":
        return (set(detail) == {"failure_code"} and type(detail["failure_code"]) is str
                and 0 < len(detail["failure_code"]) <= 200)
    if event == "CLEANUP_COMPLETED":
        return detail == {"failure_type": None}
    if event == "CLEANUP_FAILED":
        return (set(detail) == {"failure_type"}
                and type(detail["failure_type"]) is str and bool(detail["failure_type"]))
    return False


def _sha256_identity(value):
    return (type(value) is str and len(value) == 64
            and all(character in "0123456789abcdef" for character in value))


def _failure_event(provider_request_id, failure_code, sequence=0, previous=None):
    value = {
        "schema_name": "pastila-semantic-admission-v2-construction-obligation-v2-linux-supervisor-event",
        "schema_version": "1.0.0",
        "supervisor_candidate_identity": SUPERVISOR_CANDIDATE_IDENTITY,
        "provider_request_id": provider_request_id,
        "sequence": sequence, "event": "EXECUTION_FAILED",
        "failure_code": failure_code, "event_identity": "",
    }
    if previous is not None:
        value["previous_event_identity"] = previous
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
    "SUPERVISOR_CANDIDATE_IDENTITY",
    "InjectedChildProcessOperationsV1",
    "InjectedDurableSinkV1",
    "LinuxGenerationChildInvocationV1",
    "LinuxGenerationSupervisorOutcomeV1",
    "supervise_linux_generation_candidate_v1_2_1",
)
