"""Supported objective deterministic editorial rules.

Rules here inspect exact structure or text. They perform no semantic inference.
"""

import re
import unicodedata
from dataclasses import dataclass
from itertools import pairwise

from pastila_scout.editor.qa.models import (
    EditorialConfidence,
    EditorialFinding,
    EditorialIssueFamily,
    EditorialSeverity,
    EvidenceItem,
    FindingLocation,
    MetadataEntry,
    ReviewScope,
)
from pastila_scout.editor.qa.rules.base import scope_applicability
from pastila_scout.editor.qa.rules.context import (
    ComponentTextEntry,
    RuleContext,
    comparison_text,
)
from pastila_scout.editor.qa.rules.models import (
    RuleCapability,
    RuleCategory,
    RuleOperationalStatus,
)

REVIEWER_ID = "deterministic-editorial-rules"
REGEX_CHECK_KEYS = frozenset(
    {
        "placeholder",
        "template",
        "punctuation",
        "markup",
        "control",
        "trailing",
        "inline_space",
    }
)


@dataclass(frozen=True)
class ObjectiveRule:
    rule_id: str
    category: RuleCategory
    description: str
    supported_scopes: tuple[ReviewScope, ...]
    check: str
    default_severity: EditorialSeverity = EditorialSeverity.ERROR
    rule_version: str = "1.0.0"
    operational_status: RuleOperationalStatus = (
        RuleOperationalStatus.OPERATIONALLY_REACHABLE
    )

    @property
    def default_enabled(self) -> bool:
        """All explicitly constructed default rules are enabled."""

        return True

    @property
    def blocking(self) -> bool:
        return self.default_severity >= EditorialSeverity.ERROR

    @property
    def capabilities(self) -> tuple[RuleCapability, ...]:
        values = [RuleCapability(self.category.value)]
        if ReviewScope.TRANSITION in self.supported_scopes:
            values.append(RuleCapability.TRANSITION)
        return tuple(dict.fromkeys(values))

    def applicability(self, context: RuleContext):
        return scope_applicability(self, context)

    def evaluate(self, context: RuleContext) -> tuple[EditorialFinding, ...]:
        method = resolve_checker(self)
        defects = method(self, context)
        bounded = defects[: context.policy.maximum_findings_per_rule]
        return tuple(
            _finding(
                self,
                entry,
                summary,
                explanation,
                evidence,
                index,
                len(defects),
                len(bounded),
            )
            for index, (entry, summary, explanation, evidence) in enumerate(bounded)
        )


def resolve_checker(rule: ObjectiveRule):
    """Resolve a rule's declared checker through the authoritative dispatch path."""

    if rule.check in REGEX_CHECK_KEYS:
        return _check_regex
    return globals()[f"_check_{rule.check}"]


Defect = tuple[ComponentTextEntry | None, str, str, str]


def _finding(rule, entry, summary, explanation, evidence, index, detected, reported):
    scope = entry.scope if entry else ReviewScope.EPISODE
    component_id = entry.component_id if entry else None
    excerpt = evidence[:200]
    metadata = [MetadataEntry(key="rule_version", value=rule.rule_version)]
    if detected > reported:
        metadata.extend(
            (
                MetadataEntry(key="total_detected", value=str(detected)),
                MetadataEntry(key="reported", value=str(reported)),
                MetadataEntry(key="truncated", value="true"),
            )
        )
    return EditorialFinding.build(
        reviewer_id=REVIEWER_ID,
        issue_family=EditorialIssueFamily(rule.category.value),
        issue_code=rule.rule_id,
        severity=rule.default_severity,
        confidence=EditorialConfidence.HIGH,
        scope=scope,
        location=FindingLocation(
            component_type=scope,
            component_id=component_id,
            transition_from_story_position=(
                entry.transition_from_story_position if entry else None
            ),
            transition_to_story_position=(
                entry.transition_to_story_position if entry else None
            ),
            quoted_excerpt=excerpt or None,
            description=f"occurrence {index + 1}",
        ),
        summary=summary,
        explanation=explanation,
        evidence=(
            (EvidenceItem(evidence_id=f"occurrence-{index + 1}", text=excerpt),)
            if excerpt
            else ()
        ),
        recommendation="Review the identified component and correct the objective defect.",
        blocking=rule.blocking,
        waivable=rule.default_severity is not EditorialSeverity.CRITICAL,
        metadata=tuple(metadata),
    )


def _entries(context, scopes):
    return context.target_entries(scopes)


