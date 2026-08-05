"""Provider-free coordinator for deterministic Editor preparation."""

from __future__ import annotations

import inspect
from dataclasses import dataclass
from types import FunctionType
from typing import NoReturn, get_type_hints

from pastila_scout.contracts.editor_output import (
    EditorAgentOutputV1,
    validate_editor_output_against_input,
)
from pastila_scout.contracts.episode_context import EpisodeContextV1
from pastila_scout.contracts.identity import verify_scout_input_identity
from pastila_scout.contracts.scout_editor import ScoutEditorInputV1
from pastila_scout.contracts.selection_profile import SelectionProfileV1
from pastila_scout.editor.engine import EditorialSelectionResult
from pastila_scout.editor.models import DecisionTrace

from .errors import EditorOperationalConfigurationError
from .models import (
    INVALID_INPUT_LIFECYCLE,
    POST_SELECTION_FAILED_LIFECYCLE,
    SELECTION_FAILED_LIFECYCLE,
    SUCCESS_LIFECYCLE,
    EditorGenerationPlanV1,
    EditorOperationalFailureCodeV1,
    EditorOperationalPreparationResultV1,
    make_failure,
)
from .protocols import EditorSelectionEngineV1


@dataclass(frozen=True, slots=True, init=False, repr=False)
class EditorOperationalCoordinatorV1:
    selection_engine: EditorSelectionEngineV1

    def __init__(self, selection_engine: EditorSelectionEngineV1) -> None:
        if not _valid_selection_engine(selection_engine):
            del self, selection_engine
            _raise_configuration_error()
        object.__setattr__(self, "selection_engine", selection_engine)

    def prepare(
        self,
        scout_input: ScoutEditorInputV1,
        selection_profile: SelectionProfileV1,
        episode_context: EpisodeContextV1,
    ) -> EditorOperationalPreparationResultV1:
        engine = _validated_engine(self)
        try:
            source = _reconstruct(ScoutEditorInputV1, scout_input)
            profile = _reconstruct(SelectionProfileV1, selection_profile)
            context = _reconstruct(EpisodeContextV1, episode_context)
            verify_scout_input_identity(source)
        except Exception:  # noqa: BLE001 - input details remain private
            del self, engine, scout_input, selection_profile, episode_context
            return _failed_invalid_input()
        source_id = source.report_id
        source_fingerprint = source.content_fingerprint
        try:
            raw_selection = engine.select(source, profile, context)
        except Exception:  # noqa: BLE001 - dependency details remain private
            del self, engine, scout_input, selection_profile, episode_context
            del source, profile, context
            return _failed(
                source_id,
                source_fingerprint,
                SELECTION_FAILED_LIFECYCLE,
                EditorOperationalFailureCodeV1.SELECTION_FAILED,
            )
        if type(raw_selection) is not EditorialSelectionResult:
            del self, engine, scout_input, selection_profile, episode_context
            del source, profile, context, raw_selection
            return _failed(
                source_id,
                source_fingerprint,
                POST_SELECTION_FAILED_LIFECYCLE,
                EditorOperationalFailureCodeV1.INVALID_SELECTION_RESULT,
            )
        try:
            output = _reconstruct(EditorAgentOutputV1, raw_selection.output)
            trace = _reconstruct(DecisionTrace, raw_selection.trace)
            validate_editor_output_against_input(
                output,
                source,
                selection_profile=profile,
                episode_context=context,
            )
        except Exception:  # noqa: BLE001 - selection details remain private
            del self, engine, scout_input, selection_profile, episode_context
            del source, profile, context, raw_selection
            return _failed(
                source_id,
                source_fingerprint,
                POST_SELECTION_FAILED_LIFECYCLE,
                EditorOperationalFailureCodeV1.INVALID_SELECTION_RESULT,
            )
        del raw_selection
        try:
            plan = EditorGenerationPlanV1(
                source,
                profile,
                context,
                output,
                trace,
                source_id,
                source_fingerprint,
                trace.selected_event_ids,
                trace.backup_event_ids,
                trace.rejected_event_ids,
            )
        except Exception:  # noqa: BLE001 - plan details remain private
            del self, engine, scout_input, selection_profile, episode_context
            del source, profile, context, output, trace
            return _failed(
                source_id,
                source_fingerprint,
                POST_SELECTION_FAILED_LIFECYCLE,
                EditorOperationalFailureCodeV1.PLAN_CONSTRUCTION_FAILED,
            )
        del self, engine, scout_input, selection_profile, episode_context
        del source, profile, context, output, trace
        return EditorOperationalPreparationResultV1(
            source_id,
            source_fingerprint,
            SUCCESS_LIFECYCLE,
            plan,
            None,
        )

    def __repr__(self) -> str:
        _validated_engine(self)
        return (
            "EditorOperationalCoordinatorV1("
            "selection_engine=<injected EditorSelectionEngineV1>)"
        )

    def __eq__(self, other: object) -> bool:
        engine = _validated_engine(self)
        if type(other) is not EditorOperationalCoordinatorV1:
            return False
        return engine is _validated_engine(other)

    def __copy__(self) -> EditorOperationalCoordinatorV1:
        return EditorOperationalCoordinatorV1(_validated_engine(self))

    def __deepcopy__(self, memo: dict[int, object]) -> EditorOperationalCoordinatorV1:
        del memo
        return self.__copy__()

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        _validated_engine(self)
        del self, protocol
        raise TypeError("EditorOperationalCoordinatorV1 does not support pickle")


