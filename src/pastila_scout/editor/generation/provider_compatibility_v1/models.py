"""Strict immutable Producer compatibility contracts."""

from __future__ import annotations

import math
import re
import unicodedata
from dataclasses import dataclass, fields
from enum import Enum, StrEnum
from typing import Any, ClassVar, Literal, Self

from pydantic import BaseModel, ValidationError

from pastila_scout.editor.generation.revision import ControlledRevisionGatewayResult
from pastila_scout.provider_execution_v2 import (
    ExecutionOutcomeV2,
    ProviderExecutionRequestV2,
)
from pastila_scout.provider_v2 import ProviderFinishReasonV2

from .canonical import (
    canonical_json,
    canonical_json_bytes,
    reference_for,
    semantic_sha256,
)

_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_DECIMAL = re.compile(r"^(0|[1-9][0-9]*)(\.[0-9]*[1-9])?$")
_FORBIDDEN = (
    "authorization",
    "bearer ",
    "api_key",
    "credential",
    "password",
    "secret",
    "traceback",
    "cookie",
    "c:\\",
    "/home/",
)


class _Contract:
    __slots__ = ()

    @classmethod
    def model_validate(cls, value: object, *, strict: bool = True) -> Self:
        if strict is not True:
            raise ValueError("strict reconstruction is required")
        payload = (
            value.model_dump(mode="python", warnings=False)
            if isinstance(value, _Contract)
            else value
        )
        if type(payload) is not dict:
            raise ValueError(f"{cls.__name__} requires an exact mapping")
        expected = {item.name for item in fields(cls)}
        if set(payload) != expected:
            raise ValueError(f"{cls.__name__} fields are invalid")
        return cls(**payload)

    @classmethod
    def reconstruct(cls, value: object) -> Self:
        return cls.model_validate(value, strict=True)

    def model_dump(
        self, *, mode: str = "python", warnings: bool = False, **kwargs
    ) -> dict[str, Any]:
        del warnings
        if mode != "python" or kwargs:
            raise ValueError("only canonical Python dumping is supported")
        return {
            item.name: _dump_value(getattr(self, item.name)) for item in fields(self)
        }

    def model_copy(self, *, update=None, deep: bool = False):
        del deep
        payload = self.model_dump()
        if update:
            if type(update) is not dict:
                raise ValueError("updates require an exact mapping")
            payload.update(update)
        return type(self).model_validate(payload, strict=True)

    def canonical_json(self) -> str:
        return canonical_json(self.model_dump())

    def canonical_bytes(self) -> bytes:
        return canonical_json_bytes(self.model_dump())

    @classmethod
    def model_json_schema(cls) -> dict[str, Any]:
        return {
            "title": cls.__name__,
            "type": "object",
            "additionalProperties": False,
            "properties": {
                item.name: {"title": item.name, "type": str(item.type)}
                for item in fields(cls)
            },
            "required": [item.name for item in fields(cls)],
        }


class _FingerprintContract(_Contract):
    __slots__ = ()
    _kind: ClassVar[str]
    _excluded: ClassVar[tuple[str, str]]
    _reference_field: ClassVar[str]
    _fingerprint_field: ClassVar[str]

    @classmethod
    def build(cls, **values: Any) -> Self:
        payload = dict(values)
        version_field = next(
            item for item in fields(cls) if item.name == "contract_version"
        )
        payload.setdefault("contract_version", version_field.default)
        payload.pop(cls._reference_field, None)
        payload.pop(cls._fingerprint_field, None)
        fingerprint = semantic_sha256(payload)
        payload[cls._fingerprint_field] = fingerprint
        payload[cls._reference_field] = reference_for(cls._kind, fingerprint)
        return cls.model_validate(payload, strict=True)

    def semantic_payload(self) -> dict[str, Any]:
        payload = self.model_dump()
        return {
            key: value for key, value in payload.items() if key not in self._excluded
        }

    def semantic_json(self) -> str:
        return canonical_json(self.semantic_payload())

    def _validate_identity(self) -> None:
        fingerprint = semantic_sha256(self.semantic_payload())
        if getattr(self, self._fingerprint_field) != fingerprint:
            raise ValueError("compatibility fingerprint mismatch")
        if getattr(self, self._reference_field) != reference_for(
            self._kind, fingerprint
        ):
            raise ValueError("compatibility reference mismatch")


class ProducerDiagnosticAuthorityV1(StrEnum):
    APPLICATION_DIAGNOSTICS_AUTHORITY = "application_diagnostics_authority"
    COMPATIBILITY_CLOCK = "compatibility_clock"
    PROVIDER_RESULT = "provider_result"
    PRODUCER_COORDINATOR = "producer_coordinator"
    UNAVAILABLE = "unavailable"


