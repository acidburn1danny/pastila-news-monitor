"""Production Ollama executor for ProviderExecutionV2."""

from datetime import datetime

from pydantic import ValidationError

from pastila_scout.provider_execution_v2 import (
    ExecutionConfigurationError,
    ExecutionOutcomeV2,
    ProviderExecutionRequestV2,
    ProviderExecutionResultV2,
)
from pastila_scout.provider_v2 import ProviderOutputInputV2, ProviderResultProjectionV2

from .client import OllamaHttpClientV1
from .errors import (
    OllamaConnectionError,
    OllamaHttpError,
    OllamaInvalidRequestError,
    OllamaMalformedResponseError,
    OllamaModelUnavailableError,
    OllamaTimeoutError,
)
from .mapping import build_ollama_request, map_ollama_response
from .models import OllamaChatResponseV1, OllamaExecutionConfigV1


class OllamaProviderExecutorV1:
    """Map, dispatch once, validate, and project one Ollama completion."""

    def __init__(
        self,
        client: OllamaHttpClientV1,
        config: OllamaExecutionConfigV1,
    ) -> None:
        if type(client) is not OllamaHttpClientV1:
            raise _isolated_configuration_error("invalid Ollama HTTP client")
        self.client = client
        invalid_config = False
        try:
            payload = config.model_dump(mode="python", warnings=False)
            validated_config = OllamaExecutionConfigV1.model_validate(
                payload, strict=True
            )
        except (AttributeError, TypeError, ValueError, ValidationError):
            invalid_config = True
            validated_config = None
        if invalid_config:
            raise _isolated_configuration_error("invalid Ollama configuration")
        self.config = validated_config

    def execute(self, request: ProviderExecutionRequestV2) -> ProviderExecutionResultV2:
        invalid_request = False
        try:
            request_payload = request.model_dump(mode="python", warnings=False)
            authority = ProviderExecutionRequestV2.model_validate(
                request_payload, strict=True
            )
        except (AttributeError, TypeError, ValueError, ValidationError):
            invalid_request = True
            authority = None
        if invalid_request:
            raise _isolated_configuration_error("invalid provider execution request")
        if authority.context.cancellation.cancellation_requested:
            return _failure(
                authority,
                ExecutionOutcomeV2.CANCELLED,
                "ollama-pre-dispatch-cancelled",
                "Ollama execution was cancelled before dispatch.",
                authority.context.requested_at,
            )
        unsupported_request = False
        try:
            mapped = build_ollama_request(authority, self.config)
        except OllamaInvalidRequestError:
            unsupported_request = True
            mapped = None
        if unsupported_request:
            raise _isolated_configuration_error("unsupported Ollama request")
        try:
            raw = self.client.chat(
                mapped,
                self.config.base_url,
                authority.timeout_policy.timeout_seconds,
            )
        except OllamaTimeoutError:
            return _failure(
                authority,
                ExecutionOutcomeV2.TIMEOUT,
                "ollama-timeout",
                "The Ollama request timed out.",
                authority.context.requested_at,
            )
        except OllamaModelUnavailableError:
            return _failure(
                authority,
                ExecutionOutcomeV2.PROVIDER_FAILURE,
                "ollama-model-unavailable",
                "The configured Ollama model is unavailable.",
                authority.context.requested_at,
            )
        except OllamaInvalidRequestError:
            return _failure(
                authority,
                ExecutionOutcomeV2.PROVIDER_FAILURE,
                "ollama-invalid-request",
                "Ollama rejected the request.",
                authority.context.requested_at,
            )
        except OllamaConnectionError:
            return _failure(
                authority,
                ExecutionOutcomeV2.PROVIDER_FAILURE,
                "ollama-connection-failure",
                "The Ollama endpoint is unavailable.",
                authority.context.requested_at,
            )
        except OllamaHttpError:
            return _failure(
                authority,
                ExecutionOutcomeV2.PROVIDER_FAILURE,
                "ollama-http-failure",
                "Ollama returned an HTTP failure.",
                authority.context.requested_at,
            )
        except OllamaMalformedResponseError:
            return _failure(
                authority,
                ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE,
                "ollama-malformed-response",
                "Ollama returned a malformed response.",
                authority.context.requested_at,
            )
        except Exception:  # noqa: BLE001 - transport implementations are not uniform
            return _failure(
                authority,
                ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE,
                "ollama-transport-contract-failure",
                "The Ollama HTTP transport failed unexpectedly.",
                authority.context.requested_at,
            )
        try:
            response = OllamaChatResponseV1.model_validate(raw)
            text, status, reason, failure_code = map_ollama_response(response)
            projection = ProviderResultProjectionV2(
                status=status,
                outputs=(
                    ProviderOutputInputV2(
                        source_request_reference=authority.request_envelope.request_units[
                            0
                        ].source_request_reference,
                        ordinal=0,
                        generated_text=text,
                        finish_reason=reason,
                    ),
                ),
                failure_code=failure_code,
            )
        except (TypeError, ValueError, ValidationError, OllamaMalformedResponseError):
            return _failure(
                authority,
                ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE,
                "ollama-malformed-response",
                "Ollama returned a malformed response.",
                authority.context.requested_at,
            )
        return ProviderExecutionResultV2(
            request_id=authority.context.request_id,
            provider_id="ollama",
            request_envelope_identity=authority.request_envelope.identity,
            outcome=ExecutionOutcomeV2.COMPLETED,
            finished_at=response.created_at,
            provider_result=projection,
        )


def _failure(
    request: ProviderExecutionRequestV2,
    outcome: ExecutionOutcomeV2,
    code: str,
    message: str,
    finished_at: datetime,
) -> ProviderExecutionResultV2:
    return ProviderExecutionResultV2(
        request_id=request.context.request_id,
        provider_id=request.provider.provider_id,
        request_envelope_identity=request.request_envelope.identity,
        outcome=outcome,
        finished_at=finished_at,
        failure_code=code,
        failure_message=message,
    )


def _isolated_configuration_error(message: str) -> ExecutionConfigurationError:
    error = ExecutionConfigurationError(message)
    error.__suppress_context__ = True
    return error


__all__ = ("OllamaProviderExecutorV1",)
