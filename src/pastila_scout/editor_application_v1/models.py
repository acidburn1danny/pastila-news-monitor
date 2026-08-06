"""Strict immutable contracts for the Editor application boundary."""

from __future__ import annotations

import copy
import hashlib
import json
import math
import unicodedata
from dataclasses import dataclass
from datetime import datetime
from enum import IntEnum, StrEnum
from pathlib import Path
from typing import NoReturn

from pydantic import BaseModel

from pastila_scout.contracts.episode_context import EpisodeContextV1
from pastila_scout.contracts.identity import verify_scout_input_identity
from pastila_scout.contracts.scout_editor import ScoutEditorInputV1
from pastila_scout.contracts.selection_profile import SelectionProfileV1
from pastila_scout.editor_operational_execution_v1 import (
    EditorOperationalGenerationFailureCodeV1,
    EditorOperationalGenerationStatusV1,
    EditorOperationalResultV1,
)
from pastila_scout.provider_execution_v2 import CancellationTokenV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1

from .errors import EditorApplicationConfigurationError, raise_configuration_error

_CONFIGURATION_VERSION = "editor-application-generation-config-v1"
_SHA256_PREFIX = "sha256:"
_PATH_TYPE = type(Path())


class _SafeStrEnum(StrEnum):
    def __copy__(self):
        return self

    def __deepcopy__(self, memo: dict[int, object]):
        del memo
        return self

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        name = type(self).__name__
        del self, protocol
        raise TypeError(f"{name} does not support pickle")


class _SafeIntEnum(IntEnum):
    def __copy__(self):
        return self

    def __deepcopy__(self, memo: dict[int, object]):
        del memo
        return self

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        name = type(self).__name__
        del self, protocol
        raise TypeError(f"{name} does not support pickle")


class EditorOverwritePolicyV1(_SafeStrEnum):
    FAIL_IF_EXISTS = "fail_if_exists"


class EditorApplicationStatusV1(_SafeStrEnum):
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EditorApplicationLifecycleStateV1(_SafeStrEnum):
    ACCEPTED = "accepted"
    VALIDATED = "validated"
    PREPARED = "prepared"
    EXECUTED = "executed"
    SERIALIZED = "serialized"
    EXPORTED = "exported"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class EditorApplicationFailureCodeV1(_SafeStrEnum):
    INVALID_APPLICATION_REQUEST = "invalid_application_request"
    INVALID_SCOUT_INPUT = "invalid_scout_input"
    INVALID_SELECTION_PROFILE = "invalid_selection_profile"
    INVALID_EPISODE_CONTEXT = "invalid_episode_context"
    INVALID_GENERATION_CONFIGURATION = "invalid_generation_configuration"
    PREPARATION_FAILED = "preparation_failed"
    EXECUTION_REQUEST_CONSTRUCTION_FAILED = "execution_request_construction_failed"
    OPERATIONAL_EXECUTION_FAILED = "operational_execution_failed"
    SERIALIZATION_FAILED = "serialization_failed"
    INVALID_DESTINATION = "invalid_destination"
    DESTINATION_EXISTS = "destination_exists"
    EXPORT_FAILED = "export_failed"
    EXPORT_CLEANUP_FAILED = "export_cleanup_failed"
    INTERNAL_APPLICATION_FAILURE = "internal_application_failure"
    CANCELLED = "cancelled"
    INVALID_EXECUTION_REQUEST = "invalid_execution_request"


class EditorApplicationExitCodeV1(_SafeIntEnum):
    COMPLETED = 0
    INVALID_INPUT = 2
    EXECUTION_FAILED = 3
    TIMEOUT = 4
    CANCELLED = 5
    OUTPUT_FAILED = 6
    CLEANUP_OR_INTERNAL_FAILURE = 7


