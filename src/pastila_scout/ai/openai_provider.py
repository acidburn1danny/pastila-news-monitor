"""OpenAI implementation hidden behind the provider protocol."""

import json
from typing import Any

from pastila_scout.ai.provider import (
    ProviderError,
    StructuredAIRequest,
    StructuredAIResponse,
)
from pastila_scout.config import AIConfig
from pastila_scout.models.ai import (
    EventVerificationRequest,
    ProviderVerificationDecision,
)


class OpenAIProvider:
    """Request strict JSON Schema output through the OpenAI Responses API."""

    def __init__(self, config: AIConfig, api_key: str) -> None:
        self._config = config
        try:
            from openai import OpenAI
        except ImportError as exc:  # pragma: no cover - installation failure
            raise ProviderError("OpenAI SDK is not installed", retryable=False) from exc
        self._client: Any = OpenAI(api_key=api_key)

    def verify(self, request: EventVerificationRequest) -> str:
        """Return provider output text; validation belongs to the verifier."""

        return self.verify_with_diagnostics(request).output_text

    def verify_with_diagnostics(
        self, request: EventVerificationRequest
    ) -> StructuredAIResponse:
        """Run the unchanged verification prompt while retaining usage metadata."""

        return self.complete_structured(
            StructuredAIRequest(
                name="event_verification",
                instructions=(
                    "Compare only the supplied confirmed facts. Decide whether both "
                    "articles describe the same concrete real-world event. Unknown "
                    "entities must be null. Keep reasoning concise."
                ),
                input_json=json.dumps(
                    request.model_dump(mode="json"), ensure_ascii=False
                ),
                json_schema=ProviderVerificationDecision.model_json_schema(),
            )
        )

    def complete_structured(self, request: StructuredAIRequest) -> StructuredAIResponse:
        """Execute a provider-neutral structured task through Responses API."""

        try:
            response = self._client.responses.create(
                model=self._config.model,
                temperature=self._config.temperature,
                instructions=request.instructions,
                input=request.input_json,
                text={
                    "format": {
                        "type": "json_schema",
                        "name": request.name,
                        "strict": True,
                        "schema": request.json_schema,
                    }
                },
            )
        except Exception as exc:  # SDK exception types remain provider-private
            raise ProviderError(f"OpenAI request failed: {type(exc).__name__}") from exc
        output = getattr(response, "output_text", None)
        if not isinstance(output, str) or not output.strip():
            raise ProviderError("OpenAI returned no output text", retryable=False)
        usage = getattr(response, "usage", None)
        return StructuredAIResponse(
            output_text=output,
            input_tokens=_usage_value(usage, "input_tokens"),
            output_tokens=_usage_value(usage, "output_tokens"),
            total_tokens=_usage_value(usage, "total_tokens"),
        )


def _usage_value(usage: object, name: str) -> int | None:
    value = getattr(usage, name, None)
    return int(value) if isinstance(value, int) else None
