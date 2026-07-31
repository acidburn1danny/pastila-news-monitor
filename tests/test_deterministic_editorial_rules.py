"""Focused M6C.5B deterministic-rule architecture and freeze-audit tests."""

import os
import re
import subprocess
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

import pytest

from pastila_scout.editor.generation import DraftAssembler
from pastila_scout.editor.generation.models import CommentaryBlockResult, DraftStory
from pastila_scout.editor.qa.models import EditorialReviewRequest, ReviewScope
from pastila_scout.editor.qa.rules import (
    DeterministicEditorialRulePolicy,
    DeterministicRulesReviewer,
    RuleContext,
    RuleEngine,
    RuleRegistry,
    TextMetrics,
    build_supported_rules,
)
from pastila_scout.editor.qa.rules.concrete import REGEX_CHECK_KEYS, resolve_checker
from pastila_scout.editor.qa.rules.models import RuleOperationalStatus
from pastila_scout.editor.qa.rules.policy import LiteralPhraseRule
from pastila_scout.editor.qa.validation import validate_review_result


def _draft(*, commentary="Aceasta este o propoziție repetată în mod exact."):
    block = CommentaryBlockResult(
        block_type="commentary",
        text=commentary,
        sequence=1,
        source_fact_ids=("fact-1",),
        blueprint_intent_ids=("intent-1",),
        voice_plan_ids=("voice-1",),
        satire_target_ids=(),
        protected_target_ids=(),
    )
    stories = tuple(
        DraftStory(
            story_id=index,
            factual_summary=f"Fapt confirmat {index}.",
            commentary_blocks=(block,),
            ending=f"Final {index}.",
        )
        for index in (1, 2)
    )
    from pastila_scout.editor.generation.models import DraftTransition

    return DraftAssembler().assemble(
        episode_id="episod-românesc",
        story_order=(1, 2),
        opening="Bună seara, România!",
        stories=stories,
        transitions=(
            DraftTransition(from_story_id=1, to_story_id=2, text="Mai departe."),
        ),
        closing="Aceasta a fost ediția.",
        cta=None,
    )


def _request(draft=None):
    return EditorialReviewRequest(
        review_id="review-1",
        reviewer_id="deterministic-editorial-rules",
        episode_draft=draft or _draft(),
        scope=ReviewScope.EPISODE,
        component_ids=(),
    )


def test_metrics_are_unicode_safe_and_deterministic():
    assert TextMetrics.from_text("Știre nouă?\n\nDa!") == TextMetrics.from_text(
        "Știre nouă?\n\nDa!"
    )
    assert TextMetrics.from_text("Știre nouă?").word_count == 2


def test_registry_and_context_fingerprints_are_stable():
    registry = RuleRegistry(build_supported_rules())
    request = _request()
    first = RuleContext.from_request(request)
    second = RuleContext.from_request(request)
    assert first.context_fingerprint == second.context_fingerprint
    assert (
        registry.select().rule_set_fingerprint == registry.select().rule_set_fingerprint
    )


def test_reviewer_is_reproducible_and_emits_rule_identity():
    reviewer = DeterministicRulesReviewer()
    first = reviewer.review(_request())
    second = reviewer.review(_request())
    assert first == second
    duplicate = [
        item
        for item in first.findings
        if item.issue_code == "repetition.duplicate-sentence"
    ]
    assert duplicate
    assert duplicate[0].reviewer_id == reviewer.reviewer_id
    assert any(item.key == "rule_version" for item in duplicate[0].metadata)


def test_objective_limits_are_policy_driven():
    reviewer = DeterministicRulesReviewer(
        DeterministicEditorialRulePolicy(opening_max_words=2)
    )
    result = reviewer.review(_request())
    assert "runtime.opening-too-long" in {item.issue_code for item in result.findings}


def test_rule_context_excludes_static_cta_from_fingerprint():
    from pastila_scout.editor.generation.models import (
        CallToActionDraft,
        CTAPlacement,
    )

    original = _draft()

    def with_secret(secret):
        cta = CallToActionDraft(
            placement=CTAPlacement.AFTER_CLOSING,
            after_story_id=None,
            bridge_text="Susține proiectul.",
            static_content=secret,
        )
        return DraftAssembler().assemble(
            episode_id=original.episode_id,
            story_order=(1, 2),
            opening=original.opening,
            stories=original.stories,
            transitions=original.transitions,
            closing=original.closing,
            cta=cta,
        )

    first = RuleContext.from_request(_request(with_secret("SECRET-A")))
    second = RuleContext.from_request(_request(with_secret("SECRET-B")))
    assert first.context_fingerprint == second.context_fingerprint
    assert "SECRET" not in repr(first.component_texts)


