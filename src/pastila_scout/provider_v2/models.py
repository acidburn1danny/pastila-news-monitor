"""Strict immutable provider-neutral V2 authority contracts."""

import unicodedata
from enum import Enum, StrEnum
from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

IDENTITY_PATTERN = r"^scout:[a-z0-9]+(?:-[a-z0-9]+)*:[0-9a-f]{64}$"
FINGERPRINT_PATTERN = r"^[0-9a-f]{64}$"
PROVIDER_IDENTIFIER_PATTERN = r"^[a-z0-9]+(?:-[a-z0-9]+)*$"
SEMVER_PATTERN = r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)$"


class ProviderV2Model(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    @field_validator("*", mode="before")
    @classmethod
    def normalize_unicode(cls, value):
        if isinstance(value, Enum):
            return value
        if isinstance(value, str):
            return unicodedata.normalize("NFC", value)
        return value


class ProviderCapabilityV2(StrEnum):
    REQUEST_CONSTRUCTION = "request_construction"
    EXECUTION = "execution"
    RESPONSE_EXTRACTION = "response_extraction"
    VALIDATION = "validation"
    PROJECTION = "projection"
    METADATA = "metadata"


class ProviderResultStatusV2(StrEnum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


class ProviderFinishReasonV2(StrEnum):
    COMPLETED = "completed"
    LENGTH = "length"
    CONTENT_FILTERED = "content_filtered"
    FAILED = "failed"
    UNKNOWN = "unknown"


class ProviderDescriptorV2(ProviderV2Model):
    contract_version: Literal["module-2.9-provider-descriptor-v2"] = (
        "module-2.9-provider-descriptor-v2"
    )
    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    provider_id: str = Field(pattern=PROVIDER_IDENTIFIER_PATTERN, max_length=64)
    display_name: str = Field(min_length=1, max_length=80)
    capabilities: tuple[ProviderCapabilityV2, ...] = Field(min_length=1)
    descriptor_version: str = Field(pattern=SEMVER_PATTERN)
    adapter_identity: str = Field(pattern=IDENTITY_PATTERN)

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(cls, value):
        if len(value) != len(set(value)) or value != tuple(sorted(value, key=str)):
            raise ValueError("capabilities must be unique and canonically ordered")
        return value


class ProviderMessageInputV2(ProviderV2Model):
    role: Literal["instruction", "context", "generation"]
    content: str = Field(min_length=1, max_length=200_000)
    ordinal: int = Field(ge=0, strict=True)


class ProviderRequestUnitInputV2(ProviderV2Model):
    source_request_reference: str = Field(min_length=1, max_length=200)
    ordinal: int = Field(ge=0, strict=True)
    messages: tuple[ProviderMessageInputV2, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_message_order(self) -> Self:
        if tuple(item.ordinal for item in self.messages) != tuple(
            range(len(self.messages))
        ):
            raise ValueError("message ordinals must match tuple order")
        return self


class ProviderRequestIntentV2(ProviderV2Model):
    execution_plan_reference: str = Field(min_length=1, max_length=200)
    execution_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    execution_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    draft_reference: str = Field(min_length=1, max_length=200)
    draft_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    request_units: tuple[ProviderRequestUnitInputV2, ...]

    @model_validator(mode="after")
    def validate_unit_order(self) -> Self:
        if tuple(item.ordinal for item in self.request_units) != tuple(
            range(len(self.request_units))
        ):
            raise ValueError("request-unit ordinals must match tuple order")
        references = tuple(item.source_request_reference for item in self.request_units)
        if len(references) != len(set(references)):
            raise ValueError("source request references must be unique")
        return self


class ProviderRequestMessageV2(ProviderV2Model):
    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    message_reference: str = Field(min_length=1, max_length=200)
    role: Literal["instruction", "context", "generation"]
    content: str = Field(min_length=1, max_length=200_000)
    ordinal: int = Field(ge=0, strict=True)


class ProviderRequestUnitV2(ProviderV2Model):
    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    request_unit_reference: str = Field(min_length=1, max_length=200)
    source_request_reference: str = Field(min_length=1, max_length=200)
    ordinal: int = Field(ge=0, strict=True)
    messages: tuple[ProviderRequestMessageV2, ...] = Field(min_length=1)


class ProviderRequestEnvelopeV2(ProviderV2Model):
    contract_version: Literal["module-2.9-provider-request-envelope-v2"] = (
        "module-2.9-provider-request-envelope-v2"
    )
    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    request_envelope_reference: str = Field(min_length=1, max_length=200)
    descriptor_identity: str = Field(pattern=IDENTITY_PATTERN)
    descriptor_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    adapter_identity: str = Field(pattern=IDENTITY_PATTERN)
    execution_plan_reference: str = Field(min_length=1, max_length=200)
    execution_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    execution_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    draft_reference: str = Field(min_length=1, max_length=200)
    draft_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    request_units: tuple[ProviderRequestUnitV2, ...]


class ProviderOutputInputV2(ProviderV2Model):
    source_request_reference: str = Field(min_length=1, max_length=200)
    ordinal: int = Field(ge=0, strict=True)
    generated_text: str = Field(min_length=1, max_length=500_000)
    finish_reason: ProviderFinishReasonV2


class ProviderResultProjectionV2(ProviderV2Model):
    status: ProviderResultStatusV2
    outputs: tuple[ProviderOutputInputV2, ...]
    failure_code: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_status(self) -> Self:
        ordinals = tuple(item.ordinal for item in self.outputs)
        if ordinals != tuple(range(len(self.outputs))):
            raise ValueError("output ordinals must match tuple order")
        _validate_result_semantics(self.status, self.outputs, self.failure_code)
        return self


class ProviderResultUnitV2(ProviderV2Model):
    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    result_unit_reference: str = Field(min_length=1, max_length=200)
    source_request_reference: str = Field(min_length=1, max_length=200)
    request_unit_reference: str = Field(min_length=1, max_length=200)
    request_unit_identity: str = Field(pattern=IDENTITY_PATTERN)
    request_unit_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    ordinal: int = Field(ge=0, strict=True)
    generated_text: str = Field(min_length=1, max_length=500_000)
    finish_reason: ProviderFinishReasonV2


class ProviderResultEnvelopeV2(ProviderV2Model):
    contract_version: Literal["module-2.9-provider-result-envelope-v2"] = (
        "module-2.9-provider-result-envelope-v2"
    )
    identity: str = Field(pattern=IDENTITY_PATTERN)
    fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    result_envelope_reference: str = Field(min_length=1, max_length=200)
    descriptor_identity: str = Field(pattern=IDENTITY_PATTERN)
    descriptor_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    adapter_identity: str = Field(pattern=IDENTITY_PATTERN)
    request_envelope_reference: str = Field(min_length=1, max_length=200)
    request_envelope_identity: str = Field(pattern=IDENTITY_PATTERN)
    request_envelope_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    execution_plan_reference: str = Field(min_length=1, max_length=200)
    execution_plan_identity: str = Field(pattern=IDENTITY_PATTERN)
    execution_plan_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    draft_reference: str = Field(min_length=1, max_length=200)
    draft_fingerprint: str = Field(pattern=FINGERPRINT_PATTERN)
    status: ProviderResultStatusV2
    outputs: tuple[ProviderResultUnitV2, ...]
    failure_code: str | None = Field(default=None, max_length=120)

    @model_validator(mode="after")
    def validate_status(self) -> Self:
        _validate_result_semantics(self.status, self.outputs, self.failure_code)
        return self


class ProviderV2ValidationIssue(ProviderV2Model):
    code: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    artifact_reference: str = Field(min_length=1, max_length=200)
    field: str | None = Field(default=None, max_length=100)


def _validate_result_semantics(status, outputs, failure_code) -> None:
    reasons = tuple(item.finish_reason for item in outputs)
    if status is ProviderResultStatusV2.SUCCESS:
        if not outputs:
            raise ValueError("successful result requires output")
        if failure_code is not None:
            raise ValueError("successful result cannot contain failure_code")
        if any(reason is not ProviderFinishReasonV2.COMPLETED for reason in reasons):
            raise ValueError("successful result requires completed outputs")
        return
    if not failure_code:
        raise ValueError("non-successful result requires failure_code")
    if status is ProviderResultStatusV2.FAILED:
        if outputs:
            raise ValueError("failed result cannot contain outputs")
        return
    if not outputs:
        raise ValueError("partial result requires output")
    if all(reason is ProviderFinishReasonV2.COMPLETED for reason in reasons):
        raise ValueError("partial result cannot be fully completed")
    if all(reason is ProviderFinishReasonV2.FAILED for reason in reasons):
        raise ValueError("partial result cannot be wholly failed")


__all__ = tuple(
    name
    for name in globals()
    if name.startswith("Provider") and name not in {"ProviderV2Model"}
)
