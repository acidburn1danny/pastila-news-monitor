"""Immutable provider-neutral execution contracts."""

from __future__ import annotations

import math
from datetime import datetime
from enum import StrEnum

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    ValidationError,
    field_validator,
    model_validator,
)

from pastila_scout.provider_v2 import (
    ProviderDescriptorV2,
    ProviderRequestEnvelopeV2,
    ProviderRequestIntentV2,
    ProviderResultProjectionV2,
    validate_provider_descriptor,
    validate_provider_request_envelope,
)


class _FrozenContract(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
        hide_input_in_errors=True,
    )


class ExecutionOutcomeV2(StrEnum):
    """Mutually exclusive outcomes of one execution attempt."""

    COMPLETED = "completed"
    PROVIDER_FAILURE = "provider_failure"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    INTERNAL_EXECUTION_FAILURE = "internal_execution_failure"


class CancellationTokenV2(_FrozenContract):
    """Snapshot of provider-neutral cancellation state."""

    cancellation_requested: StrictBool = False


class TimeoutPolicyV2(_FrozenContract):
    """Declarative timeout budget without timer behavior."""

    timeout_seconds: StrictInt | StrictFloat = Field(gt=0)

    @field_validator("timeout_seconds", mode="before")
    @classmethod
    def require_supported_timeout_type(cls, value: object) -> object:
        if type(value) not in {int, float}:
            raise ValueError("timeout_seconds must be a strict integer or float")
        return value

    @field_validator("timeout_seconds")
    @classmethod
    def require_finite_timeout(cls, value: float) -> int | float:
        if not math.isfinite(value):
            raise ValueError("timeout_seconds must be finite")
        return value


class ExecutionContextV2(_FrozenContract):
    """Immutable information supplied to one future execution attempt."""

    request_id: StrictStr = Field(min_length=1, max_length=200)
    requested_at: datetime
    cancellation: CancellationTokenV2 = Field(default_factory=CancellationTokenV2)
    metadata: tuple[tuple[StrictStr, StrictStr], ...] = ()

    @field_validator("request_id")
    @classmethod
    def validate_request_id(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError("request_id must be non-whitespace without padding")
        return value

    @field_validator("requested_at")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("requested_at must include a timezone")
        return value

    @field_validator("metadata")
    @classmethod
    def validate_metadata(
        cls, value: tuple[tuple[str, str], ...]
    ) -> tuple[tuple[str, str], ...]:
        keys = tuple(key for key, _ in value)
        if any(not key.strip() for key, _ in value):
            raise ValueError("execution metadata keys must be non-whitespace")
        if any(not item.strip() for _, item in value):
            raise ValueError("execution metadata values must be non-whitespace")
        if len(keys) != len(set(keys)):
            raise ValueError("execution metadata keys must be unique")
        return value


class ProviderExecutionRequestV2(_FrozenContract):
    """Provider-neutral request presented to a future executor."""

    provider: ProviderDescriptorV2
    request_intent: ProviderRequestIntentV2
    request_envelope: ProviderRequestEnvelopeV2
    context: ExecutionContextV2
    timeout_policy: TimeoutPolicyV2

    @model_validator(mode="before")
    @classmethod
    def revalidate_nested_contracts(cls, value: object) -> object:
        if not isinstance(value, dict):
            return value
        validated = dict(value)
        contracts = (
            ("provider", ProviderDescriptorV2, "invalid provider descriptor authority"),
            (
                "request_intent",
                ProviderRequestIntentV2,
                "invalid request intent authority",
            ),
            (
                "request_envelope",
                ProviderRequestEnvelopeV2,
                "invalid request envelope authority",
            ),
            ("context", ExecutionContextV2, "invalid execution context"),
            ("timeout_policy", TimeoutPolicyV2, "invalid timeout policy"),
        )
        for field, model, error in contracts:
            if field in validated:
                validated[field] = _strict_reconstruction(
                    model, validated[field], error
                )
        return validated

    @model_validator(mode="after")
    def validate_provider_authority(self) -> ProviderExecutionRequestV2:
        if validate_provider_descriptor(self.provider):
            raise ValueError("invalid provider descriptor authority")
        if validate_provider_request_envelope(
            self.request_envelope, self.request_intent, self.provider
        ):
            raise ValueError("invalid request envelope authority")
        if self.provider.identity != self.request_envelope.descriptor_identity:
            raise ValueError("provider authority mismatch")
        if self.provider.fingerprint != self.request_envelope.descriptor_fingerprint:
            raise ValueError("provider authority mismatch")
        if self.provider.adapter_identity != self.request_envelope.adapter_identity:
            raise ValueError("adapter authority mismatch")
        return self


class ProviderExecutionResultV2(_FrozenContract):
    """Exactly one execution-layer outcome, separate from result semantics."""

    request_id: StrictStr = Field(min_length=1, max_length=200)
    provider_id: StrictStr = Field(min_length=1, max_length=100)
    request_envelope_identity: StrictStr = Field(min_length=1, max_length=200)
    outcome: ExecutionOutcomeV2 = Field(strict=True)
    finished_at: datetime
    provider_result: ProviderResultProjectionV2 | None = None
    failure_code: StrictStr | None = Field(default=None, min_length=1, max_length=120)
    failure_message: StrictStr | None = Field(
        default=None, min_length=1, max_length=500
    )

    @model_validator(mode="before")
    @classmethod
    def revalidate_provider_result(cls, value: object) -> object:
        if not isinstance(value, dict) or value.get("provider_result") is None:
            return value
        validated = dict(value)
        validated["provider_result"] = _strict_reconstruction(
            ProviderResultProjectionV2,
            validated["provider_result"],
            "invalid provider result projection",
        )
        return validated

    @field_validator("request_id", "provider_id", "request_envelope_identity")
    @classmethod
    def validate_identifiers(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError(
                "execution identifiers must be non-whitespace without padding"
            )
        return value

    @field_validator("failure_code")
    @classmethod
    def validate_failure_code(cls, value: str | None) -> str | None:
        if value is not None and (not value.strip() or value != value.strip()):
            raise ValueError("failure_code must be non-whitespace without padding")
        return value

    @field_validator("finished_at")
    @classmethod
    def require_aware_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("finished_at must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_exact_outcome(self) -> ProviderExecutionResultV2:
        if self.outcome is ExecutionOutcomeV2.COMPLETED:
            if self.provider_result is None:
                raise ValueError("completed execution requires a provider result")
            if self.failure_code is not None or self.failure_message is not None:
                raise ValueError("completed execution forbids failure details")
            return self
        if self.provider_result is not None:
            raise ValueError("failed execution forbids a provider result")
        if self.failure_code is None:
            raise ValueError("failed execution requires a failure code")
        return self


def _strict_reconstruction[ContractT: BaseModel](
    model: type[ContractT], value: object, error: str
) -> ContractT:
    """Reconstruct a nested contract without trusting an existing instance."""
    try:
        payload = (
            value.model_dump(mode="python", warnings=False)
            if isinstance(value, BaseModel)
            else value
        )
        return model.model_validate(payload, strict=True)
    except (
        AttributeError,
        IndexError,
        KeyError,
        TypeError,
        ValueError,
        ValidationError,
    ) as validation_error:
        raise ValueError(error) from validation_error


__all__ = (
    "CancellationTokenV2",
    "ExecutionContextV2",
    "ExecutionOutcomeV2",
    "ProviderExecutionRequestV2",
    "ProviderExecutionResultV2",
    "TimeoutPolicyV2",
)
