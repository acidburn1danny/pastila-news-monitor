"""Safe normalization of official OpenAI SDK exceptions."""

from __future__ import annotations

import openai

from pastila_scout.editor.generation.ai_provider_adapter import (
    AIProviderExecutionFailureKind,
    AIProviderNormalizedError,
)


class OpenAIExceptionNormalizer:
    """Map typed SDK failures without retaining messages, bodies, or headers."""

    def normalize(self, error: BaseException) -> AIProviderNormalizedError:
        """Return a provider-neutral category and sanitized diagnostic code."""

        category = AIProviderExecutionFailureKind.INTERNAL
        code = "openai_internal_failure"
        retryable = False
        metadata: tuple[tuple[str, str], ...] = ()
        if isinstance(error, openai.AuthenticationError):
            category, code = (
                AIProviderExecutionFailureKind.CREDENTIAL,
                "openai_authentication_failed",
            )
        elif isinstance(error, openai.PermissionDeniedError):
            category, code = (
                AIProviderExecutionFailureKind.CONFIGURATION,
                "openai_authorization_failed",
            )
        elif isinstance(error, openai.RateLimitError):
            category, code, retryable = (
                AIProviderExecutionFailureKind.CLIENT,
                "provider_rate_limited",
                True,
            )
        elif isinstance(error, openai.APITimeoutError):
            category, code, retryable = (
                AIProviderExecutionFailureKind.CLIENT,
                "provider_timeout",
                True,
            )
        elif isinstance(error, openai.APIConnectionError):
            category, code, retryable = (
                AIProviderExecutionFailureKind.CLIENT,
                "provider_transport_failed",
                True,
            )
        elif isinstance(error, openai.NotFoundError):
            category, code = (
                AIProviderExecutionFailureKind.UNSUPPORTED_CAPABILITY,
                "openai_model_or_endpoint_unsupported",
            )
        elif isinstance(
            error, (openai.BadRequestError, openai.UnprocessableEntityError)
        ):
            category, code = (
                AIProviderExecutionFailureKind.SCHEMA,
                "openai_request_rejected",
            )
        elif isinstance(error, openai.ConflictError):
            category, code, retryable = (
                AIProviderExecutionFailureKind.CLIENT,
                "provider_unavailable",
                True,
            )
            metadata = (("http_status", "409"),)
        elif isinstance(error, openai.APIStatusError):
            category, code, retryable = self._status_error(error.status_code)
            metadata = (("http_status", str(error.status_code)),)
        elif isinstance(error, openai.APIResponseValidationError):
            category, code = (
                AIProviderExecutionFailureKind.MALFORMED_RESPONSE,
                "openai_sdk_response_invalid",
            )
        return AIProviderNormalizedError(
            category=category,
            diagnostic_code=code,
            retryable=retryable,
            metadata=metadata,
        )

    @staticmethod
    def _status_error(
        status_code: int,
    ) -> tuple[AIProviderExecutionFailureKind, str, bool]:
        if status_code == 408:
            return AIProviderExecutionFailureKind.CLIENT, "provider_timeout", True
        if status_code == 409 or status_code >= 500:
            return AIProviderExecutionFailureKind.CLIENT, "provider_unavailable", True
        if status_code == 429:
            return AIProviderExecutionFailureKind.CLIENT, "provider_rate_limited", True
        if status_code == 401:
            return (
                AIProviderExecutionFailureKind.CREDENTIAL,
                "openai_authentication_failed",
                False,
            )
        if status_code == 403:
            return (
                AIProviderExecutionFailureKind.CONFIGURATION,
                "openai_authorization_failed",
                False,
            )
        if status_code == 404:
            return (
                AIProviderExecutionFailureKind.UNSUPPORTED_CAPABILITY,
                "openai_model_or_endpoint_unsupported",
                False,
            )
        if status_code in (400, 422):
            return (
                AIProviderExecutionFailureKind.SCHEMA,
                "openai_request_rejected",
                False,
            )
        return AIProviderExecutionFailureKind.INTERNAL, "openai_internal_failure", False
