"""Deferred spawn-process adapter for Construction-Obligation V2 generation.

The adapter maps the committed Linux runtime operations onto the injected
supervisor process protocol.  Import and construction do not launch a process;
the returned ``start`` callable is the sole execution-authority boundary.
"""

from __future__ import annotations

import hashlib
from collections.abc import Callable
from dataclasses import dataclass

from pastila_scout.experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_1 import (
    ConstructionObligationV2RunnerPreflightV1_1,
)
from pastila_scout.experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_2 import (
    bind_static_projector_preflight_v1_2,
)
from pastila_scout.experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_3 import (
    bind_static_callback_preflight_v1_3,
)

from .stage_p_construction_obligation_v2_generation_authority_preload_v1_2_1 import (
    parse_generation_authority_v1_2_1,
)
from .stage_p_construction_obligation_v2_generation_execution_policy_gate_v1 import (
    canonical_observed_generation_execution_policy_v1,
    validate_generation_execution_policy_gate_v1,
)
from .stage_p_construction_obligation_v2_host_wsl_payload_contract_v1 import (
    parse_construction_obligation_v2_host_wsl_payload_v1,
)
from .stage_p_construction_obligation_v2_injected_generation_supervisor_v1_2_1 import (
    SUPERVISOR_IDENTITY, InjectedGenerationSupervisorResultV1,
    supervise_injected_generation_v1_2_1,
)
from .stage_p_construction_obligation_v2_linux_generation_supervisor_candidate_v1_2_1 import (
    SYSTEM_PROMPT_SHA256,
    InjectedChildProcessOperationsV1,
    LinuxGenerationChildInvocationV1,
)
from .stage_p_construction_obligation_v2_linux_preload_observer_v1_1 import (
    observe_linux_generation_preload_v1_1,
)
from .stage_p_construction_obligation_v2_linux_runtime_operations_adapter_v1_1 import (
    prepare_linux_runtime_operations_v1_1,
)
from .stage_p_construction_obligation_v2_runner_protocol_codec_v1 import (
    parse_runner_request_v1,
)
from .stage_p_construction_obligation_v2_runtime_operations_adapter_v1_2_1 import (
    RUNTIME_OPERATIONS_ADAPTER_IDENTITY,
    adapt_runtime_operations_v1_2_1,
)

CANONICAL_PROVIDER_EXECUTION_SOURCE_SHA256 = (
    "8db391d93872c049b331c386767dcebfba8bc23112c3ed6f7319c6d63af7d2f7"
)
CANONICAL_PROVIDER_EXECUTION_REQUEST_TYPE = (
    "pastila_scout.provider_execution_v2.models.ProviderExecutionRequestV2"
)
CANONICAL_APPLICATION_REQUEST_SOURCE_SHA256 = (
    "dbb2a3a2fc894a0fe83834891b92fed635570af5aededbe0ed08cbc19b090994"
)
CANONICAL_APPLICATION_PROVIDER_REQUEST_TYPE = (
    "pastila_scout.application_request_authority_v1.models.ApplicationProviderRequestV1"
)
LINUX_CHILD_PROCESS_ADAPTER_IDENTITY_FIELDS = (
    "construction-obligation-v2-linux-child-process-adapter-v1.2.1",
    "provider-execution-source:" + CANONICAL_PROVIDER_EXECUTION_SOURCE_SHA256,
    "provider-request-type:" + CANONICAL_PROVIDER_EXECUTION_REQUEST_TYPE,
    "application-request-source:" + CANONICAL_APPLICATION_REQUEST_SOURCE_SHA256,
    "application-request-type:" + CANONICAL_APPLICATION_PROVIDER_REQUEST_TYPE,
    "runtime-operations-adapter:" + RUNTIME_OPERATIONS_ADAPTER_IDENTITY,
    "injected-supervisor:" + SUPERVISOR_IDENTITY,
    "progress-channel:bounded-lifecycle-compatibility-and-generation-aggregate",
    "progress-collection:once-after-child-terminal",
    "deferred-spawn:sole-start-edge",
)
LINUX_CHILD_PROCESS_ADAPTER_IDENTITY = hashlib.sha256(
    "\n".join(LINUX_CHILD_PROCESS_ADAPTER_IDENTITY_FIELDS).encode()
).hexdigest()


@dataclass(slots=True)
class LinuxGenerationProcessHandleV1:
    process: object
    result_queue: object
    progress_queue: object
    result_collected: bool = False
    progress_collected: bool = False


