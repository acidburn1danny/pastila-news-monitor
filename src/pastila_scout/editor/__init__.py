"""Deterministic Editor Agent selection primitives."""

from pastila_scout.editor.blueprint_builder import (
    BlueprintValidationError,
    EditorialBlueprintBuilder,
)
from pastila_scout.editor.blueprint_models import (
    BlueprintBuildResult,
    BlueprintDecisionTrace,
    EditorialBlueprint,
)
from pastila_scout.editor.commentary_builder import CommentaryBlueprintBuilder
from pastila_scout.editor.commentary_models import (
    CommentaryBlueprintTrace,
    CommentaryBuildResult,
    EpisodeCommentaryBlueprint,
)
from pastila_scout.editor.engine import EditorialSelectionResult, SelectionEngine
from pastila_scout.editor.flow_models import FlowDecisionTrace, FlowOptimizationResult
from pastila_scout.editor.flow_optimizer import EpisodeFlowOptimizer
from pastila_scout.editor.models import (
    DecisionOutcome,
    DecisionTrace,
    EditorialDecision,
    EditorialReason,
)
from pastila_scout.editor.voice_builder import VoiceModelBuilder
from pastila_scout.editor.voice_models import (
    EpisodeVoicePlan,
    VoiceBuildResult,
    VoiceDecisionTrace,
)

__all__ = [
    "BlueprintBuildResult",
    "BlueprintDecisionTrace",
    "BlueprintValidationError",
    "CommentaryBlueprintBuilder",
    "CommentaryBlueprintTrace",
    "CommentaryBuildResult",
    "ControlledGenerator",
    "DecisionOutcome",
    "DecisionTrace",
    "EditorialBlueprint",
    "EditorialBlueprintBuilder",
    "EditorialDecision",
    "EditorialReason",
    "EditorialSelectionResult",
    "EpisodeCommentaryBlueprint",
    "EpisodeFlowOptimizer",
    "EpisodeVoicePlan",
    "FlowDecisionTrace",
    "FlowOptimizationResult",
    "SelectionEngine",
    "VoiceBuildResult",
    "VoiceDecisionTrace",
    "VoiceModelBuilder",
]


def __getattr__(name: str):
    """Load the generation boundary only when that public symbol is requested.

    Importing an unrelated editor submodule must not eagerly construct the
    complete generation/provider authority graph.
    """

    if name == "ControlledGenerator":
        from pastila_scout.editor.generation.controlled_generator import (
            ControlledGenerator,
        )

        return ControlledGenerator
    raise AttributeError(name)
