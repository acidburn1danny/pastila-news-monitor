"""Canonical smoke plan minting and a deliberately non-operational shell."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum, auto
from typing import Never, Self

from pydantic import ValidationError

from pastila_scout.provider_v2.canonical import semantic_sha256

from .errors import (
    SmokeExecutionRequestAuthorityError,
    SmokeExecutionRequestConfigurationError,
    SmokeExecutionRequestDependencyError,
)
from .models import (
    _DRAFT_REFERENCE,
    _FIXED_PROMPT,
    _PLAN_REFERENCE,
    _SOURCE_REQUEST_REFERENCE,
    SmokeExecutionPlanV2,
)


def _draft_semantics() -> dict[str, object]:
    return {
        "domain": "module-2.9-canonical-smoke-draft-v2",
        "draft_reference": _DRAFT_REFERENCE,
        "messages": (
            {
                "role": "generation",
                "content": _FIXED_PROMPT,
                "ordinal": 0,
            },
        ),
    }


def _plan_semantics(draft_fingerprint: str) -> dict[str, object]:
    return {
        "domain": "module-2.9-canonical-smoke-execution-plan-v2",
        "contract_version": "module-2.9-smoke-execution-plan-v2",
        "plan_reference": _PLAN_REFERENCE,
        "draft_reference": _DRAFT_REFERENCE,
        "draft_fingerprint": draft_fingerprint,
        "request_units": (
            {
                "source_request_reference": _SOURCE_REQUEST_REFERENCE,
                "ordinal": 0,
                "messages": (
                    {
                        "role": "generation",
                        "content": _FIXED_PROMPT,
                        "ordinal": 0,
                    },
                ),
            },
        ),
    }


def _expected_plan_seals(plan: SmokeExecutionPlanV2) -> tuple[str, str, str]:
    draft = semantic_sha256(_draft_semantics())
    semantics = _plan_semantics(draft)
    identity = f"scout:smoke-execution-plan-v2:{semantic_sha256(semantics)}"
    fingerprint = semantic_sha256(
        {
            "domain": "module-2.9-canonical-smoke-plan-seal-v2",
            "plan_identity": identity,
            "plan": semantics,
        }
    )
    del plan
    return identity, fingerprint, draft


def build_canonical_smoke_execution_plan() -> SmokeExecutionPlanV2:
    """Mint the one canonical fixed-prompt smoke plan deterministically."""

    draft = semantic_sha256(_draft_semantics())
    semantics = _plan_semantics(draft)
    identity = f"scout:smoke-execution-plan-v2:{semantic_sha256(semantics)}"
    fingerprint = semantic_sha256(
        {
            "domain": "module-2.9-canonical-smoke-plan-seal-v2",
            "plan_identity": identity,
            "plan": semantics,
        }
    )
    return SmokeExecutionPlanV2(
        plan_identity=identity,
        plan_fingerprint=fingerprint,
        draft_fingerprint=draft,
    )


class _ConstructionCategory(Enum):
    INVALID = auto()
    NON_OPERATIONAL = auto()


@dataclass(frozen=True, slots=True)
class _SafeConstructionOutcome:
    category: _ConstructionCategory


class SmokeProviderExecutionRequestAuthorityV2:
    """Immutable non-operational holder for future request construction."""

    __slots__ = ()

    def construct(
        self,
        *,
        execution_plan: object,
        execution_request_id: object,
        requested_at: object,
        timeout_seconds: object,
    ) -> Never:
        """Validate specification inputs without constructing a provider DTO."""

        outcome = _evaluate_inputs(
            execution_plan,
            execution_request_id,
            requested_at,
            timeout_seconds,
        )
        del execution_plan
        del execution_request_id
        del requested_at
        del timeout_seconds
        del self
        _raise_outcome(outcome)

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        memo[id(self)] = self
        return self

    def __reduce__(self) -> Never:
        del self
        _raise_serialization_error()

    def __reduce_ex__(self, protocol: int) -> Never:
        del protocol
        del self
        _raise_serialization_error()

    def __getstate__(self) -> Never:
        del self
        _raise_serialization_error()

    def __setstate__(self, state: object) -> Never:
        del state
        del self
        _raise_serialization_error()

    def __repr__(self) -> str:
        return "SmokeProviderExecutionRequestAuthorityV2()"


def _evaluate_inputs(
    execution_plan: object,
    execution_request_id: object,
    requested_at: object,
    timeout_seconds: object,
) -> _SafeConstructionOutcome:
    if type(execution_plan) is not SmokeExecutionPlanV2:
        return _SafeConstructionOutcome(_ConstructionCategory.INVALID)
    try:
        payload = execution_plan.model_dump(mode="python", warnings=False)
        SmokeExecutionPlanV2.model_validate(payload, strict=True)
    except (
        AttributeError,
        IndexError,
        KeyError,
        LookupError,
        RuntimeError,
        TypeError,
        ValueError,
        ValidationError,
    ):
        return _SafeConstructionOutcome(_ConstructionCategory.INVALID)
    if (
        type(execution_request_id) is not str
        or not execution_request_id
        or not execution_request_id.strip()
        or execution_request_id != execution_request_id.strip()
        or len(execution_request_id) > 200
    ):
        return _SafeConstructionOutcome(_ConstructionCategory.INVALID)
    if type(requested_at) is not datetime or requested_at.tzinfo is not UTC:
        return _SafeConstructionOutcome(_ConstructionCategory.INVALID)
    if type(timeout_seconds) is int:
        valid_timeout = timeout_seconds > 0
    elif type(timeout_seconds) is float:
        valid_timeout = math.isfinite(timeout_seconds) and timeout_seconds > 0.0
    else:
        valid_timeout = False
    if not valid_timeout:
        return _SafeConstructionOutcome(_ConstructionCategory.INVALID)
    return _SafeConstructionOutcome(_ConstructionCategory.NON_OPERATIONAL)


def _raise_outcome(outcome: _SafeConstructionOutcome) -> Never:
    if outcome.category is _ConstructionCategory.INVALID:
        error: SmokeExecutionRequestAuthorityError = (
            SmokeExecutionRequestConfigurationError(
                "invalid canonical smoke request authority input"
            )
        )
    else:
        error = SmokeExecutionRequestDependencyError(
            "canonical smoke request construction is not operational"
        )
    try:
        raise error from None
    finally:
        error.__context__ = None
        error.__cause__ = None
        error.__suppress_context__ = True


def _raise_serialization_error() -> Never:
    error = TypeError("smoke request authority holders cannot be serialized")
    try:
        raise error from None
    finally:
        error.__context__ = None
        error.__cause__ = None
        error.__suppress_context__ = True


__all__ = (
    "SmokeProviderExecutionRequestAuthorityV2",
    "build_canonical_smoke_execution_plan",
)
