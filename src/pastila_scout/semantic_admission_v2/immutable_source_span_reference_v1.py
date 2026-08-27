"""Versioned copyless source-span references and their pure resolver.

This module performs no I/O and has no evaluator, runner, or model dependency.
Evidence text is always sliced from caller-supplied immutable UTF-8 bytes.
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from enum import StrEnum
from typing import Annotated, Literal, Mapping

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator


SCHEMA_NAME = "pastila-semantic-admission-v2-source-span-reference"
SCHEMA_VERSION = "1.0.0-evaluation.1"

Sha256Hex = Annotated[str, StringConstraints(pattern=r"^[0-9a-f]{64}$")]


class SourceRoleV1(StrEnum):
    CANDIDATE = "CANDIDATE"
    FACTUAL_AUTHORITY = "FACTUAL_AUTHORITY"


class SourceSpanReferenceV1(BaseModel):
    """A model-selectable source identity plus half-open UTF-8 byte range."""

    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)

    schema_name: Literal[SCHEMA_NAME] = SCHEMA_NAME
    schema_version: Literal[SCHEMA_VERSION] = SCHEMA_VERSION
    source_role: SourceRoleV1
    source_sha256: Sha256Hex
    start_utf8: int = Field(ge=0)
    end_utf8: int = Field(ge=0)

    @model_validator(mode="after")
    def require_nonempty_half_open_range(self) -> "SourceSpanReferenceV1":
        if self.start_utf8 >= self.end_utf8:
            raise ValueError("source span must satisfy start_utf8 < end_utf8")
        return self


@dataclass(frozen=True, slots=True)
class ImmutableUtf8SourceV1:
    role: SourceRoleV1
    data: bytes
    sha256: str

    @classmethod
    def bind(cls, *, role: SourceRoleV1, data: bytes) -> "ImmutableUtf8SourceV1":
        immutable = bytes(data)
        immutable.decode("utf-8", errors="strict")
        return cls(role=role, data=immutable, sha256=hashlib.sha256(immutable).hexdigest())


class SourceProjectionFailureCodeV1(StrEnum):
    IDENTITY_DRIFT = "STAGE_P_SOURCE_REFERENCE_IDENTITY_DRIFT"
    ROLE_MISMATCH = "STAGE_P_SOURCE_REFERENCE_ROLE_MISMATCH"
    RANGE_INVALID = "STAGE_P_SOURCE_REFERENCE_RANGE_INVALID"
    UTF8_BOUNDARY_INVALID = "STAGE_P_SOURCE_REFERENCE_UTF8_BOUNDARY_INVALID"
    EMPTY = "STAGE_P_SOURCE_REFERENCE_EMPTY"
    SOURCE_UNAVAILABLE = "STAGE_P_SOURCE_PROJECTION_FAILURE"


@dataclass(frozen=True, slots=True)
class SourceProjectionErrorV1(ValueError):
    code: SourceProjectionFailureCodeV1

    def __str__(self) -> str:
        return self.code.value


@dataclass(frozen=True, slots=True)
class ResolvedSourceSpanV1:
    source_role: SourceRoleV1
    source_sha256: str
    start_utf8: int
    end_utf8: int
    projected_bytes: bytes
    projected_sha256: str
    projected_text: str


def resolve_source_span_v1(
    reference: SourceSpanReferenceV1,
    *,
    expected_role: SourceRoleV1,
    sources: Mapping[SourceRoleV1, ImmutableUtf8SourceV1],
) -> ResolvedSourceSpanV1:
    """Resolve exactly one immutable slice or raise a stable fail-closed error."""
    if reference.source_role is not expected_role:
        raise SourceProjectionErrorV1(SourceProjectionFailureCodeV1.ROLE_MISMATCH)
    source = sources.get(expected_role)
    if source is None or source.role is not expected_role:
        raise SourceProjectionErrorV1(SourceProjectionFailureCodeV1.SOURCE_UNAVAILABLE)
    if reference.source_sha256 != source.sha256:
        raise SourceProjectionErrorV1(SourceProjectionFailureCodeV1.IDENTITY_DRIFT)
    if reference.start_utf8 == reference.end_utf8:
        raise SourceProjectionErrorV1(SourceProjectionFailureCodeV1.EMPTY)
    if not (0 <= reference.start_utf8 < reference.end_utf8 <= len(source.data)):
        raise SourceProjectionErrorV1(SourceProjectionFailureCodeV1.RANGE_INVALID)
    projected = source.data[reference.start_utf8:reference.end_utf8]
    try:
        text = projected.decode("utf-8", errors="strict")
    except UnicodeDecodeError as exc:
        raise SourceProjectionErrorV1(
            SourceProjectionFailureCodeV1.UTF8_BOUNDARY_INVALID
        ) from exc
    return ResolvedSourceSpanV1(
        source_role=source.role,
        source_sha256=source.sha256,
        start_utf8=reference.start_utf8,
        end_utf8=reference.end_utf8,
        projected_bytes=projected,
        projected_sha256=hashlib.sha256(projected).hexdigest(),
        projected_text=text,
    )


__all__ = (
    "ImmutableUtf8SourceV1",
    "ResolvedSourceSpanV1",
    "SCHEMA_NAME",
    "SCHEMA_VERSION",
    "SourceProjectionErrorV1",
    "SourceProjectionFailureCodeV1",
    "SourceRoleV1",
    "SourceSpanReferenceV1",
    "resolve_source_span_v1",
)
