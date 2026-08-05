"""Static dependency protocol for deterministic Editor selection."""

from typing import Protocol

from pastila_scout.contracts.episode_context import EpisodeContextV1
from pastila_scout.contracts.scout_editor import ScoutEditorInputV1
from pastila_scout.contracts.selection_profile import SelectionProfileV1
from pastila_scout.editor.engine import EditorialSelectionResult


class EditorSelectionEngineV1(Protocol):
    """The exact existing deterministic selection operation."""

    def select(
        self,
        scout_input: ScoutEditorInputV1,
        profile: SelectionProfileV1,
        context: EpisodeContextV1,
    ) -> EditorialSelectionResult: ...


__all__ = ("EditorSelectionEngineV1",)
