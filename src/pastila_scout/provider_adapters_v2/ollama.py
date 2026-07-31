"""Ollama architecture placeholder."""

from .base import ProviderAdapterBase, adapter_identity, placeholder_descriptor


class OllamaProviderAdapter(ProviderAdapterBase):
    provider_id = "ollama"
    adapter_identity = adapter_identity(provider_id)
    descriptor = placeholder_descriptor(provider_id, "Ollama")


__all__ = ("OllamaProviderAdapter",)
