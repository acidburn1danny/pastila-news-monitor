"""Fixed public errors for the offline live-shaped OpenAI smoke boundary."""


class OpenAILiveSmokeError(RuntimeError):
    """Base error for offline live-shaped smoke orchestration."""


class OpenAILiveSmokeConfigurationError(OpenAILiveSmokeError):
    """The supplied smoke configuration is invalid or unconfirmed."""


class OpenAILiveSmokeDependencyError(OpenAILiveSmokeError):
    """A verified lower dependency failed or returned invalid authority."""


class OpenAILiveSmokeLifecycleError(OpenAILiveSmokeError):
    """The single delegated cleanup obligation failed."""


__all__ = (
    "OpenAILiveSmokeConfigurationError",
    "OpenAILiveSmokeDependencyError",
    "OpenAILiveSmokeError",
    "OpenAILiveSmokeLifecycleError",
)