class ProducerFailureCodeV1(StrEnum):
    PRODUCER_REQUEST_INVALID = "producer_request_invalid"
    PRODUCER_EXECUTION_CONFIGURATION_FAILED = "producer_execution_configuration_failed"
    PROVIDER_EXECUTOR_CONTRACT_FAILED = "provider_executor_contract_failed"
    PROVIDER_RESULT_INVALID = "provider_result_invalid"
    PROVIDER_EXECUTION_FAILED = "provider_execution_failed"
    PROVIDER_TIMEOUT = "provider_timeout"
    PROVIDER_RATE_LIMITED = "provider_rate_limited"
    PROVIDER_TRANSPORT_FAILED = "provider_transport_failed"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    PRODUCER_EXECUTION_CANCELLED = "producer_execution_cancelled"
    PROVIDER_PARTIAL_RESULT = "provider_partial_result"
    PROVIDER_REFUSAL = "provider_refusal"
    PROVIDER_LENGTH_LIMITED = "provider_length_limited"
    PROVIDER_CONTENT_FILTERED = "provider_content_filtered"
    PROVIDER_OUTPUT_INVALID = "provider_output_invalid"
    GATEWAY_PROJECTION_FAILED = "gateway_projection_failed"
    PROVIDER_INTERNAL_FAILURE = "provider_internal_failure"
    RETRY_EXHAUSTED = "retry_exhausted"


class ProducerExecutionLifecycleStateV1(StrEnum):
    ACCEPTED = "accepted"
    REQUEST_VALIDATED = "request_validated"
    ATTEMPTING = "attempting"
    ATTEMPT_SUCCEEDED = "attempt_succeeded"
    ATTEMPT_FAILED = "attempt_failed"
    RETRY_WAIT = "retry_wait"
    PROJECTING_RESULT = "projecting_result"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ProducerCompatibilityEventCodeV1(StrEnum):
    EXECUTION_STARTED = "execution_started"
    REQUEST_VALIDATED = "request_validated"
    ATTEMPT_STARTED = "attempt_started"
    ATTEMPT_SUCCEEDED = "attempt_succeeded"
    ATTEMPT_FAILED = "attempt_failed"
    DIAGNOSTICS_SAMPLED = "diagnostics_sampled"
    DIAGNOSTICS_UNAVAILABLE = "diagnostics_unavailable"
    DIAGNOSTICS_REJECTED = "diagnostics_rejected"
    RETRY_SCHEDULED = "retry_scheduled"
    BACKOFF_STARTED = "backoff_started"
    BACKOFF_COMPLETED = "backoff_completed"
    PROJECTION_STARTED = "projection_started"
    PROJECTION_COMPLETED = "projection_completed"
    PROJECTION_FAILED = "projection_failed"
    TIMEOUT_DETECTED = "timeout_detected"
    EXECUTION_SUCCEEDED = "execution_succeeded"
    EXECUTION_FAILED = "execution_failed"
    EXECUTION_CANCELLED = "execution_cancelled"


class AIProviderExecutionStatus(StrEnum):
    SUCCESS = "success"
    FAILED = "failed"
    CANCELLED = "cancelled"


class AIProviderExecutionFailureKind(StrEnum):
    PROJECTION = "projection_failure"
    CONFIGURATION = "configuration_failure"
    CLIENT = "client_failure"
    RETRY_EXHAUSTED = "retry_exhausted"
    CANCELLATION = "cancellation"
    MALFORMED_RESPONSE = "malformed_provider_response"
    REFUSAL = "provider_refusal"
    INCOMPLETE_RESPONSE = "incomplete_provider_response"
    INVALID_GATEWAY_PROJECTION = "invalid_gateway_projection"
    SCHEMA = "schema_failure"
    INTERNAL = "internal_failure"


@dataclass(frozen=True, slots=True)
class AIRetryPolicy(_Contract):
    maximum_attempts: int = 1
    delay_seconds: float = 0.0
    retry_timeouts: bool = True
    retry_rate_limits: bool = True
    retry_transport_errors: bool = True

    def __post_init__(self) -> None:
        _exact_positive_int(self.maximum_attempts, "maximum_attempts")
        if (
            type(self.delay_seconds) is not float
            or not math.isfinite(self.delay_seconds)
            or self.delay_seconds < 0
        ):
            raise ValueError("delay_seconds must be an exact nonnegative float")
        for value in (
            self.retry_timeouts,
            self.retry_rate_limits,
            self.retry_transport_errors,
        ):
            _exact_bool(value, "retry flag")


