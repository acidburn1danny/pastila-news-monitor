"""Deterministic identities and fingerprints for OpenAI Phase 6.3 results."""

from .canonical import semantic_fingerprint
from .identity import derive_identity
from .openai_result_models import (
    OpenAIProviderExecutionResult,
    OpenAIProviderResponse,
    OpenAIProviderResponseMessage,
    OpenAIProviderResultDomainModel,
)


def _payload(value: OpenAIProviderResultDomainModel):
    payload = value.model_dump(mode="python", exclude={"fingerprint"}, warnings=False)
    if isinstance(value, OpenAIProviderResponse):
        payload["messages"] = {str(i): item for i, item in enumerate(value.messages)}
    elif isinstance(value, OpenAIProviderExecutionResult):
        payload["responses"] = {str(i): item for i, item in enumerate(value.responses)}
    return payload


def _identity(kind: str, value: OpenAIProviderResultDomainModel) -> str:
    payload = _payload(value)
    payload.pop("identity", None)
    return derive_identity(kind, payload)


def openai_result_fingerprint(value: OpenAIProviderResultDomainModel) -> str:
    """Return the canonical semantic fingerprint for a concrete result."""

    return semantic_fingerprint(_payload(value))


def derive_openai_provider_response_message_identity(
    value: OpenAIProviderResponseMessage,
) -> str:
    return _identity("openai-provider-response-message", value)


def derive_openai_provider_response_identity(value: OpenAIProviderResponse) -> str:
    return _identity("openai-provider-response", value)


def derive_openai_provider_execution_result_identity(
    value: OpenAIProviderExecutionResult,
) -> str:
    return _identity("openai-provider-execution-result", value)


def derive_openai_provider_response_message_fingerprint(
    value: OpenAIProviderResponseMessage,
) -> str:
    return openai_result_fingerprint(value)


def derive_openai_provider_response_fingerprint(
    value: OpenAIProviderResponse,
) -> str:
    return openai_result_fingerprint(value)


def derive_openai_provider_execution_result_fingerprint(
    value: OpenAIProviderExecutionResult,
) -> str:
    return openai_result_fingerprint(value)


__all__ = (
    "derive_openai_provider_execution_result_fingerprint",
    "derive_openai_provider_execution_result_identity",
    "derive_openai_provider_response_fingerprint",
    "derive_openai_provider_response_identity",
    "derive_openai_provider_response_message_fingerprint",
    "derive_openai_provider_response_message_identity",
)
