"""Strict configuration and injection contracts for provider selection."""

from dataclasses import dataclass
from enum import StrEnum

from .errors import ProviderSelectionConfigurationError


class ProviderChoiceV1(StrEnum):
    """The complete set of explicitly selectable providers."""

    OPENAI = "openai"
    OLLAMA = "ollama"


@dataclass(frozen=True, slots=True)
class ProviderSelectionConfigV1:
    """One explicit provider choice with no default or automatic mode."""

    provider: ProviderChoiceV1

    def __post_init__(self) -> None:
        if type(self.provider) is not ProviderChoiceV1:
            error = ProviderSelectionConfigurationError(
                "invalid provider selection configuration"
            )
            error.__suppress_context__ = True
            raise error


__all__ = ("ProviderChoiceV1", "ProviderSelectionConfigV1")
