"""Shared primitives for the public Scout/Editor JSON contracts."""

from __future__ import annotations

import re
from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

SCOUT_INPUT_VERSION = "scout-editor-input-v1"
EDITOR_OUTPUT_VERSION = "editor-agent-output-v1"
EDITORIAL_CONTRACT_VERSION = "scout-editorial-semantics-v1"
SELECTION_PROFILE_VERSION = "editor-selection-profile-v1"
EPISODE_CONTEXT_VERSION = "episode-context-v1"
ALLOWED_CATEGORIES = (
    "Politica",
    "Social",
    "Conspiratii",
    "Economie",
    "CanCan",
    "Externe",
    "Diverse",
)

NonEmptyText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
ShortText = Annotated[
    str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)
]
Extensions = dict[str, Any]


class ContractModel(BaseModel):
    """Strict immutable base for all public contract models."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class ContractStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    INVALID_INPUT = "invalid_input"
    INCOMPATIBLE_CONTRACT = "incompatible_contract"
    INSUFFICIENT_CANDIDATES = "insufficient_candidates"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    FAILED = "failed"


class ContractIssue(ContractModel):
    code: NonEmptyText
    message: NonEmptyText
    event_id: int | None = Field(default=None, gt=0)
    recoverable: bool


class DurationValue(ContractModel):
    unit: str = Field(default="seconds", pattern="^seconds$")
    value: int = Field(ge=0)


class SourceReference(ContractModel):
    source_id: NonEmptyText
    source_name: NonEmptyText
    url: NonEmptyText
    title: NonEmptyText
    published_at: datetime | None = None


class InheritedScoutScores(ContractModel):
    deterministic_score: float = Field(ge=0, le=100)
    ai_editorial_score: float | None = Field(default=None, ge=0, le=100)
    final_score: float = Field(ge=0, le=100)
    recommendation: str = Field(pattern="^(STRONG_PICK|POSSIBLE_PICK|BACKUP|SKIP)$")


def validate_unique_positive_ids(values: tuple[int, ...]) -> tuple[int, ...]:
    """Validate a stable sequence of positive, unique identifiers."""

    if any(value <= 0 for value in values):
        raise ValueError("event IDs must be positive")
    if len(values) != len(set(values)):
        raise ValueError("event IDs must be unique")
    return values


def validate_extension_keys(value: Extensions) -> Extensions:
    """Keep extensions explicit and namespaced."""

    invalid = [key for key in value if not re.fullmatch(r"[a-z][a-z0-9_.-]*", key)]
    if invalid:
        raise ValueError("extension keys must be lowercase namespaced identifiers")
    return value


class ExtensibleContractModel(ContractModel):
    """Contract model with the sole forward-compatible extension point."""

    extensions: Extensions = Field(default_factory=dict)

    _extension_keys = field_validator("extensions")(validate_extension_keys)