_FAILURE_MESSAGES = {
    EditorApplicationFailureCodeV1.INVALID_APPLICATION_REQUEST: "Editor application request is invalid.",
    EditorApplicationFailureCodeV1.INVALID_SCOUT_INPUT: "Editor Scout input is invalid.",
    EditorApplicationFailureCodeV1.INVALID_SELECTION_PROFILE: "Editor selection profile is invalid.",
    EditorApplicationFailureCodeV1.INVALID_EPISODE_CONTEXT: "Editor episode context is invalid.",
    EditorApplicationFailureCodeV1.INVALID_GENERATION_CONFIGURATION: "Editor generation configuration is invalid.",
    EditorApplicationFailureCodeV1.PREPARATION_FAILED: "Editor preparation failed.",
    EditorApplicationFailureCodeV1.EXECUTION_REQUEST_CONSTRUCTION_FAILED: "Editor execution request construction failed.",
    EditorApplicationFailureCodeV1.OPERATIONAL_EXECUTION_FAILED: "Editor operational execution failed.",
    EditorApplicationFailureCodeV1.SERIALIZATION_FAILED: "Editor result serialization failed.",
    EditorApplicationFailureCodeV1.INVALID_DESTINATION: "Editor output destination is invalid.",
    EditorApplicationFailureCodeV1.DESTINATION_EXISTS: "Editor output destination already exists.",
    EditorApplicationFailureCodeV1.EXPORT_FAILED: "Editor output export failed.",
    EditorApplicationFailureCodeV1.EXPORT_CLEANUP_FAILED: "Editor output cleanup failed.",
    EditorApplicationFailureCodeV1.INTERNAL_APPLICATION_FAILURE: "Editor application execution failed.",
    EditorApplicationFailureCodeV1.CANCELLED: "Editor application execution was cancelled.",
    EditorApplicationFailureCodeV1.INVALID_EXECUTION_REQUEST: "Editor operational execution request is invalid.",
}


def _canonical(value: object) -> object:
    if value is None or type(value) in {str, int, float, bool}:
        return value
    if isinstance(value, (StrEnum, IntEnum)):
        return value.value
    if type(value) is datetime:
        return value.isoformat()
    if type(value) is _PATH_TYPE:
        return str(value)
    if type(value) is tuple:
        return [_canonical(item) for item in value]
    if type(value) is dict:
        return {str(key): _canonical(item) for key, item in value.items()}
    if isinstance(value, BaseModel):
        return _canonical(value.model_dump(mode="python", warnings=False))
    if type(value) is EditorOperationalResultV1:
        return object.__getattribute__(value, "result_fingerprint")
    if type(value) is EditorApplicationFailureV1:
        return [value.code.value, value.safe_message, value.retryable]
    raise TypeError


def _seal(values: object) -> str:
    payload = json.dumps(
        _canonical(values), ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _text(value: object, *, maximum: int = 200) -> bool:
    return (
        type(value) is str
        and bool(value)
        and value == value.strip()
        and len(value) <= maximum
        and unicodedata.is_normalized("NFC", value)
    )


def _model_copy[ModelT: BaseModel](model: type[ModelT], value: object) -> ModelT:
    if type(value) is not model:
        raise TypeError
    return model.model_validate(
        value.model_dump(mode="python", warnings=False), strict=True
    )


def _cancellation(value: object) -> CancellationTokenV2:
    return _model_copy(CancellationTokenV2, value)


def _operational(value: object) -> EditorOperationalResultV1:
    if type(value) is not EditorOperationalResultV1:
        raise TypeError
    rebuilt = copy.copy(value)
    if type(rebuilt) is not EditorOperationalResultV1:
        raise TypeError
    return rebuilt


def _pickle_error(name: str) -> NoReturn:
    raise TypeError(f"{name} does not support pickle")


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class EditorApplicationFailureV1:
    code: EditorApplicationFailureCodeV1
    safe_message: str
    retryable: bool
    _seal: str

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Editor application values cannot be subclassed")

    def __init__(self, code, safe_message, retryable=False) -> None:
        values = seal = None
        try:
            if (
                type(code) is not EditorApplicationFailureCodeV1
                or type(safe_message) is not str
                or safe_message != _FAILURE_MESSAGES[code]
                or type(retryable) is not bool
                or retryable
            ):
                raise TypeError
            values = (code, safe_message, False)
            seal = _seal(values)
        except Exception:  # noqa: BLE001 - protected values collapse here
            del self, code, safe_message, retryable, values, seal
            raise_configuration_error()
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "safe_message", safe_message)
        object.__setattr__(self, "retryable", False)
        object.__setattr__(self, "_seal", seal)

    def __repr__(self) -> str:
        valid = reconstruct_application_failure(self)
        return f"EditorApplicationFailureV1(code={valid.code.value!r})"

    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and _failure_values(
            reconstruct_application_failure(self)
        ) == _failure_values(reconstruct_application_failure(other))

    def __copy__(self):
        return reconstruct_application_failure(self)

    def __deepcopy__(self, memo: dict[int, object]):
        del memo
        return reconstruct_application_failure(self)

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        _pickle_error("EditorApplicationFailureV1")


