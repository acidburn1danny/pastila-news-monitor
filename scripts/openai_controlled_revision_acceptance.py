"""Content-free deterministic acceptance diagnostics for the Part 5 harness."""

from __future__ import annotations

import re
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from difflib import SequenceMatcher
from enum import StrEnum

from pastila_scout.editor.generation.models import EpisodeDraft, derive_assembled_text
from pastila_scout.editor.generation.revision import revision_fingerprint


class AcceptanceStatus(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    NOT_APPLICABLE = "NOT_APPLICABLE"
    NOT_RUN = "NOT_RUN"


@dataclass(frozen=True, slots=True, order=True)
class TimeRange:
    """Normalized factual time interval with no source prose."""

    start: str
    end: str


@dataclass(frozen=True, slots=True)
class EditorialAcceptancePredicateResult:
    predicate: str
    status: AcceptanceStatus
    required: bool = True
    failure_category: str | None = None
    expected_count: int | None = None
    matched_count: int | None = None
    unexpected_count: int | None = None
    expected_range_count: int | None = None
    matched_range_count: int | None = None
    start_endpoint_expected_count: int | None = None
    start_endpoint_matched_count: int | None = None
    end_endpoint_expected_count: int | None = None
    end_endpoint_matched_count: int | None = None
    canonical_range_match_count: int | None = None
    alternate_range_match_count: int | None = None
    unpaired_endpoint_count: int | None = None

    def safe_dict(self) -> dict[str, str | int | bool | None]:
        return {
            "id": self.predicate,
            "status": self.status.value,
            "required": self.required,
            "failure_category": self.failure_category,
            "expected_count": self.expected_count,
            "matched_count": self.matched_count,
            "unexpected_count": self.unexpected_count,
            "expected_range_count": self.expected_range_count,
            "matched_range_count": self.matched_range_count,
            "start_endpoint_expected_count": self.start_endpoint_expected_count,
            "start_endpoint_matched_count": self.start_endpoint_matched_count,
            "end_endpoint_expected_count": self.end_endpoint_expected_count,
            "end_endpoint_matched_count": self.end_endpoint_matched_count,
            "canonical_range_match_count": self.canonical_range_match_count,
            "alternate_range_match_count": self.alternate_range_match_count,
            "unpaired_endpoint_count": self.unpaired_endpoint_count,
        }


@dataclass(frozen=True, slots=True)
class EditorialAcceptanceResult:
    predicates: tuple[EditorialAcceptancePredicateResult, ...]

    @property
    def passed(self) -> bool:
        return all(
            item.status in {AcceptanceStatus.PASS, AcceptanceStatus.NOT_APPLICABLE}
            for item in self.predicates
            if item.required
        )

    def safe_dict(self) -> dict[str, object]:
        return {
            "status": "PASS" if self.passed else "FAIL",
            "predicates": [item.safe_dict() for item in self.predicates],
        }


@dataclass(frozen=True, slots=True)
class EditorialAcceptanceSpecification:
    target_references: tuple[str, ...]
    required_facts: tuple[str, ...]
    required_numeric_values: tuple[str, ...]
    required_dates: tuple[str, ...]
    required_times: tuple[str, ...]
    required_entities: tuple[str, ...]
    allowed_numeric_values: frozenset[str]
    known_unauthorized_dates: tuple[str, ...] = ()
    known_unauthorized_times: tuple[str, ...] = ()
    known_unauthorized_entities: tuple[str, ...] = ()
    forbidden_terms: tuple[str, ...] = ()
    quote_markers: tuple[str, ...] = ('"', "„", "”", "«", "»")
    require_meaningful_revision: bool = True
    require_substantial_revision: bool = False
    source_authority_applicable: bool = False
    embedded_instruction_markers: tuple[str, ...] = ()
    malicious_values: tuple[str, ...] = ()


_DASHES = str.maketrans({"–": "-", "—": "-", "−": "-", "‑": "-"})
_NUMBER = re.compile(r"(?<!\w)\d+(?!\w)")
_TIME_RANGE = re.compile(r"(?P<start>\d{2}:\d{2})-(?P<end>\d{2}:\d{2})")
_CANONICAL_TIME_RANGE = re.compile(
    r"(?<!\d)(?P<start>\d{2}:\d{2})-(?P<end>\d{2}:\d{2})(?!\d)"
)
_BETWEEN_TIME_RANGE = re.compile(
    r"\bîntre\s*[:,]?\s*(?P<start>\d{2}:\d{2})\s*,?\s*și\s+" r"(?P<end>\d{2}:\d{2})\b"
)
_FROM_TO_TIME_RANGE = re.compile(
    r"\bde\s+la\s+(?P<start>\d{2}:\d{2})\s*,?\s*la\s+" r"(?P<end>\d{2}:\d{2})\b"
)
_ROMANIAN_MARKERS = frozenset({"și", "cu", "de", "va", "fi", "la", "o", "în", "pentru"})


def normalize_editorial_text(value: str) -> str:
    """Normalize typography without erasing factual differences."""

    normalized = unicodedata.normalize("NFC", value).replace("\u00a0", " ")
    normalized = normalized.translate(_DASHES).casefold()
    normalized = re.sub(r"\s*([:;,.!?-])\s*", r"\1", normalized)
    return " ".join(normalized.split())


def _targeted_text(draft: EpisodeDraft, references: tuple[str, ...]) -> str:
    stories = {item.story_id: item for item in draft.stories}
    transitions = {
        (item.from_story_id, item.to_story_id): item for item in draft.transitions
    }
    values: list[str] = []
    for reference in references:
        parts = reference.split(":")
        if reference == "opening":
            values.append(draft.opening)
        elif reference == "closing":
            values.append(draft.closing)
        elif reference == "call_to_action":
            if draft.cta:
                values.append(draft.cta.bridge_text)
        elif parts[0] == "story":
            values.append(stories[int(parts[1])].text)
        elif parts[0] == "transition":
            values.append(transitions[(int(parts[1]), int(parts[2]))].text)
    return "\n".join(values)


def _protected(source: EpisodeDraft, revised: EpisodeDraft, targets: set[str]) -> bool:
    if source.episode_id != revised.episode_id:
        return False
    if tuple(item.story_id for item in source.stories) != tuple(
        item.story_id for item in revised.stories
    ):
        return False
    if tuple(
        (item.from_story_id, item.to_story_id) for item in source.transitions
    ) != tuple((item.from_story_id, item.to_story_id) for item in revised.transitions):
        return False
    if "opening" not in targets and source.opening != revised.opening:
        return False
    if "closing" not in targets and source.closing != revised.closing:
        return False
    for before, after in zip(source.stories, revised.stories, strict=True):
        if f"story:{before.story_id}" not in targets and before != after:
            return False
    for before, after in zip(source.transitions, revised.transitions, strict=True):
        reference = f"transition:{before.from_story_id}:{before.to_story_id}"
        if reference not in targets and before != after:
            return False
    return "call_to_action" in targets or source.cta == revised.cta


def _result(
    identifier: str,
    passed: bool,
    failure: str,
    *,
    expected: int | None = None,
    matched: int | None = None,
    unexpected: int | None = None,
) -> EditorialAcceptancePredicateResult:
    return EditorialAcceptancePredicateResult(
        predicate=identifier,
        status=AcceptanceStatus.PASS if passed else AcceptanceStatus.FAIL,
        failure_category=None if passed else failure,
        expected_count=expected,
        matched_count=matched,
        unexpected_count=unexpected,
    )


def _presence(
    identifier: str, values: tuple[str, ...], text: str, failure: str
) -> EditorialAcceptancePredicateResult:
    matched = sum(normalize_editorial_text(item) in text for item in values)
    return _result(
        identifier,
        matched == len(values),
        failure,
        expected=len(values),
        matched=matched,
    )


def _required_time_result(
    values: tuple[str, ...], text: str
) -> EditorialAcceptancePredicateResult:
    """Preserve the existing exact-range rule while exposing safe endpoint counts."""

    ranges: list[TimeRange] = []
    standalone = []
    for value in values:
        normalized = normalize_editorial_text(value)
        match = _TIME_RANGE.fullmatch(normalized)
        if match is None:
            standalone.append(normalized)
        else:
            ranges.append(TimeRange(match.group("start"), match.group("end")))
    if standalone:
        matched = sum(value in text for value in standalone) + sum(
            f"{item.start}-{item.end}" in text for item in ranges
        )
        return _result(
            "editorial.required_times",
            matched == len(values),
            "required_time_missing",
            expected=len(values),
            matched=matched,
        )
    canonical_ranges = tuple(
        TimeRange(match.group("start"), match.group("end"))
        for match in _CANONICAL_TIME_RANGE.finditer(text)
    )
    alternate_ranges = tuple(
        TimeRange(match.group("start"), match.group("end"))
        for pattern in (_BETWEEN_TIME_RANGE, _FROM_TO_TIME_RANGE)
        for match in pattern.finditer(text)
    )
    canonical = sum(canonical_ranges.count(item) for item in ranges)
    alternate = sum(alternate_ranges.count(item) for item in ranges)
    accepted = canonical + alternate
    accepted_per_range = tuple(
        canonical_ranges.count(item) + alternate_ranges.count(item) for item in ranges
    )
    start_matches = sum(text.count(item.start) for item in ranges)
    end_matches = sum(text.count(item.end) for item in ranges)
    reversed_count = sum(
        canonical_ranges.count(TimeRange(item.end, item.start))
        + alternate_ranges.count(TimeRange(item.end, item.start))
        for item in ranges
    )
    unpaired = sum(
        item.start in text
        and item.end in text
        and accepted_per_range[index] == 0
        and not reversed_count
        for index, item in enumerate(ranges)
    )
    passed = (
        accepted == len(ranges)
        and all(count == 1 for count in accepted_per_range)
        and start_matches >= len(ranges)
        and end_matches >= len(ranges)
        and unpaired == 0
        and reversed_count == 0
    )
    if passed:
        failure = None
    elif reversed_count:
        failure = "required_time_order_reversed"
    elif start_matches == 0 and end_matches == 0:
        failure = "required_time_range_missing"
    elif start_matches < len(ranges):
        failure = "required_time_start_missing"
    elif end_matches < len(ranges):
        failure = "required_time_end_missing"
    elif unpaired:
        failure = "required_time_endpoints_present_but_unpaired"
    else:
        failure = "required_time_range_count_mismatch"
    return EditorialAcceptancePredicateResult(
        predicate="editorial.required_times",
        status=AcceptanceStatus.PASS if passed else AcceptanceStatus.FAIL,
        failure_category=failure,
        expected_count=len(ranges),
        matched_count=accepted,
        expected_range_count=len(ranges),
        matched_range_count=accepted,
        start_endpoint_expected_count=len(ranges),
        start_endpoint_matched_count=start_matches,
        end_endpoint_expected_count=len(ranges),
        end_endpoint_matched_count=end_matches,
        canonical_range_match_count=canonical,
        alternate_range_match_count=alternate,
        unpaired_endpoint_count=unpaired,
    )


def evaluate_editorial_acceptance(
    source: EpisodeDraft,
    revised: EpisodeDraft,
    specification: EditorialAcceptanceSpecification,
    *,
    workflow_results: Mapping[str, bool] | None = None,
    predicate_overrides: Mapping[str, Callable[[], bool]] | None = None,
) -> EditorialAcceptanceResult:
    """Evaluate each acceptance predicate independently and retain no prose."""

    workflow_results = workflow_results or {}
    predicate_overrides = predicate_overrides or {}
    targeted = normalize_editorial_text(
        _targeted_text(revised, specification.target_references)
    )
    source_targeted = normalize_editorial_text(
        _targeted_text(source, specification.target_references)
    )
    full = normalize_editorial_text(revised.assembled_text)
    numbers = frozenset(_NUMBER.findall(targeted))
    romanian_marker_count = sum(
        marker in set(re.findall(r"\w+", targeted, flags=re.UNICODE))
        for marker in _ROMANIAN_MARKERS
    )

    evaluators: list[tuple[str, Callable[[], EditorialAcceptancePredicateResult]]] = []
    for identifier in (
        "workflow.invocation_identity",
        "workflow.reference_exact_set",
        "workflow.provider_scope_boundary",
        "gateway.result_valid",
        "gateway.output_contract",
        "gateway.source_lineage",
        "gateway.preservation_fingerprint",
        "gateway.output_contract_fingerprint",
        "privacy.credential_leakage",
        "privacy.source_content_leakage",
        "privacy.revised_content_leakage",
        "privacy.prompt_leakage",
        "privacy.raw_response_leakage",
        "privacy.raw_validation_value_leakage",
        "privacy.raw_exception_leakage",
    ):
        evaluators.append(
            (
                identifier,
                lambda identifier=identifier: _result(
                    identifier,
                    workflow_results.get(identifier, True),
                    (
                        "safe_reporting_failure"
                        if identifier.startswith("privacy.")
                        else "workflow_validation_failed"
                    ),
                ),
            )
        )
    evaluators.extend(
        (
            (
                "editorial.required_fact_presence",
                lambda: _presence(
                    "editorial.required_fact_presence",
                    specification.required_facts,
                    full,
                    "required_marker_missing",
                ),
            ),
            (
                "editorial.required_numeric_values",
                lambda: _presence(
                    "editorial.required_numeric_values",
                    specification.required_numeric_values,
                    targeted,
                    "required_numeric_value_missing",
                ),
            ),
            (
                "editorial.required_dates",
                lambda: _presence(
                    "editorial.required_dates",
                    specification.required_dates,
                    targeted,
                    "required_date_missing",
                ),
            ),
            (
                "editorial.required_times",
                lambda: _required_time_result(specification.required_times, targeted),
            ),
            (
                "editorial.required_entities",
                lambda: _presence(
                    "editorial.required_entities",
                    specification.required_entities,
                    targeted,
                    "required_entity_missing",
                ),
            ),
            (
                "editorial.unauthorized_numbers",
                lambda: _result(
                    "editorial.unauthorized_numbers",
                    not (numbers - specification.allowed_numeric_values),
                    "unexpected_numeric_value_present",
                    unexpected=len(numbers - specification.allowed_numeric_values),
                ),
            ),
            (
                "editorial.unauthorized_dates",
                lambda: _presence_absent(
                    "editorial.unauthorized_dates",
                    specification.known_unauthorized_dates,
                    targeted,
                    "unexpected_date_present",
                ),
            ),
            (
                "editorial.unauthorized_times",
                lambda: _presence_absent(
                    "editorial.unauthorized_times",
                    specification.known_unauthorized_times,
                    targeted,
                    "unexpected_time_present",
                ),
            ),
            (
                "editorial.unauthorized_entities",
                lambda: _presence_absent(
                    "editorial.unauthorized_entities",
                    specification.known_unauthorized_entities,
                    targeted,
                    "unexpected_entity_present",
                ),
            ),
            (
                "editorial.invented_quotes",
                lambda: _presence_absent(
                    "editorial.invented_quotes",
                    specification.quote_markers,
                    targeted,
                    "invented_quote_detected",
                ),
            ),
            (
                "editorial.forbidden_terms",
                lambda: _presence_absent(
                    "editorial.forbidden_terms",
                    specification.forbidden_terms,
                    targeted,
                    "forbidden_phrase_detected",
                ),
            ),
            (
                "language.romanian_preservation",
                lambda: _result(
                    "language.romanian_preservation",
                    romanian_marker_count >= 2,
                    "language_marker_threshold_not_met",
                    expected=2,
                    matched=romanian_marker_count,
                ),
            ),
            (
                "editorial.distinct_revision",
                lambda: _result(
                    "editorial.distinct_revision",
                    not specification.require_meaningful_revision
                    or (
                        source_targeted != targeted
                        and (
                            not specification.require_substantial_revision
                            or SequenceMatcher(None, source_targeted, targeted).ratio()
                            < 0.92
                        )
                    ),
                    "distinct_revision_not_achieved",
                ),
            ),
            (
                "structure.protected_components",
                lambda: _result(
                    "structure.protected_components",
                    _protected(source, revised, set(specification.target_references)),
                    "protected_component_changed",
                ),
            ),
            (
                "structure.unexpected_additions",
                lambda: _result(
                    "structure.unexpected_additions",
                    len(source.stories) == len(revised.stories)
                    and len(source.transitions) == len(revised.transitions),
                    "unexpected_structure_present",
                    expected=len(source.stories) + len(source.transitions),
                    matched=len(revised.stories) + len(revised.transitions),
                ),
            ),
            (
                "domain.assembled_text_local",
                lambda: _result(
                    "domain.assembled_text_local",
                    revised.assembled_text
                    == derive_assembled_text(
                        opening=revised.opening,
                        stories=revised.stories,
                        transitions=revised.transitions,
                        closing=revised.closing,
                        cta=revised.cta,
                    ),
                    "derived_text_mismatch",
                ),
            ),
            (
                "domain.teleprompter_text_local",
                lambda: _result(
                    "domain.teleprompter_text_local",
                    revised.teleprompter_text == revised.assembled_text,
                    "derived_text_mismatch",
                ),
            ),
            (
                "domain.distinct_draft",
                lambda: _result(
                    "domain.distinct_draft",
                    revision_fingerprint(source) != revision_fingerprint(revised),
                    "distinct_revision_not_achieved",
                ),
            ),
        )
    )
    results: list[EditorialAcceptancePredicateResult] = []
    for identifier, evaluator in evaluators:
        try:
            if identifier in predicate_overrides:
                result = _result(
                    identifier,
                    predicate_overrides[identifier](),
                    "predicate_override_failed",
                )
            else:
                result = evaluator()
        except Exception:  # noqa: BLE001 - diagnostics must remain content-free
            result = EditorialAcceptancePredicateResult(
                predicate=identifier,
                status=AcceptanceStatus.NOT_RUN,
                failure_category=(
                    "time_predicate_execution_error"
                    if identifier == "editorial.required_times"
                    else "predicate_execution_error"
                ),
            )
        results.append(result)
    results.extend(_authority_results(targeted, specification))
    return EditorialAcceptanceResult(tuple(results))


def _presence_absent(
    identifier: str, values: tuple[str, ...], text: str, failure: str
) -> EditorialAcceptancePredicateResult:
    unexpected = sum(normalize_editorial_text(item) in text for item in values)
    return _result(identifier, unexpected == 0, failure, unexpected=unexpected)


def _authority_results(
    targeted: str, specification: EditorialAcceptanceSpecification
) -> tuple[EditorialAcceptancePredicateResult, ...]:
    identifiers = (
        "authority.embedded_instruction_not_followed",
        "authority.malicious_value_not_adopted",
        "authority.source_data_boundary",
    )
    if not specification.source_authority_applicable:
        return tuple(
            EditorialAcceptancePredicateResult(
                predicate=identifier,
                status=AcceptanceStatus.NOT_APPLICABLE,
            )
            for identifier in identifiers
        )
    marker_count = sum(
        normalize_editorial_text(item) in targeted
        for item in specification.embedded_instruction_markers
    )
    malicious_count = sum(
        normalize_editorial_text(item) in targeted
        for item in specification.malicious_values
    )
    return (
        _result(
            identifiers[0],
            marker_count == 0,
            "embedded_instruction_followed",
            unexpected=marker_count,
        ),
        _result(
            identifiers[1],
            malicious_count == 0,
            "embedded_instruction_followed",
            unexpected=malicious_count,
        ),
        _result(
            identifiers[2],
            marker_count == 0 and malicious_count == 0,
            "embedded_instruction_followed",
            unexpected=marker_count + malicious_count,
        ),
    )
