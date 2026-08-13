"""Strict GUI-local values for the structural desktop shell."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from typing import NoReturn

from .errors import _DesktopShellConfigurationError


def _bad() -> NoReturn:
    raise _DesktopShellConfigurationError() from None


def _pickle(name: str) -> NoReturn:
    raise TypeError(f"{name} does not support pickle")


class _DesktopPageV1(StrEnum):
    SCOUT = "scout"
    EDITOR = "editor"
    CHIEF_EDITOR = "chief_editor"

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        _pickle(type(self).__name__)


class _DesktopLaneV1(StrEnum):
    APPLICATION = "application"
    UPDATE = "update"

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        _pickle(type(self).__name__)


class _DesktopTaskStateV1(StrEnum):
    IDLE = "idle"
    SUBMITTED = "submitted"
    RUNNING = "running"
    CANCELLING = "cancelling"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    CLOSED = "closed"

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        _pickle(type(self).__name__)


class _ValueSafety:
    __slots__ = ()

    def __init_subclass__(cls, **kwargs: object) -> None:
        super().__init_subclass__(**kwargs)
        if cls.__module__ != __name__:
            raise TypeError("Desktop shell values are final")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        _pickle(type(self).__name__)


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class _DesktopTaskCompletionV1(_ValueSafety):
    value: object

    def __init__(self, value: object) -> None:
        object.__setattr__(self, "value", value)

    def __repr__(self) -> str:
        return "_DesktopTaskCompletionV1(value=<opaque>)"

    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and other.value is self.value

    def __copy__(self):
        return _DesktopTaskCompletionV1(self.value)

    def __deepcopy__(self, memo):
        del memo
        return self.__copy__()


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class _DesktopQueueEventV1(_ValueSafety):
    lane: _DesktopLaneV1
    state: _DesktopTaskStateV1
    completion: _DesktopTaskCompletionV1 | None

    def __init__(
        self,
        lane: _DesktopLaneV1,
        state: _DesktopTaskStateV1,
        completion: _DesktopTaskCompletionV1 | None = None,
    ) -> None:
        if type(lane) is not _DesktopLaneV1 or type(state) is not _DesktopTaskStateV1:
            _bad()
        if state is _DesktopTaskStateV1.COMPLETED:
            if type(completion) is not _DesktopTaskCompletionV1:
                _bad()
        elif completion is not None or state not in {
            _DesktopTaskStateV1.RUNNING,
            _DesktopTaskStateV1.FAILED,
            _DesktopTaskStateV1.CANCELLED,
        }:
            _bad()
        object.__setattr__(self, "lane", lane)
        object.__setattr__(self, "state", state)
        object.__setattr__(self, "completion", completion)

    def __repr__(self) -> str:
        return f"_DesktopQueueEventV1(lane={self.lane.value!r}, state={self.state.value!r})"

    def __eq__(self, other: object) -> bool:
        return (
            type(other) is type(self)
            and other.lane is self.lane
            and other.state is self.state
            and other.completion == self.completion
        )

    def __copy__(self):
        return _reconstruct_desktop_queue_event_v1(self)

    def __deepcopy__(self, memo):
        del memo
        return self.__copy__()


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class _DesktopShellSnapshotV1(_ValueSafety):
    selected_page: _DesktopPageV1
    application_state: _DesktopTaskStateV1
    update_state: _DesktopTaskStateV1
    is_closed: bool

    def __init__(
        self, selected_page, application_state, update_state, is_closed
    ) -> None:
        if (
            type(selected_page) is not _DesktopPageV1
            or type(application_state) is not _DesktopTaskStateV1
            or type(update_state) is not _DesktopTaskStateV1
            or type(is_closed) is not bool
            or ((application_state is _DesktopTaskStateV1.CLOSED) != is_closed)
            or ((update_state is _DesktopTaskStateV1.CLOSED) != is_closed)
        ):
            _bad()
        object.__setattr__(self, "selected_page", selected_page)
        object.__setattr__(self, "application_state", application_state)
        object.__setattr__(self, "update_state", update_state)
        object.__setattr__(self, "is_closed", is_closed)

    def __repr__(self) -> str:
        return (
            "_DesktopShellSnapshotV1("
            f"selected_page={self.selected_page.value!r}, "
            f"application_state={self.application_state.value!r}, "
            f"update_state={self.update_state.value!r}, is_closed={self.is_closed!r})"
        )

    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and (
            other.selected_page,
            other.application_state,
            other.update_state,
            other.is_closed,
        ) == (
            self.selected_page,
            self.application_state,
            self.update_state,
            self.is_closed,
        )

    def __copy__(self):
        return _reconstruct_desktop_shell_snapshot_v1(self)

    def __deepcopy__(self, memo):
        del memo
        return self.__copy__()


class _ActionInputBase(_ValueSafety):
    __slots__ = ()

    def __repr__(self) -> str:
        return f"{type(self).__name__}(values=<redacted>)"


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class _DesktopScoutActionInputV1(_ActionInputBase):
    period: str
    category: str

    def __init__(self, period: str, category: str) -> None:
        if type(period) is not str or type(category) is not str:
            _bad()
        object.__setattr__(self, "period", period)
        object.__setattr__(self, "category", category)

    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and (other.period, other.category) == (
            self.period,
            self.category,
        )

    def __copy__(self):
        return _reconstruct_desktop_scout_action_input_v1(self)

    def __deepcopy__(self, memo):
        del memo
        return self.__copy__()


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class _DesktopEditorActionInputV1(_ActionInputBase):
    event_id: int
    scout_input_path: str
    selection_profile_path: str
    episode_context_path: str
    generation_config_path: str
    provider: str
    model: str
    timeout_seconds: str
    output_path: str
    no_replace: bool

    def __init__(self, *values, **kwargs) -> None:
        names = (
            "event_id",
            "scout_input_path",
            "selection_profile_path",
            "episode_context_path",
            "generation_config_path",
            "provider",
            "model",
            "timeout_seconds",
            "output_path",
            "no_replace",
        )
        if values or set(kwargs) != set(names):
            _bad()
        ordered = tuple(kwargs[name] for name in names)
        if (
            type(ordered[0]) is not int
            or ordered[0] <= 0
            or any(type(value) is not str for value in ordered[1:-1])
            or type(ordered[-1]) is not bool
        ):
            _bad()
        for name, value in zip(names, ordered, strict=True):
            object.__setattr__(self, name, value)

    def __eq__(self, other: object) -> bool:
        if type(other) is not type(self):
            return False
        return tuple(getattr(other, name) for name in self.__slots__) == tuple(
            getattr(self, name) for name in self.__slots__
        )

    def __copy__(self):
        return _reconstruct_desktop_editor_action_input_v1(self)

    def __deepcopy__(self, memo):
        del memo
        return self.__copy__()


def _reconstruct_desktop_task_completion_v1(value: object) -> _DesktopTaskCompletionV1:
    if type(value) is not _DesktopTaskCompletionV1:
        _bad()
    return _DesktopTaskCompletionV1(value.value)


def _reconstruct_desktop_queue_event_v1(value: object) -> _DesktopQueueEventV1:
    if type(value) is not _DesktopQueueEventV1:
        _bad()
    completion = value.completion
    return _DesktopQueueEventV1(
        value.lane,
        value.state,
        (
            None
            if completion is None
            else _reconstruct_desktop_task_completion_v1(completion)
        ),
    )


def _reconstruct_desktop_shell_snapshot_v1(value: object) -> _DesktopShellSnapshotV1:
    if type(value) is not _DesktopShellSnapshotV1:
        _bad()
    return _DesktopShellSnapshotV1(
        value.selected_page,
        value.application_state,
        value.update_state,
        value.is_closed,
    )


def _reconstruct_desktop_scout_action_input_v1(
    value: object,
) -> _DesktopScoutActionInputV1:
    if type(value) is not _DesktopScoutActionInputV1:
        _bad()
    return _DesktopScoutActionInputV1(value.period, value.category)


def _reconstruct_desktop_editor_action_input_v1(
    value: object,
) -> _DesktopEditorActionInputV1:
    if type(value) is not _DesktopEditorActionInputV1:
        _bad()
    return _DesktopEditorActionInputV1(
        **{name: getattr(value, name) for name in value.__slots__}
    )
