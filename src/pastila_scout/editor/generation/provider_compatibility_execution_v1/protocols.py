"""Application-owned authorities for the opt-in Producer execution path."""

from typing import Protocol

from pastila_scout.editor.generation.revision import ControlledRevisionGatewayResult
from pastila_scout.provider_execution_v2 import (
    ProviderExecutionRequestV2,
    ProviderExecutionResultV2,
)


class ProducerGatewayProjectorV1(Protocol):
    """Project one validated provider result into the existing gateway contract."""

    def project(
        self,
        *,
        request: ProviderExecutionRequestV2,
        result: ProviderExecutionResultV2,
    ) -> ControlledRevisionGatewayResult | None: ...


__all__ = ()