def _check_empty(rule, context) -> list[Defect]:
    return [
        (item, "Component has no visible content", rule.description, "")
        for item in _entries(context, rule.supported_scopes)
        if item.metrics.visible_character_count == 0
    ]


def _check_story_count_min(rule, context) -> list[Defect]:
    count = len(context.story_ids)
    return (
        [
            (
                None,
                "Episode has too few stories",
                f"Found {count}; minimum is {context.policy.minimum_story_count}.",
                str(count),
            )
        ]
        if count < context.policy.minimum_story_count
        else []
    )


def _check_story_count_max(rule, context) -> list[Defect]:
    count = len(context.story_ids)
    return (
        [
            (
                None,
                "Episode has too many stories",
                f"Found {count}; maximum is {context.policy.maximum_story_count}.",
                str(count),
            )
        ]
        if count > context.policy.maximum_story_count
        else []
    )


def _check_missing_transition(rule, context) -> list[Defect]:
    expected = set(pairwise(context.story_ids))
    return [
        (
            None,
            "Required transition is missing",
            f"No transition connects stories {a} and {b}.",
            f"{a}->{b}",
        )
        for a, b in sorted(expected - set(context.transition_pairs))
    ]


def _check_orphan_transition(rule, context) -> list[Defect]:
    expected = set(pairwise(context.story_ids))
    return [
        (
            None,
            "Transition is orphaned",
            f"Transition {a}->{b} is not an episode adjacency.",
            f"{a}->{b}",
        )
        for a, b in sorted(set(context.transition_pairs) - expected)
    ]


def _check_component_order(rule, context) -> list[Defect]:
    return (
        []
        if context.transition_pairs == tuple(pairwise(context.story_ids))
        else [
            (
                None,
                "Component order is inconsistent",
                rule.description,
                "transition ordering",
            )
        ]
    )


def _check_cta_placement(rule, context) -> list[Defect]:
    cta = context.cta_placement
    if (
        cta
        and cta.placement == "after_story"
        and cta.after_story_id not in context.story_ids[:-1]
    ):
        return [
            (
                None,
                "CTA placement is inconsistent",
                rule.description,
                str(cta.after_story_id),
            )
        ]
    return []


def _limit_for(rule, context):
    name = rule.supported_scopes[0].value
    return getattr(context.policy, f"{name}_max_words"), getattr(
        context.policy, f"{name}_max_characters"
    )


def _check_length_episode(rule, context) -> list[Defect]:
    metrics = context.episode_draft.assembled_text
    from pastila_scout.editor.qa.rules.context import TextMetrics

    measured = TextMetrics.from_text(metrics)
    return _length_defect(
        rule,
        None,
        measured,
        context.policy.episode_max_words,
        context.policy.episode_max_characters,
    )


def _check_length_component(rule, context) -> list[Defect]:
    words, chars = _limit_for(rule, context)
    defects = []
    for item in _entries(context, rule.supported_scopes):
        defects += _length_defect(rule, item, item.metrics, words, chars)
    return defects


def _length_defect(rule, item, metrics, words, chars):
    if metrics.word_count <= words and metrics.character_count <= chars:
        return []
    return [
        (
            item,
            "Component exceeds objective length limit",
            f"Found {metrics.word_count} words/{metrics.character_count} characters; limits are {words}/{chars}.",
            f"words={metrics.word_count}; characters={metrics.character_count}",
        )
    ]


def _check_story_imbalance(rule, context) -> list[Defect]:
    entries = _entries(context, (ReviewScope.STORY,))
    if len(entries) < 2:
        return []
    counts = [item.metrics.word_count for item in entries]
    low, high = min(counts), max(counts)
    return (
        [
            (
                None,
                "Story lengths are disproportionate",
                f"Longest story is more than three times the shortest nonempty story ({high}/{low}).",
                f"min={low}; max={high}",
            )
        ]
        if low and high > low * 3
        else []
    )


def _check_transition_disproportion(rule, context) -> list[Defect]:
    transitions = _entries(context, (ReviewScope.TRANSITION,))
    stories = _entries(context, (ReviewScope.STORY,))
    baseline = (
        sum(x.metrics.word_count for x in stories) / len(stories) if stories else 0
    )
    return [
        (
            item,
            "Transition is disproportionate",
            "Transition exceeds half the mean story length.",
            str(item.metrics.word_count),
        )
        for item in transitions
        if baseline and item.metrics.word_count > baseline / 2
    ]


def _sentences(value):
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", value) if part.strip()]


