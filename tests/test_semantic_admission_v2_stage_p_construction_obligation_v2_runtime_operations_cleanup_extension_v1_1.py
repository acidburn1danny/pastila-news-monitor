from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_injected_generation_supervisor_v1 import (
    supervise_injected_generation_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_injected_generation_worker_v1 import (
    InjectedCompatibleGenerationResourceV1, InjectedGenerationOperationsV1,
    InjectedGenerationOutputV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_runner_protocol_cleanup_extension_v1_1 import (
    CLEANUP_EXTENSION_IDENTITY, build_cleanup_receipt_v1_1,
    build_result_envelope_v1_1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_runtime_operations_adapter_v1_1 import (
    RUNTIME_OPERATIONS_ADAPTER_IDENTITY, ExplicitRuntimeGenerationOperationsV1_1,
    adapt_runtime_operations_v1_1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_runtime_operations_contract_v1 import (
    DECODER_IDENTITY, DEVICE_TRANSFER_POLICY, TOKENIZER_IDENTITY,
    RuntimePromptBatchV1,
)


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tests"))
from test_semantic_admission_v2_stage_p_construction_obligation_v2_injected_generation_worker_supervisor_v1 import (  # noqa: E402
    COMPATIBILITY, _authority, _policy, _terminal_fixture,
)


def _batch(prompt):
    return RuntimePromptBatchV1(
        (1, 2), (1, 1), 2, hashlib.sha256(prompt.encode()).hexdigest(),
        TOKENIZER_IDENTITY, DECODER_IDENTITY, 1, DEVICE_TRANSFER_POLICY)


def _run(bound, text, generated, operations):
    return supervise_injected_generation_v1(
        raw_policy_receipt=_policy(), raw_authority_receipt=_authority(bound),
        callback_preflight=bound, rendered_prompt="prompt", operations=operations)


def test_explicit_batch_adapter_is_equivalent_to_direct_injected_operations() -> None:
    direct_bound, text, generated = _terminal_fixture()
    direct_resource = object()

    def direct_generate(_resource, prompt_ids, _maximum, allowed):
        assert allowed((*prompt_ids, *generated)) == (2,)
        return InjectedGenerationOutputV1(text.encode(), (*generated, 2), True)

    direct = _run(direct_bound, text, generated, InjectedGenerationOperationsV1(
        lambda _: (1, 2),
        lambda: InjectedCompatibleGenerationResourceV1(
            direct_resource, COMPATIBILITY.read_bytes()),
        direct_generate, lambda _: None))

    adapted_bound, text, generated = _terminal_fixture()
    runtime_resource = object()

    def runtime_generate(_resource, batch, _maximum, allowed):
        assert batch == _batch("prompt")
        assert allowed((*batch.input_token_ids, *generated)) == (2,)
        return InjectedGenerationOutputV1(text.encode(), (*generated, 2), True)

    adapted = _run(adapted_bound, text, generated, adapt_runtime_operations_v1_1(
        rendered_prompt="prompt",
        operations=ExplicitRuntimeGenerationOperationsV1_1(
            _batch("prompt"),
            lambda: InjectedCompatibleGenerationResourceV1(
                runtime_resource, COMPATIBILITY.read_bytes()),
            runtime_generate, lambda _: None)))
    assert adapted.status == direct.status == "TERMINAL_OUTPUT"
    assert adapted.runner_result == direct.runner_result
    assert adapted.lifecycle_events == direct.lifecycle_events
    assert adapted.raw_output == direct.raw_output == text.encode()


def test_cleanup_extension_binds_success_and_partial_failure() -> None:
    bound, text, generated = _terminal_fixture()
    result = _run(bound, text, generated, adapt_runtime_operations_v1_1(
        rendered_prompt="prompt",
        operations=ExplicitRuntimeGenerationOperationsV1_1(
            _batch("prompt"),
            lambda: InjectedCompatibleGenerationResourceV1(
                object(), COMPATIBILITY.read_bytes()),
            lambda resource, batch, maximum, allowed: (
                allowed((*batch.input_token_ids, *generated)) and
                InjectedGenerationOutputV1(text.encode(), (*generated, 2), True)
            ), lambda _: None)))
    request = bound.projector_preflight.preflight.request
    terminal = json.loads(result.lifecycle_events[-1])
    cleanup = build_cleanup_receipt_v1_1(
        provider_request_id=request.provider_request_id,
        source_context_identity=request.source_context_identity,
        worker_terminal_event_identity=terminal["event_identity"],
        cleanup_status="CLEANUP_COMPLETED", cleanup_failure_code=None)
    envelope = json.loads(build_result_envelope_v1_1(
        raw_base_runner_result=result.runner_result,
        raw_cleanup_receipt=cleanup, raw_partial_output=None))
    assert envelope["cleanup_extension_identity"] == CLEANUP_EXTENSION_IDENTITY
    assert envelope["partial_output_semantic_authority"] is False


def test_cleanup_failure_and_partial_authority_mutations_fail_closed() -> None:
    bound, text, generated = _terminal_fixture()
    success = _run(bound, text, generated, InjectedGenerationOperationsV1(
        lambda _: (1, 2),
        lambda: InjectedCompatibleGenerationResourceV1(
            object(), COMPATIBILITY.read_bytes()),
        lambda resource, prompt, maximum, allowed: (
            allowed((*prompt, *generated)) and
            InjectedGenerationOutputV1(text.encode(), (*generated, 2), True)
        ), lambda _: None))
    request = bound.projector_preflight.preflight.request
    terminal = json.loads(success.lifecycle_events[-1])
    failed_cleanup = build_cleanup_receipt_v1_1(
        provider_request_id=request.provider_request_id,
        source_context_identity=request.source_context_identity,
        worker_terminal_event_identity=terminal["event_identity"],
        cleanup_status="CLEANUP_FAILED", cleanup_failure_code="SYNTHETIC")
    with pytest.raises(ValueError, match="SUCCESS_WITHOUT_CLEANUP"):
        build_result_envelope_v1_1(
            raw_base_runner_result=success.runner_result,
            raw_cleanup_receipt=failed_cleanup, raw_partial_output=None)
    completed = build_cleanup_receipt_v1_1(
        provider_request_id=request.provider_request_id,
        source_context_identity=request.source_context_identity,
        worker_terminal_event_identity=terminal["event_identity"],
        cleanup_status="CLEANUP_COMPLETED", cleanup_failure_code=None)
    with pytest.raises(ValueError, match="PARTIAL_OUTPUT_SEMANTIC_AUTHORITY"):
        build_result_envelope_v1_1(
            raw_base_runner_result=success.runner_result,
            raw_cleanup_receipt=completed, raw_partial_output=b"partial")


def test_artifact_adapter_and_cleanup_identities_are_exact_and_no_authority() -> None:
    artifact = json.loads((ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-runtime-operations-cleanup-extension-v1-1.json").read_text("utf-8"))
    assert hashlib.sha256("\n".join(artifact["cleanup_extension"]["identity_derivation"]["ordered_utf8_fields"]).encode()).hexdigest() == CLEANUP_EXTENSION_IDENTITY
    assert hashlib.sha256("\n".join(artifact["adapter"]["identity_derivation"]["ordered_utf8_fields"]).encode()).hexdigest() == RUNTIME_OPERATIONS_ADAPTER_IDENTITY
    assert all(value is False for key, value in artifact["authority"].items()
               if key != "contract_normalization")
    source = "\n".join((ROOT / relative).read_text("utf-8") for relative in (
        "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_runtime_operations_adapter_v1_1.py",
        "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_runner_protocol_cleanup_extension_v1_1.py",
    ))
    assert all(term not in source for term in (
        "from_pretrained", ".generate(", "build_invocation", ".execute(",
        "subprocess", "AutoTokenizer", "AutoModel", "if __name__",
    ))
