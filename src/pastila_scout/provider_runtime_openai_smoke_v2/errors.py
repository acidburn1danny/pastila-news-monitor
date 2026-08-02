"""Fixed errors for the non-operational OpenAI smoke-test boundary."""


class OpenAISmokeTestError(RuntimeError):
    """Base error for OpenAI live smoke-test planning failures."""


class OpenAISmokeTestConfirmationError(OpenAISmokeTestError):
    """Explicit authorization for a future live request is absent."""


class OpenAISmokeTestConfigurationError(OpenAISmokeTestError):
    """The immutable smoke-test configuration is invalid."""


class OpenAISmokeTestDependencyError(OpenAISmokeTestError):
    """The operational smoke-test implementation is unavailable."""


__all__ = (
    "OpenAISmokeTestConfigurationError",
    "OpenAISmokeTestConfirmationError",
    "OpenAISmokeTestDependencyError",
    "OpenAISmokeTestError",
)
