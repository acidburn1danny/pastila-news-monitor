"""Deterministic identities and fingerprints for common Phase 6.2 DTOs."""

from .canonical import semantic_fingerprint
from .identity import derive_identity
from .provider_mapping_models import (
    DraftProviderRequestPlan,
    ProviderMappingDomainModel,
    ProviderRequestPlanDescriptor,
)


def _payload(value: ProviderMappingDomainModel, *, exclude_fingerprint: bool):
    return value.model_dump(
        mode="python",
        exclude={"fingerprint"} if exclude_fingerprint else set(),
        warnings=False,
    )


def _identity(kind: str, value: ProviderMappingDomainModel) -> str:
    payload = _payload(value, exclude_fingerprint=True)
    payload.pop("identity", None)
    return derive_identity(kind, payload)


def provider_mapping_fingerprint(value: ProviderMappingDomainModel) -> str:
    """Return the canonical semantic fingerprint for a common mapping DTO."""

    return semantic_fingerprint(_payload(value, exclude_fingerprint=True))


def derive_provider_request_plan_descriptor_identity(
    value: ProviderRequestPlanDescriptor,
) -> str:
    return _identity("provider-request-plan-descriptor", value)


def derive_draft_provider_request_plan_identity(
    value: DraftProviderRequestPlan,
) -> str:
    return _identity("draft-provider-request-plan", value)


def derive_provider_request_plan_descriptor_fingerprint(
    value: ProviderRequestPlanDescriptor,
) -> str:
    return provider_mapping_fingerprint(value)


def derive_draft_provider_request_plan_fingerprint(
    value: DraftProviderRequestPlan,
) -> str:
    return provider_mapping_fingerprint(value)


__all__ = (
    "derive_draft_provider_request_plan_fingerprint",
    "derive_draft_provider_request_plan_identity",
    "derive_provider_request_plan_descriptor_fingerprint",
    "derive_provider_request_plan_descriptor_identity",
)
