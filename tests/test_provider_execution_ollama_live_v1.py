"""Explicitly opted-in live validation against a local Ollama installation."""

import os
from datetime import UTC, datetime

import httpx
import pytest

from pastila_scout.provider_adapters_v2.ollama import OllamaProviderAdapter
from pastila_scout.provider_execution_ollama_v1 import (
    OllamaExecutionConfigV1,
    OllamaHttpClientV1,
    OllamaProviderExecutorV1,
)
from pastila_scout.provider_execution_v2 import (
    ExecutionContextV2,
    ExecutionOutcomeV2,
    ProviderExecutionRequestV2,
    TimeoutPolicyV2,
)
from pastila_scout.provider_v2 import (
    ProviderMessageInputV2,
    ProviderRequestIntentV2,
    ProviderRequestUnitInputV2,
    build_provider_request_envelope,
)

ZERO = "0" * 64
IDENTITY = f"scout:live-artifact:{ZERO}"


def test_local_qwen3_14b_is_available_and_generates() -> None:
    if os.environ.get("PASTILA_OLLAMA_LIVE") != "1":
        pytest.skip("set PASTILA_OLLAMA_LIVE=1 to enable local Ollama validation")
    try:
        with httpx.Client(base_url="http://localhost:11434", timeout=5) as client:
            tags = client.get("/api/tags")
            tags.raise_for_status()
            names = {item["name"] for item in tags.json().get("models", [])}
            if "qwen3:14b" not in names:
                pytest.skip("qwen3:14b is not installed locally")
            request = _live_request()
            result = OllamaProviderExecutorV1(
                OllamaHttpClientV1(client),
                OllamaExecutionConfigV1(model="qwen3:14b", max_output_tokens=256),
            ).execute(request)
            assert result.outcome is ExecutionOutcomeV2.COMPLETED
            assert result.request_id == request.context.request_id
            assert result.provider_id == request.provider.provider_id
            assert result.request_envelope_identity == request.request_envelope.identity
    except httpx.RequestError:
        pytest.skip("Ollama is not available locally")
    assert result.provider_result is not None
    assert result.provider_result.outputs[0].generated_text


def _live_request() -> ProviderExecutionRequestV2:
    intent = ProviderRequestIntentV2(
        execution_plan_reference="plan:ollama-live",
        execution_plan_identity=IDENTITY,
        execution_plan_fingerprint=ZERO,
        draft_reference="draft:ollama-live",
        draft_fingerprint=ZERO,
        request_units=(
            ProviderRequestUnitInputV2(
                source_request_reference="source:ollama-live",
                ordinal=0,
                messages=(
                    ProviderMessageInputV2(
                        role="generation",
                        content="Reply only with OK. /no_think",
                        ordinal=0,
                    ),
                ),
            ),
        ),
    )
    descriptor = OllamaProviderAdapter.descriptor
    return ProviderExecutionRequestV2(
        provider=descriptor,
        request_intent=intent,
        request_envelope=build_provider_request_envelope(intent, descriptor),
        context=ExecutionContextV2(
            request_id="ollama-live-request",
            requested_at=datetime.now(UTC),
        ),
        timeout_policy=TimeoutPolicyV2(timeout_seconds=60),
    )
