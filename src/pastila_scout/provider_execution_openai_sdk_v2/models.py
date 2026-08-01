"""Immutable transport specifications without concrete SDK imports."""

import math
from datetime import datetime
from typing import Self

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    StrictStr,
    field_validator,
    model_validator,
)


class _SDKContract(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
        hide_input_in_errors=True,
    )


class OpenAISDKMessageV2(_SDKContract):
    role: StrictStr
    content: StrictStr = Field(min_length=1, max_length=200_000)

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if type(value) is not str or value not in {"system", "user", "assistant"}:
            raise ValueError("invalid SDK message role")
        return value

    @field_validator("content", mode="before")
    @classmethod
    def validate_content(cls, value: object) -> object:
        if type(value) is not str or not value.strip():
            raise ValueError("invalid SDK message content")
        return value


class OpenAISDKRequestV2(_SDKContract):
    model: StrictStr = Field(min_length=1, max_length=200)
    messages: tuple[OpenAISDKMessageV2, ...] = Field(min_length=1)
    timeout_seconds: StrictInt | StrictFloat = Field(gt=0)
    temperature: StrictInt | StrictFloat | None = Field(default=None, ge=0, le=2)
    max_output_tokens: StrictInt | None = Field(default=None, gt=0)
    stop_sequences: tuple[StrictStr, ...] = ()

    @field_validator("model", mode="before")
    @classmethod
    def validate_model(cls, value: object) -> object:
        if type(value) is not str or not value.strip() or value != value.strip():
            raise ValueError("invalid SDK model identifier")
        return value

    @field_validator("stop_sequences", mode="before")
    @classmethod
    def validate_stop_sequences(cls, value: object) -> tuple[str, ...]:
        return _validate_stop_sequences(value)

    @field_validator("timeout_seconds", "temperature")
    @classmethod
    def validate_finite_numbers(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("SDK numeric controls must be finite")
        return value


class OpenAISDKOutputV2(_SDKContract):
    ordinal: StrictInt = Field(ge=0)
    text: StrictStr = Field(min_length=1, max_length=500_000)
    finish_reason: StrictStr = Field(min_length=1, max_length=80)

    @field_validator("text", mode="before")
    @classmethod
    def validate_text(cls, value: object) -> object:
        if type(value) is not str or not value.strip():
            raise ValueError("invalid SDK output text")
        return value


class OpenAISDKResponseV2(_SDKContract):
    response_id: StrictStr = Field(min_length=1, max_length=200)
    model: StrictStr = Field(min_length=1, max_length=200)
    finished_at: datetime
    outputs: tuple[OpenAISDKOutputV2, ...] = Field(min_length=1)

    @field_validator("response_id", "model")
    @classmethod
    def validate_identifiers(cls, value: str) -> str:
        if not value.strip() or value != value.strip():
            raise ValueError("SDK response identifiers must be unpadded")
        return value

    @field_validator("finished_at")
    @classmethod
    def validate_timestamp(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("SDK response timestamp must be timezone-aware")
        return value

    @model_validator(mode="after")
    def validate_output_order(self) -> Self:
        if tuple(item.ordinal for item in self.outputs) != tuple(
            range(len(self.outputs))
        ):
            raise ValueError("SDK output ordinals must match tuple order")
        return self


def _validate_stop_sequences(value: object) -> tuple[str, ...]:
    if not isinstance(value, (list, tuple)):
        raise TypeError("invalid SDK stop sequences")
    if any(type(item) is not str for item in value):
        raise ValueError("invalid SDK stop sequences")
    result = tuple(value)
    if any(not item.strip() or item != item.strip() for item in result):
        raise ValueError("invalid SDK stop sequences")
    if len(result) != len(set(result)):
        raise ValueError("invalid SDK stop sequences")
    return result


__all__ = ("OpenAISDKRequestV2",)