def make_application_failure(
    code: EditorApplicationFailureCodeV1,
) -> EditorApplicationFailureV1:
    if type(code) is not EditorApplicationFailureCodeV1:
        raise_configuration_error()
    return EditorApplicationFailureV1(code, _FAILURE_MESSAGES[code], False)


def _failure_values(value: EditorApplicationFailureV1) -> tuple[object, ...]:
    return tuple(
        object.__getattribute__(value, name)
        for name in ("code", "safe_message", "retryable")
    )


def reconstruct_application_failure(value: object) -> EditorApplicationFailureV1:
    rebuilt = None
    try:
        if type(value) is not EditorApplicationFailureV1:
            raise TypeError
        rebuilt = EditorApplicationFailureV1(*_failure_values(value))
        if object.__getattribute__(value, "_seal") != object.__getattribute__(
            rebuilt, "_seal"
        ):
            raise TypeError
        return rebuilt
    except EditorApplicationConfigurationError:
        del value, rebuilt
        raise
    except Exception:  # noqa: BLE001 - copied-invalid state collapses here
        del value, rebuilt
        raise_configuration_error()


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class EditorApplicationGenerationConfigurationV1:
    contract_version: str
    provider: ProviderChoiceV1
    model_identifier: str
    model_revision: str | None
    temperature: float
    top_p: float
    max_output_tokens: int
    seed: None
    structured_output_mode: bool
    timeout_seconds: float
    _seal: str

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Editor application values cannot be subclassed")

    def __init__(
        self,
        contract_version,
        provider,
        model_identifier,
        model_revision,
        temperature,
        top_p,
        max_output_tokens,
        seed,
        structured_output_mode,
        timeout_seconds,
    ) -> None:
        values = (
            contract_version,
            provider,
            model_identifier,
            model_revision,
            temperature,
            top_p,
            max_output_tokens,
            seed,
            structured_output_mode,
            timeout_seconds,
        )
        seal = None
        try:
            if (
                contract_version != _CONFIGURATION_VERSION
                or type(contract_version) is not str
            ):
                raise TypeError
            if type(provider) is not ProviderChoiceV1:
                raise TypeError
            if not _text(model_identifier):
                raise TypeError
            if model_revision is not None and not _text(model_revision):
                raise TypeError
            if (
                type(temperature) is not float
                or not math.isfinite(temperature)
                or not 0.0 <= temperature <= 2.0
            ):
                raise TypeError
            if type(top_p) is not float or not math.isfinite(top_p) or top_p != 1.0:
                raise TypeError
            if type(max_output_tokens) is not int or max_output_tokens <= 0:
                raise TypeError
            if seed is not None:
                raise TypeError
            if type(structured_output_mode) is not bool or not structured_output_mode:
                raise TypeError
            if (
                type(timeout_seconds) is not float
                or not math.isfinite(timeout_seconds)
                or timeout_seconds <= 0.0
            ):
                raise TypeError
            seal = _seal(values)
        except Exception:  # noqa: BLE001 - protected values collapse here
            del self, values, seal, contract_version, provider, model_identifier
            del model_revision, temperature, top_p, max_output_tokens, seed
            del structured_output_mode, timeout_seconds
            raise_configuration_error()
        for name, value in zip(_GENERATION_FIELDS, values, strict=True):
            object.__setattr__(self, name, value)
        object.__setattr__(self, "_seal", seal)

    def __repr__(self) -> str:
        valid = reconstruct_generation_configuration(self)
        return (
            "EditorApplicationGenerationConfigurationV1("
            f"provider={valid.provider.value!r}, model=<redacted>)"
        )

    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and _generation_values(
            reconstruct_generation_configuration(self)
        ) == _generation_values(reconstruct_generation_configuration(other))

    def __copy__(self):
        return reconstruct_generation_configuration(self)

    def __deepcopy__(self, memo: dict[int, object]):
        del memo
        return reconstruct_generation_configuration(self)

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        _pickle_error("EditorApplicationGenerationConfigurationV1")


_GENERATION_FIELDS = (
    "contract_version",
    "provider",
    "model_identifier",
    "model_revision",
    "temperature",
    "top_p",
    "max_output_tokens",
    "seed",
    "structured_output_mode",
    "timeout_seconds",
)


def _generation_values(
    value: EditorApplicationGenerationConfigurationV1,
) -> tuple[object, ...]:
    return tuple(object.__getattribute__(value, name) for name in _GENERATION_FIELDS)


