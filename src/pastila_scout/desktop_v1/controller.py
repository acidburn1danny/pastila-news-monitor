"""Two-lane executor and Tk-thread marshalling controller."""

# ruff: noqa: BLE001, S110, TRY004

from __future__ import annotations

import inspect
import queue
import threading
import types
from collections.abc import Callable
from concurrent.futures import Executor, ThreadPoolExecutor

from .errors import _DesktopShellConfigurationError, _DesktopShellExecutionError
from .models import (
    _DesktopLaneV1,
    _DesktopPageV1,
    _DesktopQueueEventV1,
    _DesktopShellSnapshotV1,
    _DesktopTaskCompletionV1,
    _DesktopTaskStateV1,
)


def _configuration() -> None:
    raise _DesktopShellConfigurationError() from None


def _callable_arity(value: object, count: int, *, allow_variadic: bool = False) -> None:
    target = value
    drop_self = False
    if type(value) is types.FunctionType:
        if (
            inspect.getattr_static(value, "__signature__", None) is not None
            or inspect.getattr_static(value, "__wrapped__", None) is not None
        ):
            _configuration()
    elif type(value) is types.MethodType:
        target = value.__func__
        drop_self = True
    else:
        try:
            target = inspect.getattr_static(type(value), "__call__")
        except AttributeError:
            _configuration()
        if isinstance(target, (property, staticmethod, classmethod)) or not callable(
            target
        ):
            _configuration()
        drop_self = True
    try:
        signature = inspect.signature(target, follow_wrapped=False)
    except (TypeError, ValueError):
        _configuration()
    parameters = tuple(signature.parameters.values())
    if drop_self:
        if not parameters:
            _configuration()
        parameters = parameters[1:]
    fixed = tuple(
        p for p in parameters if p.kind not in {p.VAR_POSITIONAL, p.VAR_KEYWORD}
    )
    if (
        len(fixed) != count
        or (not allow_variadic and len(parameters) != count)
        or any(p.kind not in {p.POSITIONAL_OR_KEYWORD, p.KEYWORD_ONLY} for p in fixed)
    ):
        _configuration()