def _check_duplicate_sentence(rule, context) -> list[Defect]:
    seen = {}
    for item in context.component_texts:
        for sentence in _sentences(item.text):
            key = comparison_text(sentence)
            if len(key.split()) >= 4:
                seen.setdefault(key, []).append((item, sentence))
    return [
        (
            values[1][0],
            "Sentence is repeated",
            f"The exact normalized sentence occurs {len(values)} times.",
            values[1][1],
        )
        for values in seen.values()
        if len(values) > context.policy.maximum_identical_sentence_occurrences
    ]


def _check_repeated_phrase(rule, context) -> list[Defect]:
    size = context.policy.repeated_phrase_minimum_words
    found = {}
    for item in context.component_texts:
        words = comparison_text(item.text).split()
        local = {
            tuple(words[i : i + size]) for i in range(max(0, len(words) - size + 1))
        }
        for phrase in local:
            found.setdefault(phrase, []).append(item)
    return [
        (
            items[1],
            "Phrase is repeated across components",
            f"The exact {size}-word phrase occurs in {len(items)} components.",
            " ".join(phrase),
        )
        for phrase, items in sorted(found.items())
        if len(items) > context.policy.maximum_repeated_phrase_occurrences
    ]


def _check_reused_transition(rule, context) -> list[Defect]:
    return _duplicate_components(
        context, (ReviewScope.TRANSITION,), "Transition text is reused"
    )


def _check_duplicate_component(rule, context) -> list[Defect]:
    return _duplicate_components(
        context, rule.supported_scopes, "Full component text is duplicated"
    )


def _duplicate_components(context, scopes, summary):
    seen = {}
    for item in _entries(context, scopes):
        if comparison_text(item.text):
            seen.setdefault(comparison_text(item.text), []).append(item)
    return [
        (
            items[1],
            summary,
            f"The normalized component text occurs {len(items)} times.",
            items[1].text[:200],
        )
        for items in seen.values()
        if len(items) > 1
    ]


def _check_component_edge(rule, context) -> list[Defect]:
    opening = rule.rule_id.endswith("opening")
    seen = {}
    for item in context.component_texts:
        sentences = _sentences(item.text)
        if sentences:
            value = sentences[0 if opening else -1]
            seen.setdefault(comparison_text(value), []).append((item, value))
    label = "opening" if opening else "ending"
    return [
        (
            items[1][0],
            f"Component {label} is repeated",
            f"The exact normalized {label} occurs {len(items)} times.",
            items[1][1],
        )
        for items in seen.values()
        if len(items) > 1
    ]


def _check_regex(rule, context) -> list[Defect]:
    patterns = {
        "placeholder": r"(?i)(?:\bTODO\b|\bTBD\b|\[placeholder\]|INSERT (?:JOKE|TEXT) HERE)",
        "template": r"(?:\{\{[^{}]+\}\}|\{%[^%]+%\}|<%[^%]+%>)",
        "punctuation": rf"[!?.,]{{{context.policy.maximum_consecutive_punctuation + 1},}}",
        "markup": r"(?:</?[a-zA-Z][^>]*>|\[[^\]]+\]\([^\)]+\))",
        "control": r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]",
        "trailing": r"(?m)[ \t]+$",
        "inline_space": r"[^\S\r\n]{2,}",
    }
    pattern = re.compile(patterns[rule.check])
    return [
        (item, rule.description, rule.description, match.group(0))
        for item in _entries(context, rule.supported_scopes)
        for match in pattern.finditer(item.text)
    ]


def _check_blank_lines(rule, context) -> list[Defect]:
    pattern = re.compile(rf"(?:\r?\n){{{context.policy.maximum_blank_lines + 2},}}")
    return [
        (item, rule.description, rule.description, "excessive blank lines")
        for item in _entries(context, rule.supported_scopes)
        if pattern.search(item.text)
    ]


def _check_line_length(rule, context) -> list[Defect]:
    return [
        (
            item,
            rule.description,
            f"A line exceeds {context.policy.maximum_line_length} characters.",
            line[:200],
        )
        for item in _entries(context, rule.supported_scopes)
        for line in item.text.splitlines()
        if len(line) > context.policy.maximum_line_length
    ]


def _check_unicode(rule, context) -> list[Defect]:
    return [
        (item, rule.description, "Text is not Unicode NFC normalized.", item.text[:200])
        for item in _entries(context, rule.supported_scopes)
        if item.text != unicodedata.normalize("NFC", item.text)
    ]


