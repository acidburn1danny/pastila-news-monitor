"""Installed Desktop interaction state for governed deterministic Voice V2."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from pastila_scout.editor_voice_deterministic_v2 import EditorVoiceInteractionV2

from .voice_adjudication_presentation import VoiceAdjudicationPresentationV1

VoiceDesktopActionV2 = Literal[
    "load",
    "refresh",
    "select_program",
    "select_expression",
    "preview",
    "accept",
    "reject",
]


@dataclass(frozen=True, slots=True)
class VoiceDesktopActionInputV2:
    action: VoiceDesktopActionV2
    event_id: int
    candidate_identity: str | None = None


@dataclass(frozen=True, slots=True)
class VoiceDesktopPresentationV2:
    event_id: int
    interaction: EditorVoiceInteractionV2
    program_choices: tuple[tuple[str, str], ...] = ()
    selected_program_identity: str | None = None
    program_selection_finalized: bool = False
    expression_choices: tuple[tuple[str, str], ...] = ()
    selected_expression_identity: str | None = None
    expression_selection_finalized: bool = False
    preview_text: str = ""
    preview_enabled: bool = False
    accept_enabled: bool = False
    reject_enabled: bool = False
    refresh_enabled: bool = True
    adjudication: VoiceAdjudicationPresentationV1 | None = None


__all__ = ["VoiceDesktopActionInputV2", "VoiceDesktopPresentationV2"]
