"""Provider-neutral application execution shared by production and tests."""

from typing import NoReturn, Self

from pastila_scout.provider_execution_v2 import (
    ProviderExecutionRequestV2,
    ProviderExecutionResultV2,
)
from pastila_scout.provider_selection_v1 import (
    ProviderChoiceV1,
    ProviderExecutorRegistrationV1,
    ProviderSelectionConfigV1,
    ProviderSelectorV1,
)
from pastila_scout.scout_runtime_execution_v1 import (
    ScoutRuntimeExecutionBridgeV1,
    ScoutRuntimeRequestV1,
    ScoutRuntimeResultV1,
)
from pastila_scout.scout_runtime_v1 import (
    ScoutCancellationV1,
    ScoutRuntimeCompositionV1,
    ScoutRuntimeConfigV1,
    ScoutRuntimeOptionsV1,
)
from pastila_scout.scout_workflow_execution_v1 import ScoutWorkflowExecutionV1


class _UnavailableLegacyWorkflow:
    __slots__ = ()

    def execute(self, request: ScoutRuntimeRequestV1) -> ScoutRuntimeResultV1:
        del request
        raise RuntimeError("legacy workflow is unavailable for provider-run")

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        memo[id(self)] = self
        return self

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("provider-run legacy placeholders cannot be serialized")

    def __repr__(self) -> str:
        return "_UnavailableLegacyWorkflow(<private>)"


class _UnavailableProviderExecutor:
    __slots__ = ()

    def execute(self, request: ProviderExecutionRequestV2) -> ProviderExecutionResultV2:
        del request
        raise RuntimeError("unselected provider executor is unavailable")

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        memo[id(self)] = self
        return self

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("provider-run executor placeholders cannot be serialized")

    def __repr__(self) -> str:
        return "_UnavailableProviderExecutor(<private>)"


def execute_provider_run(
    *,
    provider: ProviderChoiceV1,
    provider_request,
    selected_executor: object,
) -> ScoutRuntimeResultV1:
    """Compose the verified chain and execute the selected provider exactly once."""
    unavailable = _UnavailableProviderExecutor()
    executors = {
        ProviderChoiceV1.OPENAI: (
            selected_executor if provider is ProviderChoiceV1.OPENAI else unavailable
        ),
        ProviderChoiceV1.OLLAMA: (
            selected_executor if provider is ProviderChoiceV1.OLLAMA else unavailable
        ),
    }
    selector = ProviderSelectorV1(
        ProviderSelectionConfigV1(provider=provider),
        tuple(
            ProviderExecutorRegistrationV1(choice, executors[choice])
            for choice in (ProviderChoiceV1.OPENAI, ProviderChoiceV1.OLLAMA)
        ),
    )
    composition = ScoutRuntimeCompositionV1(
        selector,
        ScoutRuntimeConfigV1("scout-config:provider-run-v1"),
        ScoutRuntimeOptionsV1("scout-options:provider-run-v1"),
        ScoutCancellationV1(False),
    )
    workflow = ScoutWorkflowExecutionV1(
        _UnavailableLegacyWorkflow(), ScoutRuntimeExecutionBridgeV1(composition)
    )
    return workflow.execute_provider_neutral(
        ScoutRuntimeRequestV1(True, provider_request)
    )


__all__ = ("execute_provider_run",)
