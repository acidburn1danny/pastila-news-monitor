"""Command-time composition for explicit event-verification provider choice."""

from pastila_scout.provider_execution_v2 import ProviderExecutionRequestV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1
from pastila_scout.scout_runtime_execution_v1 import ScoutRuntimeResultV1

from .provider import ProviderNeutralEventVerificationProviderV1


def compose_event_verification_provider(
    provider_text: str,
) -> ProviderNeutralEventVerificationProviderV1:
    """Validate exact selection without constructing a provider or client."""

    return ProviderNeutralEventVerificationProviderV1(
        ProviderChoiceV1(provider_text), _execute_provider_request
    )


def _execute_provider_request(
    provider: ProviderChoiceV1, request: ProviderExecutionRequestV2
) -> ScoutRuntimeResultV1:
    from pastila_scout.scout_cli_provider_run_v1 import composition

    if provider is ProviderChoiceV1.OPENAI:
        return composition._run_openai(provider, request)
    return composition._run_ollama(provider, request)


__all__ = ("compose_event_verification_provider",)
