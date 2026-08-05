"""Package-private runtime composition dependency protocols."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, Protocol

from pastila_scout.editor_generation_authority_v1 import (
    EditorGenerationRuntimeOptionsV1,
)
from pastila_scout.editor_generation_provider_adapter_v1 import (
    EditorGenerationAttemptObservationV1,
)
from pastila_scout.provider_execution_v2 import CancellationTokenV2
from pastila_scout.provider_runtime_openai_v2 import OpenAIRuntimeComposerV2
from pastila_scout.scout_runtime_v1 import ScoutRuntimeCompositionV1
from pastila_scout.scout_workflow_execution_v1 import ScoutWorkflowExecutionV1

if TYPE_CHECKING:
    from .models import EditorAdapterDependenciesV1, EditorOllamaRuntimeHandleV1


class EditorGenerationClockV1(Protocol):
    def now(self) -> datetime: ...


class EditorGenerationCancellationSourceV1(Protocol):
    def snapshot(self) -> CancellationTokenV2: ...


class EditorGenerationReferenceFactoryV1(Protocol):
    def create(self, *, prompt_fingerprint: str, attempt_number: int) -> str: ...


class EditorGenerationAttemptRecorderV1(Protocol):
    def record(self, observation: EditorGenerationAttemptObservationV1) -> None: ...

    def snapshot(self) -> tuple[EditorGenerationAttemptObservationV1, ...]: ...


class EditorOpenAIRuntimeComposerFactoryV1(Protocol):
    def create(
        self, *, model_identifier: str, timeout_seconds: int | float  # noqa: PYI041
    ) -> OpenAIRuntimeComposerV2: ...


class EditorOllamaRuntimeFactoryV1(Protocol):
    def open(
        self, options: EditorGenerationRuntimeOptionsV1
    ) -> EditorOllamaRuntimeHandleV1: ...


class EditorScoutWorkflowFactoryV1(Protocol):
    def create(
        self, *, runtime_composition: ScoutRuntimeCompositionV1
    ) -> ScoutWorkflowExecutionV1: ...


class EditorAdapterDependencyFactoryV1(Protocol):
    def create(self, *, operation_reference: str) -> EditorAdapterDependenciesV1: ...


class _EditorRuntimeLifecycleAuthorityV1(Protocol):  # noqa: PYI046
    def close(self) -> None: ...


__all__: tuple[str, ...] = ()