@dataclass(frozen=True, slots=True)
class ProducerTokenUsageV1(_Contract):
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    estimated_cost: str | None = None
    pricing_version: str | None = None

    def __post_init__(self) -> None:
        for value in (self.prompt_tokens, self.completion_tokens, self.total_tokens):
            if value is not None:
                _exact_nonnegative_int(value, "token value")
        if self.estimated_cost is not None:
            _exact_decimal(self.estimated_cost, "estimated_cost")
        if self.pricing_version is not None:
            _exact_string(self.pricing_version, "pricing_version")
        if (
            all(
                value is None
                for value in (
                    self.prompt_tokens,
                    self.completion_tokens,
                    self.total_tokens,
                )
            )
            and self.estimated_cost is None
        ):
            raise ValueError("usage must contain a token count or cost")
        if (
            None not in (self.prompt_tokens, self.completion_tokens, self.total_tokens)
            and self.total_tokens != self.prompt_tokens + self.completion_tokens
        ):
            raise ValueError("token total is inconsistent")
        if (self.estimated_cost is None) != (self.pricing_version is None):
            raise ValueError("cost and pricing version must be paired")


@dataclass(frozen=True, slots=True)
class ProducerFinishMetadataV1(_Contract):
    source_request_reference: str
    ordinal: int
    finish_reason: ProviderFinishReasonV2

    def __post_init__(self) -> None:
        _exact_string(self.source_request_reference, "source_request_reference")
        _exact_nonnegative_int(self.ordinal, "ordinal")
        _exact_enum(self.finish_reason, ProviderFinishReasonV2, "finish_reason")


_FAILURE_DETAILS = {
    ProducerFailureCodeV1.PRODUCER_REQUEST_INVALID: (
        AIProviderExecutionFailureKind.PROJECTION,
        "Producer execution request is invalid.",
        False,
    ),
    ProducerFailureCodeV1.PRODUCER_EXECUTION_CONFIGURATION_FAILED: (
        AIProviderExecutionFailureKind.CONFIGURATION,
        "Producer execution configuration failed.",
        False,
    ),
    ProducerFailureCodeV1.PROVIDER_EXECUTOR_CONTRACT_FAILED: (
        AIProviderExecutionFailureKind.INTERNAL,
        "Provider executor contract failed.",
        False,
    ),
    ProducerFailureCodeV1.PROVIDER_RESULT_INVALID: (
        AIProviderExecutionFailureKind.MALFORMED_RESPONSE,
        "Provider execution result is invalid.",
        False,
    ),
    ProducerFailureCodeV1.PROVIDER_EXECUTION_FAILED: (
        AIProviderExecutionFailureKind.CLIENT,
        "Provider execution failed.",
        False,
    ),
    ProducerFailureCodeV1.PROVIDER_TIMEOUT: (
        AIProviderExecutionFailureKind.CLIENT,
        "Provider execution timed out.",
        True,
    ),
    ProducerFailureCodeV1.PROVIDER_RATE_LIMITED: (
        AIProviderExecutionFailureKind.CLIENT,
        "Provider rate limit was reached.",
        True,
    ),
    ProducerFailureCodeV1.PROVIDER_TRANSPORT_FAILED: (
        AIProviderExecutionFailureKind.CLIENT,
        "Provider transport failed.",
        True,
    ),
    ProducerFailureCodeV1.PROVIDER_UNAVAILABLE: (
        AIProviderExecutionFailureKind.CLIENT,
        "Provider is unavailable.",
        True,
    ),
    ProducerFailureCodeV1.PRODUCER_EXECUTION_CANCELLED: (
        AIProviderExecutionFailureKind.CANCELLATION,
        "Producer execution was cancelled.",
        False,
    ),
    ProducerFailureCodeV1.PROVIDER_PARTIAL_RESULT: (
        AIProviderExecutionFailureKind.INCOMPLETE_RESPONSE,
        "Provider returned a partial result.",
        False,
    ),
    ProducerFailureCodeV1.PROVIDER_REFUSAL: (
        AIProviderExecutionFailureKind.REFUSAL,
        "Provider refused the request.",
        False,
    ),
    ProducerFailureCodeV1.PROVIDER_LENGTH_LIMITED: (
        AIProviderExecutionFailureKind.INCOMPLETE_RESPONSE,
        "Provider output reached its length limit.",
        False,
    ),
    ProducerFailureCodeV1.PROVIDER_CONTENT_FILTERED: (
        AIProviderExecutionFailureKind.REFUSAL,
        "Provider output was content filtered.",
        False,
    ),
    ProducerFailureCodeV1.PROVIDER_OUTPUT_INVALID: (
        AIProviderExecutionFailureKind.SCHEMA,
        "Provider output is invalid.",
        False,
    ),
    ProducerFailureCodeV1.GATEWAY_PROJECTION_FAILED: (
        AIProviderExecutionFailureKind.INVALID_GATEWAY_PROJECTION,
        "Gateway result projection failed.",
        False,
    ),
    ProducerFailureCodeV1.PROVIDER_INTERNAL_FAILURE: (
        AIProviderExecutionFailureKind.INTERNAL,
        "Provider execution failed internally.",
        False,
    ),
    ProducerFailureCodeV1.RETRY_EXHAUSTED: (
        AIProviderExecutionFailureKind.RETRY_EXHAUSTED,
        "Provider retries were exhausted.",
        False,
    ),
}


