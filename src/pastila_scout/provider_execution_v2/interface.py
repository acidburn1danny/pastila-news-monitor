"""Protocol for future provider-neutral execution implementations."""

from typing import Protocol, runtime_checkable

from .models import ProviderExecutionRequestV2, ProviderExecutionResultV2


@runtime_checkable
class ProviderExecutorV2(Protocol):
    """Contract implemented by a future provider execution adapter."""

    def execute(
        self, request: ProviderExecutionRequestV2
    ) -> ProviderExecutionResultV2: ...


__all__ = ("ProviderExecutorV2",)
