"""Sole composition root for Module 2.9 V2 providers."""

from pastila_scout.provider_adapters_v2.claude import ClaudeProviderAdapter
from pastila_scout.provider_adapters_v2.gemini import GeminiProviderAdapter
from pastila_scout.provider_adapters_v2.ollama import OllamaProviderAdapter
from pastila_scout.provider_adapters_v2.openai import OpenAIProviderAdapter
from pastila_scout.provider_v2 import ProviderRegistry


def build_provider_registry() -> ProviderRegistry:
    """Create the immutable four-provider application registry."""

    return ProviderRegistry(
        (
            OpenAIProviderAdapter(),
            ClaudeProviderAdapter(),
            GeminiProviderAdapter(),
            OllamaProviderAdapter(),
        )
    )


__all__ = ("build_provider_registry",)
