"""Source-only supervisor for the injected Construction-Obligation V2 worker."""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

from pastila_scout.experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_3 import (
    ConstructionObligationV2RunnerCallbackPreflightV1_3,
)

from .stage_p_construction_obligation_v2_generation_authority_preload_v1_1 import (
    GenerationPreloadObservationV1_1,
)
from .stage_p_construction_obligation_v2_injected_generation_worker_v1_2_1 import (
    InjectedGenerationOperationsV1,
    execute_injected_generation_worker_v1_2_1,
)
from .stage_p_construction_obligation_v2_runner_protocol_codec_v1 import (
    build_runner_result_v1,
)

SUPERVISOR_IDENTITY = "4d5d89cfac5156cb33ff4e5afa8db1397701806cd5cc61c9a7d72bb53af22718"


@dataclass(frozen=True, slots=True)
class InjectedGenerationSupervisorResultV1:
    status: str
    lifecycle_events: tuple[bytes, ...]
    runner_result: bytes
    raw_output: bytes | None
    raw_partial_output: bytes | None
    compatibility_receipt: bytes | None
    cleanup_receipt: bytes


def supervise_injected_generation_v1_2_1(
    *, raw_policy_receipt: bytes, raw_authority_receipt: bytes,
    expected_runner_request_sha256: str,
    preload_observation: GenerationPreloadObservationV1_1,
    callback_preflight: ConstructionObligationV2RunnerCallbackPreflightV1_3,
    rendered_prompt: str, operations: InjectedGenerationOperationsV1,
) -> InjectedGenerationSupervisorResultV1:
    """Return all durable bytes to the caller; persist or launch nothing."""
    outcome = execute_injected_generation_worker_v1_2_1(
        raw_policy_receipt=raw_policy_receipt,
        raw_authority_receipt=raw_authority_receipt,
        expected_runner_request_sha256=expected_runner_request_sha256,
        preload_observation=preload_observation,
        callback_preflight=callback_preflight,
        rendered_prompt=rendered_prompt,
        operations=operations,
    )
    request = callback_preflight.projector_preflight.preflight.request
    terminal = json.loads(outcome.events[-1])
    if terminal["event"] not in {"CLEANUP_COMPLETED", "CLEANUP_FAILED"}:
        raise RuntimeError("GENERATION_SUPERVISOR_CLEANUP_TERMINAL_MISSING")
    cleanup_receipt = _cleanup_receipt(terminal)
    lifecycle_identity = terminal["event_identity"]
    if outcome.status == "TERMINAL_OUTPUT":
        runner_result = build_runner_result_v1(
            request=request, status="TERMINAL_OUTPUT",
            lifecycle_terminal_event_identity=lifecycle_identity,
            output=outcome.raw_output,
        )
    elif outcome.status == "CONSTRAINT_LIVENESS_FAILURE":
        receipt_identity = json.loads(outcome.no_legal_token_receipt)["receipt_identity"]
        runner_result = build_runner_result_v1(
            request=request, status="CONSTRAINT_LIVENESS_FAILURE",
            lifecycle_terminal_event_identity=lifecycle_identity,
            no_legal_token_receipt_identity=receipt_identity,
        )
    else:
        runner_result = build_runner_result_v1(
            request=request, status="EXECUTION_FAILURE",
            lifecycle_terminal_event_identity=lifecycle_identity,
            execution_failure_code=outcome.failure_code or "UNCLASSIFIED_EXECUTION_FAILURE",
        )
    value = json.loads(runner_result)
    if outcome.raw_partial_output is not None and value["output_utf8_base64"] is not None:
        raise RuntimeError("GENERATION_SUPERVISOR_PARTIAL_OUTPUT_GAINED_SEMANTIC_AUTHORITY")
    return InjectedGenerationSupervisorResultV1(
        outcome.status, outcome.events, runner_result, outcome.raw_output,
        outcome.raw_partial_output, outcome.compatibility_receipt, cleanup_receipt,
    )


def _cleanup_receipt(terminal: dict[str, object]) -> bytes:
    value = {
        "schema_name": "pastila-semantic-admission-v2-construction-obligation-v2-generation-cleanup-receipt",
        "schema_version": "1.0.0", "supervisor_identity": SUPERVISOR_IDENTITY,
        "worker_terminal_event_identity": terminal["event_identity"],
        "cleanup_status": terminal["event"], "receipt_identity": "",
    }
    value["receipt_identity"] = hashlib.sha256(_canonical(
        {key: item for key, item in value.items() if key != "receipt_identity"}
    )).hexdigest()
    return _canonical(value)


def _canonical(value: dict[str, object]) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


__all__ = (
    "SUPERVISOR_IDENTITY",
    "InjectedGenerationSupervisorResultV1",
    "supervise_injected_generation_v1_2_1",
)


