"""Package-private dependency contracts for Editor application composition."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import NoReturn, Protocol

from pastila_scout.contracts.episode_context import EpisodeContextV1
from pastila_scout.contracts.scout_editor import ScoutEditorInputV1
from pastila_scout.contracts.selection_profile import SelectionProfileV1
from pastila_scout.editor.blueprint_models import EditorialBlueprint
from pastila_scout.editor.commentary_models import EpisodeCommentaryBlueprint
from pastila_scout.editor.flow_models import FlowOptimizationResult
from pastila_scout.editor.generation.models import LanguageGenerationConfig
from pastila_scout.editor.voice_models import EpisodeVoicePlan
from pastila_scout.editor_generation_authority_v1 import (
    EditorGenerationRuntimeOptionsV1,
)
from pastila_scout.editor_generation_execution_v1 import (
    EditorGenerationExecutionRequestV1,
)
from pastila_scout.editor_operational_execution_v1 import (
    EditorOperationalResultV1,
)
from pastila_scout.editor_operational_v1 import (
    EditorGenerationPlanV1,
    EditorOperationalPreparationResultV1,
)
from pastila_scout.provider_execution_v2 import CancellationTokenV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1

from .models import EditorOutputDestinationV1
from .serialization import EditorSerializedOperationalResultV1


@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class _EditorDeterministicArtifactsV1:
    flow_result: FlowOptimizationResult
    editorial_blueprint: EditorialBlueprint
    commentary_blueprint: EpisodeCommentaryBlueprint
    voice_plan: EpisodeVoicePlan

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Editor deterministic artifacts cannot be subclassed")

    def __init__(
        self,
        flow_result: FlowOptimizationResult,
        editorial_blueprint: EditorialBlueprint,
        commentary_blueprint: EpisodeCommentaryBlueprint,
        voice_plan: EpisodeVoicePlan,
    ) -> None:
        if not _valid_artifacts(
            flow_result,
            editorial_blueprint,
            commentary_blueprint,
            voice_plan,
        ):
            raise TypeError("invalid Editor deterministic artifacts")
        object.__setattr__(self, "flow_result", flow_result)
        object.__setattr__(self, "editorial_blueprint", editorial_blueprint)
        object.__setattr__(self, "commentary_blueprint", commentary_blueprint)
        object.__setattr__(self, "voice_plan", voice_plan)

    def __repr__(self) -> str:
        _reconstruct_artifacts(self)
        return "_EditorDeterministicArtifactsV1(content=<redacted>)"

    def __eq__(self, other: object) -> bool:
        return type(other) is type(self) and _artifact_values(
            _reconstruct_artifacts(self)
        ) == _artifact_values(_reconstruct_artifacts(other))

    def __copy__(self) -> _EditorDeterministicArtifactsV1:
        return _reconstruct_artifacts(self)

    def __deepcopy__(self, memo: dict[int, object]) -> _EditorDeterministicArtifactsV1:
        del memo
        return _reconstruct_artifacts(self)

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("_EditorDeterministicArtifactsV1 does not support pickle")


def _artifact_values(value: _EditorDeterministicArtifactsV1) -> tuple[object, ...]:
    return tuple(
        object.__getattribute__(value, name)
        for name in (
            "flow_result",
            "editorial_blueprint",
            "commentary_blueprint",
            "voice_plan",
        )
    )


def _valid_artifacts(*values: object) -> bool:
    flow, editorial, commentary, voice = values
    if (
        type(flow) is not FlowOptimizationResult
        or type(editorial) is not EditorialBlueprint
        or type(commentary) is not EpisodeCommentaryBlueprint
        or type(voice) is not EpisodeVoicePlan
    ):
        return False
    proposal = flow.output.episode_proposal
    if proposal is None:
        return False
    order = tuple(item.event_id for item in proposal.episode_flow)
    return order == editorial.flow_order == commentary.flow_order == voice.flow_order


def _reconstruct_artifacts(value: object) -> _EditorDeterministicArtifactsV1:
    if type(value) is not _EditorDeterministicArtifactsV1:
        raise TypeError("invalid Editor deterministic artifacts")
    fields = _artifact_values(value)
    return _EditorDeterministicArtifactsV1(*fields)


class _EditorPreparationDependencyV1(Protocol):  # noqa: PYI046
    def prepare(
        self,
        *,
        scout_input: ScoutEditorInputV1,
        selection_profile: SelectionProfileV1,
        episode_context: EpisodeContextV1,
    ) -> EditorOperationalPreparationResultV1: ...


class _EditorArtifactDependencyV1(Protocol):  # noqa: PYI046
    def build(
        self, *, plan: EditorGenerationPlanV1
    ) -> _EditorDeterministicArtifactsV1: ...


class _EditorExecutionRequestAuthorityDependencyV1(Protocol):  # noqa: PYI046
    def construct(
        self,
        *,
        preparation: EditorOperationalPreparationResultV1,
        plan: EditorGenerationPlanV1,
        flow_result: FlowOptimizationResult,
        editorial_blueprint: EditorialBlueprint,
        commentary_blueprint: EpisodeCommentaryBlueprint,
        voice_plan: EpisodeVoicePlan,
        generation_configuration: LanguageGenerationConfig,
        runtime_options: EditorGenerationRuntimeOptionsV1,
        provider: ProviderChoiceV1,
        requested_at: datetime,
        request_reference: str,
        cancellation: CancellationTokenV2,
    ) -> EditorGenerationExecutionRequestV1: ...


class _EditorOperationalExecutionDependencyV1(Protocol):  # noqa: PYI046
    def execute(
        self, *, request: EditorGenerationExecutionRequestV1
    ) -> EditorOperationalResultV1: ...


class _EditorSerializerDependencyV1(Protocol):  # noqa: PYI046
    def serialize(
        self, *, result: EditorOperationalResultV1
    ) -> EditorSerializedOperationalResultV1: ...


class _EditorExporterDependencyV1(Protocol):  # noqa: PYI046
    def publish(
        self, *, payload: bytes, destination: EditorOutputDestinationV1
    ) -> Path: ...
