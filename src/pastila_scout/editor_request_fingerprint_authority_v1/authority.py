"""Public deterministic authority for Editor generation request fingerprints."""

from __future__ import annotations

import hmac
import json
import math
import unicodedata
from copy import copy
from dataclasses import dataclass
from datetime import UTC, datetime
from enum import Enum
from hashlib import sha256
from typing import Any, NoReturn, Self

from pastila_scout.editor_generation_authority_v1 import (
    EditorGenerationRuntimeOptionsV1,
)
from pastila_scout.provider_execution_v2 import CancellationTokenV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1

from .errors import EditorRequestFingerprintAuthorityError

_ERROR_MESSAGE = "Editor request fingerprint authority is invalid."
_HEX = frozenset("0123456789abcdef")
_MAX_PROMPT = 200_000


def _raise_invalid() -> NoReturn:
    error = EditorRequestFingerprintAuthorityError(_ERROR_MESSAGE)
    error.__cause__ = None
    error.__context__ = None
    error.__suppress_context__ = True
    raise error from None


@dataclass(frozen=True, slots=True, init=False)
class EditorRequestFingerprintAuthorityV1:
    """Stateless public owner of generation request fingerprint semantics."""

    def __init__(self) -> None:
        pass

    def fingerprint(
        self,
        *,
        provider: ProviderChoiceV1,
        prompt: str,
        request_reference: str,
        requested_at: datetime,
        options: EditorGenerationRuntimeOptionsV1,
        output_schema_name: str,
        output_schema_canonical_json: str,
        output_schema_fingerprint: str,
        cancellation: CancellationTokenV2,
    ) -> str:
        outcome = _calculate(
            self,
            provider,
            prompt,
            request_reference,
            requested_at,
            options,
            output_schema_name,
            output_schema_canonical_json,
            output_schema_fingerprint,
            cancellation,
        )
        del self, provider, prompt, request_reference, requested_at, options
        del output_schema_name, output_schema_canonical_json
        del output_schema_fingerprint, cancellation
        if outcome is None:
            del outcome
            _raise_invalid()
        return outcome

    def reconstruct(
        self,
        fingerprint: str,
        *,
        provider: ProviderChoiceV1,
        prompt: str,
        request_reference: str,
        requested_at: datetime,
        options: EditorGenerationRuntimeOptionsV1,
        output_schema_name: str,
        output_schema_canonical_json: str,
        output_schema_fingerprint: str,
        cancellation: CancellationTokenV2,
    ) -> str:
        supplied = fingerprint if _fingerprint_is_valid(fingerprint) else None
        outcome = _calculate(
            self,
            provider,
            prompt,
            request_reference,
            requested_at,
            options,
            output_schema_name,
            output_schema_canonical_json,
            output_schema_fingerprint,
            cancellation,
        )
        del self, fingerprint, provider, prompt, request_reference, requested_at
        del options, output_schema_name, output_schema_canonical_json
        del output_schema_fingerprint, cancellation
        valid = supplied is not None and outcome is not None
        if valid:
            valid = hmac.compare_digest(supplied, outcome)
        del supplied
        if not valid or outcome is None:
            del valid, outcome
            _raise_invalid()
        return outcome

    def __repr__(self) -> str:
        return "EditorRequestFingerprintAuthorityV1()"

    def __eq__(self, other: object) -> bool:
        return type(self) is EditorRequestFingerprintAuthorityV1 and type(
            other
        ) is type(self)

    def __copy__(self) -> Self:
        return self

    def __deepcopy__(self, memo: dict[int, object]) -> Self:
        memo[id(self)] = self
        return self

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("EditorRequestFingerprintAuthorityV1 does not support pickle")


