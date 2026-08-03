"""Strict public contracts for the offline live-shaped OpenAI smoke run."""

from __future__ import annotations

import math
from datetime import UTC, datetime
from typing import Literal

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


class _StrictModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        hide_input_in_errors=True,
    )


class OpenAILiveSmokeConfigurationV2(_StrictModel):
    """Caller-owned identity, time, timeout, and offline confirmation."""

    confirm_live: StrictBool = False
    request_id: StrictStr = Field(min_length=1, max_length=200)
    requested_at: datetime
    timeout_seconds: StrictInt | StrictFloat = Field(gt=0)

    @field_validator("confirm_live", mode="before")
    @classmethod
    def require_exact_confirmation_type(cls, value: object) -> object:
        if type(value) is not bool:
            raise ValueError("confirmation must be an exact boolean")
        return value

    @field_validator("request_id", mode="before")
    @classmethod
    def require_exact_request_id(cls, value: object) -> object:
        if (
            type(value) is not str
            or not value
            or not value.strip()
            or value != value.strip()
        ):
            raise ValueError("invalid request identifier")
        return value

    @field_validator("requested_at", mode="before")
    @classmethod
    def require_exact_utc_datetime(cls, value: object) -> object:
        if type(value) is not datetime or value.tzinfo is not UTC:
            raise ValueError("requested_at must be an exact UTC datetime")
        return value

    @field_validator("timeout_seconds", mode="before")
    @classmethod
    def require_frozen_timeout(cls, value: object) -> object:
        valid = False
        if type(value) is int:
            try:
                valid = value > 0 and math.isfinite(value)
            except OverflowError:
                valid = False
        elif type(value) is float:
            valid = value > 0.0 and math.isfinite(value)
        if not valid:
            raise ValueError("invalid timeout")
        return value


class OpenAILiveSmokeResultV2(_StrictModel):
    """Minimal successful interpretation of authentic provider output."""

    success: Literal[True] = True
    response_text: Literal["SMOKE_OK"] = "SMOKE_OK"


__all__ = ("OpenAILiveSmokeConfigurationV2", "OpenAILiveSmokeResultV2")
