"""Fixed errors for the injected offline OpenAI smoke-test boundary."""


class OpenAISmokeTestError(RuntimeError):
    """Base error for OpenAI live smoke-test planning failures."""


class OpenAISmokeTestConfirmationError(OpenAISmokeTestError):
    """Explicit authorization for a future live request is absent."""


class OpenAISmokeTestConfigurationError(OpenAISmokeTestError):
    """The immutable smoke-test configuration is invalid."""


class OpenAISmokeTestDependencyError(OpenAISmokeTestError):
    """An injected smoke-test dependency or lifecycle operation failed."""


__all__ = (
    "OpenAISmokeTestConfigurationError",
    "OpenAISmokeTestConfirmationError",
    "OpenAISmokeTestDependencyError",
    "OpenAISmokeTestError",
)