@dataclass(frozen=True, slots=True)
class ProducerExecutionFailureV1(_Contract):
    failure_kind: AIProviderExecutionFailureKind
    diagnostic_code: ProducerFailureCodeV1
    safe_message: str
    retryable: bool
    source_outcome: ExecutionOutcomeV2 | None = None
    source_failure_code: str | None = None

    def __post_init__(self) -> None:
        _exact_enum(self.failure_kind, AIProviderExecutionFailureKind, "failure_kind")
        _exact_enum(self.diagnostic_code, ProducerFailureCodeV1, "diagnostic_code")
        _exact_string(self.safe_message, "safe_message")
        _exact_bool(self.retryable, "retryable")
        if self.source_outcome is not None:
            _exact_enum(self.source_outcome, ExecutionOutcomeV2, "source_outcome")
        if self.source_failure_code is not None:
            _exact_string(self.source_failure_code, "source_failure_code")
        if (self.failure_kind, self.safe_message, self.retryable) != _FAILURE_DETAILS[
            self.diagnostic_code
        ]:
            raise ValueError("failure fields do not match the controlled table")
        if self.source_outcome is None and self.source_failure_code is not None:
            raise ValueError("source code requires source outcome")

    @classmethod
    def from_code(
        cls,
        code: ProducerFailureCodeV1,
        *,
        source_outcome=None,
        source_failure_code=None,
    ) -> Self:
        _exact_enum(code, ProducerFailureCodeV1, "diagnostic_code")
        kind, message, retryable = _FAILURE_DETAILS[code]
        return cls(kind, code, message, retryable, source_outcome, source_failure_code)


@dataclass(frozen=True, slots=True)
class ProducerAttemptDiagnosticsV1(_Contract):
    usage: ProducerTokenUsageV1 | None
    usage_authority: ProducerDiagnosticAuthorityV1
    latency_ms: str | None
    latency_authority: ProducerDiagnosticAuthorityV1
    provider_request_id: str | None
    provider_request_id_authority: ProducerDiagnosticAuthorityV1
    returned_model_id: str | None
    returned_model_id_authority: ProducerDiagnosticAuthorityV1
    finish_metadata: tuple[ProducerFinishMetadataV1, ...]
    finish_metadata_authority: ProducerDiagnosticAuthorityV1

    def __post_init__(self) -> None:
        _initialize_diagnostics(self, aggregate=False)


@dataclass(frozen=True, slots=True)
class ProducerExecutionDiagnosticsV1(_Contract):
    usage: ProducerTokenUsageV1 | None
    usage_authority: ProducerDiagnosticAuthorityV1
    latency_ms: str | None
    latency_authority: ProducerDiagnosticAuthorityV1
    provider_request_id: str | None
    provider_request_id_authority: ProducerDiagnosticAuthorityV1
    returned_model_id: str | None
    returned_model_id_authority: ProducerDiagnosticAuthorityV1
    finish_metadata: tuple[ProducerFinishMetadataV1, ...]
    finish_metadata_authority: ProducerDiagnosticAuthorityV1
    retryable: bool | None
    retryability_authority: ProducerDiagnosticAuthorityV1
    attempt_count: int
    attempt_count_authority: ProducerDiagnosticAuthorityV1
    lifecycle_state: ProducerExecutionLifecycleStateV1
    lifecycle_authority: ProducerDiagnosticAuthorityV1

    def __post_init__(self) -> None:
        _initialize_diagnostics(self, aggregate=True)
        if self.retryable is not None:
            _exact_bool(self.retryable, "retryable")
        _paired_authority(
            self.retryable,
            self.retryability_authority,
            ProducerDiagnosticAuthorityV1.PRODUCER_COORDINATOR,
            "retryability",
        )
        _exact_nonnegative_int(self.attempt_count, "attempt_count")
        if (
            self.attempt_count_authority
            is not ProducerDiagnosticAuthorityV1.PRODUCER_COORDINATOR
            or self.lifecycle_authority
            is not ProducerDiagnosticAuthorityV1.PRODUCER_COORDINATOR
        ):
            raise ValueError("aggregate diagnostics require coordinator authority")
        _exact_enum(
            self.lifecycle_state, ProducerExecutionLifecycleStateV1, "lifecycle_state"
        )
        if self.lifecycle_state not in _TERMINAL_STATES:
            raise ValueError("execution diagnostics require terminal lifecycle")


