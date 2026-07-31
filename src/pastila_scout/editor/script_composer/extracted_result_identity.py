"""Canonical identities and fingerprints for extracted-result authority."""

from .canonical import semantic_fingerprint
from .extracted_result_models import (
    ExtractedResultDomainModel,
    OpenAIExtractedExecutionResult,
    OpenAIExtractedResponse,
    OpenAIExtractedResponseMessage,
)
from .identity import derive_identity


def _payload(value: ExtractedResultDomainModel):
    payload = value.model_dump(mode="python", exclude={"fingerprint"}, warnings=False)
    if isinstance(value, OpenAIExtractedResponse):
        payload["messages"] = {str(i): item for i, item in enumerate(value.messages)}
    elif isinstance(value, OpenAIExtractedExecutionResult):
        payload["responses"] = {str(i): item for i, item in enumerate(value.responses)}
    return payload


def _identity(kind: str, value: ExtractedResultDomainModel) -> str:
    payload = _payload(value)
    payload.pop("identity", None)
    return derive_identity(kind, payload)


def extracted_result_fingerprint(value: ExtractedResultDomainModel) -> str:
    """Return the semantic fingerprint for extracted authority."""

    return semantic_fingerprint(_payload(value))


def derive_openai_extracted_response_message_identity(
    value: OpenAIExtractedResponseMessage,
) -> str:
    return _identity("openai-extracted-response-message", value)


def derive_openai_extracted_response_identity(value: OpenAIExtractedResponse) -> str:
    return _identity("openai-extracted-response", value)


def derive_openai_extracted_execution_result_identity(
    value: OpenAIExtractedExecutionResult,
) -> str:
    return _identity("openai-extracted-execution-result", value)


def derive_openai_extracted_response_message_fingerprint(
    value: OpenAIExtractedResponseMessage,
) -> str:
    return extracted_result_fingerprint(value)


def derive_openai_extracted_response_fingerprint(
    value: OpenAIExtractedResponse,
) -> str:
    return extracted_result_fingerprint(value)


def derive_openai_extracted_execution_result_fingerprint(
    value: OpenAIExtractedExecutionResult,
) -> str:
    return extracted_result_fingerprint(value)


__all__ = (
    "derive_openai_extracted_execution_result_fingerprint",
    "derive_openai_extracted_execution_result_identity",
    "derive_openai_extracted_response_fingerprint",
    "derive_openai_extracted_response_identity",
    "derive_openai_extracted_response_message_fingerprint",
    "derive_openai_extracted_response_message_identity",
)
