"""Shared lifecycle mechanics for architecture-only provider adapters."""

from abc import ABC

from pastila_scout.provider_v2 import (
    ProviderCapabilityUnavailableError,
    ProviderCapabilityV2,
    ProviderDescriptorV2,
    ProviderRequestEnvelopeV2,
    ProviderRequestIntentV2,
    ProviderResultEnvelopeV2,
    ProviderResultProjectionV2,
    ProviderV2ValidationIssue,
    build_provider_descriptor,
    build_provider_request_envelope,
    build_provider_result_envelope,
    validate_provider_request_envelope,
    validate_provider_result_envelope,
)
from pastila_scout.provider_v2.canonical import semantic_sha256


def adapter_identity(provider_id: str, version: str = "1.0.0") -> str:
    return f"scout:provider-adapter-v2:{semantic_sha256((provider_id, version))}"


class ProviderAdapterBase(ABC):
    """Complete neutral lifecycle except provider-owned execution/extraction."""

    provider_id: str
    adapter_identity: str
    descriptor: ProviderDescriptorV2

    def construct_request(
        self, intent: ProviderRequestIntentV2
    ) -> ProviderRequestEnvelopeV2:
        return build_provider_request_envelope(intent, self.descriptor)

    def validate_request(
        self, request: ProviderRequestEnvelopeV2, intent: ProviderRequestIntentV2
    ) -> tuple[ProviderV2ValidationIssue, ...]:
        return validate_provider_request_envelope(request, intent, self.descriptor)

    def execute(self, request: ProviderRequestEnvelopeV2) -> ProviderResultProjectionV2:
        del request
        raise ProviderCapabilityUnavailableError(
            f"{self.provider_id} execution is not implemented in Phase 7.1"
        )

    def extract_response(
        self, execution_result: ProviderResultProjectionV2
    ) -> ProviderResultProjectionV2:
        return ProviderResultProjectionV2.model_validate(
            execution_result.model_dump(mode="python", warnings=False)
        )

    def project_result(
        self,
        request: ProviderRequestEnvelopeV2,
        intent: ProviderRequestIntentV2,
        projection: ProviderResultProjectionV2,
    ) -> ProviderResultEnvelopeV2:
        return build_provider_result_envelope(
            request, intent, self.descriptor, projection
        )

    def validate_result(
        self,
        result: ProviderResultEnvelopeV2,
        request: ProviderRequestEnvelopeV2,
        intent: ProviderRequestIntentV2,
        projection: ProviderResultProjectionV2,
    ) -> tuple[ProviderV2ValidationIssue, ...]:
        return validate_provider_result_envelope(
            result, request, intent, self.descriptor, projection
        )


# Python 3.14 defers source annotations. These registry-owned implementations
# publish an explicit materialized mapping so registry validation never needs to
# invoke their generated ``__annotate__`` functions.
ProviderAdapterBase.construct_request.__annotations__ = {
    "intent": ProviderRequestIntentV2,
    "return": ProviderRequestEnvelopeV2,
}
ProviderAdapterBase.validate_request.__annotations__ = {
    "request": ProviderRequestEnvelopeV2,
    "intent": ProviderRequestIntentV2,
    "return": tuple[ProviderV2ValidationIssue, ...],
}
ProviderAdapterBase.execute.__annotations__ = {
    "request": ProviderRequestEnvelopeV2,
    "return": ProviderResultProjectionV2,
}
ProviderAdapterBase.extract_response.__annotations__ = {
    "execution_result": ProviderResultProjectionV2,
    "return": ProviderResultProjectionV2,
}
ProviderAdapterBase.project_result.__annotations__ = {
    "request": ProviderRequestEnvelopeV2,
    "intent": ProviderRequestIntentV2,
    "projection": ProviderResultProjectionV2,
    "return": ProviderResultEnvelopeV2,
}
ProviderAdapterBase.validate_result.__annotations__ = {
    "result": ProviderResultEnvelopeV2,
    "request": ProviderRequestEnvelopeV2,
    "intent": ProviderRequestIntentV2,
    "projection": ProviderResultProjectionV2,
    "return": tuple[ProviderV2ValidationIssue, ...],
}


def placeholder_descriptor(provider_id: str, display_name: str) -> ProviderDescriptorV2:
    identity = adapter_identity(provider_id)
    return build_provider_descriptor(
        provider_id=provider_id,
        display_name=display_name,
        capabilities=(ProviderCapabilityV2.METADATA,),
        descriptor_version="1.0.0",
        adapter_identity=identity,
    )


__all__ = (
    "ProviderAdapterBase",
    "adapter_identity",
    "placeholder_descriptor",
)
