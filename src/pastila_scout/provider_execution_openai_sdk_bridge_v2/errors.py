"""Safe public errors for the OpenAI execution-to-SDK bridge."""


class OpenAIExecutionSDKBridgeError(RuntimeError):
    """Base error for the offline execution-to-SDK compatibility boundary."""


class OpenAIExecutionSDKBridgeConfigurationError(OpenAIExecutionSDKBridgeError):
    """The supplied execution request is incompatible with the SDK boundary."""


class OpenAIExecutionSDKBridgeDependencyError(OpenAIExecutionSDKBridgeError):
    """The pinned SDK dependency failed or returned an invalid result."""


__all__ = (
    "OpenAIExecutionSDKBridgeConfigurationError",
    "OpenAIExecutionSDKBridgeDependencyError",
    "OpenAIExecutionSDKBridgeError",
)