def _check_required_phrase(rule, context) -> list[Defect]:
    defects = []
    for phrase_rule in context.policy.required_phrase_rules:
        text = " ".join(item.text for item in _entries(context, phrase_rule.scopes))
        if comparison_text(phrase_rule.phrase) not in comparison_text(text):
            defects.append(
                (
                    None,
                    rule.description,
                    f"Required literal phrase is absent: {phrase_rule.phrase}",
                    phrase_rule.phrase,
                )
            )
    return defects


def _check_forbidden_phrase(rule, context) -> list[Defect]:
    return [
        (
            item,
            rule.description,
            "A configured forbidden literal phrase is present.",
            phrase.phrase,
        )
        for phrase in context.policy.forbidden_phrase_rules
        for item in _entries(context, phrase.scopes)
        if comparison_text(phrase.phrase) in comparison_text(item.text)
    ]


def _check_rhetorical_question(rule, context) -> list[Defect]:
    return [
        (
            None,
            rule.description,
            f"No question mark appears in required {scope.value} scope.",
            scope.value,
        )
        for scope in context.policy.required_rhetorical_question_scopes
        if not any("?" in item.text for item in _entries(context, (scope,)))
    ]


def _check_profanity(rule, context) -> list[Defect]:
    defects = []
    for limit in context.policy.maximum_profanity_count_by_scope:
        count = sum(
            comparison_text(item.text).split().count(word)
            for item in _entries(context, (limit.scope,))
            for word in context.policy.profanity_literals
        )
        if count > limit.maximum:
            defects.append(
                (
                    None,
                    rule.description,
                    f"Configured literal profanity count {count} exceeds {limit.maximum}.",
                    str(count),
                )
            )
    return defects


def _check_sentence_length(rule, context) -> list[Defect]:
    return [
        (
            item,
            rule.description,
            "A sentence exceeds the configured story word ceiling.",
            sentence[:200],
        )
        for item in context.component_texts
        for sentence in _sentences(item.text)
        if len(sentence.split()) > context.policy.story_max_words
    ]


