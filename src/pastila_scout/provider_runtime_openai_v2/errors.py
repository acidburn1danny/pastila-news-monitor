"""Fixed safe errors for trusted OpenAI runtime composition."""


class OpenAIRuntimeCompositionError(RuntimeError):
    """Base error for OpenAI runtime composition failures."""


class OpenAIRuntimeConfigurationError(OpenAIRuntimeCompositionError):
    """Runtime policy or an injected dependency is invalid."""


class OpenAIRuntimeCredentialError(OpenAIRuntimeCompositionError):
    """An injected credential value is invalid."""


class OpenAIRuntimeDependencyError(OpenAIRuntimeCompositionError):
    """A required operational runtime dependency is unavailable."""


class OpenAIRuntimeLifecycleError(OpenAIRuntimeCompositionError):
    """SDK-client lifecycle ownership is invalid."""


__all__ = (
    "OpenAIRuntimeCompositionError",
    "OpenAIRuntimeConfigurationError",
    "OpenAIRuntimeCredentialError",
    "OpenAIRuntimeDependencyError",
    "OpenAIRuntimeLifecycleError",
)