def _reconstruct(model: type, value: object):
    if type(value) is not model:
        raise TypeError("invalid Editor operational input")
    return model.model_validate(
        value.model_dump(mode="python", warnings=False), strict=True
    )


def _failed_invalid_input() -> EditorOperationalPreparationResultV1:
    return EditorOperationalPreparationResultV1(
        "",
        "",
        INVALID_INPUT_LIFECYCLE,
        None,
        make_failure(EditorOperationalFailureCodeV1.INVALID_INPUT),
    )


def _failed(
    source_id: str,
    source_fingerprint: str,
    lifecycle: tuple,
    code: EditorOperationalFailureCodeV1,
) -> EditorOperationalPreparationResultV1:
    return EditorOperationalPreparationResultV1(
        source_id,
        source_fingerprint,
        lifecycle,
        None,
        make_failure(code),
    )


def _valid_selection_engine(value: object) -> bool:
    value_type = type(value)
    if value_type.__getattribute__ is not object.__getattribute__:
        return False
    if "__getattr__" in value_type.__dict__:
        return False
    try:
        descriptor = inspect.getattr_static(value_type, "select")
        instance_descriptor = inspect.getattr_static(value, "select")
    except AttributeError:
        return False
    if descriptor is not instance_descriptor or type(descriptor) is not FunctionType:
        return False
    if hasattr(descriptor, "__signature__") or hasattr(descriptor, "__wrapped__"):
        return False
    try:
        signature = inspect.signature(descriptor, follow_wrapped=False)
        hints = get_type_hints(descriptor)
    except (NameError, TypeError, ValueError):
        return False
    parameters = tuple(signature.parameters.values())
    return (
        len(parameters) == 4
        and tuple(item.name for item in parameters)
        == ("self", "scout_input", "profile", "context")
        and all(
            item.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
            and item.default is inspect.Parameter.empty
            for item in parameters
        )
        and hints
        == {
            "scout_input": ScoutEditorInputV1,
            "profile": SelectionProfileV1,
            "context": EpisodeContextV1,
            "return": EditorialSelectionResult,
        }
    )


def _validated_engine(value: object) -> EditorSelectionEngineV1:
    if type(value) is not EditorOperationalCoordinatorV1:
        del value
        _raise_configuration_error()
    try:
        engine = object.__getattribute__(value, "selection_engine")
    except AttributeError:
        del value
        _raise_configuration_error()
    del value
    if not _valid_selection_engine(engine):
        del engine
        _raise_configuration_error()
    return engine


def _raise_configuration_error() -> NoReturn:
    error = EditorOperationalConfigurationError()
    error.__suppress_context__ = True
    raise error from None


__all__ = ("EditorOperationalCoordinatorV1",)
