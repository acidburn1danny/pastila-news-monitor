"""Explicit object-only composition for future AI Provider Adapters."""

from dataclasses import dataclass

from .contracts import (
    AICredentialProvider,
    AIProviderAdapter,
    AIProviderAdapterConstructor,
    AIProviderClient,
    AIProviderConfiguration,
    AIProviderObservabilityHook,
)


@dataclass(frozen=True, slots=True)
class AIProviderAdapterComposition:
    """Retain exact injected dependency identities and the constructed adapter."""

    configuration: AIProviderConfiguration
    client: AIProviderClient
    credential_provider: AICredentialProvider
    observability_hook: AIProviderObservabilityHook | None
    adapter: AIProviderAdapter


def compose_ai_provider_adapter(
    *,
    constructor: AIProviderAdapterConstructor,
    configuration: AIProviderConfiguration,
    client: AIProviderClient,
    credential_provider: AICredentialProvider,
    observability_hook: AIProviderObservabilityHook | None = None,
) -> AIProviderAdapterComposition:
    """Construct once from explicit dependencies; perform no provider request."""

    adapter = constructor(
        configuration=configuration,
        client=client,
        credential_provider=credential_provider,
        observability_hook=observability_hook,
    )
    return AIProviderAdapterComposition(
        configuration=configuration,
        client=client,
        credential_provider=credential_provider,
        observability_hook=observability_hook,
        adapter=adapter,
    )