def test_execution_trace_is_ordered_and_complete():
    reviewer = DeterministicRulesReviewer()
    reviewer.review(_request())
    execution = reviewer.last_execution_result
    assert execution.executed_rule_count == (
        execution.successful_rule_count
        + execution.skipped_rule_count
        + execution.failed_rule_count
    )
    assert [item.sequence_number for item in execution.trace] == list(
        range(1, len(execution.trace) + 1)
    )


def test_default_inventory_is_exact_unique_and_documented():
    registry = RuleRegistry(tuple(reversed(build_supported_rules())))
    selected = registry.resolve(registry.select())
    counts = Counter(rule.category.value for rule in selected)
    assert len(selected) == 40
    assert counts == {
        "structure": 10,
        "runtime": 7,
        "repetition": 6,
        "language": 11,
        "voice": 6,
    }
    assert len({rule.rule_id for rule in selected}) == 40
    assert all(
        rule.rule_version == "1.0.0" and rule.default_enabled for rule in selected
    )
    assert tuple(rule.rule_id for rule in selected) == tuple(
        rule.rule_id for rule in RuleRegistry(build_supported_rules()).rules
    )
    document = Path("docs/m6c5b-deterministic-editorial-rules.md").read_text(
        encoding="utf-8"
    )
    implemented_section = document.split("## Omitted-rule inventory", 1)[0]
    documented = set(
        re.findall(
            r"`((?:structure|runtime|repetition|language|voice)\.[a-z0-9-]+)`",
            implemented_section,
        )
    )
    assert documented == {rule.rule_id for rule in selected}


def test_operational_and_defensive_classification_partitions_default_inventory():
    rules = RuleRegistry(build_supported_rules()).rules
    defensive = {
        rule.rule_id
        for rule in rules
        if rule.operational_status is RuleOperationalStatus.DEFENSIVE
    }
    reachable = {
        rule.rule_id
        for rule in rules
        if rule.operational_status is RuleOperationalStatus.OPERATIONALLY_REACHABLE
    }
    assert defensive == {
        "structure.cta-placement-inconsistent",
        "structure.missing-required-transition",
        "structure.orphan-transition",
    }
    assert len(reachable) == 37
    assert defensive.isdisjoint(reachable)
    assert defensive | reachable == {rule.rule_id for rule in rules}
    assert not any(rule_id.startswith("callback.") for rule_id in defensive | reachable)


def test_callback_candidates_are_explicitly_unsupported_and_not_registered():
    candidates = {
        "callback.declared-but-unused",
        "callback.used-before-introduction",
        "callback.excessive-reuse",
        "callback.missing-target",
        "callback.duplicate-introduction",
        "callback.literal-drift",
    }
    registered = {rule.rule_id for rule in build_supported_rules()}
    assert not candidates & registered
    document = Path("docs/m6c5b-deterministic-editorial-rules.md").read_text(
        encoding="utf-8"
    )
    assert all(
        document.count(f"`{rule_id}`") == 1
        and f"| `{rule_id}` | UNSUPPORTED BY FROZEN CONTRACT" in document
        for rule_id in candidates
    )


def test_registry_and_ruleset_are_input_order_independent():
    rules = build_supported_rules()
    first = RuleRegistry(rules)
    second = RuleRegistry(tuple(reversed(rules)))
    assert first.registry_fingerprint == second.registry_fingerprint
    ids = tuple(rule.rule_id for rule in rules[:5])
    assert (
        first.select(rule_ids=ids).rule_set_fingerprint
        == first.select(rule_ids=tuple(reversed(ids))).rule_set_fingerprint
    )


