"""Protocol for a future dependency-injected OpenAI client capability."""

from typing import Protocol, runtime_checkable

from .models import OpenAIExecutionRequestV2, OpenAIExecutionResponseV2


@runtime_checkable
class OpenAIExecutionClientV2(Protocol):
    """Transport-neutral client boundary; Revision 5 provides no implementation."""

    def complete(
        self, request: OpenAIExecutionRequestV2
    ) -> OpenAIExecutionResponseV2: ...


__all__ = ("OpenAIExecutionClientV2",)
