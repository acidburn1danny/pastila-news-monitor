"""Provider boundary for AI verification."""

from dataclasses import dataclass
from typing import Protocol

from pastila_scout.models.ai import EventVerificationRequest


class ProviderError(RuntimeError):
    """A provider failure with an explicit retry policy."""

    def __init__(self, message: str, *, retryable: bool = True) -> None:
        super().__init__(message)
        self.retryable = retryable


class AIProvider(Protocol):
    """Generate one structured decision without exposing an SDK upstream."""

    def verify(self, request: EventVerificationRequest) -> str:
        """Return a JSON decision for a storage-independent article pair."""


@dataclass(frozen=True)
class StructuredAIRequest:
    """Provider-neutral structured-output operation."""

    name: str
    instructions: str
    input_json: str
    json_schema: dict[str, object]


@dataclass(frozen=True)
class StructuredAIResponse:
    """Provider output and optional usage accounting."""

    output_text: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None


class StructuredAIProvider(Protocol):
    """Complete a named schema-constrained task."""

    def complete_structured(self, request: StructuredAIRequest) -> StructuredAIResponse:
        """Return structured text and usage without leaking an SDK upstream."""


def resolve_openai_api_key(env_file: str = ".env") -> str | None:
    """Resolve the OpenAI key from the environment, then a local .env file."""

    import os
    from pathlib import Path

    key = os.environ.get("OPENAI_API_KEY", "").strip()
    if key:
        return key
    path = Path(env_file)
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None
    for line in lines:
        candidate = line.strip()
        if not candidate or candidate.startswith("#") or "=" not in candidate:
            continue
        name, value = candidate.split("=", 1)
        if name.strip() == "OPENAI_API_KEY":
            return value.strip().strip("\"'") or None
    return None