def test_behavioral_rule_metadata_changes_registry_fingerprint():
    rules = build_supported_rules()
    registry_fingerprint = RuleRegistry(rules).registry_fingerprint
    for changed in (
        replace(rules[0], rule_version="1.0.1"),
        replace(rules[0], default_severity=20),
        replace(rules[0], check="unicode"),
    ):
        assert (
            RuleRegistry((changed, *rules[1:])).registry_fingerprint
            != registry_fingerprint
        )


def test_policy_collection_order_is_canonical_and_thresholds_change_identity():
    first_rule = LiteralPhraseRule(
        phrase="Bună seara", scopes=(ReviewScope.STORY, ReviewScope.OPENING)
    )
    second_rule = LiteralPhraseRule(phrase="România", scopes=(ReviewScope.CLOSING,))
    first = DeterministicEditorialRulePolicy(
        required_phrase_rules=(first_rule, second_rule)
    )
    second = DeterministicEditorialRulePolicy(
        required_phrase_rules=(second_rule, first_rule)
    )
    assert first.policy_fingerprint == second.policy_fingerprint
    assert (
        first.policy_fingerprint
        != DeterministicEditorialRulePolicy(
            opening_max_words=121, required_phrase_rules=(first_rule, second_rule)
        ).policy_fingerprint
    )


def test_context_target_order_is_canonical():
    draft = _draft()
    first = EditorialReviewRequest(
        review_id="same",
        reviewer_id="deterministic-editorial-rules",
        episode_draft=draft,
        scope=ReviewScope.STORY,
        component_ids=("story-02", "story-01"),
    )
    second = first.model_copy(update={"component_ids": ("story-01", "story-02")})
    assert (
        RuleContext.from_request(first).context_fingerprint
        == RuleContext.from_request(second).context_fingerprint
    )


def test_fingerprints_are_stable_across_python_hash_seeds():
    code = (
        "from pastila_scout.editor.qa.rules import build_supported_rules,RuleRegistry;"
        "r=RuleRegistry(tuple(reversed(build_supported_rules())));"
        "print(r.registry_fingerprint, r.select().rule_set_fingerprint)"
    )
    outputs = set()
    for seed in ("1", "7", "123"):
        environment = os.environ.copy()
        environment["PYTHONHASHSEED"] = seed
        outputs.add(
            subprocess.check_output(
                [sys.executable, "-c", code],
                text=True,
                encoding="utf-8",
                env=environment,
            ).strip()
        )
    assert len(outputs) == 1


def test_emitted_story_finding_uses_canonical_location_without_transition_fields():
    reviewer = DeterministicRulesReviewer(
        DeterministicEditorialRulePolicy(story_max_words=2)
    )
    result = reviewer.review(_request())
    finding = next(
        item for item in result.findings if item.issue_code == "runtime.story-too-long"
    )
    assert finding.location.component_id == "story-01"
    assert finding.location.transition_from_story_position is None
    assert finding.location.transition_to_story_position is None
    assert finding.blocking and finding.severity.name == "ERROR"
    assert finding.evidence and finding.recommendation


def test_emitted_transition_finding_has_complete_frozen_location_and_valid_result():
    request = _request()
    reviewer = DeterministicRulesReviewer(
        DeterministicEditorialRulePolicy(transition_max_words=1)
    )
    first = reviewer.review(request)
    second = reviewer.review(request)
    finding = next(
        item
        for item in first.findings
        if item.issue_code == "runtime.transition-too-long"
    )
    assert finding.location.component_id == "transition-01-02"
    assert finding.location.transition_from_story_position == 1
    assert finding.location.transition_to_story_position == 2
    assert finding.blocking and finding.severity.name == "ERROR"
    assert finding.evidence and finding.recommendation
    assert first == second
    assert validate_review_result(request, first) is first


def test_three_story_transition_positions_follow_episode_order_not_source_ids():
    from pastila_scout.editor.generation.models import DraftTransition

    base = _draft()
    third = base.stories[0].model_copy(update={"story_id": 99})
    draft = DraftAssembler().assemble(
        episode_id="three-stories",
        story_order=(1, 2, 99),
        opening=base.opening,
        stories=(*base.stories, third),
        transitions=(
            *base.transitions,
            DraftTransition(from_story_id=2, to_story_id=99, text="Tot mai departe."),
        ),
        closing=base.closing,
        cta=None,
    )
    entries = RuleContext.from_request(_request(draft)).component_texts
    transitions = tuple(
        item for item in entries if item.scope is ReviewScope.TRANSITION
    )
    assert tuple(
        (
            item.component_id,
            item.transition_from_story_position,
            item.transition_to_story_position,
        )
        for item in transitions
    ) == (("transition-01-02", 1, 2), ("transition-02-03", 2, 3))