def reconstruct_generation_configuration(
    value: object,
) -> EditorApplicationGenerationConfigurationV1:
    rebuilt = None
    try:
        if type(value) is not EditorApplicationGenerationConfigurationV1:
            raise TypeError
        rebuilt = EditorApplicationGenerationConfigurationV1(*_generation_values(value))
        if object.__getattribute__(value, "_seal") != object.__getattribute__(
            rebuilt, "_seal"
        ):
            raise TypeError
        return rebuilt
    except EditorApplicationConfigurationError:
        del value, rebuilt
        raise
    except Exception:  # noqa: BLE001 - copied-invalid state collapses here
        del value, rebuilt
        raise_configuration_error()


def _lexical_destination(path: object) -> Path:
    if type(path) is not _PATH_TYPE or not path.is_absolute():
        raise TypeError
    raw = str(path)
    lowered = raw.lower()
    if (
        not raw
        or "://" in raw
        or lowered.startswith(("http:", "https:", "ftp:", "file:"))
        or raw.startswith(("\\\\", "//", "\\\\?\\", "\\\\.\\"))
    ):
        raise TypeError
    reserved = {"CON", "PRN", "AUX", "NUL", "CLOCK$"}
    reserved.update(
        f"{prefix}{number}" for prefix in ("COM", "LPT") for number in range(1, 10)
    )
    if any(part.split(".", 1)[0].upper() in reserved for part in path.parts):
        raise TypeError
    return Path(raw)


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class EditorOutputDestinationV1:
    path: Path
    overwrite_policy: EditorOverwritePolicyV1
    _seal: str

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Editor application values cannot be subclassed")

    def __init__(self, path, overwrite_policy) -> None:
        rebuilt_path = seal = None
        try:
            rebuilt_path = _lexical_destination(path)
            if type(overwrite_policy) is not EditorOverwritePolicyV1:
                raise TypeError
            seal = _seal((rebuilt_path, overwrite_policy))
        except Exception:  # noqa: BLE001 - protected values collapse here
            del self, path, overwrite_policy, rebuilt_path, seal
            raise_configuration_error()
        object.__setattr__(self, "path", rebuilt_path)
        object.__setattr__(self, "overwrite_policy", overwrite_policy)
        object.__setattr__(self, "_seal", seal)

    def __repr__(self) -> str:
        reconstruct_output_destination(self)
        return "EditorOutputDestinationV1(path=<redacted>, overwrite_policy='fail_if_exists')"

    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and _destination_values(
            reconstruct_output_destination(self)
        ) == _destination_values(reconstruct_output_destination(other))

    def __copy__(self):
        return reconstruct_output_destination(self)

    def __deepcopy__(self, memo: dict[int, object]):
        del memo
        return reconstruct_output_destination(self)

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        _pickle_error("EditorOutputDestinationV1")


def _destination_values(value: EditorOutputDestinationV1) -> tuple[object, ...]:
    return (
        object.__getattribute__(value, "path"),
        object.__getattribute__(value, "overwrite_policy"),
    )


