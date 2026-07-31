"""Gemini architecture placeholder."""

from .base import ProviderAdapterBase, adapter_identity, placeholder_descriptor


class GeminiProviderAdapter(ProviderAdapterBase):
    provider_id = "gemini"
    adapter_identity = adapter_identity(provider_id)
    descriptor = placeholder_descriptor(provider_id, "Gemini")


__all__ = ("GeminiProviderAdapter",)
