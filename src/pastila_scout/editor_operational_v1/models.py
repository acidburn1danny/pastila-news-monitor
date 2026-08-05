"""Strict immutable contracts for deterministic Editor preparation."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from enum import Enum, StrEnum
from typing import Any, NoReturn

from pydantic import BaseModel

from pastila_scout.contracts.common import ContractStatus
from pastila_scout.contracts.editor_output import (
    EditorAgentOutputV1,
    validate_editor_output_against_input,
)
from pastila_scout.contracts.episode_context import EpisodeContextV1
from pastila_scout.contracts.identity import verify_scout_input_identity
from pastila_scout.contracts.scout_editor import ScoutEditorInputV1
from pastila_scout.contracts.selection_profile import SelectionProfileV1
from pastila_scout.editor.models import DecisionTrace


class EditorOperationalLifecycleStateV1(StrEnum):
    ACCEPTED = "accepted"
    VALIDATED = "validated"
    SELECTED = "selected"
    PLANNED = "planned"
    FAILED = "failed"


class EditorOperationalFailureCodeV1(StrEnum):
    INVALID_INPUT = "editor_operational_invalid_input"
    SELECTION_FAILED = "editor_operational_selection_failed"
    INVALID_SELECTION_RESULT = "editor_operational_invalid_selection_result"
    PLAN_CONSTRUCTION_FAILED = "editor_operational_plan_construction_failed"


_FAILURE_MESSAGES = {
    EditorOperationalFailureCodeV1.INVALID_INPUT: (
        "Editor operational input is invalid."
    ),
    EditorOperationalFailureCodeV1.SELECTION_FAILED: (
        "Editor deterministic selection failed."
    ),
    EditorOperationalFailureCodeV1.INVALID_SELECTION_RESULT: (
        "Editor deterministic selection returned an invalid result."
    ),
    EditorOperationalFailureCodeV1.PLAN_CONSTRUCTION_FAILED: (
        "Editor generation plan construction failed."
    ),
}

_SUCCESS_LIFECYCLE = (
    EditorOperationalLifecycleStateV1.ACCEPTED,
    EditorOperationalLifecycleStateV1.VALIDATED,
    EditorOperationalLifecycleStateV1.SELECTED,
    EditorOperationalLifecycleStateV1.PLANNED,
)
_INVALID_INPUT_LIFECYCLE = (
    EditorOperationalLifecycleStateV1.ACCEPTED,
    EditorOperationalLifecycleStateV1.FAILED,
)
_SELECTION_FAILED_LIFECYCLE = (
    EditorOperationalLifecycleStateV1.ACCEPTED,
    EditorOperationalLifecycleStateV1.VALIDATED,
    EditorOperationalLifecycleStateV1.FAILED,
)
_POST_SELECTION_FAILED_LIFECYCLE = (
    EditorOperationalLifecycleStateV1.ACCEPTED,
    EditorOperationalLifecycleStateV1.VALIDATED,
    EditorOperationalLifecycleStateV1.SELECTED,
    EditorOperationalLifecycleStateV1.FAILED,
)
_PLAN_FIELD_NAMES = (
    "source_input",
    "selection_profile",
    "episode_context",
    "selection_output",
    "selection_trace",
    "source_report_id",
    "source_report_fingerprint",
    "selected_event_ids",
    "backup_event_ids",
    "rejected_event_ids",
)


def _canonical(value: Any) -> Any:
    if isinstance(value, BaseModel):
        return _canonical(value.model_dump(mode="json", warnings=False))
    if isinstance(value, Enum):
        return value.value
    if value is None or type(value) in {bool, int, float, str}:
        return value
    if type(value) is tuple:
        return [_canonical(item) for item in value]
    if type(value) is list:
        return [_canonical(item) for item in value]
    if type(value) is dict:
        return {str(key): _canonical(item) for key, item in value.items()}
    raise TypeError("unsupported Editor operational canonical value")


def _seal(values: dict[str, Any]) -> str:
    payload = json.dumps(
        _canonical(values),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _strict_model(model: type[BaseModel], value: object) -> BaseModel:
    if type(value) is not model:
        raise TypeError("invalid Editor operational model")
    return model.model_validate(
        value.model_dump(mode="python", warnings=False), strict=True
    )


def _exact_ids(value: object) -> tuple[int, ...]:
    if type(value) is not tuple or any(
        type(item) is not int or item <= 0 for item in value
    ):
        raise TypeError("invalid Editor operational identifiers")
    if len(value) != len(set(value)):
        raise ValueError("duplicate Editor operational identifiers")
    return value


def _validated_plan_state(*values: object) -> dict[str, Any] | None:
    try:
        (
            source_input,
            selection_profile,
            episode_context,
            selection_output,
            selection_trace,
            source_report_id,
            source_report_fingerprint,
            selected_event_ids,
            backup_event_ids,
            rejected_event_ids,
        ) = values
        source = _strict_model(ScoutEditorInputV1, source_input)
        profile = _strict_model(SelectionProfileV1, selection_profile)
        context = _strict_model(EpisodeContextV1, episode_context)
        output = _strict_model(EditorAgentOutputV1, selection_output)
        trace = _strict_model(DecisionTrace, selection_trace)
        verify_scout_input_identity(source)
        if type(source_report_id) is not str or source_report_id != source.report_id:
            return None
        if (
            type(source_report_fingerprint) is not str
            or source_report_fingerprint != source.content_fingerprint
        ):
            return None
        selected = _exact_ids(selected_event_ids)
        backups = _exact_ids(backup_event_ids)
        rejected = _exact_ids(rejected_event_ids)
        if selected != trace.selected_event_ids or backups != trace.backup_event_ids:
            return None
        if rejected != trace.rejected_event_ids or set(selected).intersection(backups):
            return None
        source_ids = {item.event_id for item in source.ranked_events}
        if not {*selected, *backups, *rejected}.issubset(source_ids):
            return None
        validate_editor_output_against_input(
            output,
            source,
            selection_profile=profile,
            episode_context=context,
        )
        if (
            output.status is not ContractStatus.SUCCESS
            or output.episode_proposal is None
        ):
            return None
        proposal_selected = tuple(
            item.event_id for item in output.episode_proposal.selected_stories
        )
        proposal_backups = tuple(
            item.event_id for item in output.episode_proposal.backup_stories
        )
        if proposal_selected != selected or proposal_backups != backups:
            return None
        return {
            "source_input": source,
            "selection_profile": profile,
            "episode_context": context,
            "selection_output": output,
            "selection_trace": trace,
            "source_report_id": source_report_id,
            "source_report_fingerprint": source_report_fingerprint,
            "selected_event_ids": selected,
            "backup_event_ids": backups,
            "rejected_event_ids": rejected,
        }
    except Exception:  # noqa: BLE001 - all invalid detail remains private
        return None


def _raise_invalid_plan() -> NoReturn:
    error = ValueError("invalid Editor generation plan")
    error.__suppress_context__ = True
    raise error from None


@dataclass(frozen=True, slots=True, init=False, repr=False)
class EditorOperationalFailureV1:
    code: EditorOperationalFailureCodeV1
    safe_message: str
    retryable: bool
    _seal: str

    def __init__(
        self,
        code: EditorOperationalFailureCodeV1,
        safe_message: str,
        retryable: bool = False,
    ) -> None:
        if (
            type(code) is not EditorOperationalFailureCodeV1
            or type(safe_message) is not str
            or safe_message != _FAILURE_MESSAGES.get(code)
            or type(retryable) is not bool
            or retryable
        ):
            del self, code, safe_message, retryable
            _raise_invalid_failure()
        object.__setattr__(self, "code", code)
        object.__setattr__(self, "safe_message", safe_message)
        object.__setattr__(self, "retryable", retryable)
        object.__setattr__(
            self,
            "_seal",
            _seal(
                {
                    "code": code,
                    "safe_message": safe_message,
                    "retryable": retryable,
                }
            ),
        )

    def __repr__(self) -> str:
        valid = reconstruct_failure(self)
        return f"EditorOperationalFailureV1(code={valid.code!r}, retryable=False)"

    def __eq__(self, other: object) -> bool:
        valid = reconstruct_failure(self)
        if type(other) is not EditorOperationalFailureV1:
            return False
        candidate = reconstruct_failure(other)
        return (
            valid.code,
            valid.safe_message,
            valid.retryable,
        ) == (candidate.code, candidate.safe_message, candidate.retryable)

    def __copy__(self) -> EditorOperationalFailureV1:
        return reconstruct_failure(self)

    def __deepcopy__(self, memo: dict[int, object]) -> EditorOperationalFailureV1:
        del memo
        return reconstruct_failure(self)

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("EditorOperationalFailureV1 does not support pickle")


@dataclass(frozen=True, slots=True, init=False, repr=False)
class EditorGenerationPlanV1:
    source_input: ScoutEditorInputV1
    selection_profile: SelectionProfileV1
    episode_context: EpisodeContextV1
    selection_output: EditorAgentOutputV1
    selection_trace: DecisionTrace
    source_report_id: str
    source_report_fingerprint: str
    selected_event_ids: tuple[int, ...]
    backup_event_ids: tuple[int, ...]
    rejected_event_ids: tuple[int, ...]
    _seal: str

    def __init__(
        self,
        source_input: ScoutEditorInputV1,
        selection_profile: SelectionProfileV1,
        episode_context: EpisodeContextV1,
        selection_output: EditorAgentOutputV1,
        selection_trace: DecisionTrace,
        source_report_id: str,
        source_report_fingerprint: str,
        selected_event_ids: tuple[int, ...],
        backup_event_ids: tuple[int, ...],
        rejected_event_ids: tuple[int, ...],
    ) -> None:
        values = _validated_plan_state(
            source_input,
            selection_profile,
            episode_context,
            selection_output,
            selection_trace,
            source_report_id,
            source_report_fingerprint,
            selected_event_ids,
            backup_event_ids,
            rejected_event_ids,
        )
        if values is None:
            del self, source_input, selection_profile, episode_context
            del selection_output, selection_trace, source_report_id
            del source_report_fingerprint, selected_event_ids, backup_event_ids
            del rejected_event_ids, values
            _raise_invalid_plan()
        for name, value in values.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "_seal", _seal(values))

    def __repr__(self) -> str:
        valid = reconstruct_plan(self)
        return (
            "EditorGenerationPlanV1("
            f"selected={len(valid.selected_event_ids)}, "
            f"backups={len(valid.backup_event_ids)}, "
            f"rejected={len(valid.rejected_event_ids)})"
        )

    def __eq__(self, other: object) -> bool:
        valid = reconstruct_plan(self)
        if type(other) is not EditorGenerationPlanV1:
            return False
        candidate = reconstruct_plan(other)
        return _plan_values(valid) == _plan_values(candidate)

    def __copy__(self) -> EditorGenerationPlanV1:
        return reconstruct_plan(self)

    def __deepcopy__(self, memo: dict[int, object]) -> EditorGenerationPlanV1:
        del memo
        return reconstruct_plan(self)

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("EditorGenerationPlanV1 does not support pickle")


def _validated_result_state(*items: object) -> dict[str, Any] | None:
    try:
        source_report_id, source_report_fingerprint, lifecycle, plan, failure = items
        if (
            type(source_report_id) is not str
            or type(source_report_fingerprint) is not str
        ):
            return None
        if type(lifecycle) is not tuple or any(
            type(item) is not EditorOperationalLifecycleStateV1 for item in lifecycle
        ):
            return None
        valid_plan = (
            reconstruct_plan(plan) if type(plan) is EditorGenerationPlanV1 else None
        )
        valid_failure = (
            reconstruct_failure(failure)
            if type(failure) is EditorOperationalFailureV1
            else None
        )
        if lifecycle == _SUCCESS_LIFECYCLE:
            if valid_plan is None or failure is not None:
                return None
            if (
                source_report_id != valid_plan.source_report_id
                or source_report_fingerprint != valid_plan.source_report_fingerprint
            ):
                return None
        else:
            expected = _failures_for_lifecycle(lifecycle)
            if (
                plan is not None
                or valid_failure is None
                or valid_failure.code not in expected
            ):
                return None
            if valid_failure.code is EditorOperationalFailureCodeV1.INVALID_INPUT:
                if source_report_id or source_report_fingerprint:
                    return None
            elif not source_report_id or not source_report_fingerprint:
                return None
        return {
            "source_report_id": source_report_id,
            "source_report_fingerprint": source_report_fingerprint,
            "lifecycle": lifecycle,
            "plan": valid_plan,
            "failure": valid_failure,
        }
    except Exception:  # noqa: BLE001 - all invalid detail remains private
        return None


def _result_seal_values(values: dict[str, Any]) -> dict[str, Any]:
    valid_plan = values["plan"]
    valid_failure = values["failure"]
    return {
        "source_report_id": values["source_report_id"],
        "source_report_fingerprint": values["source_report_fingerprint"],
        "lifecycle": values["lifecycle"],
        "plan": (
            dict(zip(_PLAN_FIELD_NAMES, _plan_values(valid_plan), strict=True))
            if valid_plan is not None
            else None
        ),
        "failure": (
            {
                "code": valid_failure.code,
                "safe_message": valid_failure.safe_message,
                "retryable": valid_failure.retryable,
            }
            if valid_failure is not None
            else None
        ),
    }


def _raise_invalid_result() -> NoReturn:
    error = ValueError("invalid Editor operational preparation result")
    error.__suppress_context__ = True
    raise error from None


@dataclass(frozen=True, slots=True, init=False, repr=False)
class EditorOperationalPreparationResultV1:
    source_report_id: str
    source_report_fingerprint: str
    lifecycle: tuple[EditorOperationalLifecycleStateV1, ...]
    plan: EditorGenerationPlanV1 | None
    failure: EditorOperationalFailureV1 | None
    _seal: str

    def __init__(
        self,
        source_report_id: str,
        source_report_fingerprint: str,
        lifecycle: tuple[EditorOperationalLifecycleStateV1, ...],
        plan: EditorGenerationPlanV1 | None,
        failure: EditorOperationalFailureV1 | None,
    ) -> None:
        values = _validated_result_state(
            source_report_id,
            source_report_fingerprint,
            lifecycle,
            plan,
            failure,
        )
        if values is None:
            del self, source_report_id, source_report_fingerprint, lifecycle
            del plan, failure, values
            _raise_invalid_result()
        for name, value in values.items():
            object.__setattr__(self, name, value)
        object.__setattr__(self, "_seal", _seal(_result_seal_values(values)))

    def __repr__(self) -> str:
        valid = reconstruct_preparation_result(self)
        terminal = valid.lifecycle[-1]
        code = valid.failure.code.value if valid.failure is not None else "none"
        return (
            "EditorOperationalPreparationResultV1("
            f"terminal={terminal.value!r}, failure_code={code!r})"
        )

    def __eq__(self, other: object) -> bool:
        valid = reconstruct_preparation_result(self)
        if type(other) is not EditorOperationalPreparationResultV1:
            return False
        candidate = reconstruct_preparation_result(other)
        return _result_values(valid) == _result_values(candidate)

    def __copy__(self) -> EditorOperationalPreparationResultV1:
        return reconstruct_preparation_result(self)

    def __deepcopy__(
        self, memo: dict[int, object]
    ) -> EditorOperationalPreparationResultV1:
        del memo
        return reconstruct_preparation_result(self)

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("EditorOperationalPreparationResultV1 does not support pickle")


def reconstruct_failure(value: object) -> EditorOperationalFailureV1:
    if type(value) is not EditorOperationalFailureV1:
        del value
        _raise_invalid_failure()
    try:
        code = object.__getattribute__(value, "code")
        message = object.__getattribute__(value, "safe_message")
        retryable = object.__getattribute__(value, "retryable")
        retained = object.__getattribute__(value, "_seal")
    except AttributeError:
        del value
        _raise_invalid_failure()
    try:
        rebuilt = EditorOperationalFailureV1(code, message, retryable)
    except Exception:  # noqa: BLE001 - copied-invalid state remains private
        del value, code, message, retryable, retained
        _raise_invalid_failure()
    if retained != object.__getattribute__(rebuilt, "_seal"):
        del value, code, message, retryable, retained, rebuilt
        _raise_invalid_failure()
    return rebuilt


def _raise_invalid_failure() -> NoReturn:
    error = ValueError("invalid Editor operational failure")
    error.__suppress_context__ = True
    raise error from None


def _plan_values(value: EditorGenerationPlanV1) -> tuple[object, ...]:
    return tuple(object.__getattribute__(value, name) for name in _PLAN_FIELD_NAMES)


def reconstruct_plan(value: object) -> EditorGenerationPlanV1:
    if type(value) is not EditorGenerationPlanV1:
        del value
        _raise_invalid_plan()
    try:
        fields = _plan_values(value)
        retained = object.__getattribute__(value, "_seal")
    except (AttributeError, TypeError):
        del value
        _raise_invalid_plan()
    try:
        rebuilt = EditorGenerationPlanV1(*fields)
    except Exception:  # noqa: BLE001 - copied-invalid state remains private
        del value, fields, retained
        _raise_invalid_plan()
    if retained != object.__getattribute__(rebuilt, "_seal"):
        del value, fields, retained, rebuilt
        _raise_invalid_plan()
    return rebuilt


def _result_values(
    value: EditorOperationalPreparationResultV1,
) -> tuple[object, ...]:
    return tuple(
        object.__getattribute__(value, name)
        for name in (
            "source_report_id",
            "source_report_fingerprint",
            "lifecycle",
            "plan",
            "failure",
        )
    )


def reconstruct_preparation_result(
    value: object,
) -> EditorOperationalPreparationResultV1:
    if type(value) is not EditorOperationalPreparationResultV1:
        del value
        _raise_invalid_result()
    try:
        fields = _result_values(value)
        retained = object.__getattribute__(value, "_seal")
    except (AttributeError, TypeError):
        del value
        _raise_invalid_result()
    try:
        rebuilt = EditorOperationalPreparationResultV1(*fields)
    except Exception:  # noqa: BLE001 - copied-invalid state remains private
        del value, fields, retained
        _raise_invalid_result()
    if retained != object.__getattribute__(rebuilt, "_seal"):
        del value, fields, retained, rebuilt
        _raise_invalid_result()
    return rebuilt


def _failures_for_lifecycle(
    lifecycle: tuple[EditorOperationalLifecycleStateV1, ...],
) -> tuple[EditorOperationalFailureCodeV1, ...]:
    if lifecycle == _INVALID_INPUT_LIFECYCLE:
        return (EditorOperationalFailureCodeV1.INVALID_INPUT,)
    if lifecycle == _SELECTION_FAILED_LIFECYCLE:
        return (EditorOperationalFailureCodeV1.SELECTION_FAILED,)
    if lifecycle == _POST_SELECTION_FAILED_LIFECYCLE:
        return (
            EditorOperationalFailureCodeV1.INVALID_SELECTION_RESULT,
            EditorOperationalFailureCodeV1.PLAN_CONSTRUCTION_FAILED,
        )
    raise ValueError("invalid Editor operational lifecycle")


def make_failure(code: EditorOperationalFailureCodeV1) -> EditorOperationalFailureV1:
    return EditorOperationalFailureV1(code, _FAILURE_MESSAGES[code])


SUCCESS_LIFECYCLE = _SUCCESS_LIFECYCLE
INVALID_INPUT_LIFECYCLE = _INVALID_INPUT_LIFECYCLE
SELECTION_FAILED_LIFECYCLE = _SELECTION_FAILED_LIFECYCLE
POST_SELECTION_FAILED_LIFECYCLE = _POST_SELECTION_FAILED_LIFECYCLE


__all__ = (
    "EditorGenerationPlanV1",
    "EditorOperationalFailureCodeV1",
    "EditorOperationalFailureV1",
    "EditorOperationalLifecycleStateV1",
    "EditorOperationalPreparationResultV1",
)