def reconstruct_output_destination(value: object) -> EditorOutputDestinationV1:
    rebuilt = None
    try:
        if type(value) is not EditorOutputDestinationV1:
            raise TypeError
        rebuilt = EditorOutputDestinationV1(*_destination_values(value))
        if object.__getattribute__(value, "_seal") != object.__getattribute__(
            rebuilt, "_seal"
        ):
            raise TypeError
        return rebuilt
    except EditorApplicationConfigurationError:
        del value, rebuilt
        raise
    except Exception:  # noqa: BLE001 - copied-invalid state collapses here
        del value, rebuilt
        raise_configuration_error()


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class EditorApplicationRequestV1:
    scout_input: ScoutEditorInputV1
    selection_profile: SelectionProfileV1
    episode_context: EpisodeContextV1
    generation_configuration: EditorApplicationGenerationConfigurationV1
    destination: EditorOutputDestinationV1
    requested_at: datetime
    operation_reference: str
    cancellation: CancellationTokenV2
    _seal: str

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Editor application values cannot be subclassed")

    def __init__(
        self,
        scout_input,
        selection_profile,
        episode_context,
        generation_configuration,
        destination,
        requested_at,
        operation_reference,
        cancellation,
    ) -> None:
        source = profile = context = configuration = None
        valid_destination = valid_cancellation = values = seal = None
        try:
            source = _model_copy(ScoutEditorInputV1, scout_input)
            verify_scout_input_identity(source)
            profile = _model_copy(SelectionProfileV1, selection_profile)
            context = _model_copy(EpisodeContextV1, episode_context)
            configuration = reconstruct_generation_configuration(
                generation_configuration
            )
            valid_destination = reconstruct_output_destination(destination)
            if type(requested_at) is not datetime or requested_at.tzinfo is None:
                raise TypeError
            if requested_at.utcoffset() is None:
                raise TypeError
            if not _text(operation_reference, maximum=120):
                raise TypeError
            valid_cancellation = _cancellation(cancellation)
            _validate_request_lineage(source, profile, context)
            values = (
                source,
                profile,
                context,
                configuration,
                valid_destination,
                requested_at,
                operation_reference,
                valid_cancellation,
            )
            seal = _seal(_request_seal_values(values))
        except Exception:  # noqa: BLE001 - protected values collapse here
            del self, scout_input, selection_profile, episode_context
            del generation_configuration, destination, requested_at
            del operation_reference, cancellation
            del source, profile, context, configuration, valid_destination
            del valid_cancellation, values, seal
            raise_configuration_error()
        for name, value in zip(_REQUEST_FIELDS, values, strict=True):
            object.__setattr__(self, name, value)
        object.__setattr__(self, "_seal", seal)

    def __repr__(self) -> str:
        valid = reconstruct_application_request(self)
        return (
            "EditorApplicationRequestV1("
            f"operation_reference={valid.operation_reference!r}, content=<redacted>, path=<redacted>)"
        )

    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and _request_values(
            reconstruct_application_request(self)
        ) == _request_values(reconstruct_application_request(other))

    def __copy__(self):
        return reconstruct_application_request(self)

    def __deepcopy__(self, memo: dict[int, object]):
        del memo
        return reconstruct_application_request(self)

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        _pickle_error("EditorApplicationRequestV1")


_REQUEST_FIELDS = (
    "scout_input",
    "selection_profile",
    "episode_context",
    "generation_configuration",
    "destination",
    "requested_at",
    "operation_reference",
    "cancellation",
)


def _request_values(value: EditorApplicationRequestV1) -> tuple[object, ...]:
    return tuple(object.__getattribute__(value, name) for name in _REQUEST_FIELDS)


def _request_seal_values(values: tuple[object, ...]) -> tuple[object, ...]:
    (
        source,
        profile,
        context,
        configuration,
        destination,
        requested_at,
        reference,
        token,
    ) = values
    return (
        source.model_dump(mode="python", warnings=False),
        profile.model_dump(mode="python", warnings=False),
        context.model_dump(mode="python", warnings=False),
        _generation_values(configuration),
        _destination_values(destination),
        requested_at,
        reference,
        token.model_dump(mode="python", warnings=False),
    )


def _validate_request_lineage(
    source: ScoutEditorInputV1,
    profile: SelectionProfileV1,
    context: EpisodeContextV1,
) -> None:
    if profile.target_story_count != context.target_story_count:
        raise TypeError
    event_ids = {item.event_id for item in source.ranked_events}
    if any(item not in event_ids for item in context.mandatory_event_ids):
        raise TypeError


def reconstruct_application_request(value: object) -> EditorApplicationRequestV1:
    rebuilt = None
    try:
        if type(value) is not EditorApplicationRequestV1:
            raise TypeError
        rebuilt = EditorApplicationRequestV1(*_request_values(value))
        if object.__getattribute__(value, "_seal") != object.__getattribute__(
            rebuilt, "_seal"
        ):
            raise TypeError
        return rebuilt
    except EditorApplicationConfigurationError:
        del value, rebuilt
        raise
    except Exception:  # noqa: BLE001 - copied-invalid state collapses here
        del value, rebuilt
        raise_configuration_error()


