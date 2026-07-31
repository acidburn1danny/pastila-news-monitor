"""Complete SDK-free provider adapter lifecycle."""

from typing import Protocol, runtime_checkable

from .models import (
    ProviderDescriptorV2,
    ProviderRequestEnvelopeV2,
    ProviderRequestIntentV2,
    ProviderResultEnvelopeV2,
    ProviderResultProjectionV2,
    ProviderV2ValidationIssue,
)


@runtime_checkable
class ProviderAdapter(Protocol):
    @property
    def provider_id(self) -> str: ...

    @property
    def adapter_identity(self) -> str: ...

    @property
    def descriptor(self) -> ProviderDescriptorV2: ...

    def construct_request(
        self, intent: ProviderRequestIntentV2
    ) -> ProviderRequestEnvelopeV2: ...

    def validate_request(
        self, request: ProviderRequestEnvelopeV2, intent: ProviderRequestIntentV2
    ) -> tuple[ProviderV2ValidationIssue, ...]: ...

    def execute(
        self, request: ProviderRequestEnvelopeV2
    ) -> ProviderResultProjectionV2: ...

    def extract_response(
        self, execution_result: ProviderResultProjectionV2
    ) -> ProviderResultProjectionV2: ...

    def project_result(
        self,
        request: ProviderRequestEnvelopeV2,
        intent: ProviderRequestIntentV2,
        projection: ProviderResultProjectionV2,
    ) -> ProviderResultEnvelopeV2: ...

    def validate_result(
        self,
        result: ProviderResultEnvelopeV2,
        request: ProviderRequestEnvelopeV2,
        intent: ProviderRequestIntentV2,
        projection: ProviderResultProjectionV2,
    ) -> tuple[ProviderV2ValidationIssue, ...]: ...


__all__ = ("ProviderAdapter",)
