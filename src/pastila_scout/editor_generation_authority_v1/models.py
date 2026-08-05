"""Strict immutable generation authority contracts."""

from __future__ import annotations

import json
import math
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from typing import NoReturn

from pydantic import ValidationError

from pastila_scout.provider_execution_v2 import CancellationTokenV2, TimeoutPolicyV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1

from .canonical import canonical_json, semantic_fingerprint, tagged_number
from .errors import EditorGenerationAuthorityError

_HASH_LENGTH = 64
_MAX_PROMPT = 200_000


def _raise_invalid() -> NoReturn:
    error = EditorGenerationAuthorityError("Editor generation authority is invalid.")
    error.__suppress_context__ = True
    raise error from None


def _hash_is_valid(value: object) -> bool:
    return (
        type(value) is str
        and len(value) == _HASH_LENGTH
        and all(character in "0123456789abcdef" for character in value)
    )


def _text_is_valid(value: object, *, maximum: int = 200) -> bool:
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


def _timeout(value: object) -> TimeoutPolicyV2:
    if type(value) is not TimeoutPolicyV2:
        _raise_invalid()
    try:
        return TimeoutPolicyV2.model_validate(
            value.model_dump(mode="python", warnings=False), strict=True
        )
    except (AttributeError, TypeError, ValueError, ValidationError):
        _raise_invalid()


def _cancellation(value: object) -> CancellationTokenV2:
    if type(value) is not CancellationTokenV2:
        _raise_invalid()
    try:
        return CancellationTokenV2.model_validate(
            value.model_dump(mode="python", warnings=False), strict=True
        )
    except (AttributeError, TypeError, ValueError, ValidationError):
        _raise_invalid()


@dataclass(frozen=True, slots=True, init=False, repr=False)
class EditorGenerationRuntimeOptionsV1:
    provider: ProviderChoiceV1
    model_identifier: str
    model_revision: str | None
    temperature: int | float
    top_p: int | float
    max_output_tokens: int
    seed: None
    stop_sequences: tuple[str, ...]
    structured_output_mode: bool
    timeout_policy: TimeoutPolicyV2
    _seal: str

    def __init__(
        self,
        provider,
        model_identifier,
        model_revision,
        temperature,
        top_p,
        max_output_tokens,
        seed,
        stop_sequences,
        structured_output_mode,
        timeout_policy,
    ) -> None:
        valid = True
        try:
            self._initialize(
                provider,
                model_identifier,
                model_revision,
                temperature,
                top_p,
                max_output_tokens,
                seed,
                stop_sequences,
                structured_output_mode,
                timeout_policy,
            )
        except Exception:  # noqa: BLE001 - validation detail is discarded
            valid = False
        if not valid:
            del self, provider, model_identifier, model_revision, temperature
            del top_p, max_output_tokens, seed, stop_sequences
            del structured_output_mode, timeout_policy
            _raise_invalid()

    def _initialize(
        self,
        provider,
        model_identifier,
        model_revision,
        temperature,
        top_p,
        max_output_tokens,
        seed,
        stop_sequences,
        structured_output_mode,
        timeout_policy,
    ) -> None:
        try:
            if type(provider) is not ProviderChoiceV1:
                _raise_invalid()
            if not _text_is_valid(model_identifier):
                _raise_invalid()
            if model_revision is not None and not _text_is_valid(model_revision):
                _raise_invalid()
            if (
                type(temperature) not in {int, float}
                or not math.isfinite(temperature)
                or not 0 <= temperature <= 2
            ):
                _raise_invalid()
            if (
                type(top_p) not in {int, float}
                or not math.isfinite(top_p)
                or top_p != 1
            ):
                _raise_invalid()
            if type(max_output_tokens) is not int or max_output_tokens <= 0:
                _raise_invalid()
            if seed is not None or type(stop_sequences) is not tuple or stop_sequences:
                _raise_invalid()
            if type(structured_output_mode) is not bool or not structured_output_mode:
                _raise_invalid()
            valid_timeout = _timeout(timeout_policy)
            values = (
                provider,
                model_identifier,
                model_revision,
                temperature,
                top_p,
                max_output_tokens,
                None,
                (),
                True,
                valid_timeout,
            )
            seal = semantic_fingerprint(_options_semantics(values))
        except EditorGenerationAuthorityError:
            raise
        except Exception:  # noqa: BLE001 - invalid values retain no details
            _raise_invalid()
        for name, value in zip(_OPTION_FIELDS, values, strict=True):
            object.__setattr__(self, name, value)
        object.__setattr__(self, "_seal", seal)

    def __repr__(self) -> str:
        valid = reconstruct_runtime_options(self)
        return f"EditorGenerationRuntimeOptionsV1(provider={valid.provider.value!r}, model_identifier={valid.model_identifier!r})"

    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and _option_values(
            reconstruct_runtime_options(self)
        ) == _option_values(reconstruct_runtime_options(other))

    def __copy__(self):
        return reconstruct_runtime_options(self)

    def __deepcopy__(self, memo):
        del memo
        return reconstruct_runtime_options(self)

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("EditorGenerationRuntimeOptionsV1 does not support pickle")