_ACCEPTED_FAILED = (
    EditorApplicationLifecycleStateV1.ACCEPTED,
    EditorApplicationLifecycleStateV1.FAILED,
)
_VALIDATED_FAILED = (
    EditorApplicationLifecycleStateV1.ACCEPTED,
    EditorApplicationLifecycleStateV1.VALIDATED,
    EditorApplicationLifecycleStateV1.FAILED,
)
_PREPARED_FAILED = (
    EditorApplicationLifecycleStateV1.ACCEPTED,
    EditorApplicationLifecycleStateV1.VALIDATED,
    EditorApplicationLifecycleStateV1.PREPARED,
    EditorApplicationLifecycleStateV1.FAILED,
)
_EXECUTED_FAILED = (
    EditorApplicationLifecycleStateV1.ACCEPTED,
    EditorApplicationLifecycleStateV1.VALIDATED,
    EditorApplicationLifecycleStateV1.PREPARED,
    EditorApplicationLifecycleStateV1.EXECUTED,
    EditorApplicationLifecycleStateV1.FAILED,
)
_SERIALIZED_FAILED = (
    EditorApplicationLifecycleStateV1.ACCEPTED,
    EditorApplicationLifecycleStateV1.VALIDATED,
    EditorApplicationLifecycleStateV1.PREPARED,
    EditorApplicationLifecycleStateV1.EXECUTED,
    EditorApplicationLifecycleStateV1.SERIALIZED,
    EditorApplicationLifecycleStateV1.FAILED,
)
_INITIAL_CANCELLED = (
    EditorApplicationLifecycleStateV1.ACCEPTED,
    EditorApplicationLifecycleStateV1.VALIDATED,
    EditorApplicationLifecycleStateV1.CANCELLED,
)
_EXECUTED_CANCELLED = (
    EditorApplicationLifecycleStateV1.ACCEPTED,
    EditorApplicationLifecycleStateV1.VALIDATED,
    EditorApplicationLifecycleStateV1.PREPARED,
    EditorApplicationLifecycleStateV1.EXECUTED,
    EditorApplicationLifecycleStateV1.CANCELLED,
)
_COMPLETED = (
    EditorApplicationLifecycleStateV1.ACCEPTED,
    EditorApplicationLifecycleStateV1.VALIDATED,
    EditorApplicationLifecycleStateV1.PREPARED,
    EditorApplicationLifecycleStateV1.EXECUTED,
    EditorApplicationLifecycleStateV1.SERIALIZED,
    EditorApplicationLifecycleStateV1.EXPORTED,
    EditorApplicationLifecycleStateV1.COMPLETED,
)


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class EditorApplicationResultV1:
    operation_reference: str | None
    status: EditorApplicationStatusV1
    lifecycle: tuple[EditorApplicationLifecycleStateV1, ...]
    operational_result: EditorOperationalResultV1 | None
    output_path: Path | None
    payload_sha256: str | None
    exported: bool
    handoff_permitted: bool
    failure: EditorApplicationFailureV1 | None
    exit_code: EditorApplicationExitCodeV1
    _seal: str

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Editor application values cannot be subclassed")

    def __init__(
        self,
        operation_reference,
        status,
        lifecycle,
        operational_result,
        output_path,
        payload_sha256,
        exported,
        handoff_permitted,
        failure,
        exit_code,
    ) -> None:
        values = (
            operation_reference,
            status,
            lifecycle,
            operational_result,
            output_path,
            payload_sha256,
            exported,
            handoff_permitted,
            failure,
            exit_code,
        )
        rebuilt = seal = None
        try:
            rebuilt = _validated_result(values)
            seal = _seal(_result_seal_values(rebuilt))
        except Exception:  # noqa: BLE001 - protected values collapse here
            del self, values, operation_reference, status, lifecycle
            del operational_result, output_path, payload_sha256, exported
            del handoff_permitted, failure, exit_code
            del rebuilt, seal
            raise_configuration_error()
        for name, value in zip(_RESULT_FIELDS, rebuilt, strict=True):
            object.__setattr__(self, name, value)
        object.__setattr__(self, "_seal", seal)

    def __repr__(self) -> str:
        valid = reconstruct_application_result(self)
        code = valid.failure.code.value if valid.failure else "none"
        return (
            "EditorApplicationResultV1("
            f"status={valid.status.value!r}, failure_code={code!r})"
        )

    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and _result_values(
            reconstruct_application_result(self)
        ) == _result_values(reconstruct_application_result(other))

    def __copy__(self):
        return reconstruct_application_result(self)

    def __deepcopy__(self, memo: dict[int, object]):
        del memo
        return reconstruct_application_result(self)

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        _pickle_error("EditorApplicationResultV1")


_RESULT_FIELDS = (
    "operation_reference",
    "status",
    "lifecycle",
    "operational_result",
    "output_path",
    "payload_sha256",
    "exported",
    "handoff_permitted",
    "failure",
    "exit_code",
)


def _result_values(value: EditorApplicationResultV1) -> tuple[object, ...]:
    return tuple(object.__getattribute__(value, name) for name in _RESULT_FIELDS)


def _result_seal_values(values: tuple[object, ...]) -> tuple[object, ...]:
    return values


def _valid_hash(value: object) -> bool:
    return (
        type(value) is str
        and value.startswith(_SHA256_PREFIX)
        and len(value) == len(_SHA256_PREFIX) + 64
        and all(character in "0123456789abcdef" for character in value[7:])
    )


