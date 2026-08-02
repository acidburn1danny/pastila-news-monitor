"""Fixed public errors for canonical smoke request authority."""


class SmokeExecutionRequestAuthorityError(RuntimeError):
    """Base error for the canonical smoke request authority boundary."""


class SmokeExecutionRequestConfigurationError(SmokeExecutionRequestAuthorityError):
    """Supplied smoke authority inputs are invalid."""


class SmokeExecutionRequestDependencyError(SmokeExecutionRequestAuthorityError):
    """A later request-construction dependency is unavailable."""


__all__ = (
    "SmokeExecutionRequestAuthorityError",
    "SmokeExecutionRequestConfigurationError",
    "SmokeExecutionRequestDependencyError",
)
