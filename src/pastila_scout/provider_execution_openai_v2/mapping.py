"""Pure deterministic mappings for the OpenAI execution specification."""

from pydantic import ValidationError

from pastila_scout.provider_adapters_v2.openai import OpenAIProviderAdapter
from pastila_scout.provider_execution_v2 import (
    ExecutionOutcomeV2,
    ProviderExecutionRequestV2,
    ProviderExecutionResultV2,
)
from pastila_scout.provider_v2 import (
    ProviderOutputInputV2,
    ProviderResultProjectionV2,
    build_provider_result_envelope,
)

from .errors import (
    OpenAIConfigurationError,
    OpenAIRequestMappingError,
    OpenAIResponseMappingError,
)
from .models import (
    OpenAIClientErrorCategoryV2,
    OpenAIExecutionConfigV2,
    OpenAIExecutionMessageV2,
    OpenAIExecutionRequestV2,
    OpenAIExecutionResponseV2,
)

_ROLE_MAPPING = {
    "instruction": "system",
    "context": "user",
    "generation": "user",
}

_FAILURE_OUTCOMES = {
    OpenAIClientErrorCategoryV2.AUTHENTICATION: ExecutionOutcomeV2.PROVIDER_FAILURE,
    OpenAIClientErrorCategoryV2.RATE_LIMITED: ExecutionOutcomeV2.PROVIDER_FAILURE,
    OpenAIClientErrorCategoryV2.INVALID_REQUEST: ExecutionOutcomeV2.PROVIDER_FAILURE,
    OpenAIClientErrorCategoryV2.PROVIDER_UNAVAILABLE: (
        ExecutionOutcomeV2.PROVIDER_FAILURE
    ),
    OpenAIClientErrorCategoryV2.TIMEOUT: ExecutionOutcomeV2.TIMEOUT,
    OpenAIClientErrorCategoryV2.CANCELLED: ExecutionOutcomeV2.CANCELLED,
    OpenAIClientErrorCategoryV2.MALFORMED_RESPONSE: (
        ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE
    ),
    OpenAIClientErrorCategoryV2.INTERNAL_CLIENT_ERROR: (
        ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE
    ),
}


def build_openai_execution_request(
    request: ProviderExecutionRequestV2,
    config: OpenAIExecutionConfigV2,
) -> OpenAIExecutionRequestV2:
    """Map verified provider-neutral authority into an immutable OpenAI DTO."""

    authority = _execution_request(request)
    settings = _config(config)
    expected = OpenAIProviderAdapter.descriptor
    if (
        authority.provider.provider_id != "openai"
        or authority.provider.identity != expected.identity
        or authority.provider.fingerprint != expected.fingerprint
        or authority.provider.adapter_identity != expected.adapter_identity
    ):
        raise OpenAIRequestMappingError("request does not belong to OpenAI authority")
    messages = []
    for unit in authority.request_envelope.request_units:
        for message in unit.messages:
            messages.append(
                OpenAIExecutionMessageV2(
                    role=_ROLE_MAPPING[message.role],
                    content=message.content,
                    ordinal=len(messages),
                )
            )
    try:
        return OpenAIExecutionRequestV2(
            execution_request_id=authority.context.request_id,
            request_envelope_identity=authority.request_envelope.identity,
            model=settings.model,
            messages=tuple(messages),
            timeout_seconds=authority.timeout_policy.timeout_seconds,
            cancellation_requested=(
                authority.context.cancellation.cancellation_requested
            ),
            temperature=settings.temperature,
            max_output_tokens=settings.max_output_tokens,
            stop_sequences=settings.stop_sequences,
        )
    except (TypeError, ValueError, ValidationError) as error:
        raise OpenAIRequestMappingError(
            "invalid OpenAI execution request mapping"
        ) from error


def project_openai_execution_response(
    response: OpenAIExecutionResponseV2,
    request: ProviderExecutionRequestV2,
) -> ProviderExecutionResultV2:
    """Project one validated OpenAI DTO without performing provider execution."""

    authority = _execution_request(request)
    _require_openai_authority(authority)
    output = _response(response)
    category = output.failure_category
    common = {
        "request_id": authority.context.request_id,
        "provider_id": authority.provider.provider_id,
        "request_envelope_identity": authority.request_envelope.identity,
        "finished_at": output.finished_at,
    }
    if category in _FAILURE_OUTCOMES:
        return ProviderExecutionResultV2(
            **common,
            outcome=_FAILURE_OUTCOMES[category],
            failure_code=output.failure_code,
            failure_message=f"OpenAI client category: {category.value}.",
        )
    try:
        projection = ProviderResultProjectionV2(
            status=output.status,
            outputs=tuple(
                ProviderOutputInputV2(
                    source_request_reference=(
                        authority.request_envelope.request_units[
                            item.ordinal
                        ].source_request_reference
                    ),
                    ordinal=item.ordinal,
                    generated_text=item.generated_text,
                    finish_reason=item.finish_reason,
                )
                for item in output.outputs
            ),
            failure_code=output.failure_code,
        )
        # Reuse the frozen provider authority for output coverage and lineage.
        build_provider_result_envelope(
            authority.request_envelope,
            authority.request_intent,
            authority.provider,
            projection,
        )
        return ProviderExecutionResultV2(
            **common,
            outcome=ExecutionOutcomeV2.COMPLETED,
            provider_result=projection,
        )
    except (IndexError, TypeError, ValueError, ValidationError) as error:
        raise OpenAIResponseMappingError(
            "invalid OpenAI response projection"
        ) from error


def _execution_request(
    value: ProviderExecutionRequestV2,
) -> ProviderExecutionRequestV2:
    try:
        return ProviderExecutionRequestV2.model_validate(value)
    except (TypeError, ValueError, ValidationError) as error:
        raise OpenAIRequestMappingError("invalid provider execution request") from error


def _config(value: OpenAIExecutionConfigV2) -> OpenAIExecutionConfigV2:
    try:
        return OpenAIExecutionConfigV2.model_validate(value)
    except (TypeError, ValueError, ValidationError) as error:
        raise OpenAIConfigurationError(
            "invalid OpenAI execution configuration"
        ) from error


def _response(value: OpenAIExecutionResponseV2) -> OpenAIExecutionResponseV2:
    try:
        return OpenAIExecutionResponseV2.model_validate(value)
    except (TypeError, ValueError, ValidationError) as error:
        raise OpenAIResponseMappingError("invalid OpenAI execution response") from error


def _require_openai_authority(request: ProviderExecutionRequestV2) -> None:
    expected = OpenAIProviderAdapter.descriptor
    if (
        request.provider.provider_id != "openai"
        or request.provider.identity != expected.identity
        or request.provider.fingerprint != expected.fingerprint
        or request.provider.adapter_identity != expected.adapter_identity
    ):
        raise OpenAIResponseMappingError("request does not belong to OpenAI authority")


__all__ = ("build_openai_execution_request", "project_openai_execution_response")
