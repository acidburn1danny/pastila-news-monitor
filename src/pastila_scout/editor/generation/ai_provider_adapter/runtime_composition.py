"""Transport-free composition of the canonical AI provider runtime."""

from dataclasses import dataclass

from .runtime import (
    AIProviderAdapterRuntime,
    CanonicalAIProviderExceptionNormalizer,
    CanonicalAIProviderRetryDecider,
    ConstantAIProviderBackoff,
    NeverCancelledAIProviderToken,
    NoOpAIProviderSleeper,
)


@dataclass(frozen=True, slots=True)
class AIProviderRuntimeComposition:
    configuration: object
    client: object
    credential_provider: object
    projector: object
    interpreter: object
    exception_normalizer: object
    retry_decider: object
    backoff_strategy: object
    sleeper: object
    cancellation_token: object
    observer: object | None
    runtime: AIProviderAdapterRuntime


def compose_ai_provider_runtime(
    *,
    configuration,
    client,
    credential_provider,
    projector,
    interpreter,
    exception_normalizer=None,
    retry_decider=None,
    backoff_strategy=None,
    sleeper=None,
    cancellation_token=None,
    observer=None,
) -> AIProviderRuntimeComposition:
    """Construct dependencies explicitly and perform no execution or transport."""

    normalizer = exception_normalizer or CanonicalAIProviderExceptionNormalizer()
    decider = retry_decider or CanonicalAIProviderRetryDecider()
    backoff = backoff_strategy or ConstantAIProviderBackoff()
    delay_executor = sleeper or NoOpAIProviderSleeper()
    cancellation = cancellation_token or NeverCancelledAIProviderToken()
    runtime = AIProviderAdapterRuntime(
        configuration=configuration,
        client=client,
        credential_provider=credential_provider,
        projector=projector,
        interpreter=interpreter,
        exception_normalizer=normalizer,
        retry_decider=decider,
        backoff_strategy=backoff,
        sleeper=delay_executor,
        cancellation_token=cancellation,
        observer=observer,
    )
    return AIProviderRuntimeComposition(
        configuration,
        client,
        credential_provider,
        projector,
        interpreter,
        normalizer,
        decider,
        backoff,
        delay_executor,
        cancellation,
        observer,
        runtime,
    )