def _calculate(
    authority: object,
    provider: object,
    prompt: object,
    request_reference: object,
    requested_at: object,
    options: object,
    output_schema_name: object,
    output_schema_canonical_json: object,
    output_schema_fingerprint: object,
    cancellation: object,
) -> str | None:
    try:
        if type(authority) is not EditorRequestFingerprintAuthorityV1:
            return None
        valid_options = _options(options)
        valid_cancellation = _cancellation(cancellation)
        if (
            type(provider) is not ProviderChoiceV1
            or provider is not valid_options.provider
            or not _prompt_is_valid(prompt)
            or not _text_is_valid(request_reference, maximum=120)
            or type(requested_at) is not datetime
            or requested_at.tzinfo is None
            or requested_at.utcoffset() is None
            or not _text_is_valid(output_schema_name, maximum=200)
            or type(output_schema_canonical_json) is not str
        ):
            return None
        schema = json.loads(output_schema_canonical_json)
        if (
            type(schema) is not dict
            or _canonical_json(schema) != output_schema_canonical_json
            or type(output_schema_fingerprint) is not str
            or _sha256(schema) != output_schema_fingerprint
        ):
            return None
        payload = {
            "provider": provider.value,
            "prompt": prompt,
            "request_reference": request_reference,
            "requested_at": requested_at,
            "options": _option_payload(valid_options),
            "output_schema_name": output_schema_name,
            "output_schema_canonical_json": output_schema_canonical_json,
            "output_schema_fingerprint": output_schema_fingerprint,
            "cancellation_requested": valid_cancellation.cancellation_requested,
        }
        return _sha256(payload)
    except Exception:  # noqa: BLE001 - invalid semantic details are discarded
        return None


def _options(value: object) -> EditorGenerationRuntimeOptionsV1:
    if type(value) is not EditorGenerationRuntimeOptionsV1:
        raise TypeError("invalid options")
    rebuilt = copy(value)
    if type(rebuilt) is not EditorGenerationRuntimeOptionsV1:
        raise TypeError("invalid options")
    return rebuilt


def _cancellation(value: object) -> CancellationTokenV2:
    if type(value) is not CancellationTokenV2:
        raise TypeError("invalid cancellation")
    return CancellationTokenV2.model_validate(
        value.model_dump(mode="python", warnings=False), strict=True
    )


def _text_is_valid(value: object, *, maximum: int) -> bool:
    return (
        type(value) is str
        and bool(value)
        and value == value.strip()
        and len(value) <= maximum
        and unicodedata.is_normalized("NFC", value)
    )


def _prompt_is_valid(value: object) -> bool:
    return (
        type(value) is str
        and bool(value)
        and value == value.strip()
        and len(value) <= _MAX_PROMPT
    )


def _fingerprint_is_valid(value: object) -> bool:
    return type(value) is str and len(value) == 64 and set(value).issubset(_HEX)


def _tagged_number(value: object) -> dict[str, object]:
    if type(value) is int:
        return {"type": "int", "value": value}
    if type(value) is float and math.isfinite(value):
        return {"type": "float", "value": value}
    raise TypeError("invalid number")


def _option_payload(options: EditorGenerationRuntimeOptionsV1) -> dict[str, object]:
    return {
        "provider": options.provider.value,
        "model_identifier": options.model_identifier,
        "model_revision": options.model_revision,
        "temperature": _tagged_number(options.temperature),
        "top_p": _tagged_number(options.top_p),
        "max_output_tokens": options.max_output_tokens,
        "seed": options.seed,
        "stop_sequences": options.stop_sequences,
        "structured_output_mode": options.structured_output_mode,
        "timeout_seconds": _tagged_number(options.timeout_policy.timeout_seconds),
    }


def _canonical_value(value: object) -> Any:
    if value is None or type(value) in {bool, int, str}:
        return unicodedata.normalize("NFC", value) if type(value) is str else value
    if type(value) is float:
        if not math.isfinite(value):
            raise TypeError("invalid value")
        return value
    if type(value) is datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise TypeError("invalid value")
        return (
            value.astimezone(UTC)
            .isoformat(timespec="microseconds")
            .replace("+00:00", "Z")
        )
    if isinstance(value, Enum):
        return _canonical_value(value.value)
    if type(value) in {tuple, list}:
        return [_canonical_value(item) for item in value]
    if type(value) is dict:
        if any(type(key) is not str for key in value):
            raise TypeError("invalid value")
        return {
            _canonical_value(key): _canonical_value(item) for key, item in value.items()
        }
    raise TypeError("invalid value")


def _canonical_json(value: object) -> str:
    return json.dumps(
        _canonical_value(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256(value: object) -> str:
    return sha256(_canonical_json(value).encode("utf-8")).hexdigest()


__all__ = ("EditorRequestFingerprintAuthorityV1",)
