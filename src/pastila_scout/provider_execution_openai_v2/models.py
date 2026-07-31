"""Strict immutable DTOs for the future OpenAI execution boundary."""

import math
from datetime import datetime
from enum import StrEnum
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)

from pastila_scout.provider_v2 import (
    ProviderFinishReasonV2,
    ProviderOutputInputV2,
    ProviderResultProjectionV2,
    ProviderResultStatusV2,
)


class _OpenAIContract(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
        hide_input_in_errors=True,
    )


class OpenAIClientErrorCategoryV2(StrEnum):
    """Stable categories independent of concrete SDK exceptions."""

    AUTHENTICATION = "authentication"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    INVALID_REQUEST = "invalid_request"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    CONTENT_FILTERED = "content_filtered"
    MALFORMED_RESPONSE = "malformed_response"
    INTERNAL_CLIENT_ERROR = "internal_client_error"


class OpenAIExecutionConfigV2(_OpenAIContract):
    """Generation configuration without credentials or transport settings."""

    model: StrictStr = Field(min_length=1, max_length=200)
    temperature: StrictInt | StrictFloat | None = Field(default=None, ge=0, le=2)
    max_output_tokens: StrictInt | None = Field(default=None, gt=0)
    stop_sequences: tuple[StrictStr, ...] = ()

    @field_validator("model")
    @classmethod
    def validate_model(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError("model must be non-whitespace without padding")
        return value

    @field_validator("temperature", mode="before")
    @classmethod
    def validate_temperature_type(cls, value: object) -> object:
        if value is not None and type(value) not in {int, float}:
            raise ValueError("temperature must be a strict integer or float")
        return value

    @field_validator("temperature")
    @classmethod
    def validate_finite_temperature(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("temperature must be finite")
        return value

    @field_validator("stop_sequences", mode="before")
    @classmethod
    def validate_stop_sequences(cls, value: object) -> tuple[str, ...]:
        return _validate_stop_sequences(value)


class OpenAIExecutionMessageV2(_OpenAIContract):
    """One ordered transport-neutral OpenAI message."""

    role: StrictStr
    content: StrictStr = Field(min_length=1, max_length=200_000)
    ordinal: StrictInt = Field(ge=0)

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if type(value) is not str or value not in {"system", "user", "assistant"}:
            raise ValueError("role must be system, user, or assistant")
        return value

    @field_validator("content")
    @classmethod
    def validate_content(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("message content must be non-whitespace")
        return value


class OpenAIExecutionRequestV2(_OpenAIContract):
    """Transport-neutral request for a future injected OpenAI client."""

    provider_id: StrictStr = "openai"
    execution_request_id: StrictStr = Field(min_length=1, max_length=200)
    request_envelope_identity: StrictStr = Field(min_length=1, max_length=200)
    model: StrictStr = Field(min_length=1, max_length=200)
    messages: tuple[OpenAIExecutionMessageV2, ...] = Field(min_length=1)
    timeout_seconds: StrictInt | StrictFloat = Field(gt=0)
    cancellation_requested: StrictBool
    temperature: StrictInt | StrictFloat | None = Field(default=None, ge=0, le=2)
    max_output_tokens: StrictInt | None = Field(default=None, gt=0)
    stop_sequences: tuple[StrictStr, ...] = ()

    @field_validator("provider_id")
    @classmethod
    def validate_provider_id(cls, value: str) -> str:
        if type(value) is not str or value != "openai":
            raise ValueError("provider_id must be exactly openai")
        return value

    @field_validator("execution_request_id", "request_envelope_identity", "model")
    @classmethod
    def validate_identifiers(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError(
                "request identifiers must be non-whitespace without padding"
            )
        return value

    @field_validator("timeout_seconds", mode="before")
    @classmethod
    def validate_timeout_type(cls, value: object) -> object:
        if type(value) not in {int, float}:
            raise ValueError("timeout_seconds must be a strict integer or float")
        return value

    @field_validator("temperature", mode="before")
    @classmethod
    def validate_temperature_type(cls, value: object) -> object:
        if value is not None and type(value) not in {int, float}:
            raise ValueError("temperature must be a strict integer or float")
        return value

    @field_validator("stop_sequences", mode="before")
    @classmethod
    def validate_stop_sequences(cls, value: object) -> tuple[str, ...]:
        return _validate_stop_sequences(value)

    @field_validator("timeout_seconds", "temperature")
    @classmethod
    def validate_finite_controls(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("generation controls must be finite")
        return value

    @model_validator(mode="after")
    def validate_message_order(self) -> Self:
        if tuple(item.ordinal for item in self.messages) != tuple(
            range(len(self.messages))
        ):
            raise ValueError("message ordinals must match tuple order")
        return self


class OpenAIExecutionOutputV2(_OpenAIContract):
    """One deterministic provider output in request-unit order."""

    ordinal: StrictInt = Field(ge=0)
    generated_text: StrictStr = Field(min_length=1, max_length=500_000)
    finish_reason: ProviderFinishReasonV2 = Field(strict=True)


class OpenAIExecutionResponseV2(_OpenAIContract):
    """Transport-neutral response returned by a future OpenAI client."""

    provider_request_id: StrictStr = Field(min_length=1, max_length=200)
    model: StrictStr = Field(min_length=1, max_length=200)
    finished_at: datetime
    status: ProviderResultStatusV2 = Field(strict=True)
    outputs: tuple[OpenAIExecutionOutputV2, ...]
    failure_category: OpenAIClientErrorCategoryV2 | None = Field(
        default=None, strict=True
    )
    failure_code: StrictStr | None = Field(default=None, min_length=1, max_length=120)

    @field_validator("provider_request_id", "model", "failure_code")
    @classmethod
    def validate_strings(cls, value: str | None) -> str | None:
        if value is not None and (not value.strip() or value != value.strip()):
            raise ValueError("response strings must be non-whitespace without padding")
        return value

    @field_validator("finished_at")
    @classmethod
    def validate_finished_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("finished_at must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_response_semantics(self) -> Self:
        if tuple(item.ordinal for item in self.outputs) != tuple(
            range(len(self.outputs))
        ):
            raise ValueError("output ordinals must match tuple order")
        category = self.failure_category
        if category is OpenAIClientErrorCategoryV2.CONTENT_FILTERED:
            if self.status is not ProviderResultStatusV2.PARTIAL:
                raise ValueError(
                    "content filtering requires partial provider semantics"
                )
            if not self.outputs:
                raise ValueError("content filtering requires output")
            if self.failure_code is None:
                raise ValueError("content filtering requires a failure code")
            if any(
                item.finish_reason is not ProviderFinishReasonV2.CONTENT_FILTERED
                for item in self.outputs
            ):
                raise ValueError(
                    "content-filter category conflicts with output finish reason"
                )
        elif category is not None and (
            self.status is not ProviderResultStatusV2.FAILED or self.outputs
        ):
            raise ValueError("client failure requires failed provider semantics")
        elif any(
            item.finish_reason is ProviderFinishReasonV2.CONTENT_FILTERED
            for item in self.outputs
        ):
            raise ValueError(
                "content-filter finish reason requires content-filter category"
            )
        _projection_from_response(self)
        return self


def _validate_stop_sequences(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise TypeError("stop sequences must be a list or tuple")
    if any(type(item) is not str for item in value):
        raise ValueError("stop sequences must contain strict strings")
    result = tuple(value)
    if any(not item.strip() or item != item.strip() for item in result):
        raise ValueError("stop sequences must contain unpadded non-whitespace text")
    if len(result) != len(set(result)):
        raise ValueError("stop sequences must be unique")
    return result


def _projection_from_response(
    response: OpenAIExecutionResponseV2,
) -> ProviderResultProjectionV2:
    return ProviderResultProjectionV2(
        status=response.status,
        outputs=tuple(
            ProviderOutputInputV2(
                source_request_reference=f"openai-output:{item.ordinal}",
                ordinal=item.ordinal,
                generated_text=item.generated_text,
                finish_reason=item.finish_reason,
            )
            for item in response.outputs
        ),
        failure_code=response.failure_code,
    )


__all__ = (
    "OpenAIClientErrorCategoryV2",
    "OpenAIExecutionConfigV2",
    "OpenAIExecutionMessageV2",
    "OpenAIExecutionOutputV2",
    "OpenAIExecutionRequestV2",
    "OpenAIExecutionResponseV2",
)