def test_opening_and_closing_finding_locations_remain_unchanged():
    reviewer = DeterministicRulesReviewer(
        DeterministicEditorialRulePolicy(opening_max_words=1, closing_max_words=1)
    )
    first = reviewer.review(_request())
    second = reviewer.review(_request())
    by_code = {item.issue_code: item for item in first.findings}
    assert by_code["runtime.opening-too-long"].location.component_id == "opening"
    assert by_code["runtime.closing-too-long"].location.component_id == "closing"
    assert first.review_fingerprint == second.review_fingerprint


@pytest.mark.parametrize(
    ("rule_id", "trigger"),
    (
        ("language.placeholder-detected", "TODO"),
        ("language.unresolved-template-marker", "{{variable}}"),
        ("language.excessive-consecutive-punctuation", "Ce este asta!!!!"),
        ("language.markup-leakage", "Text cu <b>markup</b>."),
        ("language.control-character", "Text\x01controlat."),
        ("language.trailing-whitespace", "Text cu spații finale   \nUrmătorul rând."),
        ("language.repeated-inline-whitespace", "Text cu  două spații."),
    ),
)
def test_regex_backed_language_rule_emits_valid_deterministic_finding(rule_id, trigger):
    request = _request(_draft(commentary=trigger))
    reviewer = DeterministicRulesReviewer()
    first = reviewer.review(request)
    second = reviewer.review(request)
    finding = next(item for item in first.findings if item.issue_code == rule_id)
    assert finding.severity.name == "ERROR" and finding.blocking
    assert finding.location.component_id == "story-01"
    assert finding.evidence and finding.recommendation
    assert first == second
    assert validate_review_result(request, first) is first
    assert not any(
        rule_id in item.execution_key
        for item in reviewer.last_execution_result.failed_rules
    )


def test_clean_text_does_not_trigger_any_regex_backed_language_rule():
    result = DeterministicRulesReviewer().review(
        _request(_draft(commentary="Text normal, cu punctuație și spațiere corectă."))
    )
    regex_rule_ids = {
        rule.rule_id
        for rule in build_supported_rules()
        if rule.check in REGEX_CHECK_KEYS
    }
    assert not regex_rule_ids & {item.issue_code for item in result.findings}


def test_complete_rule_inventory_resolves_callable_checkers_and_regex_rules_share_one():
    rules = build_supported_rules()
    assert len(rules) == 40
    assert all(callable(resolve_checker(rule)) for rule in rules)
    regex_checkers = {
        resolve_checker(rule) for rule in rules if rule.check in REGEX_CHECK_KEYS
    }
    assert len(regex_checkers) == 1


def test_unknown_checker_still_fails_safely_without_partial_findings():
    malformed = replace(build_supported_rules()[0], check="missing_checker")
    registry = RuleRegistry((malformed,))
    execution = RuleEngine().execute(
        RuleContext.from_request(_request()), registry, registry.select()
    )
    assert execution.failed_rule_count == 1
    assert execution.findings == ()
    assert execution.failed_rules[0].failure_code.value == "RULE_EXCEPTION"


def test_regex_backed_transition_finding_reuses_canonical_location_fields():
    from pastila_scout.editor.generation.models import DraftTransition

    base = _draft()
    draft = DraftAssembler().assemble(
        episode_id=base.episode_id,
        story_order=(1, 2),
        opening=base.opening,
        stories=base.stories,
        transitions=(DraftTransition(from_story_id=1, to_story_id=2, text="TODO"),),
        closing=base.closing,
        cta=None,
    )
    request = _request(draft)
    result = DeterministicRulesReviewer().review(request)
    finding = next(
        item
        for item in result.findings
        if item.issue_code == "language.placeholder-detected"
        and item.scope is ReviewScope.TRANSITION
    )
    assert finding.location.component_id == "transition-01-02"
    assert finding.location.transition_from_story_position == 1
    assert finding.location.transition_to_story_position == 2
    assert validate_review_result(request, result) is result
