"""Strict immutable canonical smoke-domain authority models."""

from __future__ import annotations

from typing import Literal, Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

_IDENTITY_PATTERN = r"^scout:[a-z0-9]+(?:-[a-z0-9]+)*:[0-9a-f]{64}$"
_FINGERPRINT_PATTERN = r"^[0-9a-f]{64}$"
_FIXED_PROMPT = "Reply with exactly:\n\nSMOKE_OK"
_PLAN_REFERENCE = "canonical-smoke-plan-v2"
_DRAFT_REFERENCE = "canonical-smoke-draft-v2"
_SOURCE_REQUEST_REFERENCE = "canonical-smoke-source-request-v2"


class _StrictAuthorityModel(BaseModel):
    model_config = ConfigDict(
        frozen=True,
        extra="forbid",
        strict=True,
        revalidate_instances="always",
        hide_input_in_errors=True,
    )


class _SmokeGenerationMessageV2(_StrictAuthorityModel):
    role: Literal["generation"] = "generation"
    content: Literal[_FIXED_PROMPT] = _FIXED_PROMPT
    ordinal: Literal[0] = 0


class _SmokeRequestUnitV2(_StrictAuthorityModel):
    source_request_reference: Literal[_SOURCE_REQUEST_REFERENCE] = (
        _SOURCE_REQUEST_REFERENCE
    )
    ordinal: Literal[0] = 0
    messages: tuple[_SmokeGenerationMessageV2, ...] = Field(
        default_factory=lambda: (_SmokeGenerationMessageV2(),),
        min_length=1,
        max_length=1,
    )


class SmokeExecutionPlanV2(_StrictAuthorityModel):
    """Canonical, self-verifying authority for the fixed smoke operation."""

    contract_version: Literal["module-2.9-smoke-execution-plan-v2"] = (
        "module-2.9-smoke-execution-plan-v2"
    )
    plan_reference: Literal[_PLAN_REFERENCE] = _PLAN_REFERENCE
    plan_identity: str = Field(pattern=_IDENTITY_PATTERN)
    plan_fingerprint: str = Field(pattern=_FINGERPRINT_PATTERN)
    draft_reference: Literal[_DRAFT_REFERENCE] = _DRAFT_REFERENCE
    draft_fingerprint: str = Field(pattern=_FINGERPRINT_PATTERN)
    request_units: tuple[_SmokeRequestUnitV2, ...] = Field(
        default_factory=lambda: (_SmokeRequestUnitV2(),),
        min_length=1,
        max_length=1,
    )

    @model_validator(mode="after")
    def validate_canonical_authority(self) -> Self:
        from .authority import _expected_plan_seals

        identity, fingerprint, draft = _expected_plan_seals(self)
        if self.draft_fingerprint != draft:
            raise ValueError("invalid canonical smoke draft fingerprint")
        if self.plan_identity != identity:
            raise ValueError("invalid canonical smoke plan identity")
        if self.plan_fingerprint != fingerprint:
            raise ValueError("invalid canonical smoke plan fingerprint")
        return self


__all__ = ("SmokeExecutionPlanV2",)