@dataclass(frozen=True, slots=True)
class ProducerDiagnosticsObservationV1(_Contract):
    correlation_id: str
    attempt_number: int
    execution_request_id: str
    request_envelope_identity: str
    usage: ProducerTokenUsageV1 | None = None
    provider_request_id: str | None = None
    returned_model_id: str | None = None
    contract_version: Literal["producer-diagnostics-observation-v1"] = (
        "producer-diagnostics-observation-v1"
    )

    def __post_init__(self) -> None:
        _exact_string(self.contract_version, "contract_version")
        if self.contract_version != "producer-diagnostics-observation-v1":
            raise ValueError("invalid contract version")
        _exact_sha(self.correlation_id, "correlation_id")
        _exact_positive_int(self.attempt_number, "attempt_number")
        _exact_string(self.execution_request_id, "execution_request_id")
        _exact_string(self.request_envelope_identity, "request_envelope_identity")
        if self.usage is not None:
            object.__setattr__(
                self, "usage", ProducerTokenUsageV1.reconstruct(self.usage)
            )
        for value in (self.provider_request_id, self.returned_model_id):
            if value is not None:
                _exact_string(value, "provider diagnostic identifier")

    def correlated_to(
        self,
        *,
        correlation_id: str,
        attempt_number: int,
        execution_request_id: str,
        request_envelope_identity: str,
    ) -> bool:
        return (
            self.correlation_id,
            self.attempt_number,
            self.execution_request_id,
            self.request_envelope_identity,
        ) == (
            correlation_id,
            attempt_number,
            execution_request_id,
            request_envelope_identity,
        )


@dataclass(frozen=True, slots=True)
class ProducerExecutionRequestV1(_FingerprintContract):
    request_reference: str
    request_fingerprint: str
    invocation_reference: str
    invocation_fingerprint: str
    provider_request: ProviderExecutionRequestV2
    retry_policy: AIRetryPolicy
    contract_version: Literal["producer-execution-request-v1"] = (
        "producer-execution-request-v1"
    )

    _kind = "execution-request-v1"
    _excluded = ("request_reference", "request_fingerprint")
    _reference_field = "request_reference"
    _fingerprint_field = "request_fingerprint"

    def __post_init__(self) -> None:
        _exact_version(self.contract_version, "producer-execution-request-v1")
        _exact_string(self.request_reference, "request_reference")
        _exact_sha(self.request_fingerprint, "request_fingerprint")
        _exact_string(self.invocation_reference, "invocation_reference")
        _exact_revision_fingerprint(
            self.invocation_fingerprint, "invocation_fingerprint"
        )
        object.__setattr__(
            self,
            "provider_request",
            _reconstruct_pydantic(ProviderExecutionRequestV2, self.provider_request),
        )
        object.__setattr__(
            self, "retry_policy", AIRetryPolicy.reconstruct(self.retry_policy)
        )
        self._validate_identity()


@dataclass(frozen=True, slots=True)
class ProducerExecutionAttemptV1(_FingerprintContract):
    attempt_reference: str
    attempt_fingerprint: str
    attempt_number: int
    execution_request_id: str
    request_envelope_identity: str
    timeout_seconds: int | float
    cancellation_requested: bool
    outcome: ExecutionOutcomeV2 | None
    succeeded: bool
    failure: ProducerExecutionFailureV1 | None
    diagnostics: ProducerAttemptDiagnosticsV1
    contract_version: Literal["producer-execution-attempt-v1"] = (
        "producer-execution-attempt-v1"
    )

    _kind = "execution-attempt-v1"
    _excluded = ("attempt_reference", "attempt_fingerprint")
    _reference_field = "attempt_reference"
    _fingerprint_field = "attempt_fingerprint"

    def __post_init__(self) -> None:
        _exact_version(self.contract_version, "producer-execution-attempt-v1")
        _exact_string(self.attempt_reference, "attempt_reference")
        _exact_sha(self.attempt_fingerprint, "attempt_fingerprint")
        _exact_positive_int(self.attempt_number, "attempt_number")
        _exact_string(self.execution_request_id, "execution_request_id")
        _exact_string(self.request_envelope_identity, "request_envelope_identity")
        _exact_timeout(self.timeout_seconds)
        _exact_bool(self.cancellation_requested, "cancellation_requested")
        _exact_bool(self.succeeded, "succeeded")
        if self.cancellation_requested:
            raise ValueError("dispatched attempt requires false cancellation")
        if self.outcome is not None:
            _exact_enum(self.outcome, ExecutionOutcomeV2, "outcome")
        if self.failure is not None:
            object.__setattr__(
                self, "failure", ProducerExecutionFailureV1.reconstruct(self.failure)
            )
        object.__setattr__(
            self,
            "diagnostics",
            ProducerAttemptDiagnosticsV1.reconstruct(self.diagnostics),
        )
        if self.succeeded != (
            self.outcome is ExecutionOutcomeV2.COMPLETED and self.failure is None
        ):
            raise ValueError("attempt outcome is inconsistent")
        if not self.succeeded and self.failure is None:
            raise ValueError("failed attempt requires failure")
        self._validate_identity()


