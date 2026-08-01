"""Deterministic errors for the isolated OpenAI SDK boundary."""


class OpenAISDKBoundaryError(RuntimeError):
    """Base error for SDK-boundary specification failures."""


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
