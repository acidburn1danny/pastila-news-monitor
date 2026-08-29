"""Launch-forbidden V1.2.1 injected worker with pre-load capacity admission.

All tokenizer, model, and generation behavior is supplied by test-owned callables.
The module itself imports no runtime and exposes no process entry point.
"""
from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass

from pastila_scout.experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_3 import (
    ConstructionObligationV2RunnerCallbackPreflightV1_3,
)

from .stage_p_construction_obligation_v2_generation_authority_preload_v1_2_1 import (
    GenerationPreloadObservationV1_1,
    parse_generation_authority_v1_2_1,
    validate_generation_preload_v1_2_1,
)
from .stage_p_construction_obligation_v2_generation_execution_policy_gate_v1 import (
    canonical_observed_generation_execution_policy_v1,
    validate_generation_execution_policy_gate_v1,
)

WORKER_IDENTITY_FIELDS = (
    "construction-obligation-v2-injected-generation-worker-v1.2.1",
    "progress-sink:lifecycle-canonical-bytes",
    "progress-sink:compatibility-canonical-bytes",
    "generation-policy:unchanged",
)
WORKER_IDENTITY = hashlib.sha256("\n".join(WORKER_IDENTITY_FIELDS).encode()).hexdigest()
COMPATIBILITY_RECEIPT_IDENTITY = "8ddafa5e60e892abf56a2b67d9ab646deb94a7b024e739ea8ea967c45e3ec39f"


@dataclass(frozen=True, slots=True)
class InjectedCompatibleGenerationResourceV1:
    resource: object
    compatibility_receipt: bytes


@dataclass(frozen=True, slots=True)
class InjectedGenerationOutputV1:
    output: bytes
    generated_token_ids: tuple[int, ...]
    terminal_eos: bool


@dataclass(frozen=True, slots=True)
class InjectedGenerationOperationsV1:
    tokenize_prompt: Callable[[str], Sequence[int]]
    load_compatible: Callable[[], InjectedCompatibleGenerationResourceV1]
    generate_once: Callable[
        [object, tuple[int, ...], int, Callable[[Sequence[int]], tuple[int, ...]]],
        InjectedGenerationOutputV1,
    ]
    cleanup: Callable[[object], None]


@dataclass(frozen=True, slots=True)
class InjectedGenerationWorkerOutcomeV1:
    status: str
    events: tuple[bytes, ...]
    raw_output: bytes | None
    raw_partial_output: bytes | None
    compatibility_receipt: bytes | None
    no_legal_token_receipt: bytes | None
    failure_code: str | None


class ConstraintLivenessStopV1(RuntimeError):
    def __init__(self, receipt: bytes):
        super().__init__("NO_LEGAL_TOKEN_NONTERMINAL")
        self.receipt = receipt


