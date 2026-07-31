"""Claude architecture placeholder."""

from .base import ProviderAdapterBase, adapter_identity, placeholder_descriptor


class ClaudeProviderAdapter(ProviderAdapterBase):
    provider_id = "claude"
    adapter_identity = adapter_identity(provider_id)
    descriptor = placeholder_descriptor(provider_id, "Claude")


__all__ = ("ClaudeProviderAdapter",)