_TRANSITIONS = {
    ProducerExecutionLifecycleStateV1.ACCEPTED: {
        ProducerExecutionLifecycleStateV1.REQUEST_VALIDATED,
        ProducerExecutionLifecycleStateV1.FAILED,
        ProducerExecutionLifecycleStateV1.CANCELLED,
    },
    ProducerExecutionLifecycleStateV1.REQUEST_VALIDATED: {
        ProducerExecutionLifecycleStateV1.ATTEMPTING,
        ProducerExecutionLifecycleStateV1.CANCELLED,
    },
    ProducerExecutionLifecycleStateV1.ATTEMPTING: {
        ProducerExecutionLifecycleStateV1.ATTEMPT_SUCCEEDED,
        ProducerExecutionLifecycleStateV1.ATTEMPT_FAILED,
    },
    ProducerExecutionLifecycleStateV1.ATTEMPT_SUCCEEDED: {
        ProducerExecutionLifecycleStateV1.PROJECTING_RESULT,
        ProducerExecutionLifecycleStateV1.CANCELLED,
    },
    ProducerExecutionLifecycleStateV1.PROJECTING_RESULT: {
        ProducerExecutionLifecycleStateV1.SUCCEEDED,
        ProducerExecutionLifecycleStateV1.FAILED,
    },
    ProducerExecutionLifecycleStateV1.ATTEMPT_FAILED: {
        ProducerExecutionLifecycleStateV1.RETRY_WAIT,
        ProducerExecutionLifecycleStateV1.FAILED,
        ProducerExecutionLifecycleStateV1.CANCELLED,
    },
    ProducerExecutionLifecycleStateV1.RETRY_WAIT: {
        ProducerExecutionLifecycleStateV1.RETRY_WAIT,
        ProducerExecutionLifecycleStateV1.ATTEMPTING,
        ProducerExecutionLifecycleStateV1.FAILED,
        ProducerExecutionLifecycleStateV1.CANCELLED,
    },
}
_TERMINAL_STATES = {
    ProducerExecutionLifecycleStateV1.SUCCEEDED,
    ProducerExecutionLifecycleStateV1.FAILED,
    ProducerExecutionLifecycleStateV1.CANCELLED,
}


@dataclass(frozen=True, slots=True)
class ProducerExecutionLifecycleV1(_Contract):
    states: tuple[ProducerExecutionLifecycleStateV1, ...]
    terminal_state: ProducerExecutionLifecycleStateV1
    contract_version: Literal["producer-execution-lifecycle-v1"] = (
        "producer-execution-lifecycle-v1"
    )

    def __post_init__(self) -> None:
        _exact_version(self.contract_version, "producer-execution-lifecycle-v1")
        _exact_tuple(self.states, "states")
        for state in self.states:
            _exact_enum(state, ProducerExecutionLifecycleStateV1, "lifecycle state")
        _exact_enum(
            self.terminal_state, ProducerExecutionLifecycleStateV1, "terminal_state"
        )
        if (
            not self.states
            or self.states[0] is not ProducerExecutionLifecycleStateV1.ACCEPTED
            or self.states[-1] is not self.terminal_state
            or self.terminal_state not in _TERMINAL_STATES
        ):
            raise ValueError("lifecycle endpoints are invalid")
        if any(
            following not in _TRANSITIONS.get(current, set())
            for current, following in zip(self.states, self.states[1:], strict=False)
        ):
            raise ValueError("lifecycle transition is invalid")
        if any(state in _TERMINAL_STATES for state in self.states[:-1]):
            raise ValueError("lifecycle continues after terminal state")