_OPTION_FIELDS = (
    "provider",
    "model_identifier",
    "model_revision",
    "temperature",
    "top_p",
    "max_output_tokens",
    "seed",
    "stop_sequences",
    "structured_output_mode",
    "timeout_policy",
)


def _option_values(value):
    return tuple(object.__getattribute__(value, name) for name in _OPTION_FIELDS)


def _options_semantics(values):
    (
        provider,
        model,
        revision,
        temperature,
        top_p,
        maximum,
        seed,
        stops,
        structured,
        timeout,
    ) = values
    return {
        "provider": provider.value,
        "model_identifier": model,
        "model_revision": revision,
        "temperature": tagged_number(temperature),
        "top_p": tagged_number(top_p),
        "max_output_tokens": maximum,
        "seed": seed,
        "stop_sequences": stops,
        "structured_output_mode": structured,
        "timeout_seconds": tagged_number(timeout.timeout_seconds),
    }


def reconstruct_runtime_options(value: object) -> EditorGenerationRuntimeOptionsV1:
    if type(value) is not EditorGenerationRuntimeOptionsV1:
        _raise_invalid()
    try:
        fields = _option_values(value)
        retained = object.__getattribute__(value, "_seal")
        rebuilt = EditorGenerationRuntimeOptionsV1(*fields)
        if retained != object.__getattribute__(rebuilt, "_seal"):
            _raise_invalid()
        return rebuilt
    except EditorGenerationAuthorityError:
        raise
    except Exception:  # noqa: BLE001 - copied-invalid state remains private
        _raise_invalid()


@dataclass(frozen=True, slots=True, init=False, repr=False)
class EditorGenerationApplicationRequestV1:
    provider: ProviderChoiceV1
    prompt: str
    request_reference: str
    requested_at: datetime
    options: EditorGenerationRuntimeOptionsV1
    output_schema_name: str
    output_schema_canonical_json: str
    output_schema_fingerprint: str
    cancellation: CancellationTokenV2
    request_fingerprint: str
    _seal: str

    def __init__(
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
        request_fingerprint,
    ) -> None:
        valid = True
        try:
            self._initialize(
                provider,
                prompt,
                request_reference,
                requested_at,
                options,
                output_schema_name,
                output_schema_canonical_json,
                output_schema_fingerprint,
                cancellation,
                request_fingerprint,
            )
        except Exception:  # noqa: BLE001 - validation detail is discarded
            valid = False
        if not valid:
            del self, provider, prompt, request_reference, requested_at, options
            del output_schema_name, output_schema_canonical_json
            del output_schema_fingerprint, cancellation, request_fingerprint
            _raise_invalid()

    def _initialize(
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
        request_fingerprint,
    ) -> None:
        try:
            valid_options = reconstruct_runtime_options(options)
            valid_cancellation = _cancellation(cancellation)
            if (
                type(provider) is not ProviderChoiceV1
                or provider is not valid_options.provider
            ):
                _raise_invalid()
            if not _prompt_is_valid(prompt) or not _text_is_valid(
                request_reference, maximum=120
            ):
                _raise_invalid()
            if (
                type(requested_at) is not datetime
                or requested_at.tzinfo is None
                or requested_at.utcoffset() is None
            ):
                _raise_invalid()
            if not _text_is_valid(output_schema_name):
                _raise_invalid()
            if type(output_schema_canonical_json) is not str:
                _raise_invalid()
            parsed = json.loads(output_schema_canonical_json)
            if (
                type(parsed) is not dict
                or canonical_json(parsed) != output_schema_canonical_json
            ):
                _raise_invalid()
            expected_schema_hash = semantic_fingerprint(parsed)
            if output_schema_fingerprint != expected_schema_hash:
                _raise_invalid()
            values = (
                provider,
                prompt,
                request_reference,
                requested_at,
                valid_options,
                output_schema_name,
                output_schema_canonical_json,
                output_schema_fingerprint,
                valid_cancellation,
            )
            expected = semantic_fingerprint(_request_semantics(values))
            if request_fingerprint != expected:
                _raise_invalid()
        except EditorGenerationAuthorityError:
            raise
        except Exception:  # noqa: BLE001 - schema details remain private
            _raise_invalid()
        for name, value in zip(_APPLICATION_FIELDS[:-1], values, strict=True):
            object.__setattr__(self, name, value)
        object.__setattr__(self, "request_fingerprint", request_fingerprint)
        object.__setattr__(self, "_seal", expected)

    def __repr__(self) -> str:
        valid = reconstruct_application_request(self)
        return f"EditorGenerationApplicationRequestV1(provider={valid.provider.value!r}, prompt=<redacted {len(valid.prompt)} characters>)"

    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and _application_values(
            reconstruct_application_request(self)
        ) == _application_values(reconstruct_application_request(other))

    def __copy__(self):
        return reconstruct_application_request(self)

    def __deepcopy__(self, memo):
        del memo
        return reconstruct_application_request(self)

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("EditorGenerationApplicationRequestV1 does not support pickle")


