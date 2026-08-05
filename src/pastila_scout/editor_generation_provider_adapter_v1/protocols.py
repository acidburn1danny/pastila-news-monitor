"""Private dependency protocols for the Editor generation adapter."""

from datetime import datetime
from typing import Protocol

from pastila_scout.provider_execution_v2 import CancellationTokenV2

from .models import EditorGenerationAttemptObservationV1


class EditorGenerationClockV1(Protocol):
    def now(self) -> datetime: ...


class EditorGenerationCancellationSourceV1(Protocol):
    def snapshot(self) -> CancellationTokenV2: ...


class EditorGenerationReferenceFactoryV1(Protocol):
    def create(self, *, prompt_fingerprint: str, attempt_number: int) -> str: ...


class EditorGenerationAttemptRecorderV1(Protocol):
    def record(self, observation: EditorGenerationAttemptObservationV1) -> None: ...

    def snapshot(self) -> tuple[EditorGenerationAttemptObservationV1, ...]: ...


__all__: tuple[str, ...] = ()
