"""Private immutable values for Editor generation runtime composition."""

from __future__ import annotations

import copy
from dataclasses import dataclass
from typing import NoReturn

from pastila_scout.editor_generation_provider_adapter_v1 import (
    EditorGenerationAttemptObservationV1,
)
from pastila_scout.provider_execution_v2 import ProviderExecutorV2

from .errors import EditorGenerationRuntimeCompositionError
from .protocols import (
    EditorGenerationAttemptRecorderV1,
    EditorGenerationCancellationSourceV1,
    EditorGenerationClockV1,
    EditorGenerationReferenceFactoryV1,
    _EditorRuntimeLifecycleAuthorityV1,
)


def _raise() -> NoReturn:
    error = EditorGenerationRuntimeCompositionError(
        "Editor generation runtime composition failed."
    )
    error.__cause__ = None
    error.__context__ = None
    error.__suppress_context__ = True
    raise error from None


@dataclass(frozen=True, slots=True, repr=False, eq=False)
class EditorOllamaRuntimeHandleV1:
    executor: ProviderExecutorV2
    lifecycle: _EditorRuntimeLifecycleAuthorityV1

    def __repr__(self) -> str:
        return "EditorOllamaRuntimeHandleV1(<private>)"

    def __copy__(self) -> EditorOllamaRuntimeHandleV1:
        return type(self)(self.executor, self.lifecycle)

    def __deepcopy__(self, memo: dict[int, object]) -> EditorOllamaRuntimeHandleV1:
        del memo
        return self.__copy__()

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("Editor Ollama runtime handle cannot be pickled")


@dataclass(frozen=True, slots=True, repr=False, eq=False)
class EditorAdapterDependenciesV1:
    clock: EditorGenerationClockV1
    cancellation_source: EditorGenerationCancellationSourceV1
    reference_factory: EditorGenerationReferenceFactoryV1
    attempt_recorder: EditorGenerationAttemptRecorderV1

    def __repr__(self) -> str:
        return "EditorAdapterDependenciesV1(<private>)"

    def __copy__(self) -> EditorAdapterDependenciesV1:
        return type(self)(
            self.clock,
            self.cancellation_source,
            self.reference_factory,
            self.attempt_recorder,
        )

    def __deepcopy__(self, memo: dict[int, object]) -> EditorAdapterDependenciesV1:
        del memo
        return self.__copy__()

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("Editor adapter dependencies cannot be pickled")


@dataclass(frozen=True, init=False, repr=False, eq=False)
class _EditorGenerationAttemptRecorderV1:
    _observations: list[EditorGenerationAttemptObservationV1]

    def __init__(self) -> None:
        object.__setattr__(self, "_observations", [])

    def record(self, observation: EditorGenerationAttemptObservationV1) -> None:
        try:
            rebuilt = copy.copy(observation)
            items = object.__getattribute__(self, "_observations")
            if type(items) is not list or rebuilt.attempt_number != len(items) + 1:
                _raise()
            items.append(rebuilt)
        except EditorGenerationRuntimeCompositionError:
            raise
        except Exception:  # noqa: BLE001 - copied-invalid observation is isolated
            _raise()

    def snapshot(self) -> tuple[EditorGenerationAttemptObservationV1, ...]:
        try:
            items = object.__getattribute__(self, "_observations")
            if type(items) is not list:
                _raise()
            result = tuple(copy.copy(item) for item in items)
            if tuple(item.attempt_number for item in result) != tuple(
                range(1, len(result) + 1)
            ):
                _raise()
            return result
        except EditorGenerationRuntimeCompositionError:
            raise
        except Exception:  # noqa: BLE001 - copied-invalid recorder is isolated
            _raise()

    def __repr__(self) -> str:
        return "_EditorGenerationAttemptRecorderV1(<private>)"

    def __copy__(self) -> _EditorGenerationAttemptRecorderV1:
        return self

    def __deepcopy__(
        self, memo: dict[int, object]
    ) -> _EditorGenerationAttemptRecorderV1:
        del memo
        return self

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("Editor attempt recorder cannot be pickled")


__all__: tuple[str, ...] = ()