class _DesktopTaskControllerV1:
    __slots__ = (
        "_application_executor",
        "_cancel_after",
        "_closed",
        "_drain_token",
        "_executors_closed",
        "_futures",
        "_handlers",
        "_pending_idle",
        "_publish_snapshot",
        "_queue",
        "_schedule_after",
        "_selected_page",
        "_started",
        "_states",
        "_thread",
        "_update_executor",
    )

    def __init__(
        self,
        *,
        schedule_after: Callable[[int, Callable[[], None]], object],
        cancel_after: Callable[[object], None],
        publish_snapshot: Callable[[_DesktopShellSnapshotV1], None],
        application_executor: Executor | None = None,
        update_executor: Executor | None = None,
    ) -> None:
        _callable_arity(schedule_after, 2, allow_variadic=True)
        _callable_arity(cancel_after, 1)
        _callable_arity(publish_snapshot, 1)
        if application_executor is not None:
            self._validate_executor(application_executor)
        if update_executor is not None:
            self._validate_executor(update_executor)
        self._schedule_after = schedule_after
        self._cancel_after = cancel_after
        self._publish_snapshot = publish_snapshot
        self._application_executor = application_executor or ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="pastila-application"
        )
        self._update_executor = update_executor or ThreadPoolExecutor(
            max_workers=1, thread_name_prefix="pastila-update"
        )
        self._thread = threading.get_ident()
        self._queue: queue.SimpleQueue[_DesktopQueueEventV1] = queue.SimpleQueue()
        self._selected_page = _DesktopPageV1.SCOUT
        self._states = {
            _DesktopLaneV1.APPLICATION: _DesktopTaskStateV1.IDLE,
            _DesktopLaneV1.UPDATE: _DesktopTaskStateV1.IDLE,
        }
        self._handlers: dict[_DesktopLaneV1, Callable[..., None]] = {}
        self._futures: dict[_DesktopLaneV1, object] = {}
        self._pending_idle: set[_DesktopLaneV1] = set()
        self._drain_token: object | None = None
        self._started = False
        self._closed = False
        self._executors_closed = False

    @staticmethod
    def _validate_executor(value: object) -> None:
        for name in ("submit", "shutdown"):
            try:
                member = inspect.getattr_static(type(value), name)
            except AttributeError:
                _configuration()
            if isinstance(
                member, (property, staticmethod, classmethod)
            ) or not callable(member):
                _configuration()

    def _on_thread(self) -> None:
        if threading.get_ident() != self._thread:
            _configuration()

    def _snapshot(self) -> _DesktopShellSnapshotV1:
        return _DesktopShellSnapshotV1(
            self._selected_page,
            self._states[_DesktopLaneV1.APPLICATION],
            self._states[_DesktopLaneV1.UPDATE],
            self._closed,
        )

    def _publish(self) -> None:
        self._publish_snapshot(snapshot=self._snapshot())

    def start(self) -> None:
        self._on_thread()
        if self._started or self._closed:
            _configuration()
        self._started = True
        try:
            self._publish()
            token = self._schedule_after(50, self._drain)
            if token is None:
                raise RuntimeError
            self._drain_token = token
        except BaseException:
            self.close()
            raise _DesktopShellExecutionError() from None

    def select_page(self, *, page: _DesktopPageV1) -> None:
        self._on_thread()
        if type(page) is not _DesktopPageV1 or self._closed:
            _configuration()
        if page is not self._selected_page:
            self._selected_page = page
            self._publish()

    def submit_application(self, *, task, on_completed) -> None:
        self._submit(_DesktopLaneV1.APPLICATION, task, on_completed)

    def submit_update(self, *, task, on_completed) -> None:
        self._submit(_DesktopLaneV1.UPDATE, task, on_completed)

    def _submit(self, lane: _DesktopLaneV1, task: object, on_completed: object) -> None:
        self._on_thread()
        _callable_arity(task, 0)
        _callable_arity(on_completed, 1)
        if (
            not self._started
            or self._closed
            or self._states[lane] is not _DesktopTaskStateV1.IDLE
        ):
            raise _DesktopShellExecutionError() from None
        self._states[lane] = _DesktopTaskStateV1.SUBMITTED
        self._handlers[lane] = on_completed  # type: ignore[assignment]
        self._publish()

        def worker() -> None:
            self._queue.put(_DesktopQueueEventV1(lane, _DesktopTaskStateV1.RUNNING))
            try:
                value = task()  # type: ignore[operator]
            except BaseException:
                self._queue.put(_DesktopQueueEventV1(lane, _DesktopTaskStateV1.FAILED))
                return
            self._queue.put(
                _DesktopQueueEventV1(
                    lane,
                    _DesktopTaskStateV1.COMPLETED,
                    _DesktopTaskCompletionV1(value),
                )
            )

        executor = (
            self._application_executor
            if lane is _DesktopLaneV1.APPLICATION
            else self._update_executor
        )
        try:
            future = executor.submit(worker)
            if not callable(getattr(future, "cancel", None)):
                raise RuntimeError
            self._futures[lane] = future
        except BaseException:
            self._handlers.pop(lane, None)
            self._states[lane] = _DesktopTaskStateV1.FAILED
            self._pending_idle.add(lane)
            self._publish()
            raise _DesktopShellExecutionError() from None

    def request_cancel(self, *, lane: _DesktopLaneV1) -> None:
        self._on_thread()
        if type(lane) is not _DesktopLaneV1 or self._states.get(lane) not in {
            _DesktopTaskStateV1.SUBMITTED,
            _DesktopTaskStateV1.RUNNING,
        }:
            _configuration()
        self._states[lane] = _DesktopTaskStateV1.CANCELLING
        self._publish()

    def _drain(self) -> None:
        self._on_thread()
        if self._closed:
            return
        self._drain_token = None
        for lane in (_DesktopLaneV1.APPLICATION, _DesktopLaneV1.UPDATE):
            if lane in self._pending_idle:
                self._pending_idle.remove(lane)
                self._states[lane] = _DesktopTaskStateV1.IDLE
                self._publish()
        try:
            while True:
                event = self._queue.get_nowait()
                self._accept(event)
        except queue.Empty:
            pass
        except BaseException:
            self.close()
            return
        try:
            token = self._schedule_after(50, self._drain)
            if token is None:
                raise RuntimeError
            self._drain_token = token
        except BaseException:
            self.close()

    def _accept(self, event: _DesktopQueueEventV1) -> None:
        lane, new = event.lane, event.state
        current = self._states[lane]
        if (
            current is _DesktopTaskStateV1.CANCELLING
            and new is _DesktopTaskStateV1.RUNNING
        ):
            return
        legal = {
            _DesktopTaskStateV1.SUBMITTED: {
                _DesktopTaskStateV1.RUNNING,
                _DesktopTaskStateV1.COMPLETED,
                _DesktopTaskStateV1.FAILED,
            },
            _DesktopTaskStateV1.RUNNING: {
                _DesktopTaskStateV1.COMPLETED,
                _DesktopTaskStateV1.FAILED,
            },
            _DesktopTaskStateV1.CANCELLING: {
                _DesktopTaskStateV1.COMPLETED,
                _DesktopTaskStateV1.FAILED,
                _DesktopTaskStateV1.CANCELLED,
            },
        }
        if new not in legal.get(current, set()):
            raise _DesktopShellExecutionError()
        if new is _DesktopTaskStateV1.COMPLETED:
            handler = self._handlers.pop(lane, None)
            completion = event.completion
            try:
                if handler is None or completion is None:
                    raise RuntimeError
                handler(result=completion.value)
            except BaseException:
                new = _DesktopTaskStateV1.FAILED
        elif new in {_DesktopTaskStateV1.FAILED, _DesktopTaskStateV1.CANCELLED}:
            self._handlers.pop(lane, None)
        self._states[lane] = new
        self._futures.pop(lane, None)
        self._publish()
        if new in {
            _DesktopTaskStateV1.COMPLETED,
            _DesktopTaskStateV1.FAILED,
            _DesktopTaskStateV1.CANCELLED,
        }:
            self._pending_idle.add(lane)

    def close(self) -> None:
        self._on_thread()
        if self._closed:
            return
        self._closed = True
        if self._drain_token is not None:
            try:
                self._cancel_after(self._drain_token)
            except BaseException:
                pass
            self._drain_token = None
        self._handlers.clear()
        self._futures.clear()
        self._pending_idle.clear()
        self._states = {
            _DesktopLaneV1.APPLICATION: _DesktopTaskStateV1.CLOSED,
            _DesktopLaneV1.UPDATE: _DesktopTaskStateV1.CLOSED,
        }
        try:
            self._publish()
        except BaseException:
            pass
        if not self._executors_closed:
            self._executors_closed = True
            for executor in (self._application_executor, self._update_executor):
                try:
                    executor.shutdown(wait=False, cancel_futures=True)
                except BaseException:
                    pass

    def snapshot(self) -> _DesktopShellSnapshotV1:
        self._on_thread()
        return self._snapshot()

    def __repr__(self) -> str:
        return "_DesktopTaskControllerV1(<redacted>)"

    def __init_subclass__(cls, **kwargs: object) -> None:
        del cls, kwargs
        raise TypeError("_DesktopTaskControllerV1 is final")

    def __copy__(self):
        raise TypeError("_DesktopTaskControllerV1 does not support copy")

    __deepcopy__ = __copy__

    def __reduce_ex__(self, protocol: int):
        del protocol
        raise TypeError("_DesktopTaskControllerV1 does not support pickle")
