"""Closed immutable result contracts for Editor operational execution."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from enum import StrEnum
from itertools import pairwise
from typing import NoReturn

from pastila_scout.editor.generation.manifest import GenerationManifest
from pastila_scout.editor.generation.models import EpisodeDraft, GenerationTrace
from pastila_scout.editor_generation_authority_v1.canonical import (
    canonical_value,
    semantic_fingerprint,
)
from pastila_scout.editor_generation_provider_adapter_v1 import (
    EditorGenerationAttemptObservationV1,
)


class EditorOperationalGenerationStatusV1(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EditorOperationalGenerationLifecycleStateV1(StrEnum):
    ACCEPTED = "accepted"
    VALIDATED = "validated"
    SESSION_OPENED = "session_opened"
    GENERATION_STARTED = "generation_started"
    GENERATED = "generated"
    RESULT_VALIDATED = "result_validated"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EditorOperationalGenerationFailureCodeV1(StrEnum):
    INVALID_EXECUTION_REQUEST = "invalid_execution_request"
    RUNTIME_COMPOSITION_FAILED = "runtime_composition_failed"
    PROVIDER_FAILED = "provider_failed"
    TIMEOUT_EXHAUSTED = "timeout_exhausted"
    CANCELLED = "cancelled"
    CONTROLLED_GENERATION_FAILED = "controlled_generation_failed"
    ATTEMPT_PROVENANCE_INVALID = "attempt_provenance_invalid"
    CONTROLLED_RESULT_INVALID = "controlled_result_invalid"
    INTERNAL_EXECUTION_FAILURE = "internal_execution_failure"
    CLEANUP_FAILED = "cleanup_failed"


_MESSAGES = {
    EditorOperationalGenerationFailureCodeV1.INVALID_EXECUTION_REQUEST: "Editor generation request is invalid.",
    EditorOperationalGenerationFailureCodeV1.RUNTIME_COMPOSITION_FAILED: "Editor generation runtime composition failed.",
    EditorOperationalGenerationFailureCodeV1.PROVIDER_FAILED: "Editor generation provider failed.",
    EditorOperationalGenerationFailureCodeV1.TIMEOUT_EXHAUSTED: "Editor generation timed out.",
    EditorOperationalGenerationFailureCodeV1.CANCELLED: "Editor generation was cancelled.",
    EditorOperationalGenerationFailureCodeV1.CONTROLLED_GENERATION_FAILED: "Editor controlled generation failed.",
    EditorOperationalGenerationFailureCodeV1.ATTEMPT_PROVENANCE_INVALID: "Editor generation attempt provenance is invalid.",
    EditorOperationalGenerationFailureCodeV1.CONTROLLED_RESULT_INVALID: "Editor controlled generation result is invalid.",
    EditorOperationalGenerationFailureCodeV1.INTERNAL_EXECUTION_FAILURE: "Editor generation execution failed.",
    EditorOperationalGenerationFailureCodeV1.CLEANUP_FAILED: "Editor generation cleanup failed.",
}


def _invalid() -> NoReturn:
    error = ValueError("invalid Editor operational execution result")
    error.__cause__ = None
    error.__context__ = None
    error.__suppress_context__ = True
    raise error from None


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class EditorOperationalGenerationFailureV1:
    code: EditorOperationalGenerationFailureCodeV1
    safe_message: str
    retryable: bool
    _seal: str

    def __init__(self, code, safe_message, retryable=False) -> None:
        valid = (
            type(code) is not EditorOperationalGenerationFailureCodeV1
            or safe_message != _MESSAGES.get(code)
            or type(retryable) is not bool
            or retryable
        )
        if valid:
            del self, code, safe_message, retryable, valid
            _invalid()
        values = (code, safe_message, retryable)
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "safe_message", safe_message)
        object.__setattr__(self, "retryable", retryable)
        object.__setattr__(self, "_seal", semantic_fingerprint(values))

    def __repr__(self) -> str:
        value = _reconstructed_failure_state(self)
        if value is None:
            del self, value
            _invalid()
        code = value.code
        del self, value
        return f"EditorOperationalGenerationFailureV1(code={code!r}, retryable=False)"

    def __copy__(self):
        value = _reconstructed_failure_state(self)
        if value is None:
            del self, value
            _invalid()
        del self
        return value

    def __eq__(self, other):
        if type(other) is not type(self):
            return False
        left = _reconstructed_failure_state(self)
        right = _reconstructed_failure_state(other)
        if left is None or right is None:
            del self, other, left, right
            _invalid()
        result = (left.code, left.safe_message, left.retryable) == (
            right.code,
            right.safe_message,
            right.retryable,
        )
        del self, other, left, right
        return result

    def __deepcopy__(self, memo):
        del memo
        value = _reconstructed_failure_state(self)
        if value is None:
            del self, value
            _invalid()
        del self
        return value

    def __reduce_ex__(self, protocol):
        del self, protocol
        raise TypeError("EditorOperationalGenerationFailureV1 does not support pickle")


_RESULT_FIELDS = (
    "source_report_id",
    "source_report_fingerprint",
    "preparation_result_fingerprint",
    "execution_request_reference",
    "execution_request_fingerprint",
    "status",
    "lifecycle",
    "draft",
    "generation_trace",
    "generation_manifest",
    "final_state_revision",
    "attempts",
    "attempt_count",
    "timeout_retry_count",
    "failure",
    "cleanup_failed",
    "result_fingerprint",
)


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class EditorOperationalResultV1:
    source_report_id: str
    source_report_fingerprint: str
    preparation_result_fingerprint: str
    execution_request_reference: str
    execution_request_fingerprint: str
    status: EditorOperationalGenerationStatusV1
    lifecycle: tuple[EditorOperationalGenerationLifecycleStateV1, ...]
    draft: EpisodeDraft | None
    generation_trace: GenerationTrace | None
    generation_manifest: GenerationManifest | None
    final_state_revision: int | None
    attempts: tuple[EditorGenerationAttemptObservationV1, ...]
    attempt_count: int
    timeout_retry_count: int
    failure: EditorOperationalGenerationFailureV1 | None
    cleanup_failed: bool
    result_fingerprint: str
    _seal: str

    def __init__(
        self,
        source_report_id: str,
        source_report_fingerprint: str,
        preparation_result_fingerprint: str,
        execution_request_reference: str,
        execution_request_fingerprint: str,
        status: EditorOperationalGenerationStatusV1,
        lifecycle: tuple[EditorOperationalGenerationLifecycleStateV1, ...],
        draft: EpisodeDraft | None,
        generation_trace: GenerationTrace | None,
        generation_manifest: GenerationManifest | None,
        final_state_revision: int | None,
        attempts: tuple[EditorGenerationAttemptObservationV1, ...],
        attempt_count: int,
        timeout_retry_count: int,
        failure: EditorOperationalGenerationFailureV1 | None,
        cleanup_failed: bool,
        result_fingerprint: str,
    ) -> None:
        values = (
            source_report_id,
            source_report_fingerprint,
            preparation_result_fingerprint,
            execution_request_reference,
            execution_request_fingerprint,
            status,
            lifecycle,
            draft,
            generation_trace,
            generation_manifest,
            final_state_revision,
            attempts,
            attempt_count,
            timeout_retry_count,
            failure,
            cleanup_failed,
            result_fingerprint,
        )
        rebuilt = _validated_result_state(values)
        if rebuilt is None:
            del self, values, source_report_id, source_report_fingerprint
            del preparation_result_fingerprint, execution_request_reference
            del execution_request_fingerprint, status, lifecycle, draft
            del generation_trace, generation_manifest, final_state_revision
            del attempts, attempt_count, timeout_retry_count, failure
            del cleanup_failed, result_fingerprint, rebuilt
            _invalid()
        for name, value in zip(_RESULT_FIELDS, rebuilt, strict=True):
            object.__setattr__(self, name, value)
        object.__setattr__(self, "_seal", rebuilt[-1])

    def __repr__(self) -> str:
        value = _reconstructed_result_state(self)
        if value is None:
            del self, value
            _invalid()
        status = value.status.value
        attempt_count = value.attempt_count
        timeout_count = value.timeout_retry_count
        cleanup_failed = value.cleanup_failed
        del self, value
        return (
            "EditorOperationalResultV1("
            f"status={status!r}, attempt_count={attempt_count}, "
            f"timeout_retry_count={timeout_count}, "
            f"cleanup_failed={cleanup_failed})"
        )

    def __copy__(self):
        value = _reconstructed_result_state(self)
        if value is None:
            del self, value
            _invalid()
        del self
        return value

    def __eq__(self, other):
        if type(other) is not type(self):
            return False
        left = _reconstructed_result_state(self)
        right = _reconstructed_result_state(other)
        if left is None or right is None:
            del self, other, left, right
            _invalid()
        result = tuple(
            object.__getattribute__(left, name) for name in _RESULT_FIELDS
        ) == tuple(object.__getattribute__(right, name) for name in _RESULT_FIELDS)
        del self, other, left, right
        return result

    def __deepcopy__(self, memo):
        del memo
        value = _reconstructed_result_state(self)
        if value is None:
            del self, value
            _invalid()
        del self
        return value

    def __reduce_ex__(self, protocol):
        del self, protocol
        raise TypeError("EditorOperationalResultV1 does not support pickle")


def _validate_result(values):
    (*prefix, supplied_fingerprint) = values
    (
        _source_id,
        _source_fingerprint,
        _preparation_fingerprint,
        _request_reference,
        _request_fingerprint,
        status,
        lifecycle,
        draft,
        trace,
        manifest,
        final_revision,
        attempts,
        attempt_count,
        timeout_count,
        failure,
        cleanup_failed,
    ) = prefix
    if not all(type(item) is str for item in prefix[:5]):
        _invalid()
    if type(status) is not EditorOperationalGenerationStatusV1:
        _invalid()
    if type(lifecycle) is not tuple or any(
        type(item) is not EditorOperationalGenerationLifecycleStateV1
        for item in lifecycle
    ):
        _invalid()
    if type(attempts) is not tuple or any(
        type(item) is not EditorGenerationAttemptObservationV1 for item in attempts
    ):
        _invalid()
    try:
        attempts = tuple(copy.copy(item) for item in attempts)
    except Exception:  # noqa: BLE001 - copied-invalid attempts are isolated
        _invalid()
    if type(attempt_count) is not int or attempt_count != len(attempts):
        _invalid()
    if type(timeout_count) is not int or timeout_count < 0:
        _invalid()
    if type(cleanup_failed) is not bool:
        _invalid()
    completed = status is EditorOperationalGenerationStatusV1.COMPLETED
    if completed:
        if (
            lifecycle != COMPLETED_LIFECYCLE
            or type(draft) is not EpisodeDraft
            or type(trace) is not GenerationTrace
            or type(manifest) is not GenerationManifest
            or type(final_revision) is not int
            or final_revision < 0
            or failure is not None
            or cleanup_failed
            or not attempts
            or not any(item.outcome.value == "completed" for item in attempts)
        ):
            _invalid()
        try:
            draft = EpisodeDraft.model_validate(
                draft.model_dump(mode="python", warnings=False), strict=True
            )
            trace = GenerationTrace.model_validate(
                trace.model_dump(mode="python", warnings=False), strict=True
            )
            manifest = GenerationManifest.model_validate(
                manifest.model_dump(mode="python", warnings=False), strict=True
            )
        except Exception:  # noqa: BLE001 - copied-invalid output is isolated
            _invalid()
    else:
        expected_terminal = (
            EditorOperationalGenerationLifecycleStateV1.CANCELLED
            if status is EditorOperationalGenerationStatusV1.CANCELLED
            else EditorOperationalGenerationLifecycleStateV1.FAILED
        )
        if (
            not lifecycle
            or lifecycle[-1] is not expected_terminal
            or any(
                item is not None for item in (draft, trace, manifest, final_revision)
            )
            or type(failure) is not EditorOperationalGenerationFailureV1
        ):
            _invalid()
        failure = reconstruct_failure(failure)
        if (status is EditorOperationalGenerationStatusV1.CANCELLED) != (
            failure.code is EditorOperationalGenerationFailureCodeV1.CANCELLED
        ):
            _invalid()
        if cleanup_failed != (
            failure.code is EditorOperationalGenerationFailureCodeV1.CLEANUP_FAILED
        ):
            _invalid()
        if (
            failure.code
            is EditorOperationalGenerationFailureCodeV1.ATTEMPT_PROVENANCE_INVALID
            and attempts
        ):
            _invalid()
        if (
            failure.code
            is EditorOperationalGenerationFailureCodeV1.INVALID_EXECUTION_REQUEST
        ):
            expected_lifecycle = INVALID_REQUEST_LIFECYCLE
        elif (
            failure.code
            is EditorOperationalGenerationFailureCodeV1.RUNTIME_COMPOSITION_FAILED
        ):
            expected_lifecycle = RUNTIME_FAILURE_LIFECYCLE
        elif (
            failure.code
            is EditorOperationalGenerationFailureCodeV1.CONTROLLED_RESULT_INVALID
        ):
            expected_lifecycle = CONTROLLED_RESULT_FAILURE_LIFECYCLE
        elif failure.code is EditorOperationalGenerationFailureCodeV1.CANCELLED:
            expected_lifecycle = CANCELLED_LIFECYCLE
        else:
            expected_lifecycle = GENERATION_FAILURE_LIFECYCLE
        if lifecycle != expected_lifecycle:
            _invalid()
    invalid_request = (
        failure is not None
        and failure.code
        is EditorOperationalGenerationFailureCodeV1.INVALID_EXECUTION_REQUEST
    )
    if invalid_request:
        if any(prefix[:5]):
            _invalid()
    elif not all(bool(item) for item in prefix[:5]):
        _invalid()
    if tuple(item.attempt_number for item in attempts) != tuple(
        range(1, len(attempts) + 1)
    ):
        _invalid()
    exact_timeout_count = sum(
        1
        for left, right in pairwise(attempts)
        if left.outcome.value == "timeout"
        and left.prompt_fingerprint == right.prompt_fingerprint
    )
    if timeout_count != exact_timeout_count:
        _invalid()
    prefix = (
        *prefix[:7],
        draft,
        trace,
        manifest,
        final_revision,
        attempts,
        attempt_count,
        timeout_count,
        failure,
        cleanup_failed,
    )
    canonical = (
        *prefix[:-2],
        canonical_value(failure) if failure else None,
        cleanup_failed,
    )
    expected = semantic_fingerprint(canonical)
    if supplied_fingerprint != expected:
        _invalid()
    return (*prefix[:-2], failure, cleanup_failed, expected)


def _validated_result_state(values):
    try:
        return _validate_result(values)
    except Exception:  # noqa: BLE001 - internal validation graph is discarded
        return None


def reconstruct_failure(value):
    rebuilt = _reconstructed_failure_state(value)
    if rebuilt is None:
        del value, rebuilt
        _invalid()
    del value
    return rebuilt


def _reconstructed_failure_state(value):
    rebuilt = None
    try:
        if type(value) is not EditorOperationalGenerationFailureV1:
            raise TypeError
        rebuilt = EditorOperationalGenerationFailureV1(
            object.__getattribute__(value, "code"),
            object.__getattribute__(value, "safe_message"),
            object.__getattribute__(value, "retryable"),
        )
        if object.__getattribute__(value, "_seal") != object.__getattribute__(
            rebuilt, "_seal"
        ):
            raise TypeError
        return rebuilt
    except Exception:  # noqa: BLE001 - copied-invalid state is isolated
        return None


def reconstruct_result(value):
    rebuilt = _reconstructed_result_state(value)
    if rebuilt is None:
        del value, rebuilt
        _invalid()
    del value
    return rebuilt


def _reconstructed_result_state(value):
    fields = None
    rebuilt = None
    try:
        if type(value) is not EditorOperationalResultV1:
            raise TypeError
        fields = tuple(object.__getattribute__(value, name) for name in _RESULT_FIELDS)
        rebuilt = EditorOperationalResultV1(*fields)
        if object.__getattribute__(value, "_seal") != object.__getattribute__(
            rebuilt, "_seal"
        ):
            raise TypeError
        return rebuilt
    except Exception:  # noqa: BLE001 - copied-invalid state is isolated
        return None


def make_failure(code):
    return EditorOperationalGenerationFailureV1(code, _MESSAGES[code], False)


def result_fingerprint(values) -> str:
    return semantic_fingerprint(values)


COMPLETED_LIFECYCLE = (
    EditorOperationalGenerationLifecycleStateV1.ACCEPTED,
    EditorOperationalGenerationLifecycleStateV1.VALIDATED,
    EditorOperationalGenerationLifecycleStateV1.SESSION_OPENED,
    EditorOperationalGenerationLifecycleStateV1.GENERATION_STARTED,
    EditorOperationalGenerationLifecycleStateV1.GENERATED,
    EditorOperationalGenerationLifecycleStateV1.RESULT_VALIDATED,
    EditorOperationalGenerationLifecycleStateV1.COMPLETED,
)
INVALID_REQUEST_LIFECYCLE = (
    EditorOperationalGenerationLifecycleStateV1.ACCEPTED,
    EditorOperationalGenerationLifecycleStateV1.FAILED,
)
RUNTIME_FAILURE_LIFECYCLE = (
    EditorOperationalGenerationLifecycleStateV1.ACCEPTED,
    EditorOperationalGenerationLifecycleStateV1.VALIDATED,
    EditorOperationalGenerationLifecycleStateV1.FAILED,
)
GENERATION_FAILURE_LIFECYCLE = (
    EditorOperationalGenerationLifecycleStateV1.ACCEPTED,
    EditorOperationalGenerationLifecycleStateV1.VALIDATED,
    EditorOperationalGenerationLifecycleStateV1.SESSION_OPENED,
    EditorOperationalGenerationLifecycleStateV1.GENERATION_STARTED,
    EditorOperationalGenerationLifecycleStateV1.FAILED,
)
CANCELLED_LIFECYCLE = (
    *GENERATION_FAILURE_LIFECYCLE[:-1],
    EditorOperationalGenerationLifecycleStateV1.CANCELLED,
)
CONTROLLED_RESULT_FAILURE_LIFECYCLE = (
    *GENERATION_FAILURE_LIFECYCLE[:-1],
    EditorOperationalGenerationLifecycleStateV1.GENERATED,
    EditorOperationalGenerationLifecycleStateV1.FAILED,
)


__all__ = (
    "EditorOperationalGenerationFailureCodeV1",
    "EditorOperationalGenerationFailureV1",
    "EditorOperationalGenerationLifecycleStateV1",
    "EditorOperationalGenerationStatusV1",
    "EditorOperationalResultV1",
)