def build_supported_rules() -> tuple[ObjectiveRule, ...]:
    """Construct every rule supported by the frozen EpisodeDraft contract."""

    S, R, L, V = (
        RuleCategory.STRUCTURE,
        RuleCategory.RUNTIME,
        RuleCategory.LANGUAGE,
        RuleCategory.VOICE,
    )
    REP = RuleCategory.REPETITION
    all_text = (
        ReviewScope.OPENING,
        ReviewScope.STORY,
        ReviewScope.TRANSITION,
        ReviewScope.CLOSING,
    )
    specifications = (
        (
            "structure.empty-opening",
            S,
            "Opening has no visible content",
            (ReviewScope.OPENING,),
            "empty",
        ),
        (
            "structure.empty-closing",
            S,
            "Closing has no visible content",
            (ReviewScope.CLOSING,),
            "empty",
        ),
        (
            "structure.empty-story",
            S,
            "Story has no visible content",
            (ReviewScope.STORY,),
            "empty",
        ),
        (
            "structure.empty-transition",
            S,
            "Transition has no visible content",
            (ReviewScope.TRANSITION,),
            "empty",
        ),
        (
            "structure.too-few-stories",
            S,
            "Episode story count is below policy",
            (ReviewScope.EPISODE,),
            "story_count_min",
        ),
        (
            "structure.too-many-stories",
            S,
            "Episode story count exceeds policy",
            (ReviewScope.EPISODE,),
            "story_count_max",
        ),
        (
            "structure.component-order-inconsistent",
            S,
            "Story/transition order is inconsistent",
            (ReviewScope.EPISODE,),
            "component_order",
        ),
        (
            "structure.missing-required-transition",
            S,
            "Required transition is absent",
            (ReviewScope.EPISODE,),
            "missing_transition",
        ),
        (
            "structure.orphan-transition",
            S,
            "Transition does not join adjacent stories",
            (ReviewScope.EPISODE,),
            "orphan_transition",
        ),
        (
            "structure.cta-placement-inconsistent",
            S,
            "CTA placement does not reference a valid position",
            (ReviewScope.EPISODE,),
            "cta_placement",
        ),
        (
            "runtime.episode-too-long",
            R,
            "Episode exceeds deterministic heuristic length",
            (ReviewScope.EPISODE,),
            "length_episode",
        ),
        (
            "runtime.opening-too-long",
            R,
            "Opening exceeds deterministic heuristic length",
            (ReviewScope.OPENING,),
            "length_component",
        ),
        (
            "runtime.closing-too-long",
            R,
            "Closing exceeds deterministic heuristic length",
            (ReviewScope.CLOSING,),
            "length_component",
        ),
        (
            "runtime.story-too-long",
            R,
            "Story exceeds deterministic heuristic length",
            (ReviewScope.STORY,),
            "length_component",
        ),
        (
            "runtime.transition-too-long",
            R,
            "Transition exceeds deterministic heuristic length",
            (ReviewScope.TRANSITION,),
            "length_component",
        ),
        (
            "runtime.story-length-imbalance",
            R,
            "Story lengths are objectively imbalanced",
            (ReviewScope.EPISODE,),
            "story_imbalance",
        ),
        (
            "runtime.transition-disproportionate",
            R,
            "Transition is disproportionate to stories",
            (ReviewScope.EPISODE,),
            "transition_disproportion",
        ),
        (
            "repetition.duplicate-sentence",
            REP,
            "Exact normalized sentence repeats",
            all_text,
            "duplicate_sentence",
        ),
        (
            "repetition.repeated-phrase",
            REP,
            "Exact normalized phrase repeats",
            all_text,
            "repeated_phrase",
        ),
        (
            "repetition.reused-transition",
            REP,
            "Exact transition repeats",
            (ReviewScope.TRANSITION,),
            "reused_transition",
        ),
        (
            "repetition.repeated-component-opening",
            REP,
            "Exact component opening repeats",
            all_text,
            "component_edge",
        ),
        (
            "repetition.repeated-component-ending",
            REP,
            "Exact component ending repeats",
            all_text,
            "component_edge",
        ),
        (
            "repetition.duplicate-component-text",
            REP,
            "Exact full component repeats",
            all_text,
            "duplicate_component",
        ),
        (
            "language.placeholder-detected",
            L,
            "Placeholder marker is present",
            all_text,
            "placeholder",
        ),
        (
            "language.unresolved-template-marker",
            L,
            "Unresolved template marker is present",
            all_text,
            "template",
        ),
        (
            "language.excessive-consecutive-punctuation",
            L,
            "Consecutive punctuation exceeds policy",
            all_text,
            "punctuation",
        ),
        (
            "language.excessive-blank-lines",
            L,
            "Blank-line run exceeds policy",
            all_text,
            "blank_lines",
        ),
        (
            "language.line-too-long",
            L,
            "Line length exceeds policy",
            all_text,
            "line_length",
        ),
        (
            "language.markup-leakage",
            L,
            "Markup syntax leaked into editorial text",
            all_text,
            "markup",
        ),
        (
            "language.control-character",
            L,
            "Disallowed control character is present",
            all_text,
            "control",
        ),
        (
            "language.noncanonical-unicode",
            L,
            "Text is not canonical Unicode NFC",
            all_text,
            "unicode",
        ),
        (
            "language.trailing-whitespace",
            L,
            "Line contains trailing whitespace",
            all_text,
            "trailing",
        ),
        (
            "language.repeated-inline-whitespace",
            L,
            "Repeated inline whitespace is present",
            all_text,
            "inline_space",
        ),
        (
            "language.no-visible-content",
            L,
            "Component has no visible content",
            all_text,
            "empty",
        ),
        (
            "voice.required-phrase-missing",
            V,
            "Configured required literal phrase is missing",
            all_text,
            "required_phrase",
        ),
        (
            "voice.forbidden-phrase-detected",
            V,
            "Configured forbidden literal phrase is present",
            all_text,
            "forbidden_phrase",
        ),
        (
            "voice.required-rhetorical-question-missing",
            V,
            "Configured scope has no rhetorical-question marker",
            all_text,
            "rhetorical_question",
        ),
        (
            "voice.profanity-limit-exceeded",
            V,
            "Configured literal profanity budget is exceeded",
            all_text,
            "profanity",
        ),
        (
            "voice.forbidden-profanity-detected",
            V,
            "Configured forbidden profanity is present",
            all_text,
            "profanity",
        ),
        (
            "voice.sentence-length-limit-exceeded",
            V,
            "Sentence length exceeds objective policy",
            all_text,
            "sentence_length",
        ),
    )
    defensive_rule_ids = {
        "structure.cta-placement-inconsistent",
        "structure.missing-required-transition",
        "structure.orphan-transition",
    }
    return tuple(
        ObjectiveRule(
            *values,
            operational_status=(
                RuleOperationalStatus.DEFENSIVE
                if values[0] in defensive_rule_ids
                else RuleOperationalStatus.OPERATIONALLY_REACHABLE
            ),
        )
        for values in specifications
    )
