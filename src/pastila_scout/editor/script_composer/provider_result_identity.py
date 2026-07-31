"""Deterministic identities and fingerprints for common Phase 6.3 results."""

from .canonical import semantic_fingerprint
from .identity import derive_identity
from .provider_result_models import ProviderExecutionResult, ProviderResultDomainModel


def _payload(value: ProviderResultDomainModel):
    return value.model_dump(mode="python", exclude={"fingerprint"}, warnings=False)


def provider_result_fingerprint(value: ProviderResultDomainModel) -> str:
    """Return the canonical semantic fingerprint for a generic result."""

    return semantic_fingerprint(_payload(value))


def derive_provider_execution_result_identity(value: ProviderExecutionResult) -> str:
    payload = _payload(value)
    payload.pop("identity", None)
    return derive_identity("provider-execution-result", payload)


def derive_provider_execution_result_fingerprint(
    value: ProviderExecutionResult,
) -> str:
    return provider_result_fingerprint(value)


__all__ = (
    "derive_provider_execution_result_fingerprint",
    "derive_provider_execution_result_identity",
)