@dataclass(frozen=True, slots=True)
class ProducerExecutionResultV1(_FingerprintContract):
    result_reference: str
    result_fingerprint: str
    request_reference: str
    request_fingerprint: str
    invocation_reference: str
    invocation_fingerprint: str
    status: AIProviderExecutionStatus
    gateway_result: ControlledRevisionGatewayResult | None
    diagnostics: ProducerExecutionDiagnosticsV1
    failure: ProducerExecutionFailureV1 | None
    attempts: tuple[ProducerExecutionAttemptV1, ...]
    lifecycle: ProducerExecutionLifecycleV1
    contract_version: Literal["producer-execution-result-v1"] = (
        "producer-execution-result-v1"
    )

    _kind = "execution-result-v1"
    _excluded = ("result_reference", "result_fingerprint")
    _reference_field = "result_reference"
    _fingerprint_field = "result_fingerprint"

    def __post_init__(self) -> None:
        _exact_version(self.contract_version, "producer-execution-result-v1")
        for value, name in (
            (self.result_reference, "result_reference"),
            (self.request_reference, "request_reference"),
            (self.invocation_reference, "invocation_reference"),
        ):
            _exact_string(value, name)
        for value, name in (
            (self.result_fingerprint, "result_fingerprint"),
            (self.request_fingerprint, "request_fingerprint"),
        ):
            _exact_sha(value, name)
        _exact_revision_fingerprint(
            self.invocation_fingerprint, "invocation_fingerprint"
        )
        _exact_enum(self.status, AIProviderExecutionStatus, "status")
        if self.gateway_result is not None:
            object.__setattr__(
                self,
                "gateway_result",
                _reconstruct_pydantic(
                    ControlledRevisionGatewayResult, self.gateway_result
                ),
            )
        object.__setattr__(
            self,
            "diagnostics",
            ProducerExecutionDiagnosticsV1.reconstruct(self.diagnostics),
        )
        if self.failure is not None:
            object.__setattr__(
                self, "failure", ProducerExecutionFailureV1.reconstruct(self.failure)
            )
        _exact_tuple(self.attempts, "attempts")
        object.__setattr__(
            self,
            "attempts",
            tuple(
                ProducerExecutionAttemptV1.reconstruct(item) for item in self.attempts
            ),
        )
        object.__setattr__(
            self, "lifecycle", ProducerExecutionLifecycleV1.reconstruct(self.lifecycle)
        )
        if tuple(item.attempt_number for item in self.attempts) != tuple(
            range(1, len(self.attempts) + 1)
        ):
            raise ValueError("attempt numbers must be contiguous")
        if (
            self.diagnostics.attempt_count != len(self.attempts)
            or self.diagnostics.lifecycle_state is not self.lifecycle.terminal_state
        ):
            raise ValueError("result diagnostics are inconsistent")
        expected = {
            ProducerExecutionLifecycleStateV1.SUCCEEDED: AIProviderExecutionStatus.SUCCESS,
            ProducerExecutionLifecycleStateV1.FAILED: AIProviderExecutionStatus.FAILED,
            ProducerExecutionLifecycleStateV1.CANCELLED: AIProviderExecutionStatus.CANCELLED,
        }[self.lifecycle.terminal_state]
        if self.status is not expected:
            raise ValueError("result status is inconsistent")
        success = self.status is AIProviderExecutionStatus.SUCCESS
        if success != (self.gateway_result is not None) or success == (
            self.failure is not None
        ):
            raise ValueError("result success/failure shape is inconsistent")
        self._validate_identity()


@dataclass(frozen=True, slots=True)
class ProducerCompatibilityEventV1(_Contract):
    event_code: ProducerCompatibilityEventCodeV1
    request_reference: str
    attempt_number: int | None
    diagnostic_code: ProducerFailureCodeV1 | None
    lifecycle_state: ProducerExecutionLifecycleStateV1

    def __post_init__(self) -> None:
        _exact_enum(self.event_code, ProducerCompatibilityEventCodeV1, "event_code")
        _exact_string(self.request_reference, "request_reference")
        if self.attempt_number is not None:
            _exact_positive_int(self.attempt_number, "attempt_number")
        if self.diagnostic_code is not None:
            _exact_enum(self.diagnostic_code, ProducerFailureCodeV1, "diagnostic_code")
        _exact_enum(
            self.lifecycle_state, ProducerExecutionLifecycleStateV1, "lifecycle_state"
        )


def _initialize_diagnostics(value, *, aggregate: bool) -> None:
    if value.usage is not None:
        object.__setattr__(
            value, "usage", ProducerTokenUsageV1.reconstruct(value.usage)
        )
    for name in (
        "usage_authority",
        "latency_authority",
        "provider_request_id_authority",
        "returned_model_id_authority",
        "finish_metadata_authority",
    ):
        _exact_enum(getattr(value, name), ProducerDiagnosticAuthorityV1, name)
    if value.latency_ms is not None:
        _exact_decimal(value.latency_ms, "latency_ms")
    for item in (value.provider_request_id, value.returned_model_id):
        if item is not None:
            _exact_string(item, "provider diagnostic identifier")
    _exact_tuple(value.finish_metadata, "finish_metadata")
    object.__setattr__(
        value,
        "finish_metadata",
        tuple(
            ProducerFinishMetadataV1.reconstruct(item) for item in value.finish_metadata
        ),
    )
    expected_usage = (
        ProducerDiagnosticAuthorityV1.PRODUCER_COORDINATOR
        if aggregate
        else ProducerDiagnosticAuthorityV1.APPLICATION_DIAGNOSTICS_AUTHORITY
    )
    expected_latency = (
        ProducerDiagnosticAuthorityV1.PRODUCER_COORDINATOR
        if aggregate
        else ProducerDiagnosticAuthorityV1.COMPATIBILITY_CLOCK
    )
    _paired_authority(value.usage, value.usage_authority, expected_usage, "usage")
    _paired_authority(
        value.latency_ms, value.latency_authority, expected_latency, "latency"
    )
    _paired_authority(
        value.provider_request_id,
        value.provider_request_id_authority,
        ProducerDiagnosticAuthorityV1.APPLICATION_DIAGNOSTICS_AUTHORITY,
        "provider_request_id",
    )
    _paired_authority(
        value.returned_model_id,
        value.returned_model_id_authority,
        ProducerDiagnosticAuthorityV1.APPLICATION_DIAGNOSTICS_AUTHORITY,
        "returned_model_id",
    )
    if value.finish_metadata_authority not in {
        ProducerDiagnosticAuthorityV1.PROVIDER_RESULT,
        ProducerDiagnosticAuthorityV1.UNAVAILABLE,
    }:
        raise ValueError("finish metadata authority is invalid")
    if (
        value.finish_metadata_authority is ProducerDiagnosticAuthorityV1.UNAVAILABLE
        and value.finish_metadata
    ):
        raise ValueError("unavailable finish metadata must be empty")
    if tuple(item.ordinal for item in value.finish_metadata) != tuple(
        range(len(value.finish_metadata))
    ):
        raise ValueError("finish metadata order is invalid")


