"""Pure mappings between verified V2 authority and Ollama DTOs."""

from pydantic import ValidationError

from pastila_scout.provider_adapters_v2.ollama import OllamaProviderAdapter
from pastila_scout.provider_execution_v2 import ProviderExecutionRequestV2
from pastila_scout.provider_v2 import ProviderFinishReasonV2, ProviderResultStatusV2

from .errors import OllamaInvalidRequestError, OllamaMalformedResponseError
from .models import (
    OllamaChatMessageV1,
    OllamaChatRequestV1,
    OllamaChatResponseV1,
    OllamaExecutionConfigV1,
)

_ROLES = {"instruction": "system", "context": "user", "generation": "user"}
_FINISH_REASONS = {
    "stop": ProviderFinishReasonV2.COMPLETED,
    "length": ProviderFinishReasonV2.LENGTH,
}


def build_ollama_request(
    request: ProviderExecutionRequestV2, config: OllamaExecutionConfigV1
) -> OllamaChatRequestV1:
    """Build one non-streaming Ollama chat request."""
    expected = OllamaProviderAdapter.descriptor
    if request.provider != expected:
        raise _isolated_mapping_error("request does not belong to Ollama")
    if len(request.request_envelope.request_units) != 1:
        raise _isolated_mapping_error("Ollama requires exactly one request unit")
    options: dict[str, object] = {}
    if config.temperature is not None:
        options["temperature"] = config.temperature
    if config.max_output_tokens is not None:
        options["num_predict"] = config.max_output_tokens
    if config.stop_sequences:
        options["stop"] = list(config.stop_sequences)
    unit = request.request_envelope.request_units[0]
    invalid_mapping = False
    try:
        mapped = OllamaChatRequestV1(
            model=config.model,
            messages=tuple(
                OllamaChatMessageV1(role=_ROLES[item.role], content=item.content)
                for item in unit.messages
            ),
            options=options,
        )
    except (KeyError, TypeError, ValueError, ValidationError):
        invalid_mapping = True
        mapped = None
    if invalid_mapping:
        raise _isolated_mapping_error("invalid Ollama request mapping")
    return mapped


def map_ollama_response(
    response: OllamaChatResponseV1,
) -> tuple[str, ProviderResultStatusV2, ProviderFinishReasonV2, str | None]:
    """Extract only provider-supplied completion semantics."""
    if not response.done:
        raise _isolated_response_error("non-streaming response is incomplete")
    if not response.message.content:
        raise _isolated_response_error("Ollama response contains no output")
    reason = _FINISH_REASONS[response.done_reason]
    if reason is ProviderFinishReasonV2.COMPLETED:
        return response.message.content, ProviderResultStatusV2.SUCCESS, reason, None
    return (
        response.message.content,
        ProviderResultStatusV2.PARTIAL,
        reason,
        f"ollama-finish-{response.done_reason}",
    )


def _isolated_mapping_error(message: str) -> OllamaInvalidRequestError:
    error = OllamaInvalidRequestError(message)
    error.__suppress_context__ = True
    return error


def _isolated_response_error(message: str) -> OllamaMalformedResponseError:
    error = OllamaMalformedResponseError(message)
    error.__suppress_context__ = True
    return error


__all__ = ("build_ollama_request", "map_ollama_response")
