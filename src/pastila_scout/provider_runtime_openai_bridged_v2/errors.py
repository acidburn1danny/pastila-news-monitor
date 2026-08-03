"""Fixed public errors for higher OpenAI bridged runtime composition."""


class OpenAIBridgedRuntimeError(RuntimeError):
    """Base error for bridged OpenAI runtime composition."""


class OpenAIBridgedRuntimeConfigurationError(OpenAIBridgedRuntimeError):
    """The caller supplied an invalid base runtime composer."""


class OpenAIBridgedRuntimeDependencyError(OpenAIBridgedRuntimeError):
    """A verified lower composition dependency failed."""


class OpenAIBridgedRuntimeLifecycleError(OpenAIBridgedRuntimeError):
    """Delegated base runtime cleanup failed."""


__all__ = (
    "OpenAIBridgedRuntimeConfigurationError",
    "OpenAIBridgedRuntimeDependencyError",
    "OpenAIBridgedRuntimeError",
    "OpenAIBridgedRuntimeLifecycleError",
)
