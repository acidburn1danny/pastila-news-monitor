"""Strict immutable DTOs for Ollama's chat HTTP API."""

import math
from datetime import datetime
from typing import Literal
from urllib.parse import urlsplit

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    StrictFloat,
    StrictInt,
    StrictStr,
    field_validator,
)


class _OllamaModel(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", strict=True)


class OllamaExecutionConfigV1(_OllamaModel):
    """Endpoint and generation settings owned by composition."""

    model: StrictStr = Field(default="qwen3:14b", min_length=1, max_length=200)
    base_url: StrictStr = Field(default="http://localhost:11434", min_length=1)
    temperature: StrictInt | StrictFloat | None = Field(default=None, ge=0)
    max_output_tokens: StrictInt | None = Field(default=None, gt=0)
    stop_sequences: tuple[StrictStr, ...] = ()

    @field_validator("model", "base_url", mode="before")
    @classmethod
    def validate_text(cls, value: object) -> str:
        if type(value) is not str:
            raise ValueError("configuration text must be an exact string")
        if not value.strip() or value != value.strip():
            raise ValueError("configuration text must be unpadded and non-whitespace")
        return value.rstrip("/") if value.startswith(("http://", "https://")) else value

    @field_validator("base_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        try:
            parsed = urlsplit(value)
            port = parsed.port
        except ValueError as error:
            raise ValueError("base_url must be a valid HTTP origin") from error
        if (
            parsed.scheme not in {"http", "https"}
            or parsed.hostname is None
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
            or port is not None
            and not 0 < port < 65536
        ):
            raise ValueError("base_url must be a valid credential-free HTTP origin")
        return value

    @field_validator("temperature", mode="before")
    @classmethod
    def validate_temperature_type(cls, value: object) -> object:
        if value is not None and type(value) not in {int, float}:
            raise ValueError("temperature must be an integer or float")
        return value

    @field_validator("temperature")
    @classmethod
    def validate_temperature_finite(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("temperature must be finite")
        return value

    @field_validator("stop_sequences", mode="before")
    @classmethod
    def validate_stops(cls, value: object) -> object:
        if type(value) is not tuple or any(type(item) is not str for item in value):
            raise ValueError("stop sequences must be a tuple of exact strings")
        if any(not item.strip() or item != item.strip() for item in value):
            raise ValueError("stop sequences must be unpadded and non-whitespace")
        if len(value) != len(set(value)):
            raise ValueError("stop sequences must be unique")
        return value


class OllamaChatMessageV1(_OllamaModel):
    role: StrictStr
    content: StrictStr = Field(min_length=1, max_length=200_000)

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        if value not in {"system", "user", "assistant"}:
            raise ValueError("unsupported Ollama message role")
        return value


class OllamaChatRequestV1(_OllamaModel):
    model: StrictStr
    messages: tuple[OllamaChatMessageV1, ...] = Field(min_length=1)
    stream: bool = False
    format: dict[str, object] | None = None
    options: dict[str, object] = Field(default_factory=dict)


class OllamaResponseMessageV1(_OllamaModel):
    role: StrictStr
    content: StrictStr
    thinking: StrictStr | None = None

    @field_validator("role", "content", "thinking", mode="before")
    @classmethod
    def require_exact_strings(cls, value: object) -> object:
        if value is not None and type(value) is not str:
            raise ValueError("response message fields must be exact strings")
        return value

    @field_validator("role")
    @classmethod
    def require_assistant(cls, value: str) -> str:
        if value != "assistant":
            raise ValueError("response message must be from assistant")
        return value


class OllamaChatResponseV1(_OllamaModel):
    model: StrictStr = Field(min_length=1)
    created_at: datetime
    message: OllamaResponseMessageV1
    done: bool
    done_reason: Literal["stop", "length"]
    total_duration: StrictInt | None = Field(default=None, ge=0)
    load_duration: StrictInt | None = Field(default=None, ge=0)
    prompt_eval_count: StrictInt | None = Field(default=None, ge=0)
    prompt_eval_duration: StrictInt | None = Field(default=None, ge=0)
    eval_count: StrictInt | None = Field(default=None, ge=0)
    eval_duration: StrictInt | None = Field(default=None, ge=0)

    @field_validator("model", "done_reason", mode="before")
    @classmethod
    def require_exact_strings(cls, value: object) -> object:
        if type(value) is not str:
            raise ValueError("response fields must be exact strings")
        return value

    @field_validator("created_at")
    @classmethod
    def require_aware_created_at(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("created_at must include a timezone")
        return value

    @field_validator("created_at", mode="before")
    @classmethod
    def parse_created_at(cls, value: object) -> datetime:
        if type(value) is not str:
            raise ValueError("created_at must be an exact ISO-8601 string")
        try:
            return datetime.fromisoformat(value)
        except ValueError as error:
            raise ValueError("created_at must be valid ISO-8601") from error


__all__ = (
    "OllamaChatMessageV1",
    "OllamaChatRequestV1",
    "OllamaChatResponseV1",
    "OllamaExecutionConfigV1",
    "OllamaResponseMessageV1",
)
