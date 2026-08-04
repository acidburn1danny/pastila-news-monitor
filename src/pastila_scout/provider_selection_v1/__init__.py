"""Passive public API for explicit application-owned provider selection."""

from .errors import (
    DuplicateProviderRegistrationError,
    InvalidProviderExecutorError,
    MissingProviderRegistrationError,
    ProviderSelectionConfigurationError,
    ProviderSelectionError,
    UnknownProviderSelectionError,
)
from .models import ProviderChoiceV1, ProviderSelectionConfigV1
from .selector import ProviderExecutorRegistrationV1, ProviderSelectorV1

__all__ = (
    "DuplicateProviderRegistrationError",
    "InvalidProviderExecutorError",
    "MissingProviderRegistrationError",
    "ProviderChoiceV1",
    "ProviderExecutorRegistrationV1",
    "ProviderSelectionConfigV1",
    "ProviderSelectionConfigurationError",
    "ProviderSelectionError",
    "ProviderSelectorV1",
    "UnknownProviderSelectionError",
)
