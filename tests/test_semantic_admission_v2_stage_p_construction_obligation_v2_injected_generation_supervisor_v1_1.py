from __future__ import annotations

import json

import pytest
from test_semantic_admission_v2_stage_p_construction_obligation_v2_injected_generation_worker_supervisor_v1 import (
    COMPATIBILITY,
    _policy,
    _terminal_fixture,
)
from test_semantic_admission_v2_stage_p_construction_obligation_v2_injected_generation_worker_v1_1 import (
    RUNNER_REQUEST_SHA256,
    _authority,
    _observation,
)

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_injected_generation_supervisor_v1_1 import (
    supervise_injected_generation_v1_1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_injected_generation_worker_v1_1 import (
    InjectedCompatibleGenerationResourceV1,
    InjectedGenerationOperationsV1,
    InjectedGenerationOutputV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_tokenizer_piece_adapter_v1 import (
    EOS_TOKEN_ID,
)


def test_supervisor_propagates_preload_before_worker_lifecycle() -> None:
    bound, _, _ = _terminal_fixture()
    calls = []
    with pytest.raises(ValueError, match="INSUFFICIENT_FREE_VRAM"):
        supervise_injected_generation_v1_1(
            raw_policy_receipt=_policy(), raw_authority_receipt=_authority(bound),
            expected_runner_request_sha256=RUNNER_REQUEST_SHA256,
            preload_observation=_observation(13999), callback_preflight=bound,
            rendered_prompt="synthetic", operations=InjectedGenerationOperationsV1(
                lambda _: calls.append("tokenize"), lambda: calls.append("load"),
                lambda *args: calls.append("generate"), lambda _: calls.append("cleanup")))
    assert calls == []


def test_supervisor_builds_bound_terminal_result_after_admission() -> None:
    bound, text, generated = _terminal_fixture()
    resource = object()

    def generate(_resource, prompt_ids, _maximum, allowed):
        assert allowed((*prompt_ids, *generated)) == (EOS_TOKEN_ID,)
        return InjectedGenerationOutputV1(text.encode(), (*generated, EOS_TOKEN_ID), True)

    result = supervise_injected_generation_v1_1(
        raw_policy_receipt=_policy(), raw_authority_receipt=_authority(bound),
        expected_runner_request_sha256=RUNNER_REQUEST_SHA256,
        preload_observation=_observation(15000), callback_preflight=bound,
        rendered_prompt="synthetic", operations=InjectedGenerationOperationsV1(
            lambda _: (1,), lambda: InjectedCompatibleGenerationResourceV1(
                resource, COMPATIBILITY.read_bytes()), generate, lambda _: None))
    assert result.status == "TERMINAL_OUTPUT"
    assert json.loads(result.runner_result)["terminal_eos"] is True
