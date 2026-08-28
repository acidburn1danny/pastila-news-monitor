"""Deferred V1.2 child binding for the exact V1.1 worker types."""
from __future__ import annotations

import hashlib

from pastila_scout.experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_1 import ConstructionObligationV2RunnerPreflightV1_1
from pastila_scout.experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_2 import bind_static_projector_preflight_v1_2
from pastila_scout.experimental_core_v1_2_stage_p_construction_obligation_v2_runner_v1_3 import bind_static_callback_preflight_v1_3

from . import stage_p_construction_obligation_v2_linux_child_process_adapter_v1_1 as legacy
from .stage_p_construction_obligation_v2_generation_authority_preload_v1_1 import parse_generation_authority_v1_1
from .stage_p_construction_obligation_v2_host_wsl_payload_contract_v1 import parse_construction_obligation_v2_host_wsl_payload_v1
from .stage_p_construction_obligation_v2_injected_generation_supervisor_v1_1 import supervise_injected_generation_v1_1
from .stage_p_construction_obligation_v2_linux_generation_supervisor_candidate_v1_1 import InjectedChildProcessOperationsV1, LinuxGenerationChildInvocationV1
from .stage_p_construction_obligation_v2_linux_preload_observer_v1_1 import observe_linux_generation_preload_v1_1
from .stage_p_construction_obligation_v2_linux_runtime_operations_adapter_v1_1 import prepare_linux_runtime_operations_v1_1
from .stage_p_construction_obligation_v2_runner_protocol_codec_v1 import parse_runner_request_v1
from .stage_p_construction_obligation_v2_runtime_operations_adapter_v1_2 import adapt_runtime_operations_v1_2

LINUX_CHILD_PROCESS_ADAPTER_IDENTITY_FIELDS = (
    "construction-obligation-v2-linux-child-process-adapter-v1.2",
    "process-lifecycle:v1.1-byte-preserved",
    "runtime-adapter:v1.2",
    "linux-runtime-adapter:v1.1",
)
LINUX_CHILD_PROCESS_ADAPTER_IDENTITY = hashlib.sha256(
    "\n".join(LINUX_CHILD_PROCESS_ADAPTER_IDENTITY_FIELDS).encode()
).hexdigest()


class _ContextV1_2:
    """Replace only the frozen child target; delegate lifecycle primitives."""
    def __init__(self, context: object):
        self._context = context

    def Queue(self, *args, **kwargs):
        return self._context.Queue(*args, **kwargs)

    def Process(self, *, target, kwargs, daemon):
        if target is not legacy._run_linux_generation_child_v1_1:
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_LEGACY_CHILD_TARGET_DRIFT")
        return self._context.Process(
            target=_run_linux_generation_child_v1_2, kwargs=kwargs, daemon=daemon
        )


def build_linux_child_process_operations_v1_2(
    *, raw_policy_receipt: bytes, raw_authority_receipt: bytes, context_factory=None,
) -> InjectedChildProcessOperationsV1:
    if context_factory is None:
        context_factory = legacy._spawn_context

    def v1_2_context(method: str):
        if method != "spawn":
            raise ValueError("CONSTRUCTION_OBLIGATION_V2_PROCESS_METHOD_DRIFT")
        return _ContextV1_2(context_factory(method))

    operations = legacy.build_linux_child_process_operations_v1_1(
        raw_policy_receipt=raw_policy_receipt,
        raw_authority_receipt=raw_authority_receipt,
        context_factory=v1_2_context,
    )
    if type(operations) is not InjectedChildProcessOperationsV1:
        raise TypeError("CONSTRUCTION_OBLIGATION_V2_CHILD_OPERATIONS_EXACT_TYPE_REQUIRED")
    return operations


def _run_linux_generation_child_v1_2(
    *, invocation: LinuxGenerationChildInvocationV1, raw_policy_receipt: bytes,
    raw_authority_receipt: bytes, result_queue: object,
) -> None:
    request = parse_runner_request_v1(raw_request=invocation.raw_runner_request)
    host = parse_construction_obligation_v2_host_wsl_payload_v1(raw_payload=request.host_payload)
    authority = parse_generation_authority_v1_1(
        raw_receipt=raw_authority_receipt,
        expected_host_payload_sha256=request.host_payload_sha256,
        expected_runner_request_sha256=hashlib.sha256(invocation.raw_runner_request).hexdigest(),
        expected_provider_request_id=request.provider_request_id,
        expected_source_context_identity=request.source_context_identity,
    )
    if authority.authority_receipt_identity != invocation.authority_receipt_identity:
        raise ValueError("CONSTRUCTION_OBLIGATION_V2_CHILD_AUTHORITY_IDENTITY_MISMATCH")
    preload = observe_linux_generation_preload_v1_1(
        base_manifest_sha256="bd0f84711c825a2c213b458a0e2c41d189914ad5ac4bdf283c91a38daab0c090",
        adapter_manifest_sha256="312d6f8cb7c14c769742901c4c80042c104f5a60ba2f80b2913487af22d67ae2",
    )
    prepared = prepare_linux_runtime_operations_v1_1(
        rendered_prompt=host.rendered_prompt, system_prompt=invocation.system_prompt
    )
    base = ConstructionObligationV2RunnerPreflightV1_1(request, prepared.token_piece_bundle)
    projector = bind_static_projector_preflight_v1_2(preflight=base)
    callback = bind_static_callback_preflight_v1_3(projector_preflight=projector)
    operations = adapt_runtime_operations_v1_2(
        rendered_prompt=host.rendered_prompt, operations=prepared.operations
    )
    result = supervise_injected_generation_v1_1(
        raw_policy_receipt=raw_policy_receipt,
        raw_authority_receipt=raw_authority_receipt,
        expected_runner_request_sha256=hashlib.sha256(invocation.raw_runner_request).hexdigest(),
        preload_observation=preload,
        callback_preflight=callback,
        rendered_prompt=host.rendered_prompt,
        operations=operations,
    )
    result_queue.put(result, block=True, timeout=10.0)


__all__ = (
    "LINUX_CHILD_PROCESS_ADAPTER_IDENTITY",
    "LINUX_CHILD_PROCESS_ADAPTER_IDENTITY_FIELDS",
    "build_linux_child_process_operations_v1_2",
)
