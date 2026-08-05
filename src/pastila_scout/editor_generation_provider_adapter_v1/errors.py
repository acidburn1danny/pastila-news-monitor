"""Safe errors for provider-neutral Editor generation."""

from pastila_scout.editor.generation.provider import ProviderError


class EditorGenerationProviderAdapterError(Exception):
    """Raised when the adapter boundary cannot be established."""


class ProviderCancellationError(ProviderError):
    """A non-timeout cancellation signal for ControlledGenerator."""


__all__ = ("EditorGenerationProviderAdapterError", "ProviderCancellationError")
