"""Single-attempt OpenAI Responses API transport."""

from __future__ import annotations

from collections.abc import Callable
from time import perf_counter
from typing import Any
from weakref import WeakKeyDictionary

from openai import OpenAI
from pydantic import SecretStr

from pastila_scout.editor.generation.ai_provider_adapter import (
    AICredentialProvider,
    AIProviderClientRequest,
    AIProviderClientResponse,
)

from .models import OpenAIResponsesPayload

OpenAIClientFactory = Callable[..., Any]


class OpenAIProviderClient:
    """Perform exactly one SDK attempt per call and preserve its raw response."""

    def __init__(
        self,
        *,
        authentication_reference: str,
        client_factory: OpenAIClientFactory = OpenAI,
        clock: Callable[[], float] = perf_counter,
    ) -> None:
        self._client_factory = client_factory
        self._authentication_reference = authentication_reference
        self._clock = clock
        self._execution_clients: WeakKeyDictionary[object, Any] = WeakKeyDictionary()

    def send(
        self,
        request: AIProviderClientRequest,
        *,
        credential_provider: AICredentialProvider,
    ) -> AIProviderClientResponse:
        """Execute one synchronous Responses API call with no semantic parsing."""

        if not isinstance(request.payload, OpenAIResponsesPayload):
            raise TypeError("invalid OpenAI projected payload")
        sdk_client = self._execution_clients.get(credential_provider)
        if sdk_client is None:
            secret: SecretStr = credential_provider.resolve(
                self._authentication_reference
            )
            options: dict[str, Any] = {
                "api_key": secret.get_secret_value(),
                "max_retries": 0,
            }
            if request.endpoint:
                options["base_url"] = request.endpoint
            sdk_client = self._client_factory(**options)
            self._execution_clients[credential_provider] = sdk_client
        started = self._clock()
        raw_response = sdk_client.responses.create(
            **request.payload.request_arguments(), timeout=request.timeout_seconds
        )
        latency_ms = max(0.0, (self._clock() - started) * 1000)
        return AIProviderClientResponse(payload=raw_response, latency_ms=latency_ms)