def _validated_result(values: tuple[object, ...]) -> tuple[object, ...]:
    (
        reference,
        status,
        lifecycle,
        operational,
        output,
        checksum,
        exported,
        handoff,
        failure,
        exit_code,
    ) = values
    if reference is not None and not _text(reference, maximum=120):
        raise TypeError
    if (
        type(status) is not EditorApplicationStatusV1
        or type(lifecycle) is not tuple
        or not lifecycle
        or any(
            type(item) is not EditorApplicationLifecycleStateV1 for item in lifecycle
        )
        or len(set(lifecycle)) != len(lifecycle)
        or type(exported) is not bool
        or type(handoff) is not bool
        or type(exit_code) is not EditorApplicationExitCodeV1
    ):
        raise TypeError
    valid_operational = None if operational is None else _operational(operational)
    valid_failure = (
        None if failure is None else reconstruct_application_failure(failure)
    )
    if (
        valid_operational is not None
        and reference != valid_operational.execution_request_reference
    ):
        raise TypeError
    if status is EditorApplicationStatusV1.COMPLETED:
        if (
            reference is None
            or lifecycle != _COMPLETED
            or valid_operational is None
            or valid_operational.status
            is not EditorOperationalGenerationStatusV1.COMPLETED
            or type(output) is not _PATH_TYPE
            or not output.is_absolute()
            or not _valid_hash(checksum)
            or not exported
            or not handoff
            or valid_failure is not None
            or exit_code is not EditorApplicationExitCodeV1.COMPLETED
        ):
            raise TypeError
        return (
            reference,
            status,
            lifecycle,
            valid_operational,
            Path(str(output)),
            checksum,
            True,
            True,
            None,
            exit_code,
        )
    if output is not None or checksum is not None or exported or handoff:
        raise TypeError
    if valid_failure is None:
        raise TypeError
    code = valid_failure.code
    if status is EditorApplicationStatusV1.CANCELLED:
        if code is not EditorApplicationFailureCodeV1.CANCELLED:
            raise TypeError
        if valid_operational is None:
            if lifecycle != _INITIAL_CANCELLED:
                raise TypeError
        elif (
            lifecycle != _EXECUTED_CANCELLED
            or valid_operational.status
            is not EditorOperationalGenerationStatusV1.CANCELLED
        ):
            raise TypeError
        if reference is None or exit_code is not EditorApplicationExitCodeV1.CANCELLED:
            raise TypeError
    elif status is EditorApplicationStatusV1.FAILED:
        _validate_failed_result(
            reference, lifecycle, valid_operational, code, exit_code
        )
    else:
        raise TypeError
    return (
        reference,
        status,
        lifecycle,
        valid_operational,
        None,
        None,
        False,
        False,
        valid_failure,
        exit_code,
    )


