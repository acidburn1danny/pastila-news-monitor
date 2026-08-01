"""Deterministic errors for the isolated OpenAI SDK boundary."""

from pastila_scout.provider_execution_openai_v2 import OpenAIClientErrorCategoryV2


class OpenAISDKBoundaryError(RuntimeError):
    """Base error for SDK-boundary specification failures."""

    def __init__(
        self,
        message: str,
        *,
        category: OpenAIClientErrorCategoryV2 | None = None,
    ) -> None:
        super().__init__(message)
        self.category = category


class OpenAISDKConfigurationError(OpenAISDKBoundaryError):
    """The injected SDK capability is structurally invalid."""


class OpenAISDKDependencyError(OpenAISDKBoundaryError):
    """The deferred SDK dispatch implementation is unavailable."""


class OpenAISDKResponseError(OpenAISDKBoundaryError):
    """SDK-shaped response data cannot be reconstructed safely."""


__all__ = (
    "OpenAISDKBoundaryError",
    "OpenAISDKConfigurationError",
    "OpenAISDKDependencyError",
    "OpenAISDKResponseError",
)