def _paired_authority(value, authority, expected, name: str) -> None:
    if value is None and authority is not ProducerDiagnosticAuthorityV1.UNAVAILABLE:
        raise ValueError(f"absent {name} requires unavailable authority")
    if value is not None and authority is not expected:
        raise ValueError(f"present {name} has invalid authority")


def _dump_value(value):
    if isinstance(value, _Contract):
        return value.model_dump()
    if isinstance(value, BaseModel):
        return value.model_dump(mode="python", warnings=False)
    if type(value) is tuple:
        return tuple(_dump_value(item) for item in value)
    return value


def _reconstruct_pydantic(model, value):
    payload = (
        value.model_dump(mode="python", warnings=False)
        if isinstance(value, BaseModel)
        else value
    )
    try:
        return model.model_validate(payload, strict=True)
    except (TypeError, ValueError, ValidationError) as error:
        raise ValueError(f"invalid retained {model.__name__}") from error


def _exact_string(value: object, name: str) -> str:
    if (
        type(value) is not str
        or not value
        or value != value.strip()
        or len(value) > 200
        or value != unicodedata.normalize("NFC", value)
    ):
        raise ValueError(f"{name} must be an exact short NFC string")
    folded = value.casefold()
    if any(ord(char) < 32 or 127 <= ord(char) <= 159 for char in value) or any(
        token in folded for token in _FORBIDDEN
    ):
        raise ValueError(f"{name} contains unsafe content")
    return value


def _exact_sha(value: object, name: str) -> str:
    if type(value) is not str or _SHA256.fullmatch(value) is None:
        raise ValueError(f"{name} must be lowercase SHA-256")
    return value


def _exact_revision_fingerprint(value: object, name: str) -> str:
    if (
        type(value) is not str
        or not value.startswith("sha256:")
        or _SHA256.fullmatch(value[7:]) is None
    ):
        raise ValueError(f"{name} must be an exact revision SHA-256 fingerprint")
    return value


def _exact_decimal(value: object, name: str) -> str:
    if type(value) is not str or _DECIMAL.fullmatch(value) is None:
        raise ValueError(f"{name} must be canonical nonnegative decimal")
    return value


def _exact_tuple(value: object, name: str) -> tuple:
    if type(value) is not tuple:
        raise ValueError(f"{name} must be an exact tuple")
    return value


def _exact_enum(value: object, enum_type: type[Enum], name: str) -> None:
    if type(value) is not enum_type:
        raise ValueError(f"{name} must be exact {enum_type.__name__}")


def _exact_bool(value: object, name: str) -> None:
    if type(value) is not bool:
        raise ValueError(f"{name} must be an exact boolean")


def _exact_nonnegative_int(value: object, name: str) -> None:
    if type(value) is not int or value < 0:
        raise ValueError(f"{name} must be an exact nonnegative integer")


def _exact_positive_int(value: object, name: str) -> None:
    if type(value) is not int or value <= 0:
        raise ValueError(f"{name} must be an exact positive integer")


def _exact_timeout(value: object) -> None:
    if (
        type(value) not in {int, float}
        or value <= 0
        or (
            type(value) is float
            and (
                not math.isfinite(value) or (value == 0 and math.copysign(1, value) < 0)
            )
        )
    ):
        raise ValueError("timeout must be exact finite positive number")


def _exact_version(value: object, expected: str) -> None:
    _exact_string(value, "contract_version")
    if value != expected:
        raise ValueError("invalid contract version")


__all__ = ()