def execute_injected_generation_worker_v1_2_1(
    *, raw_policy_receipt: bytes, raw_authority_receipt: bytes,
    expected_runner_request_sha256: str,
    preload_observation: GenerationPreloadObservationV1_1,
    callback_preflight: ConstructionObligationV2RunnerCallbackPreflightV1_3,
    rendered_prompt: str, operations: InjectedGenerationOperationsV1,
    lifecycle_sink: Callable[[bytes], None] | None = None,
    compatibility_sink: Callable[[bytes], None] | None = None,
) -> InjectedGenerationWorkerOutcomeV1:
    """Run one injected attempt after all identity and prompt checks pass."""
    if type(callback_preflight) is not ConstructionObligationV2RunnerCallbackPreflightV1_3:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_CALLBACK_PREFLIGHT_EXACT_TYPE_REQUIRED")
    if type(operations) is not InjectedGenerationOperationsV1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_GENERATION_OPERATIONS_EXACT_TYPE_REQUIRED")
    if type(rendered_prompt) is not str or not rendered_prompt:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_RENDERED_PROMPT_REQUIRED")
    if lifecycle_sink is not None and not callable(lifecycle_sink):
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_LIFECYCLE_SINK_CALLABLE_REQUIRED")
    if compatibility_sink is not None and not callable(compatibility_sink):
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_COMPATIBILITY_SINK_CALLABLE_REQUIRED")
    expected_policy = validate_generation_execution_policy_gate_v1(
        observed=canonical_observed_generation_execution_policy_v1())
    if raw_policy_receipt != expected_policy:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_GENERATION_POLICY_RECEIPT_MISMATCH")

    request = callback_preflight.projector_preflight.preflight.request
    authority = parse_generation_authority_v1_2_1(
        raw_receipt=raw_authority_receipt,
        expected_host_payload_sha256=request.host_payload_sha256,
        expected_runner_request_sha256=expected_runner_request_sha256,
        expected_provider_request_id=request.provider_request_id,
        expected_source_context_identity=request.source_context_identity,
    )
    validate_generation_preload_v1_2_1(
        authority=authority, observed=preload_observation)
    if not 0 < request.max_output_tokens <= 3200:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_OUTPUT_TOKEN_CEILING_INVALID")
    prompt_ids = _token_ids(operations.tokenize_prompt(rendered_prompt), "PROMPT")
    if not prompt_ids or len(prompt_ids) > 8192:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_PROMPT_TOKEN_CEILING_EXCEEDED")

    events: list[bytes] = []
    previous: str | None = None
    resource: object | None = None
    compatibility: bytes | None = None
    output: bytes | None = None
    partial: bytes | None = None
    no_legal: bytes | None = None
    failure: str | None = None
    callback_count = 0
    last_terminal = False
    last_eos_allowed = False
    last_projected_generated_ids: tuple[int, ...] = ()

    def emit(event: str, detail: dict[str, object]) -> None:
        nonlocal previous
        raw = _event(request.provider_request_id, len(events), event, detail, previous)
        previous = json.loads(raw)["event_identity"]
        events.append(raw)
        if lifecycle_sink is not None:
            lifecycle_sink(raw)

    try:
        emit("MODEL_LOAD_STARTED", {"prompt_token_count": len(prompt_ids)})
        loaded = operations.load_compatible()
        if type(loaded) is not InjectedCompatibleGenerationResourceV1 or loaded.resource is None:
            raise RuntimeError("COMPATIBLE_GENERATION_RESOURCE_MISSING")
        resource = loaded.resource
        validate_compatibility_receipt_v1_2_1(loaded.compatibility_receipt)
        compatibility = loaded.compatibility_receipt
        if compatibility_sink is not None:
            compatibility_sink(compatibility)
        emit("MODEL_LOAD_COMPLETED", {
            "compatibility_receipt_identity": COMPATIBILITY_RECEIPT_IDENTITY,
        })

        def allowed(input_ids: Sequence[int]) -> tuple[int, ...]:
            nonlocal callback_count, last_terminal, last_eos_allowed
            nonlocal last_projected_generated_ids
            ids = _token_ids(input_ids, "GENERATION_INPUT")
            decision = callback_preflight.project_input_ids(
                input_token_ids=ids,
                prompt_token_count=len(prompt_ids),
                decode_generated=lambda generated: _decode_from_preflight(
                    callback_preflight, generated),
            )
            callback_count += 1
            last_projected_generated_ids = ids[len(prompt_ids):]
            last_terminal = decision.projection_receipt.terminal
            last_eos_allowed = decision.projection_receipt.eos_allowed
            if decision.no_legal_token_receipt is not None:
                raise ConstraintLivenessStopV1(decision.no_legal_token_receipt)
            if not decision.allowed_token_ids:
                raise RuntimeError("EMPTY_ALLOWED_TOKEN_SET_WITHOUT_RECEIPT")
            return decision.allowed_token_ids

        emit("GENERATION_STARTED", {
            "maximum_output_tokens": request.max_output_tokens,
            "sole_callback": "REQUEST_BOUND_PROJECTOR_V1_3",
        })
        generated = operations.generate_once(
            resource, prompt_ids, request.max_output_tokens, allowed)
        if type(generated) is not InjectedGenerationOutputV1:
            raise RuntimeError("GENERATION_OUTPUT_EXACT_TYPE_REQUIRED")
        if not generated.terminal_eos:
            partial = generated.output or None
        generated_ids = _token_ids(generated.generated_token_ids, "GENERATED")
        if len(generated_ids) > request.max_output_tokens:
            raise RuntimeError("GENERATION_OUTPUT_TOKEN_CEILING_EXCEEDED")
        eos_token_id = callback_preflight.projector_preflight.preflight.token_piece_bundle.eos_token_id
        if generated_ids != (*last_projected_generated_ids, eos_token_id):
            raise RuntimeError("GENERATION_OUTPUT_CALLBACK_SEQUENCE_MISMATCH")
        if callback_count == 0:
            raise RuntimeError("CONSTRAINED_CALLBACK_NOT_INVOKED")
        if not generated.terminal_eos or not generated.output or not last_terminal or not last_eos_allowed:
            partial = generated.output or None
            raise RuntimeError("NONTERMINAL_OR_UNBOUND_PARTIAL_OUTPUT")
        output = generated.output
        emit("TERMINAL_EOS", {
            "generated_token_count": len(generated_ids),
            "output_sha256": hashlib.sha256(output).hexdigest(),
        })
        status = "TERMINAL_OUTPUT"
    except ConstraintLivenessStopV1 as exc:
        no_legal = exc.receipt
        failure = "NO_LEGAL_TOKEN_NONTERMINAL"
        emit("NO_LEGAL_TOKEN", {
            "receipt_identity": json.loads(no_legal)["receipt_identity"],
        })
        status = "CONSTRAINT_LIVENESS_FAILURE"
    except Exception as exc:  # noqa: BLE001 - execution failures become typed receipts
        failure = (type(exc).__name__ + ":" + str(exc))[:200]
        emit("EXECUTION_FAILED", {"failure_code": failure})
        status = "EXECUTION_FAILURE"
    finally:
        cleanup_failure = None
        if resource is not None:
            try:
                operations.cleanup(resource)
            except Exception as exc:  # noqa: BLE001 - cleanup must remain fail-closed
                cleanup_failure = type(exc).__name__
        emit("CLEANUP_COMPLETED" if cleanup_failure is None else "CLEANUP_FAILED", {
            "failure_type": cleanup_failure,
        })
        if cleanup_failure is not None:
            output = None
            partial = partial or b"CLEANUP_FAILED_AFTER_OUTPUT" if status == "TERMINAL_OUTPUT" else partial
            no_legal = None
            failure = "CLEANUP_FAILED:" + cleanup_failure
            status = "EXECUTION_FAILURE"
    return InjectedGenerationWorkerOutcomeV1(
        status, tuple(events), output, partial, compatibility, no_legal, failure)


