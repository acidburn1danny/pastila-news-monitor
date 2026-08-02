"""Canonical smoke-plan minting and provider execution-request construction."""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum, auto
from typing import Never, Self

from pydantic import ValidationError

from pastila_scout.provider_adapters_v2.openai import OpenAIProviderAdapter
from pastila_scout.provider_execution_v2 import (
    ExecutionContextV2,
    ProviderExecutionRequestV2,
    TimeoutPolicyV2,
)
from pastila_scout.provider_v2 import (
    ProviderDescriptorV2,
    ProviderMessageInputV2,
    ProviderRequestIntentV2,
    ProviderRequestUnitInputV2,
    build_provider_request_envelope,
    validate_provider_descriptor,
    validate_provider_request_envelope,
)
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

type _TimeoutValue = int | float


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
    DEPENDENCY_FAILURE = auto()
    SUCCESS = auto()


@dataclass(frozen=True, slots=True)
class _SafeConstructionOutcome:
    category: _ConstructionCategory
    request: ProviderExecutionRequestV2 | None = None


class SmokeProviderExecutionRequestAuthorityV2:
    """Immutable authority for the canonical smoke execution request."""

    __slots__ = ()

    def construct(
        self,
        *,
        execution_plan: SmokeExecutionPlanV2,
        execution_request_id: str,
        requested_at: datetime,
        timeout_seconds: _TimeoutValue,
    ) -> ProviderExecutionRequestV2:
        """Construct a defensively reconstructed canonical execution request."""

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
        if outcome.category is not _ConstructionCategory.SUCCESS:
            _raise_outcome(outcome)
        request = outcome.request
        del outcome
        if type(request) is not ProviderExecutionRequestV2:
            _raise_dependency_error()
        return request

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
    if not _timeout_is_frozen_compatible(timeout_seconds):
        return _SafeConstructionOutcome(_ConstructionCategory.INVALID)
    return _construct_request(
        execution_plan,
        execution_request_id,
        requested_at,
        timeout_seconds,
    )


def _timeout_is_frozen_compatible(value: object) -> bool:
    """Return whether frozen ``TimeoutPolicyV2`` can represent the exact value."""

    if type(value) is int:
        if value <= 0:
            return False
        try:
            return math.isfinite(value)
        except OverflowError:
            return False
    if type(value) is float:
        return math.isfinite(value) and value > 0.0
    return False


def _construct_request(
    execution_plan: SmokeExecutionPlanV2,
    execution_request_id: str,
    requested_at: datetime,
    timeout_seconds: _TimeoutValue,
) -> _SafeConstructionOutcome:
    try:
        descriptor = _canonical_openai_descriptor()
        if validate_provider_descriptor(descriptor):
            return _SafeConstructionOutcome(_ConstructionCategory.DEPENDENCY_FAILURE)
        unit = execution_plan.request_units[0]
        message = unit.messages[0]
        intent = ProviderRequestIntentV2(
            execution_plan_reference=execution_plan.plan_reference,
            execution_plan_identity=execution_plan.plan_identity,
            execution_plan_fingerprint=execution_plan.plan_fingerprint,
            draft_reference=execution_plan.draft_reference,
            draft_fingerprint=execution_plan.draft_fingerprint,
            request_units=(
                ProviderRequestUnitInputV2(
                    source_request_reference=unit.source_request_reference,
                    ordinal=unit.ordinal,
                    messages=(
                        ProviderMessageInputV2(
                            role=message.role,
                            content=message.content,
                            ordinal=message.ordinal,
                        ),
                    ),
                ),
            ),
        )
        envelope = build_provider_request_envelope(intent, descriptor)
        if validate_provider_request_envelope(envelope, intent, descriptor):
            return _SafeConstructionOutcome(_ConstructionCategory.DEPENDENCY_FAILURE)
        context = ExecutionContextV2(
            request_id=execution_request_id,
            requested_at=requested_at,
        )
        timeout_policy = TimeoutPolicyV2(timeout_seconds=timeout_seconds)
        request = ProviderExecutionRequestV2(
            provider=descriptor,
            request_intent=intent,
            request_envelope=envelope,
            context=context,
            timeout_policy=timeout_policy,
        )
        rebuilt = ProviderExecutionRequestV2.model_validate(
            request.model_dump(mode="python", warnings=False), strict=True
        )
    except Exception:  # noqa: BLE001 - isolate every project-owned dependency failure
        return _SafeConstructionOutcome(_ConstructionCategory.DEPENDENCY_FAILURE)
    if type(rebuilt) is not ProviderExecutionRequestV2:
        return _SafeConstructionOutcome(_ConstructionCategory.DEPENDENCY_FAILURE)
    return _SafeConstructionOutcome(_ConstructionCategory.SUCCESS, rebuilt)


def _canonical_openai_descriptor() -> ProviderDescriptorV2:
    """Acquire the verified static OpenAI descriptor without runtime activity."""

    return OpenAIProviderAdapter.descriptor


def _raise_outcome(outcome: _SafeConstructionOutcome) -> Never:
    if outcome.category is _ConstructionCategory.INVALID:
        error: SmokeExecutionRequestAuthorityError = (
            SmokeExecutionRequestConfigurationError(
                "invalid canonical smoke request authority input"
            )
        )
    else:
        error = SmokeExecutionRequestDependencyError(
            "canonical smoke request construction failed"
        )
    try:
        raise error from None
    finally:
        error.__context__ = None
        error.__cause__ = None
        error.__suppress_context__ = True


def _raise_dependency_error() -> Never:
    error = SmokeExecutionRequestDependencyError(
        "canonical smoke request construction failed"
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
