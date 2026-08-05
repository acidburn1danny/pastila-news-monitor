"""Safe immutable attempt provenance."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import NoReturn

from pastila_scout.provider_execution_v2 import ExecutionOutcomeV2
from pastila_scout.provider_v2 import ProviderFinishReasonV2

from .errors import EditorGenerationProviderAdapterError

_SAFE = "Editor generation provider adapter failed."
_PROMPT_HASH = re.compile(r"^sha256:[0-9a-f]{64}$")
_REQUEST_HASH = re.compile(r"^[0-9a-f]{64}$")


def _raise_invalid() -> NoReturn:
    error = EditorGenerationProviderAdapterError(_SAFE)
    error.__cause__ = None
    error.__context__ = None
    error.__suppress_context__ = True
    raise error from None


@dataclass(frozen=True, slots=True, init=False, repr=False)
class EditorGenerationAttemptObservationV1:
    attempt_number: int
    prompt_fingerprint: str
    request_reference: str
    request_fingerprint: str
    execution_request_id: str
    request_envelope_identity: str
    provider_id: str
    outcome: ExecutionOutcomeV2
    source_output_reference: str | None
    finish_reason: ProviderFinishReasonV2 | None
    failure_code: str | None

    def __init__(
        self,
        attempt_number,
        prompt_fingerprint,
        request_reference,
        request_fingerprint,
        execution_request_id,
        request_envelope_identity,
        provider_id,
        outcome,
        source_output_reference,
        finish_reason,
        failure_code,
    ) -> None:
        values = (
            attempt_number,
            prompt_fingerprint,
            request_reference,
            request_fingerprint,
            execution_request_id,
            request_envelope_identity,
            provider_id,
            outcome,
            source_output_reference,
            finish_reason,
            failure_code,
        )
        if not _valid(values):
            del self, values, attempt_number, prompt_fingerprint, request_reference
            del request_fingerprint, execution_request_id, request_envelope_identity
            del (
                provider_id,
                outcome,
                source_output_reference,
                finish_reason,
                failure_code,
            )
            _raise_invalid()
        for name, value in zip(_FIELDS, values, strict=True):
            object.__setattr__(self, name, value)

    def __repr__(self) -> str:
        _reconstruct(self)
        return "EditorGenerationAttemptObservationV1(<safe attempt metadata>)"

    def __copy__(self) -> EditorGenerationAttemptObservationV1:
        return _reconstruct(self)

    def __deepcopy__(
        self, memo: dict[int, object]
    ) -> EditorGenerationAttemptObservationV1:
        del memo
        return _reconstruct(self)

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("EditorGenerationAttemptObservationV1 does not support pickle")


_FIELDS = (
    "attempt_number",
    "prompt_fingerprint",
    "request_reference",
    "request_fingerprint",
    "execution_request_id",
    "request_envelope_identity",
    "provider_id",
    "outcome",
    "source_output_reference",
    "finish_reason",
    "failure_code",
)


def _text(value: object, maximum: int = 200) -> bool:
    return (
        type(value) is str
        and bool(value)
        and value == value.strip()
        and len(value) <= maximum
    )


def _valid(values: tuple[object, ...]) -> bool:
    (
        number,
        prompt_hash,
        reference,
        request_hash,
        request_id,
        envelope,
        provider,
        outcome,
        source,
        reason,
        failure,
    ) = values
    completed = outcome is ExecutionOutcomeV2.COMPLETED
    return (
        type(number) is int
        and number > 0
        and type(prompt_hash) is str
        and _PROMPT_HASH.fullmatch(prompt_hash) is not None
        and _text(reference)
        and type(request_hash) is str
        and _REQUEST_HASH.fullmatch(request_hash) is not None
        and _text(request_id)
        and _text(envelope)
        and _text(provider, 100)
        and type(outcome) is ExecutionOutcomeV2
        and (source is None or _text(source))
        and (reason is None or type(reason) is ProviderFinishReasonV2)
        and (failure is None or _text(failure, 120))
        and completed == (source is not None)
        and completed == (reason is not None)
        and completed == (failure is None)
    )


def _reconstruct(value: object) -> EditorGenerationAttemptObservationV1:
    try:
        if type(value) is not EditorGenerationAttemptObservationV1:
            raise TypeError
        return EditorGenerationAttemptObservationV1(
            *(object.__getattribute__(value, name) for name in _FIELDS)
        )
    except EditorGenerationProviderAdapterError:
        raise
    except Exception:  # noqa: BLE001
        _raise_invalid()


__all__ = ("EditorGenerationAttemptObservationV1",)