def build_linux_child_process_operations_v1_2_1(
    *,
    raw_policy_receipt: bytes,
    raw_authority_receipt: bytes,
    context_factory: Callable[[str], object] | None = None,
) -> InjectedChildProcessOperationsV1:
    """Construct deferred spawn operations; do not start a child."""
    if (
        type(raw_policy_receipt) is not bytes
        or type(raw_authority_receipt) is not bytes
    ):
        raise TypeError(
            "CONSTRUCTION_OBLIGATION_V2_CHILD_PROCESS_RECEIPTS_BYTES_REQUIRED"
        )
    expected_policy = validate_generation_execution_policy_gate_v1(
        observed=canonical_observed_generation_execution_policy_v1()
    )
    if raw_policy_receipt != expected_policy:
        raise ValueError(
            "CONSTRUCTION_OBLIGATION_V2_GENERATION_POLICY_RECEIPT_MISMATCH"
        )
    if context_factory is None:
        context_factory = _spawn_context
    if not callable(context_factory):
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_PROCESS_CONTEXT_FACTORY_REQUIRED")
    context = context_factory("spawn")
    if context is None or not callable(getattr(context, "Process", None)):
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_SPAWN_CONTEXT_INVALID")
    started = False

    def start(
        invocation: LinuxGenerationChildInvocationV1,
    ) -> LinuxGenerationProcessHandleV1:
        nonlocal started
        if type(invocation) is not LinuxGenerationChildInvocationV1:
            raise TypeError(
                "CONSTRUCTION_OBLIGATION_V2_CHILD_INVOCATION_EXACT_TYPE_REQUIRED"
            )
        if started:
            raise RuntimeError(
                "CONSTRUCTION_OBLIGATION_V2_CHILD_START_CEILING_EXCEEDED"
            )
        request = parse_runner_request_v1(raw_request=invocation.raw_runner_request)
        authority = parse_generation_authority_v1_2_1(
            raw_receipt=raw_authority_receipt,
            expected_host_payload_sha256=request.host_payload_sha256,
            expected_runner_request_sha256=hashlib.sha256(
                invocation.raw_runner_request).hexdigest(),
            expected_provider_request_id=request.provider_request_id,
            expected_source_context_identity=request.source_context_identity,
        )
        if (
            authority.authority_receipt_identity
            != invocation.authority_receipt_identity
        ):
            raise ValueError(
                "CONSTRUCTION_OBLIGATION_V2_CHILD_AUTHORITY_IDENTITY_MISMATCH"
            )
        if (
            type(invocation.system_prompt) is not str
            or hashlib.sha256(invocation.system_prompt.encode("utf-8")).hexdigest()
            != SYSTEM_PROMPT_SHA256
        ):
            raise ValueError(
                "CONSTRUCTION_OBLIGATION_V2_SYSTEM_PROMPT_IDENTITY_MISMATCH"
            )
        started = True
        result_queue = context.Queue(maxsize=1)
        progress_queue = context.Queue(maxsize=32)
        process = context.Process(
            target=_run_linux_generation_child_v1_2_1,
            kwargs={
                "invocation": invocation,
                "raw_policy_receipt": raw_policy_receipt,
                "raw_authority_receipt": raw_authority_receipt,
                "result_queue": result_queue,
                "progress_queue": progress_queue,
            },
            daemon=False,
        )
        handle = LinuxGenerationProcessHandleV1(process, result_queue, progress_queue)
        try:
            process.start()
        except Exception:
            result_queue.close()
            result_queue.join_thread()
            progress_queue.close()
            progress_queue.join_thread()
            raise
        return handle

    def join(handle: object, timeout: float) -> None:
        _handle(handle).process.join(timeout)

    def is_alive(handle: object) -> bool:
        return bool(_handle(handle).process.is_alive())

    def terminate(handle: object) -> None:
        _handle(handle).process.terminate()

    def kill(handle: object) -> None:
        _handle(handle).process.kill()

    def exit_code(handle: object) -> int | None:
        observed = _handle(handle).process.exitcode
        if observed is not None and type(observed) is not int:
            raise TypeError("CONSTRUCTION_OBLIGATION_V2_CHILD_EXIT_CODE_INVALID")
        return observed

    def collect_result(handle: object) -> InjectedGenerationSupervisorResultV1 | None:
        bound = _handle(handle)
        if bound.process.is_alive():
            raise RuntimeError(
                "CONSTRUCTION_OBLIGATION_V2_CHILD_RESULT_REQUESTED_WHILE_ALIVE"
            )
        if bound.result_collected:
            raise RuntimeError(
                "CONSTRUCTION_OBLIGATION_V2_CHILD_RESULT_ALREADY_COLLECTED"
            )
        bound.result_collected = True
        try:
            result = bound.result_queue.get(block=True, timeout=1.0)
        except Exception as exc:
            if type(exc).__name__ != "Empty":
                raise
            result = None
        finally:
            bound.result_queue.close()
            bound.result_queue.join_thread()
        if (
            result is not None
            and type(result) is not InjectedGenerationSupervisorResultV1
        ):
            raise TypeError(
                "CONSTRUCTION_OBLIGATION_V2_CHILD_RESULT_EXACT_TYPE_REQUIRED"
            )
        return result

    def collect_progress(handle: object) -> tuple[tuple[str, bytes], ...]:
        bound = _handle(handle)
        if bound.process.is_alive():
            raise RuntimeError("CONSTRUCTION_OBLIGATION_V2_CHILD_PROGRESS_REQUESTED_WHILE_ALIVE")
        if bound.progress_collected:
            raise RuntimeError("CONSTRUCTION_OBLIGATION_V2_CHILD_PROGRESS_ALREADY_COLLECTED")
        bound.progress_collected = True
        values = []
        try:
            while True:
                values.append(bound.progress_queue.get(block=True, timeout=0.1))
        except Exception as exc:
            if type(exc).__name__ != "Empty":
                raise
        finally:
            bound.progress_queue.close()
            bound.progress_queue.join_thread()
        if any(type(item) is not tuple or len(item) != 2
                   or item[0] not in {"lifecycle", "compatibility", "generation_progress"}
               or type(item[1]) is not bytes for item in values):
            raise TypeError("CONSTRUCTION_OBLIGATION_V2_CHILD_PROGRESS_BYTES_REQUIRED")
        return tuple(values)

    return InjectedChildProcessOperationsV1(
        start, join, is_alive, terminate, kill, exit_code, collect_result,
        collect_progress,
    )


