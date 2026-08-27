"""Immediate constraint validation for generated component results."""

import re
import unicodedata
from dataclasses import dataclass

from pastila_scout.editor.generation.models import RetryReason

_UNRESOLVED_TEMPLATE = re.compile(r"\{[^{}]+\}")
_TEMPLATE_SLOT = re.compile(r"\{[^{}]+\}")
_SENTENCE = re.compile(r"[^.!?\n]+(?:[.!?]+|$)", re.UNICODE)
_NUMERIC_TOKEN = re.compile(r"\d+(?:[.,]\d+)*|%|[^\W\d_]+", re.UNICODE)
_MALFORMED_NUMERIC_BASIS = re.compile(r"\bpe\s+mes[ăa]\s+pe\s+zi\b", re.IGNORECASE)

_UNITS = {
    "%": "percent",
    "procent": "percent",
    "procente": "percent",
    "leu": "ron",
    "lei": "ron",
    "ron": "ron",
    "euro": "eur",
    "eur": "eur",
    "dolar": "usd",
    "dolari": "usd",
    "usd": "usd",
    "metru": "metre",
    "metri": "metre",
    "kilometru": "kilometre",
    "kilometri": "kilometre",
    "kg": "kilogram",
    "kilogram": "kilogram",
    "kilograme": "kilogram",
}
_TIME_BASES = {
    "zi": "day",
    "zile": "day",
    "lună": "month",
    "luna": "month",
    "luni": "month",
    "an": "year",
    "ani": "year",
    "oră": "hour",
    "ora": "hour",
    "ore": "hour",
    "săptămână": "week",
    "saptamana": "week",
    "săptămâni": "week",
    "saptamani": "week",
}


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


def validate_v1_2_numeric_factual_consistency(text, supported_surfaces):
    """Reject mutated numeric/unit/basis facts without rewriting generated prose."""
    errors = []
    if _MALFORMED_NUMERIC_BASIS.search(text):
        errors.append("v1_2_malformed_numeric_basis:pe mesă pe zi")
    supported = {
        signature
        for surface in supported_surfaces
        for signature in _numeric_signatures(surface)
    }
    for signature, expression in _numeric_signatures(text, include_surface=True):
        if signature not in supported:
            errors.append(f"v1_2_unsupported_numeric_expression:{expression}")
    return tuple(dict.fromkeys(errors))


def _numeric_signatures(value, *, include_surface=False):
    tokens = _NUMERIC_TOKEN.findall(value.casefold())
    results = []
    for index, token in enumerate(tokens):
        if not token[0].isdigit():
            continue
        number = _normalized_number(token)
        following = tokens[index + 1 : index + 9]
        preceding = tokens[max(0, index - 3) : index]
        unit = next((_UNITS[item] for item in following[:5] if item in _UNITS), None)
        basis = None
        for offset, item in enumerate(following[:-1]):
            if item in {"pe", "per"} and following[offset + 1] in _TIME_BASES:
                basis = _TIME_BASES[following[offset + 1]]
                break
        qualifier = _numeric_qualifier(preceding)
        signature = (number, unit, basis, qualifier)
        if include_surface:
            surface = " ".join(tokens[index : index + min(9, len(tokens) - index)])
            results.append((signature, surface))
        else:
            results.append(signature)
    return tuple(results)


def _normalized_number(value):
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", value):
        return value.replace(".", "")
    return value.replace(",", ".")


def _numeric_qualifier(tokens):
    joined = " ".join(tokens)
    if "cel puțin" in joined or "minimum" in tokens:
        return "at_least"
    if (
        "mai mult de" in joined
        or "mai mare de" in joined
        or "peste" in tokens
        or "depășește" in tokens
        or "depaseste" in tokens
    ):
        return "over"
    if "aproximativ" in tokens or "aproape" in tokens:
        return "approximately"
    if "maximum" in tokens or "cel mult" in joined:
        return "at_most"
    return None


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
    closing = _normalized_words(result.text)
    for story_id in state.generated_story_ids:
        stitched = _normalized_words(
            f"{state.factual_summary(story_id)} {state.ending_summary(story_id)}"
        )
        if closing == stitched:
            errors.append("closing_mechanical_story_stitch")
            break
    if _mechanically_repeats(result.text):
        errors.append("closing_mechanical_repetition")
    return _outcome(errors)


def _normalized_words(value):
    return " ".join(value.casefold().split()).strip(" .!?")


def _mechanically_repeats(value):
    words = _normalized_words(value).split()
    for width in range(4, len(words) // 2 + 1):
        for start in range(len(words) - (2 * width) + 1):
            if words[start : start + width] == words[
                start + width : start + (2 * width)
            ]:
                return True
    return False


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
