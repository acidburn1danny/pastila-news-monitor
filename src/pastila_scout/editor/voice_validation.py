"""Cross-stage validation for deterministic voice plans."""

from pastila_scout.editor.commentary_models import Sensitivity
from pastila_scout.editor.voice_models import (
    DirectLanguageLevel,
    EndingVoice,
    RoastEligibility,
)


class VoiceValidationError(ValueError):
    """Raised when a voice plan violates an upstream or safety invariant."""


def validate_voice_plan(plan, commentary, output) -> None:
    """Validate order, budgets, sensitive safeguards, and public immutability."""
    if plan.flow_order != commentary.flow_order:
        raise VoiceValidationError("voice plan must preserve commentary order")
    if len(plan.stories) != len(commentary.stories):
        raise VoiceValidationError("one voice plan is required per selected story")
    if (
        sum(story.vocatives.maximum_per_story for story in plan.stories)
        > plan.vocative_budget
    ):
        raise VoiceValidationError("story vocative allocations exceed episode budget")
    if (
        sum(story.romanian_expression.maximum_count for story in plan.stories)
        > plan.expression_budget.maximum_total
    ):
        raise VoiceValidationError("expression allocations exceed episode budget")
    if (
        sum(story.callback.maximum_count for story in plan.stories)
        > plan.callback_budget
    ):
        raise VoiceValidationError("callback allocations exceed episode budget")
    for voice, source in zip(plan.stories, commentary.stories, strict=True):
        sensitive = source.sensitivity not in (
            Sensitivity.ORDINARY,
            Sensitivity.ELEVATED,
        )
        if sensitive and voice.roast_eligibility is not RoastEligibility.PROHIBITED:
            raise VoiceValidationError("sensitive story cannot be roast eligible")
        if sensitive and voice.profanity_ceiling is not DirectLanguageLevel.CLEAN:
            raise VoiceValidationError(
                "sensitive story requires clean language ceiling"
            )
        if sensitive and voice.ending_voice is EndingVoice.PUNCHLINE:
            raise VoiceValidationError(
                "tragedy or sensitive story cannot end only in a joke"
            )
        if voice.audience_relationship != "intelligent_peer":
            raise VoiceValidationError(
                "audience must be treated as an intelligent peer"
            )
    if output.episode_proposal is None:
        raise VoiceValidationError(
            "voice plan requires unchanged public episode output"
        )