def _validate_failed_result(reference, lifecycle, operational, code, exit_code) -> None:
    invalid_codes = {
        EditorApplicationFailureCodeV1.INVALID_APPLICATION_REQUEST,
        EditorApplicationFailureCodeV1.INVALID_SCOUT_INPUT,
        EditorApplicationFailureCodeV1.INVALID_SELECTION_PROFILE,
        EditorApplicationFailureCodeV1.INVALID_EPISODE_CONTEXT,
        EditorApplicationFailureCodeV1.INVALID_GENERATION_CONFIGURATION,
    }
    if code in invalid_codes:
        valid = (
            reference is None
            and lifecycle == _ACCEPTED_FAILED
            and operational is None
            and exit_code is EditorApplicationExitCodeV1.INVALID_INPUT
        )
    elif code is EditorApplicationFailureCodeV1.INVALID_DESTINATION:
        if lifecycle == _ACCEPTED_FAILED:
            valid = reference is None and operational is None
        elif lifecycle == _VALIDATED_FAILED:
            valid = reference is not None and operational is None
        elif lifecycle == _SERIALIZED_FAILED:
            valid = (
                reference is not None
                and operational is not None
                and operational.status is EditorOperationalGenerationStatusV1.COMPLETED
            )
        else:
            valid = False
        valid = valid and exit_code is EditorApplicationExitCodeV1.INVALID_INPUT
    elif code is EditorApplicationFailureCodeV1.DESTINATION_EXISTS:
        if lifecycle == _VALIDATED_FAILED:
            valid = reference is not None and operational is None
        elif lifecycle == _SERIALIZED_FAILED:
            valid = (
                reference is not None
                and operational is not None
                and operational.status is EditorOperationalGenerationStatusV1.COMPLETED
            )
        else:
            valid = False
        valid = valid and exit_code is EditorApplicationExitCodeV1.INVALID_INPUT
    elif code is EditorApplicationFailureCodeV1.PREPARATION_FAILED:
        valid = (
            reference is not None
            and lifecycle == _VALIDATED_FAILED
            and operational is None
            and exit_code is EditorApplicationExitCodeV1.EXECUTION_FAILED
        )
    elif code is EditorApplicationFailureCodeV1.EXECUTION_REQUEST_CONSTRUCTION_FAILED:
        valid = (
            reference is not None
            and lifecycle == _PREPARED_FAILED
            and operational is None
            and exit_code is EditorApplicationExitCodeV1.EXECUTION_FAILED
        )
    elif code is EditorApplicationFailureCodeV1.OPERATIONAL_EXECUTION_FAILED:
        valid = _operational_failure_is_valid(
            reference, lifecycle, operational, exit_code
        )
    elif code is EditorApplicationFailureCodeV1.INVALID_EXECUTION_REQUEST:
        valid = (
            reference is not None
            and lifecycle == _EXECUTED_FAILED
            and operational is None
            and exit_code is EditorApplicationExitCodeV1.EXECUTION_FAILED
        )
    elif code is EditorApplicationFailureCodeV1.SERIALIZATION_FAILED:
        valid = (
            reference is not None
            and lifecycle == _EXECUTED_FAILED
            and operational is not None
            and operational.status is EditorOperationalGenerationStatusV1.COMPLETED
            and exit_code is EditorApplicationExitCodeV1.OUTPUT_FAILED
        )
    elif code in {
        EditorApplicationFailureCodeV1.EXPORT_FAILED,
        EditorApplicationFailureCodeV1.EXPORT_CLEANUP_FAILED,
        EditorApplicationFailureCodeV1.INTERNAL_APPLICATION_FAILURE,
    }:
        expected_exit = (
            EditorApplicationExitCodeV1.OUTPUT_FAILED
            if code is EditorApplicationFailureCodeV1.EXPORT_FAILED
            else EditorApplicationExitCodeV1.CLEANUP_OR_INTERNAL_FAILURE
        )
        valid = (
            reference is not None
            and lifecycle == _SERIALIZED_FAILED
            and operational is not None
            and operational.status is EditorOperationalGenerationStatusV1.COMPLETED
            and exit_code is expected_exit
        )
    else:
        valid = False
    if not valid:
        raise TypeError


def _operational_failure_is_valid(reference, lifecycle, operational, exit_code) -> bool:
    if (
        reference is None
        or lifecycle != _EXECUTED_FAILED
        or operational is None
        or operational.status is not EditorOperationalGenerationStatusV1.FAILED
        or operational.failure is None
    ):
        return False
    lower_code = operational.failure.code
    if lower_code is EditorOperationalGenerationFailureCodeV1.TIMEOUT_EXHAUSTED:
        return exit_code is EditorApplicationExitCodeV1.TIMEOUT
    if lower_code is EditorOperationalGenerationFailureCodeV1.CLEANUP_FAILED:
        return exit_code is EditorApplicationExitCodeV1.CLEANUP_OR_INTERNAL_FAILURE
    return exit_code is EditorApplicationExitCodeV1.EXECUTION_FAILED


def reconstruct_application_result(value: object) -> EditorApplicationResultV1:
    rebuilt = None
    try:
        if type(value) is not EditorApplicationResultV1:
            raise TypeError
        rebuilt = EditorApplicationResultV1(*_result_values(value))
        if object.__getattribute__(value, "_seal") != object.__getattribute__(
            rebuilt, "_seal"
        ):
            raise TypeError
        return rebuilt
    except EditorApplicationConfigurationError:
        del value, rebuilt
        raise
    except Exception:  # noqa: BLE001 - copied-invalid state collapses here
        del value, rebuilt
        raise_configuration_error()


__all__ = (
    "EditorApplicationExitCodeV1",
    "EditorApplicationFailureCodeV1",
    "EditorApplicationFailureV1",
    "EditorApplicationGenerationConfigurationV1",
    "EditorApplicationLifecycleStateV1",
    "EditorApplicationRequestV1",
    "EditorApplicationResultV1",
    "EditorApplicationStatusV1",
    "EditorOutputDestinationV1",
    "EditorOverwritePolicyV1",
)
