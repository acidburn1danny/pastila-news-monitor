"""Controlled provider-neutral V2 architecture errors."""


class ProviderV2Error(ValueError):
    """Base V2 architecture error."""


class ProviderV2ValidationError(ProviderV2Error):
    """Raised when authoritative construction receives invalid input."""


class InvalidProviderIdentifierError(ProviderV2Error):
    """Raised for a noncanonical provider identifier."""


class InvalidProviderDescriptorError(ProviderV2Error):
    """Raised when descriptor authority is invalid."""


class InvalidProviderAdapterError(ProviderV2Error):
    """Raised when an object does not satisfy adapter ownership."""


class DuplicateProviderRegistrationError(ProviderV2Error):
    """Raised when two adapters own one provider identifier."""


class UnknownProviderError(ProviderV2Error):
    """Raised when a provider is not present in the immutable registry."""


class ProviderCapabilityUnavailableError(ProviderV2Error):
    """Raised when an architecture-only adapter cannot execute."""


__all__ = (
    "DuplicateProviderRegistrationError",
    "InvalidProviderAdapterError",
    "InvalidProviderDescriptorError",
    "InvalidProviderIdentifierError",
    "ProviderCapabilityUnavailableError",
    "ProviderV2Error",
    "ProviderV2ValidationError",
    "UnknownProviderError",
)
