"""Deterministic identities and fingerprints for OpenAI Phase 6.2 DTOs."""

from .canonical import semantic_fingerprint
from .identity import derive_identity
from .openai_mapping_models import (
    OpenAIMappingDomainModel,
    OpenAIProviderMessage,
    OpenAIProviderRequest,
    OpenAIProviderRequestPlan,
)


def _payload(value: OpenAIMappingDomainModel, *, exclude_fingerprint: bool):
    payload = value.model_dump(
        mode="python",
        exclude={"fingerprint"} if exclude_fingerprint else set(),
        warnings=False,
    )
    if isinstance(value, OpenAIProviderRequest):
        payload["messages"] = {str(i): item for i, item in enumerate(value.messages)}
    elif isinstance(value, OpenAIProviderRequestPlan):
        payload["requests"] = {str(i): item for i, item in enumerate(value.requests)}
    return payload


def _identity(kind: str, value: OpenAIMappingDomainModel) -> str:
    payload = _payload(value, exclude_fingerprint=True)
    payload.pop("identity", None)
    return derive_identity(kind, payload)


def openai_mapping_fingerprint(value: OpenAIMappingDomainModel) -> str:
    """Return the canonical semantic fingerprint for an OpenAI mapping."""

    return semantic_fingerprint(_payload(value, exclude_fingerprint=True))


def derive_openai_provider_message_identity(value: OpenAIProviderMessage) -> str:
    return _identity("openai-provider-message", value)


def derive_openai_provider_request_identity(value: OpenAIProviderRequest) -> str:
    return _identity("openai-provider-request", value)


def derive_openai_provider_request_plan_identity(
    value: OpenAIProviderRequestPlan,
) -> str:
    return _identity("openai-provider-request-plan", value)


def derive_openai_provider_message_fingerprint(value: OpenAIProviderMessage) -> str:
    return openai_mapping_fingerprint(value)


def derive_openai_provider_request_fingerprint(value: OpenAIProviderRequest) -> str:
    return openai_mapping_fingerprint(value)


def derive_openai_provider_request_plan_fingerprint(
    value: OpenAIProviderRequestPlan,
) -> str:
    return openai_mapping_fingerprint(value)


__all__ = (
    "derive_openai_provider_message_fingerprint",
    "derive_openai_provider_message_identity",
    "derive_openai_provider_request_fingerprint",
    "derive_openai_provider_request_identity",
    "derive_openai_provider_request_plan_fingerprint",
    "derive_openai_provider_request_plan_identity",
)
