"""Immediate constraint validation for generated component results."""

import re
import unicodedata
from dataclasses import dataclass

from pastila_scout.editor.generation.models import RetryReason

_UNRESOLVED_TEMPLATE = re.compile(r"\{[^{}]+\}")
_TEMPLATE_SLOT = re.compile(r"\{[^{}]+\}")
_SENTENCE = re.compile(r"[^.!?\n]+(?:[.!?]+|$)", re.UNICODE)


def _sentence_count(value: str) -> int:
    return sum(bool(item.strip()) for item in _SENTENCE.findall(value))


@dataclass(frozen=True)
class ValidationOutcome:
    errors: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()
    retry_reason: RetryReason | None = None
    fatal: bool = False

    @property
    def accepted(self):
        return not self.errors


def validate_story(result, context, state):
    errors = []
    if _sentence_count(result.factual_summary) > 2:
        errors.append("factual_setup_sentence_limit_exceeded")
    known_facts = {fact.fact_id for fact in context.approved_facts}
    used_facts = set(result.declared_fact_usage)
    if not used_facts:
        errors.append("missing_fact_anchor")
    if not used_facts <= known_facts:
        errors.append("unknown_fact_reference")
    for block in result.commentary_blocks:
        if not set(block.source_fact_ids) <= known_facts:
            errors.append("cross_story_or_unknown_fact_reference")
        if not set(block.satire_target_ids) <= set(context.allowed_satire_targets):
            errors.append("unknown_satire_target")
        if not set(block.protected_target_ids) <= set(context.protected_targets):
            errors.append("protected_target_violation")
    words = len(
        " ".join(
            (
                result.factual_summary,
                *(b.text for b in result.commentary_blocks),
                result.ending,
            )
        ).split()
    )
    if any(
        _UNRESOLVED_TEMPLATE.search(value)
        for value in (
            result.factual_summary,
            *(block.text for block in result.commentary_blocks),
            result.ending,
        )
    ):
        errors.append("unresolved_template_placeholder")
    errors.extend(_duplicate_offered_tool_errors(result, context))
    if words > context.word_budget_authority.hard_max_words:
        errors.append("word_budget_exceeded")
        errors.append(f"word_budget_actual:{words}")
    if words / 2.5 > context.runtime_budget:
        errors.append("runtime_budget_exceeded")
    if (
        result.used_vocatives + state.used_vocatives
        > context.voice_plan.get("vocatives", {}).get("maximum_per_story", 0)
        + state.used_vocatives
    ):
        errors.append("vocative_budget_exceeded")
    if (
        result.profanity_usage
        and context.voice_plan.get("profanity_ceiling") == "clean"
    ):
        errors.append("profanity_ceiling_exceeded")
    available = set(state.available_callback_ids(f"story-{context.flow_position:02d}"))
    if not set(result.used_callbacks) <= available:
        errors.append("callback_violation")
    required = (
        (
            result.declared_editorial_intent_usage,
            context.editorial_plan.get("intent_id"),
        ),
        (
            result.declared_conversation_intent_usage,
            context.conversation_plan.get("intent_id"),
        ),
        (result.declared_voice_intent_usage, context.voice_plan.get("intent_id")),
    )
    if any(not usage or expected not in usage for usage, expected in required):
        errors.append("missing_required_intent")
    if any(set(usage).difference({expected}) for usage, expected in required):
        errors.append("unknown_intent_reference")
    return _outcome(errors)


def _story_text(result) -> str:
    return "\n".join(
        (
            result.factual_summary,
            *(block.text for block in result.commentary_blocks),
            result.ending,
        )
    )


def _normalized(value: str) -> str:
    return " ".join(unicodedata.normalize("NFC", value).casefold().split())


def _literal_occurrences(surface: str, text: str) -> int:
    surface = _normalized(surface)
    text = _normalized(text)
    if not surface:
        return 0
    pattern = rf"(?<!\w){re.escape(surface)}(?!\w)"
    return sum(1 for _ in re.finditer(pattern, text))