def _decode_from_preflight(callback_preflight, generated: Sequence[int]) -> str:
    pieces = callback_preflight.projector_preflight.preflight.token_piece_bundle.token_pieces
    try:
        return "".join(pieces[item] for item in generated)
    except KeyError as exc:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_GENERATED_TOKEN_UNKNOWN") from exc


def validate_compatibility_receipt_v1_2_1(raw: bytes) -> None:
    try:
        value = json.loads(raw.decode("ascii", errors="strict"))
    except Exception as exc:
        raise ValueError("GENERATION_COMPATIBILITY_RECEIPT_INVALID") from exc
    if (
        type(value) is not dict
        or value.get("receipt_identity") != COMPATIBILITY_RECEIPT_IDENTITY
        or value.get("classification") != "STRUCTURAL_NO_OP_VISION_TARGET_OVERMATCH"
        or value.get("expected_vision_missing_key_count") != 336
        or value.get("unexpected_missing_or_extra_key_count") != 0
        or value.get("generation_authorized") is not False
        or raw != _canonical(value)
    ):
        raise ValueError("GENERATION_COMPATIBILITY_RECEIPT_MISMATCH")


def _token_ids(value: Sequence[int], label: str) -> tuple[int, ...]:
    if isinstance(value, (str, bytes)):
        raise TypeError(f"CONSTRUCTION_OBLIGATION_V2_{label}_TOKEN_IDS_INVALID")
    result = tuple(value)
    if any(type(item) is not int or item < 0 for item in result):
        raise ValueError(f"CONSTRUCTION_OBLIGATION_V2_{label}_TOKEN_IDS_INVALID")
    return result


def _event(provider_request_id, sequence, event, detail, previous):
    value = {
        "schema_name": "pastila-semantic-admission-v2-construction-obligation-v2-injected-generation-event",
        "schema_version": "1.0.0", "worker_identity": WORKER_IDENTITY,
        "provider_request_id": provider_request_id, "sequence": sequence,
        "event": event, "detail": detail, "previous_event_identity": previous,
        "event_identity": "",
    }
    value["event_identity"] = hashlib.sha256(_canonical(
        {key: item for key, item in value.items() if key != "event_identity"}
    )).hexdigest()
    return _canonical(value)


def _canonical(value: dict[str, object]) -> bytes:
    return (json.dumps(value, ensure_ascii=True, sort_keys=True,
                       separators=(",", ":"), allow_nan=False) + "\n").encode()


__all__ = (
    "WORKER_IDENTITY",
    "WORKER_IDENTITY_FIELDS",
    "ConstraintLivenessStopV1",
    "InjectedCompatibleGenerationResourceV1",
    "InjectedGenerationOperationsV1",
    "InjectedGenerationOutputV1",
    "InjectedGenerationWorkerOutcomeV1",
    "execute_injected_generation_worker_v1_2_1",
    "validate_compatibility_receipt_v1_2_1",
)
