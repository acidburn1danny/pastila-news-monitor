"""Pure deterministic evaluators for synthetic revision properties."""

from __future__ import annotations

import re
import unicodedata
from difflib import SequenceMatcher

from pastila_scout.editor.generation.models import EpisodeDraft

from .scenario import SyntheticRevisionScenario


def normalized_text(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


def preserves_values(text: str, values: tuple[str, ...]) -> bool:
    candidate = normalized_text(text)
    return all(normalized_text(value) in candidate for value in values)


def preserves_quotes(text: str, values: tuple[str, ...]) -> bool:
    return preserves_values(text, values)


def preserves_numeric_values(text: str, values: tuple[str, ...]) -> bool:
    candidate_numbers = tuple(re.findall(r"(?<!\w)\d+(?:[.,]\d+)?(?!\w)", text))
    return all(value in candidate_numbers for value in values)


def preserves_temporal_values(text: str, values: tuple[str, ...]) -> bool:
    return preserves_values(text, values)


def preserves_structure(source: EpisodeDraft, candidate: EpisodeDraft | None) -> bool:
    if candidate is None:
        return False
    return (
        tuple(item.story_id for item in source.stories)
        == tuple(item.story_id for item in candidate.stories)
        and tuple((item.from_story_id, item.to_story_id) for item in source.transitions)
        == tuple(
            (item.from_story_id, item.to_story_id) for item in candidate.transitions
        )
        and (source.cta is None) == (candidate.cta is None)
    )


def change_ratio(source: str, candidate: str) -> float:
    return 1.0 - SequenceMatcher(a=source, b=candidate, autojunk=False).ratio()


def meaning_preserved(scenario: SyntheticRevisionScenario, text: str) -> bool:
    return preserves_values(
        text,
        (
            *scenario.protected_facts,
            *scenario.protected_quotes,
            *scenario.protected_numeric_values,
            *scenario.protected_dates,
        ),
    )


def proportional_revision(scenario: SyntheticRevisionScenario, text: str) -> bool:
    ratio = change_ratio(scenario.source_draft.assembled_text, text)
    return ratio <= scenario.maximum_change_ratio


def no_op_compliant(scenario: SyntheticRevisionScenario, text: str) -> bool:
    if not scenario.expects_no_change:
        return True
    return normalized_text(text) == normalized_text(
        scenario.source_draft.assembled_text
    )