def _template_occurrences(template: str, text: str) -> int:
    template = _normalized(template)
    text = _normalized(text)
    parts = _TEMPLATE_SLOT.split(template)
    slots = _TEMPLATE_SLOT.findall(template)
    if not slots:
        return _literal_occurrences(template, text)
    pattern = re.escape(parts[0])
    for tail in parts[1:]:
        pattern += r"[^.!?\n{}]+?" + re.escape(tail)
    return sum(1 for _ in re.finditer(pattern, text))


def _duplicate_offered_tool_errors(result, context) -> tuple[str, ...]:
    toolkit = context.optional_editorial_toolkit
    if not isinstance(toolkit, dict):
        return ()
    text = _story_text(result)
    errors = []
    for section in (
        "expressions",
        "controlled_terms",
        "comedy_devices",
        "signature_devices",
    ):
        items = toolkit.get(section, ())
        if not isinstance(items, (list, tuple)):
            continue
        for item in items:
            if not isinstance(item, dict):
                continue
            identity = item.get("id")
            surface = item.get("text")
            if not isinstance(identity, str) or not isinstance(surface, str):
                continue
            occurrences = (
                _template_occurrences(surface, text)
                if section in {"comedy_devices", "signature_devices"}
                else _literal_occurrences(surface, text)
            )
            if occurrences >= 2:
                errors.append(
                    f"duplicate_offered_tool_usage:{section}:{identity}:{occurrences}"
                )
    return tuple(errors)


def validate_transition(result, context, state):
    errors = []
    if _sentence_count(result.text) > 2:
        errors.append("transition_sentence_limit_exceeded")
    if (result.from_story_id, result.to_story_id) != (
        context.from_story_id,
        context.to_story_id,
    ):
        errors.append("transition_endpoint_mismatch")
    if result.fact_references:
        errors.append("transition_new_fact_reference")
    if not set(result.callback_usage) <= set(context.callback_context):
        errors.append("callback_violation")
    return _outcome(errors)


def validate_opening(result, context):
    errors = []
    if not set(result.referenced_story_ids) <= set(context.accepted_story_ids):
        errors.append("invalid_story_reference")
    if set(result.teased_reveal_ids) & set(context.protected_payoffs):
        errors.append("protected_payoff_disclosed")
    return _outcome(errors)


def validate_closing(result, context, state):
    errors = []
    if not set(result.callback_executions) <= set(context.available_callback_anchors):
        errors.append("callback_violation")
    return _outcome(errors)


def _outcome(errors):
    errors = tuple(dict.fromkeys(errors))
    mapping = {
        "missing_fact_anchor": RetryReason.MISSING_FACT_ANCHOR,
        "unknown_fact_reference": RetryReason.UNKNOWN_FACT_REFERENCE,
        "cross_story_or_unknown_fact_reference": RetryReason.UNKNOWN_FACT_REFERENCE,
        "word_budget_exceeded": RetryReason.WORD_BUDGET_EXCEEDED,
        "runtime_budget_exceeded": RetryReason.RUNTIME_BUDGET_EXCEEDED,
        "unknown_intent_reference": RetryReason.UNKNOWN_INTENT_REFERENCE,
        "callback_violation": RetryReason.CALLBACK_VIOLATION,
        "missing_required_intent": RetryReason.MISSING_REQUIRED_INTENT,
        "protected_target_violation": RetryReason.PROTECTED_TARGET_VIOLATION,
    }
    reason = mapping.get(errors[0], RetryReason.CEILING_EXCEEDED) if errors else None
    fatal = any(
        item
        in {
            "unknown_fact_reference",
            "cross_story_or_unknown_fact_reference",
            "protected_target_violation",
            "transition_new_fact_reference",
            "protected_payoff_disclosed",
        }
        for item in errors
    ) or any(item.startswith("duplicate_offered_tool_usage:") for item in errors)
    return ValidationOutcome(errors=errors, retry_reason=reason, fatal=fatal)