def _run_linux_generation_child_v1_2_1(
    *,
    invocation: LinuxGenerationChildInvocationV1,
    raw_policy_receipt: bytes,
    raw_authority_receipt: bytes,
    result_queue: object,
    progress_queue: object,
) -> None:
    """Child-only runtime binding; called solely as the spawn target."""
    request = parse_runner_request_v1(raw_request=invocation.raw_runner_request)
    host = parse_construction_obligation_v2_host_wsl_payload_v1(
        raw_payload=request.host_payload
    )
    authority = parse_generation_authority_v1_2_1(
        raw_receipt=raw_authority_receipt,
        expected_host_payload_sha256=request.host_payload_sha256,
        expected_runner_request_sha256=hashlib.sha256(
            invocation.raw_runner_request).hexdigest(),
        expected_provider_request_id=request.provider_request_id,
        expected_source_context_identity=request.source_context_identity,
    )
    if authority.authority_receipt_identity != invocation.authority_receipt_identity:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_CHILD_AUTHORITY_IDENTITY_MISMATCH")
    preload_observation = observe_linux_generation_preload_v1_1(
        base_manifest_sha256=(
            "bd0f84711c825a2c213b458a0e2c41d189914ad5ac4bdf283c91a38daab0c090"),
        adapter_manifest_sha256=(
            "312d6f8cb7c14c769742901c4c80042c104f5a60ba2f80b2913487af22d67ae2"),
    )
    prepared = prepare_linux_runtime_operations_v1_1(
        rendered_prompt=host.rendered_prompt, system_prompt=invocation.system_prompt
    )
    base = ConstructionObligationV2RunnerPreflightV1_1(
        request, prepared.token_piece_bundle
    )
    projector = bind_static_projector_preflight_v1_2(preflight=base)
    callback = bind_static_callback_preflight_v1_3(projector_preflight=projector)
    operations = adapt_runtime_operations_v1_2_1(
        rendered_prompt=host.rendered_prompt, operations=prepared.operations
    )
    result = supervise_injected_generation_v1_2_1(
        raw_policy_receipt=raw_policy_receipt,
        raw_authority_receipt=raw_authority_receipt,
        expected_runner_request_sha256=hashlib.sha256(
            invocation.raw_runner_request).hexdigest(),
        preload_observation=preload_observation,
        callback_preflight=callback,
        rendered_prompt=host.rendered_prompt,
        operations=operations,
        lifecycle_sink=lambda raw: progress_queue.put(
            ("lifecycle", raw), block=True, timeout=10.0),
        compatibility_sink=lambda raw: progress_queue.put(
            ("compatibility", raw), block=True, timeout=10.0),
        generation_progress_sink=lambda raw: progress_queue.put(
            ("generation_progress", raw), block=True, timeout=10.0),
    )
    result_queue.put(result, block=True, timeout=10.0)


def _handle(value: object) -> LinuxGenerationProcessHandleV1:
    if type(value) is not LinuxGenerationProcessHandleV1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_PROCESS_HANDLE_EXACT_TYPE_REQUIRED")
    return value


def _spawn_context(method: str) -> object:
    import multiprocessing

    return multiprocessing.get_context(method)


__all__ = (
    "LINUX_CHILD_PROCESS_ADAPTER_IDENTITY",
    "LinuxGenerationProcessHandleV1",
    "build_linux_child_process_operations_v1_2_1",
)
