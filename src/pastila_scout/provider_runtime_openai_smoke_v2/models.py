"""Immutable contracts for the injected offline OpenAI smoke boundary."""

from __future__ import annotations

import math

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictBool,
    StrictFloat,
    StrictInt,
    StrictStr,
    field_validator,
)


class OpenAISmokeTestConfigurationV2(BaseModel):
    """Minimal non-secret policy for one explicitly confirmed live smoke test."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
        hide_input_in_errors=True,
    )

    confirm_live: StrictBool = False
    model: StrictStr
    timeout_seconds: StrictInt | StrictFloat = Field(gt=0)

    @field_validator("model", mode="before")
    @classmethod
    def validate_model(cls, value: object) -> object:
        if type(value) is not str or not value.strip() or value != value.strip():
            raise ValueError("invalid OpenAI smoke-test model")
        return value

    @field_validator("timeout_seconds", mode="before")
    @classmethod
    def validate_timeout(cls, value: object) -> object:
        if type(value) is int:
            valid = value > 0
        elif type(value) is float:
            valid = math.isfinite(value) and value > 0.0
        else:
            valid = False
        if not valid:
            raise ValueError("invalid OpenAI smoke-test timeout")
        return value


class OpenAISmokeTestResultV2(BaseModel):
    """Minimal deterministic result returned by an offline smoke execution."""

    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        revalidate_instances="always",
        hide_input_in_errors=True,
    )

    success: StrictBool
    response_text: StrictStr

    @field_validator("response_text", mode="before")
    @classmethod
    def validate_response_text(cls, value: object) -> object:
        if type(value) is not str or not value or value != value.strip():
            raise ValueError("invalid OpenAI smoke-test response")
        return value


__all__ = ("OpenAISmokeTestConfigurationV2", "OpenAISmokeTestResultV2")
