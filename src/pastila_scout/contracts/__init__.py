"""Stable public Scout/Editor contract API."""

from pastila_scout.contracts.editor_output import (
    EditorAgentOutputV1,
    EpisodeProposalV1,
    validate_editor_output_against_input,
)
from pastila_scout.contracts.episode_context import EpisodeContextV1
from pastila_scout.contracts.scout_editor import ScoutEditorInputV1
from pastila_scout.contracts.selection_profile import SelectionProfileV1

__all__ = [
    "EditorAgentOutputV1",
    "EpisodeContextV1",
    "EpisodeProposalV1",
    "ScoutEditorInputV1",
    "SelectionProfileV1",
    "validate_editor_output_against_input",
]
