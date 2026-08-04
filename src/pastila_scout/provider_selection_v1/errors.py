"""Deterministic application-owned provider-selection errors."""


class ProviderSelectionError(RuntimeError):
    """Base error for explicit provider selection failures."""


class ProviderSelectionConfigurationError(ProviderSelectionError):
    """The selection configuration is missing or invalid."""


class UnknownProviderSelectionError(ProviderSelectionError):
    """The selected provider has no injected registration."""


class DuplicateProviderRegistrationError(ProviderSelectionError):
    """A provider was injected more than once."""


class MissingProviderRegistrationError(ProviderSelectionError):
    """A required supported provider was not injected."""


class InvalidProviderExecutorError(ProviderSelectionError):
    """An injected object does not expose the neutral executor shape."""


__all__ = (
    "DuplicateProviderRegistrationError",
    "InvalidProviderExecutorError",
    "MissingProviderRegistrationError",
    "ProviderSelectionConfigurationError",
    "ProviderSelectionError",
    "UnknownProviderSelectionError",
)