_APPLICATION_FIELDS = (
    "provider",
    "prompt",
    "request_reference",
    "requested_at",
    "options",
    "output_schema_name",
    "output_schema_canonical_json",
    "output_schema_fingerprint",
    "cancellation",
    "request_fingerprint",
)


def _request_semantics(values):
    (
        provider,
        prompt,
        reference,
        requested_at,
        options,
        schema_name,
        schema_json,
        schema_hash,
        cancellation,
    ) = values
    return {
        "provider": provider.value,
        "prompt": prompt,
        "request_reference": reference,
        "requested_at": requested_at,
        "options": _options_semantics(_option_values(options)),
        "output_schema_name": schema_name,
        "output_schema_canonical_json": schema_json,
        "output_schema_fingerprint": schema_hash,
        "cancellation_requested": cancellation.cancellation_requested,
    }


def _application_values(value):
    return tuple(object.__getattribute__(value, name) for name in _APPLICATION_FIELDS)


def reconstruct_application_request(
    value: object,
) -> EditorGenerationApplicationRequestV1:
    if type(value) is not EditorGenerationApplicationRequestV1:
        _raise_invalid()
    try:
        fields = _application_values(value)
        retained = object.__getattribute__(value, "_seal")
        rebuilt = EditorGenerationApplicationRequestV1(*fields)
        if retained != object.__getattribute__(rebuilt, "_seal"):
            _raise_invalid()
        return rebuilt
    except EditorGenerationAuthorityError:
        raise
    except Exception:  # noqa: BLE001 - copied-invalid state remains private
        _raise_invalid()


@dataclass(frozen=True, slots=True, init=False, repr=False)
class EditorGenerationRuntimeAuthorityV1:
    options: EditorGenerationRuntimeOptionsV1
    runtime_reference: str
    runtime_fingerprint: str
    _seal: str

    def __init__(self, options, runtime_reference, runtime_fingerprint) -> None:
        valid = True
        try:
            self._initialize(options, runtime_reference, runtime_fingerprint)
        except Exception:  # noqa: BLE001 - validation detail is discarded
            valid = False
        if not valid:
            del self, options, runtime_reference, runtime_fingerprint
            _raise_invalid()

    def _initialize(self, options, runtime_reference, runtime_fingerprint) -> None:
        valid_options = reconstruct_runtime_options(options)
        if not _text_is_valid(runtime_reference, maximum=120):
            _raise_invalid()
        expected = semantic_fingerprint(
            {
                "options": _options_semantics(_option_values(valid_options)),
                "runtime_reference": runtime_reference,
            }
        )
        if runtime_fingerprint != expected:
            _raise_invalid()
        object.__setattr__(self, "options", valid_options)
        object.__setattr__(self, "runtime_reference", runtime_reference)
        object.__setattr__(self, "runtime_fingerprint", expected)
        object.__setattr__(self, "_seal", expected)

    def __repr__(self) -> str:
        valid = reconstruct_runtime_authority(self)
        return f"EditorGenerationRuntimeAuthorityV1(provider={valid.options.provider.value!r})"

    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and _runtime_values(
            reconstruct_runtime_authority(self)
        ) == _runtime_values(reconstruct_runtime_authority(other))

    def __copy__(self):
        return reconstruct_runtime_authority(self)

    def __deepcopy__(self, memo):
        del memo
        return reconstruct_runtime_authority(self)

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("EditorGenerationRuntimeAuthorityV1 does not support pickle")


def _runtime_values(value):
    return (
        object.__getattribute__(value, "options"),
        object.__getattribute__(value, "runtime_reference"),
        object.__getattribute__(value, "runtime_fingerprint"),
    )


def reconstruct_runtime_authority(value: object) -> EditorGenerationRuntimeAuthorityV1:
    if type(value) is not EditorGenerationRuntimeAuthorityV1:
        _raise_invalid()
    try:
        fields = _runtime_values(value)
        retained = object.__getattribute__(value, "_seal")
        rebuilt = EditorGenerationRuntimeAuthorityV1(*fields)
        if retained != object.__getattribute__(rebuilt, "_seal"):
            _raise_invalid()
        return rebuilt
    except EditorGenerationAuthorityError:
        raise
    except Exception:  # noqa: BLE001 - copied-invalid state remains private
        _raise_invalid()


__all__ = (
    "EditorGenerationApplicationRequestV1",
    "EditorGenerationRuntimeAuthorityV1",
    "EditorGenerationRuntimeOptionsV1",
)
