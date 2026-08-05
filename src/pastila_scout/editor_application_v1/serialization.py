"""Canonical in-memory serialization for completed Editor operational results."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import unicodedata
from datetime import UTC, datetime
from enum import Enum
from typing import NoReturn

from pydantic import BaseModel

from pastila_scout.editor.generation.manifest import GenerationManifest
from pastila_scout.editor.generation.models import EpisodeDraft, GenerationTrace
from pastila_scout.editor_generation_provider_adapter_v1 import (
    EditorGenerationAttemptObservationV1,
)
from pastila_scout.editor_operational_execution_v1 import (
    EditorOperationalGenerationStatusV1,
    EditorOperationalResultV1,
)

from .errors import EditorApplicationSerializationError

_SCHEMA_NAME = "pastila-editor-operational-export"
_SCHEMA_VERSION = "1"
_ATTEMPT_FIELDS = (
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


class EditorOperationalResultSerializerV1:
    """Serialize one eligible operational result without performing I/O."""

    __slots__ = ()

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Editor operational serializers cannot be subclassed")

    def __repr__(self) -> str:
        return "EditorOperationalResultSerializerV1()"

    def __eq__(self, other: object) -> bool:
        return type(other) is type(self)

    def __copy__(self) -> EditorOperationalResultSerializerV1:
        return type(self)()

    def __deepcopy__(
        self, memo: dict[int, object]
    ) -> EditorOperationalResultSerializerV1:
        del memo
        return type(self)()

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("EditorOperationalResultSerializerV1 does not support pickle")

    def serialize(self, *, result: EditorOperationalResultV1) -> bytes:
        valid, payload = _serialize_neutral(result)
        del result
        if not valid:
            del payload
            _raise_serialization_error()
        return payload


def _serialize_neutral(result: object) -> tuple[bool, bytes]:
    rebuilt = envelope = initial = checksum = final = None
    try:
        if type(result) is not EditorOperationalResultV1:
            raise TypeError
        rebuilt = copy.copy(result)
        if (
            type(rebuilt) is not EditorOperationalResultV1
            or rebuilt.status is not EditorOperationalGenerationStatusV1.COMPLETED
            or rebuilt.cleanup_failed
            or rebuilt.failure is not None
            or rebuilt.draft is None
        ):
            raise TypeError
        envelope = _envelope(rebuilt)
        initial = _encode(envelope)
        checksum = f"sha256:{hashlib.sha256(initial).hexdigest()}"
        envelope["payload_sha256"] = checksum
        final = _encode(envelope)
        return True, final
    except Exception:  # noqa: BLE001 - protected graph is reduced before publication
        del result, rebuilt, envelope, initial, checksum, final
        return False, b""


def _envelope(result: EditorOperationalResultV1) -> dict[str, object]:
    projection = _operational_projection(result)
    return {
        "schema_name": _SCHEMA_NAME,
        "schema_version": _SCHEMA_VERSION,
        "operation_reference": _string(result.execution_request_reference),
        "source_lineage": {
            "source_report_id": _string(result.source_report_id),
            "source_report_fingerprint": _string(result.source_report_fingerprint),
            "preparation_result_fingerprint": _string(
                result.preparation_result_fingerprint
            ),
            "execution_request_reference": _string(result.execution_request_reference),
            "execution_request_fingerprint": _string(
                result.execution_request_fingerprint
            ),
        },
        "operational_result": projection,
        "payload_sha256": "",
    }


def _operational_projection(result: EditorOperationalResultV1) -> dict[str, object]:
    return {
        "source_report_id": _string(result.source_report_id),
        "source_report_fingerprint": _string(result.source_report_fingerprint),
        "preparation_result_fingerprint": _string(
            result.preparation_result_fingerprint
        ),
        "execution_request_reference": _string(result.execution_request_reference),
        "execution_request_fingerprint": _string(result.execution_request_fingerprint),
        "status": _enum(result.status),
        "lifecycle": [_enum(item) for item in result.lifecycle],
        "draft": _model(result.draft, EpisodeDraft),
        "generation_trace": _model(result.generation_trace, GenerationTrace),
        "generation_manifest": _model(result.generation_manifest, GenerationManifest),
        "final_state_revision": _value(result.final_state_revision),
        "attempts": [_attempt(item) for item in result.attempts],
        "attempt_count": _integer(result.attempt_count),
        "timeout_retry_count": _integer(result.timeout_retry_count),
        "failure": None,
        "cleanup_failed": _boolean(result.cleanup_failed),
        "result_fingerprint": _string(result.result_fingerprint),
    }


def _attempt(value: object) -> dict[str, object]:
    if type(value) is not EditorGenerationAttemptObservationV1:
        raise TypeError
    return {
        name: _value(object.__getattribute__(value, name)) for name in _ATTEMPT_FIELDS
    }


def _model(value: object, model: type[BaseModel]) -> object:
    if type(value) is not model:
        raise TypeError
    return _value(value.model_dump(mode="json", warnings="error"))


def _value(value: object) -> object:
    if value is None:
        return None
    if type(value) is str:
        return _string(value)
    if type(value) is bool:
        return value
    if type(value) is int:
        return value
    if type(value) is float:
        if not math.isfinite(value):
            raise TypeError
        return value
    if type(value) is datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise TypeError
        return value.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    if isinstance(value, Enum):
        return _enum(value)
    if type(value) in {tuple, list}:
        return [_value(item) for item in value]
    if type(value) is dict:
        projected: dict[str, object] = {}
        for key, item in value.items():
            normalized = _string(key)
            if normalized in projected:
                raise TypeError
            projected[normalized] = _value(item)
        return projected
    raise TypeError


def _string(value: object) -> str:
    if type(value) is not str:
        raise TypeError
    return unicodedata.normalize("NFC", value)


def _enum(value: object) -> object:
    if not isinstance(value, Enum) or type(value.value) not in {str, int}:
        raise TypeError
    return _value(value.value)


def _integer(value: object) -> int:
    if type(value) is not int:
        raise TypeError
    return value


def _boolean(value: object) -> bool:
    if type(value) is not bool:
        raise TypeError
    return value


def _encode(payload: dict[str, object]) -> bytes:
    text = json.dumps(
        payload,
        ensure_ascii=False,
        allow_nan=False,
        sort_keys=True,
        separators=(",", ":"),
    )
    return text.encode("utf-8") + b"\n"


def _raise_serialization_error() -> NoReturn:
    error = EditorApplicationSerializationError()
    try:
        raise error from None
    except EditorApplicationSerializationError as published:
        Exception.__setattr__(published, "__context__", None)
        raise


__all__ = ("EditorOperationalResultSerializerV1",)
