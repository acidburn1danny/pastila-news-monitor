"""Canonical in-memory serialization for completed Editor operational results."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum, auto
from typing import NoReturn

from pydantic import BaseModel

from pastila_scout.editor.generation.manifest import GenerationManifest
from pastila_scout.editor.generation.models import EpisodeDraft, GenerationTrace
from pastila_scout.editor_generation_provider_adapter_v1 import (
    EditorGenerationAttemptObservationV1,
)
from pastila_scout.editor_operational_execution_v1 import (
    EditorOperationalGenerationLifecycleStateV1,
    EditorOperationalGenerationStatusV1,
    EditorOperationalResultV1,
)
from pastila_scout.provider_execution_v2 import ExecutionOutcomeV2
from pastila_scout.provider_v2 import ProviderFinishReasonV2

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
_TOP_LEVEL_FIELDS = (
    "operation_reference",
    "operational_result",
    "payload_sha256",
    "schema_name",
    "schema_version",
    "source_lineage",
)
_LINEAGE_FIELDS = (
    "execution_request_fingerprint",
    "execution_request_reference",
    "preparation_result_fingerprint",
    "source_report_fingerprint",
    "source_report_id",
)
_OPERATIONAL_FIELDS = (
    "attempt_count",
    "attempts",
    "cleanup_failed",
    "draft",
    "execution_request_fingerprint",
    "execution_request_reference",
    "failure",
    "final_state_revision",
    "generation_manifest",
    "generation_trace",
    "lifecycle",
    "preparation_result_fingerprint",
    "result_fingerprint",
    "source_report_fingerprint",
    "source_report_id",
    "status",
    "timeout_retry_count",
)


class _SerializationStatusV1(Enum):
    INVALID_INPUT_TYPE = auto()
    OPERATIONAL_RECONSTRUCTION_FAILED = auto()
    INELIGIBLE_OPERATIONAL_RESULT = auto()
    PROJECTION_FAILED = auto()
    PLACEHOLDER_ENCODING_FAILED = auto()
    PRODUCTION_CHECKSUM_FAILED = auto()
    FINAL_ENCODING_FAILED = auto()
    WRAPPER_CONSTRUCTION_FAILED = auto()
    CANONICAL_PAYLOAD_INVALID = auto()
    CHECKSUM_MISMATCH = auto()
    COPIED_INVALID_STATE = auto()
    SERIALIZATION_CORRUPTION = auto()


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class EditorSerializedOperationalResultV1:
    """Canonical payload and its serializer-owned placeholder checksum."""

    payload: bytes
    payload_sha256: str

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Editor serialized operational results cannot be subclassed")

    def __init__(self, payload: bytes, payload_sha256: str) -> None:
        valid_payload = valid_checksum = None
        try:
            valid_payload, valid_checksum = _validated_serialized_pair(
                payload, payload_sha256
            )
        except Exception:  # noqa: BLE001 - protected state collapses here
            del self, payload, payload_sha256, valid_payload, valid_checksum
            _raise_serialization_error()
        object.__setattr__(self, "payload", valid_payload)
        object.__setattr__(self, "payload_sha256", valid_checksum)

    def __repr__(self) -> str:
        _reconstruct_serialized_result(self)
        return (
            "EditorSerializedOperationalResultV1("
            "payload=<redacted>, payload_sha256=<redacted>)"
        )

    def __eq__(self, other: object) -> bool:
        if type(other) is not type(self):
            return False
        left = _reconstruct_serialized_result(self)
        right = _reconstruct_serialized_result(other)
        return (left.payload, left.payload_sha256) == (
            right.payload,
            right.payload_sha256,
        )

    def __copy__(self) -> EditorSerializedOperationalResultV1:
        return _reconstruct_serialized_result(self)

    def __deepcopy__(
        self, memo: dict[int, object]
    ) -> EditorSerializedOperationalResultV1:
        del memo
        return _reconstruct_serialized_result(self)

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("EditorSerializedOperationalResultV1 does not support pickle")


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

    def serialize(
        self, *, result: EditorOperationalResultV1
    ) -> EditorSerializedOperationalResultV1:
        status, serialized = _serialize_neutral(result)
        del result
        if status is not None:
            del status, serialized
            _raise_serialization_error()
        return serialized


def _serialize_neutral(
    result: object,
) -> tuple[_SerializationStatusV1 | None, EditorSerializedOperationalResultV1 | None]:
    rebuilt = envelope = initial = checksum = final = serialized = None
    status = None
    try:
        if type(result) is not EditorOperationalResultV1:
            status = _SerializationStatusV1.INVALID_INPUT_TYPE
        if status is None:
            try:
                rebuilt = copy.copy(result)
            except Exception:  # noqa: BLE001 - one reconstruction boundary
                status = _SerializationStatusV1.OPERATIONAL_RECONSTRUCTION_FAILED
        if status is None and (
            type(rebuilt) is not EditorOperationalResultV1
            or rebuilt.status is not EditorOperationalGenerationStatusV1.COMPLETED
            or rebuilt.cleanup_failed
            or rebuilt.failure is not None
            or rebuilt.draft is None
        ):
            status = _SerializationStatusV1.INELIGIBLE_OPERATIONAL_RESULT
        if status is None:
            try:
                envelope = _envelope(rebuilt)
            except Exception:  # noqa: BLE001 - one projection boundary
                status = _SerializationStatusV1.PROJECTION_FAILED
        if status is None:
            try:
                initial = _encode(envelope)
            except Exception:  # noqa: BLE001 - placeholder encoding boundary
                status = _SerializationStatusV1.PLACEHOLDER_ENCODING_FAILED
        if status is None:
            try:
                checksum = f"sha256:{hashlib.sha256(initial).hexdigest()}"
            except Exception:  # noqa: BLE001 - production checksum boundary
                status = _SerializationStatusV1.PRODUCTION_CHECKSUM_FAILED
        if status is None:
            envelope["payload_sha256"] = checksum
            try:
                final = _encode(envelope)
            except Exception:  # noqa: BLE001 - final encoding boundary
                status = _SerializationStatusV1.FINAL_ENCODING_FAILED
        if status is None:
            try:
                serialized = EditorSerializedOperationalResultV1(final, checksum)
            except EditorApplicationSerializationError:
                status = _SerializationStatusV1.WRAPPER_CONSTRUCTION_FAILED
    except Exception:  # noqa: BLE001 - protected graph is reduced before publication
        status = _SerializationStatusV1.SERIALIZATION_CORRUPTION
    del result, rebuilt, envelope, initial, checksum, final
    if status is not None:
        del serialized
        return status, None
    return None, serialized


def _reconstruct_serialized_result(
    value: object,
) -> EditorSerializedOperationalResultV1:
    payload = checksum = None
    try:
        if type(value) is not EditorSerializedOperationalResultV1:
            raise TypeError
        payload = object.__getattribute__(value, "payload")
        checksum = object.__getattribute__(value, "payload_sha256")
        rebuilt = EditorSerializedOperationalResultV1(payload, checksum)
        return rebuilt
    except EditorApplicationSerializationError:
        del value, payload, checksum
        _raise_serialization_error()
    except Exception:  # noqa: BLE001 - copied-invalid state collapses here
        del value, payload, checksum
        _raise_serialization_error()


def _validated_serialized_pair(payload: object, checksum: object) -> tuple[bytes, str]:
    if type(payload) is not bytes or type(checksum) is not str or not payload:
        raise TypeError
    if payload.startswith(b"\xef\xbb\xbf") or not payload.endswith(b"\n"):
        raise TypeError
    if payload.endswith(b"\n\n") or b"\r\n" in payload:
        raise TypeError
    text = payload[:-1].decode("utf-8")
    parsed = json.loads(
        text,
        object_pairs_hook=_strict_object,
        parse_constant=_reject_constant,
    )
    if type(parsed) is not dict or tuple(parsed) != _TOP_LEVEL_FIELDS:
        raise TypeError
    if (
        parsed.get("schema_name") != _SCHEMA_NAME
        or parsed.get("schema_version") != _SCHEMA_VERSION
    ):
        raise TypeError
    _validate_envelope_shape(parsed)
    embedded = parsed.get("payload_sha256")
    if not _valid_checksum(checksum) or embedded != checksum:
        raise TypeError
    if _encode(parsed) != payload:
        raise TypeError
    parsed["payload_sha256"] = ""
    expected = f"sha256:{hashlib.sha256(_encode(parsed)).hexdigest()}"
    if expected != checksum:
        raise TypeError
    return bytes(payload), str(checksum)


def _strict_object(pairs: list[tuple[object, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if type(key) is not str or not unicodedata.is_normalized("NFC", key):
            raise TypeError
        normalized = unicodedata.normalize("NFC", key)
        if normalized in result:
            raise TypeError
        result[normalized] = value
    return result


def _reject_constant(value: str) -> NoReturn:
    del value
    raise TypeError


def _validate_envelope_shape(value: dict[str, object]) -> None:
    lineage = value.get("source_lineage")
    operational = value.get("operational_result")
    if (
        type(lineage) is not dict
        or tuple(lineage) != _LINEAGE_FIELDS
        or type(operational) is not dict
        or tuple(operational) != _OPERATIONAL_FIELDS
        or not _all_values_canonical(value)
    ):
        raise TypeError
    _reconstruct_projected_operational(operational)
    reference = value.get("operation_reference")
    if not (
        type(reference) is str
        and reference
        == lineage.get("execution_request_reference")
        == operational.get("execution_request_reference")
        and lineage.get("source_report_id") == operational.get("source_report_id")
        and lineage.get("source_report_fingerprint")
        == operational.get("source_report_fingerprint")
        and lineage.get("preparation_result_fingerprint")
        == operational.get("preparation_result_fingerprint")
        and lineage.get("execution_request_fingerprint")
        == operational.get("execution_request_fingerprint")
    ):
        raise TypeError


def _reconstruct_projected_operational(
    value: dict[str, object],
) -> EditorOperationalResultV1:
    attempts = value["attempts"]
    lifecycle = value["lifecycle"]
    if type(attempts) is not list or type(lifecycle) is not list:
        raise TypeError
    rebuilt_attempts = tuple(_reconstruct_projected_attempt(item) for item in attempts)
    rebuilt_lifecycle = tuple(
        EditorOperationalGenerationLifecycleStateV1(item) for item in lifecycle
    )
    return EditorOperationalResultV1(
        value["source_report_id"],
        value["source_report_fingerprint"],
        value["preparation_result_fingerprint"],
        value["execution_request_reference"],
        value["execution_request_fingerprint"],
        EditorOperationalGenerationStatusV1(value["status"]),
        rebuilt_lifecycle,
        _model_from_projection(value["draft"], EpisodeDraft),
        _model_from_projection(value["generation_trace"], GenerationTrace),
        _model_from_projection(value["generation_manifest"], GenerationManifest),
        value["final_state_revision"],
        rebuilt_attempts,
        value["attempt_count"],
        value["timeout_retry_count"],
        None,
        value["cleanup_failed"],
        value["result_fingerprint"],
    )


def _model_from_projection(value: object, model: type[BaseModel]) -> BaseModel:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        allow_nan=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return model.model_validate_json(encoded, strict=True)


def _reconstruct_projected_attempt(
    value: object,
) -> EditorGenerationAttemptObservationV1:
    if type(value) is not dict or tuple(value) != tuple(sorted(_ATTEMPT_FIELDS)):
        raise TypeError
    finish_reason = value["finish_reason"]
    return EditorGenerationAttemptObservationV1(
        value["attempt_number"],
        value["prompt_fingerprint"],
        value["request_reference"],
        value["request_fingerprint"],
        value["execution_request_id"],
        value["request_envelope_identity"],
        value["provider_id"],
        ExecutionOutcomeV2(value["outcome"]),
        value["source_output_reference"],
        None if finish_reason is None else ProviderFinishReasonV2(finish_reason),
        value["failure_code"],
    )


def _all_values_canonical(value: object) -> bool:
    if value is None or type(value) in {bool, int}:
        return True
    if type(value) is float:
        return math.isfinite(value)
    if type(value) is str:
        return unicodedata.is_normalized("NFC", value)
    if type(value) is list:
        return all(_all_values_canonical(item) for item in value)
    if type(value) is dict:
        return all(
            type(key) is str
            and unicodedata.is_normalized("NFC", key)
            and _all_values_canonical(item)
            for key, item in value.items()
        )
    return False


def _valid_checksum(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == 71
        and value.startswith("sha256:")
        and all(character in "0123456789abcdef" for character in value[7:])
    )


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


__all__ = (
    "EditorOperationalResultSerializerV1",
    "EditorSerializedOperationalResultV1",
)
