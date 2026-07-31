"""Deterministic, rule-driven editorial selection without text generation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from pastila_scout.contracts.common import ContractStatus
from pastila_scout.contracts.editor_output import (
    EditorAgentOutputV1,
    validate_editor_output_against_input,
)
from pastila_scout.contracts.episode_context import EpisodeContextV1
from pastila_scout.contracts.identity import canonical_json_bytes
from pastila_scout.contracts.scout_editor import (
    RankedEditorialEvent,
    ScoutEditorInputV1,
)
from pastila_scout.contracts.selection_profile import (
    MinimumPolicy,
    ProviderPolicy,
    SelectionProfileV1,
)
from pastila_scout.editor.models import (
    DecisionOutcome,
    DecisionTrace,
    EditorialDecision,
    EditorialReason,
)
from pastila_scout.editor.rules import (
    DEFAULT_RULES,
    BackupQualityRule,
    EditorialConfidenceRule,
    EditorialRule,
    SelectionState,
)

EDITOR_AGENT_VERSION = "deterministic-selection-v1"


@dataclass(frozen=True)
class EditorialSelectionResult:
    """Public output plus the complete private deterministic decision trace."""

    output: EditorAgentOutputV1
    trace: DecisionTrace


class SelectionEngine:
    """Apply independent rules and resolve their decisions deterministically."""

    def __init__(
        self,
        rules: tuple[EditorialRule, ...] = DEFAULT_RULES,
        *,
        minimum_story_seconds: int = 60,
        backup_rule: BackupQualityRule | None = None,
        confidence_rule: EditorialConfidenceRule | None = None,
    ) -> None:
        if minimum_story_seconds <= 0:
            raise ValueError("minimum_story_seconds must be positive")
        self.rules = rules
        self.minimum_story_seconds = minimum_story_seconds
        self.backup_rule = backup_rule or BackupQualityRule()
        self.confidence_rule = confidence_rule or EditorialConfidenceRule()

    def select(
        self,
        scout_input: ScoutEditorInputV1,
        profile: SelectionProfileV1,
        context: EpisodeContextV1,
    ) -> EditorialSelectionResult:
        """Produce a reproducible contract proposal and private trace."""

        preflight = self._preflight(scout_input, profile, context)
        if preflight:
            status = (
                ContractStatus.PROVIDER_UNAVAILABLE
                if any(item.reason.code == "provider_required" for item in preflight)
                else ContractStatus.INVALID_INPUT
            )
            return self._failure(scout_input, profile, context, status, preflight)

        decisions: list[EditorialDecision] = []
        conflicts: list[EditorialDecision] = []
        selected: list[RankedEditorialEvent] = []
        hard_rejected: set[int] = set()
        remaining = list(scout_input.ranked_events)
        selection_decisions: dict[int, tuple[EditorialDecision, ...]] = {}

        while remaining and len(selected) < context.target_story_count:
            state = self._state(selected, context)
            evaluated: list[
                tuple[
                    float,
                    tuple[object, ...],
                    RankedEditorialEvent,
                    tuple[EditorialDecision, ...],
                ]
            ] = []
            next_remaining: list[RankedEditorialEvent] = []
            for candidate in remaining:
                candidate_decisions = tuple(
                    rule.evaluate(candidate, state, profile, context)
                    for rule in self.rules
                )
                decisions.extend(candidate_decisions)
                rejected = [
                    item
                    for item in candidate_decisions
                    if item.outcome == DecisionOutcome.REJECTED and item.hard
                ]
                if rejected:
                    hard_rejected.add(candidate.event_id)
                    continue
                contribution = sum(item.contribution for item in candidate_decisions)
                evaluated.append(
                    (
                        contribution,
                        self._candidate_tie_key(candidate),
                        candidate,
                        candidate_decisions,
                    )
                )
                next_remaining.append(candidate)
            if not evaluated:
                break
            _, _, winner, winner_decisions = max(
                evaluated,
                key=lambda item: (item[0], item[1]),
            )
            selected.append(winner)
            selection_decisions[winner.event_id] = winner_decisions
            remaining = [
                item for item in next_remaining if item.event_id != winner.event_id
            ]

        ordered = tuple(
            sorted(selected, key=lambda event: (event.rank, event.event_id))
        )
        backup_candidates = tuple(
            event
            for event in scout_input.ranked_events
            if event.event_id not in {item.event_id for item in ordered}
            and event.event_id not in hard_rejected
            and event.event_id not in context.excluded_event_ids
        )
        backups = self._select_backups(backup_candidates, ordered, profile.backup_count)
        decisions.extend(self._presentation_decisions(ordered, backups))
        warnings, constraint_conflicts = self._constraint_diagnostics(
            ordered, profile, context
        )
        decisions.extend(constraint_conflicts)
        conflicts.extend(constraint_conflicts)
        status = (
            ContractStatus.SUCCESS
            if len(ordered) == context.target_story_count and not constraint_conflicts
            else ContractStatus.INSUFFICIENT_CANDIDATES
        )
        output = self._build_output(
            scout_input,
            profile,
            context,
            ordered,
            backups,
            selection_decisions,
            hard_rejected,
            warnings,
            status,
        )
        validate_editor_output_against_input(
            output,
            scout_input,
            selection_profile=profile,
            episode_context=context,
        )
        used = {item.event_id for item in (*ordered, *backups)}
        rejected_ids = tuple(
            event.event_id
            for event in scout_input.ranked_events
            if event.event_id not in used
        )
        trace = DecisionTrace(
            decisions=tuple(decisions),
            selected_event_ids=tuple(item.event_id for item in ordered),
            backup_event_ids=tuple(item.event_id for item in backups),
            rejected_event_ids=rejected_ids,
            conflicts=tuple(conflicts),
        )
        return EditorialSelectionResult(output=output, trace=trace)

    def _preflight(
        self,
        scout_input: ScoutEditorInputV1,
        profile: SelectionProfileV1,
        context: EpisodeContextV1,
    ) -> tuple[EditorialDecision, ...]:
        conflicts: list[EditorialDecision] = []

        def conflict(code: str, message: str, event_id: int | None = None) -> None:
            conflicts.append(
                EditorialDecision(
                    rule="preflight_constraint",
                    outcome=DecisionOutcome.CONFLICT,
                    reason=EditorialReason(code=code, message=message),
                    event_id=event_id,
                    hard=True,
                )
            )

        if profile.provider_policy == ProviderPolicy.REQUIRED:
            conflict(
                "provider_required",
                "Deterministic selection cannot satisfy a required provider policy.",
            )
        if profile.target_story_count != context.target_story_count:
            conflict(
                "target_size_conflict",
                "Selection profile and episode context request different story counts.",
            )
        mandatory = set(context.mandatory_event_ids)
        excluded = set(context.excluded_event_ids)
        for event_id in sorted(mandatory.intersection(excluded)):
            conflict(
                "mandatory_excluded_conflict",
                "The same event is mandatory and excluded.",
                event_id,
            )
        available = {event.event_id for event in scout_input.ranked_events}
        for event_id in sorted(mandatory.difference(available)):
            conflict(
                "mandatory_event_unavailable",
                "A mandatory event is absent from the Scout input.",
                event_id,
            )
        if len(mandatory) > context.target_story_count:
            conflict(
                "too_many_mandatory_events",
                "Mandatory events exceed the requested episode size.",
            )
        if (
            context.target_story_count * self.minimum_story_seconds
            > context.target_runtime.value
        ):
            conflict(
                "runtime_overflow",
                "Requested story count cannot fit the minimum treatment runtime.",
            )
        mandatory_events = [
            event for event in scout_input.ranked_events if event.event_id in mandatory
        ]
        for category, constraint in profile.category_constraints.items():
            mandatory_count = sum(
                category in event.categories for event in mandatory_events
            )
            maximum = min(constraint.maximum, profile.maximum_stories_from_one_category)
            if mandatory_count > maximum:
                conflict(
                    "mandatory_category_conflict",
                    f"Mandatory events exceed the maximum for {category}.",
                )
        return tuple(conflicts)

    def _failure(
        self,
        scout_input: ScoutEditorInputV1,
        profile: SelectionProfileV1,
        context: EpisodeContextV1,
        status: ContractStatus,
        conflicts: tuple[EditorialDecision, ...],
    ) -> EditorialSelectionResult:
        errors = tuple(
            {
                "code": item.reason.code,
                "message": item.reason.message,
                "event_id": item.event_id,
                "recoverable": False,
            }
            for item in conflicts
        )
        output = EditorAgentOutputV1.model_validate_json(
            canonical_json_bytes(
                {
                    **self._output_envelope(scout_input, profile, context),
                    "status": status,
                    "episode_proposal": None,
                    "errors": errors,
                    "extensions": {},
                }
            )
        )
        trace = DecisionTrace(
            decisions=conflicts,
            selected_event_ids=(),
            backup_event_ids=(),
            rejected_event_ids=tuple(
                event.event_id for event in scout_input.ranked_events
            ),
            conflicts=conflicts,
        )
        return EditorialSelectionResult(output=output, trace=trace)

    def _state(
        self,
        selected: list[RankedEditorialEvent],
        context: EpisodeContextV1,
    ) -> SelectionState:
        category_counts: dict[str, int] = {}
        source_ids: set[str] = set()
        for event in selected:
            for category in event.categories:
                category_counts[category] = category_counts.get(category, 0) + 1
            source_ids.update(item.source_id for item in event.source_provenance)
        return SelectionState(
            selected=tuple(selected),
            category_counts=category_counts,
            source_ids=frozenset(source_ids),
            target_runtime_seconds=context.target_runtime.value,
            minimum_story_seconds=self.minimum_story_seconds,
        )

    @staticmethod
    def _candidate_tie_key(candidate: RankedEditorialEvent) -> tuple[object, ...]:
        timestamp = _timestamp(candidate.publication_bounds.last_published_at)
        return (
            candidate.final_score,
            timestamp,
            -candidate.score_rank,
            -candidate.event_id,
        )

    def _select_backups(
        self,
        candidates: tuple[RankedEditorialEvent, ...],
        selected: tuple[RankedEditorialEvent, ...],
        count: int,
    ) -> tuple[RankedEditorialEvent, ...]:
        ordered = sorted(candidates, key=self.backup_rule.order_key)
        return tuple(ordered[:count])

    def _constraint_diagnostics(
        self,
        selected: tuple[RankedEditorialEvent, ...],
        profile: SelectionProfileV1,
        context: EpisodeContextV1,
    ) -> tuple[tuple[dict[str, object], ...], tuple[EditorialDecision, ...]]:
        warnings: list[dict[str, object]] = []
        conflicts: list[EditorialDecision] = []
        category_counts = {
            category: sum(category in event.categories for event in selected)
            for category in profile.category_constraints
        }
        for category, constraint in profile.category_constraints.items():
            if category_counts[category] < constraint.minimum:
                hard = constraint.minimum_policy == MinimumPolicy.HARD
                item = EditorialDecision(
                    rule="category_balance",
                    outcome=DecisionOutcome.CONFLICT,
                    reason=EditorialReason(
                        code="category_minimum_unmet",
                        message=f"Category minimum is unmet for {category}.",
                    ),
                    hard=hard,
                )
                if hard:
                    conflicts.append(item)
                warnings.append(
                    {
                        "code": item.reason.code,
                        "message": item.reason.message,
                        "event_id": None,
                        "recoverable": not hard,
                    }
                )
        source_ids = {
            item.source_id for event in selected for item in event.source_provenance
        }
        if len(source_ids) < profile.minimum_source_diversity:
            item = EditorialDecision(
                rule="source_diversity",
                outcome=DecisionOutcome.CONFLICT,
                reason=EditorialReason(
                    code="source_diversity_unmet",
                    message="Minimum source diversity is unmet.",
                ),
                hard=True,
            )
            conflicts.append(item)
            warnings.append(
                {
                    "code": item.reason.code,
                    "message": item.reason.message,
                    "event_id": None,
                    "recoverable": False,
                }
            )
        if len(selected) < context.target_story_count:
            warnings.append(
                {
                    "code": "insufficient_candidates",
                    "message": "Fewer eligible stories were available than requested.",
                    "event_id": None,
                    "recoverable": True,
                }
            )
        return tuple(warnings), tuple(conflicts)

    def _build_output(
        self,
        scout_input: ScoutEditorInputV1,
        profile: SelectionProfileV1,
        context: EpisodeContextV1,
        selected: tuple[RankedEditorialEvent, ...],
        backups: tuple[RankedEditorialEvent, ...],
        selection_decisions: dict[int, tuple[EditorialDecision, ...]],
        hard_rejected: set[int],
        warnings: tuple[dict[str, object], ...],
        status: ContractStatus,
    ) -> EditorAgentOutputV1:
        durations = _allocate_durations(
            len(selected), context.target_story_count, context.target_runtime.value
        )
        selected_data = [
            self._selected_story(
                event,
                position,
                durations[position - 1],
                selected,
                selection_decisions[event.event_id],
                context,
            )
            for position, event in enumerate(selected, start=1)
        ]
        backup_data = [
            self._backup_story(event, position, selected, context)
            for position, event in enumerate(backups, start=1)
        ]
        flow = [
            self._flow_step(event, position, selected)
            for position, event in enumerate(selected, start=1)
        ]
        selected_ids = {event.event_id for event in selected}
        backup_ids = {event.event_id for event in backups}
        unused = [
            event
            for event in scout_input.ranked_events
            if event.event_id not in selected_ids | backup_ids
            and event.recommendation in {"STRONG_PICK", "POSSIBLE_PICK"}
        ][:5]
        excluded_count = sum(
            event.event_id in hard_rejected
            for event in scout_input.ranked_events
            if event.event_id not in selected_ids | backup_ids
        )
        otherwise = (
            len(scout_input.ranked_events)
            - len(selected)
            - len(backups)
            - excluded_count
        )
        notable = [
            {
                "event_id": event.event_id,
                "reason_code": "editorial_constraint",
                "reason": "Event was excluded by a deterministic constraint.",
                "extensions": {},
            }
            for event in scout_input.ranked_events
            if event.event_id in hard_rejected
        ][:5]
        notes = tuple(
            dict.fromkeys(
                "Review unresolved deterministic constraints before publication."
                for _ in warnings
            )
        )
        data = {
            **self._output_envelope(scout_input, profile, context),
            "status": status,
            "episode_proposal": {
                "episode_title_suggestion": "Propunere editorială deterministă",
                "editorial_angle": context.episode_objective,
                "estimated_total_runtime": {
                    "unit": "seconds",
                    "value": sum(durations),
                },
                "selected_stories": selected_data,
                "backup_stories": backup_data,
                "episode_flow": flow,
                "rejection_summary": {
                    "total_candidates": len(scout_input.ranked_events),
                    "selected": len(selected),
                    "backups": len(backups),
                    "excluded_by_constraints": excluded_count,
                    "semantically_redundant": 0,
                    "otherwise_not_selected": otherwise,
                    "notable_exclusions": notable,
                    "unused_strong_candidates": [
                        {
                            "event_id": event.event_id,
                            "canonical_title": event.canonical_title,
                            "scout_recommendation": event.recommendation,
                            "final_score": event.final_score,
                            "exclusion_reason_code": (
                                "editorial_constraint"
                                if event.event_id in hard_rejected
                                else "episode_capacity"
                            ),
                            "exclusion_reason": (
                                "Excluded by a deterministic editorial constraint."
                                if event.event_id in hard_rejected
                                else "Not used because the episode reached its capacity."
                            ),
                            "extensions": {},
                        }
                        for event in unused
                    ],
                    "extensions": {},
                },
                "warnings": warnings,
                "editorial_notes": notes,
                "overall_selection_reasoning": (
                    "Deterministic rules selected and ordered the available Scout events."
                ),
                "extensions": {},
            },
            "errors": (),
            "extensions": {},
        }
        return EditorAgentOutputV1.model_validate_json(canonical_json_bytes(data))

    @staticmethod
    def _output_envelope(
        scout_input: ScoutEditorInputV1,
        profile: SelectionProfileV1,
        context: EpisodeContextV1,
    ) -> dict[str, object]:
        return {
            "contract_version": "editor-agent-output-v1",
            "editorial_contract_version": scout_input.editorial_contract_version,
            "generated_at": scout_input.generated_at,
            "editor_agent_version": EDITOR_AGENT_VERSION,
            "source_report_id": scout_input.report_id,
            "source_contract_version": scout_input.contract_version,
            "source_content_fingerprint": scout_input.content_fingerprint,
            "selection_profile": {
                "name": profile.profile_name,
                "version": profile.profile_version,
                "extensions": {},
            },
            "requested_episode_size": context.target_story_count,
        }

    def _selected_story(
        self,
        event: RankedEditorialEvent,
        position: int,
        duration: int,
        selected: tuple[RankedEditorialEvent, ...],
        decisions: tuple[EditorialDecision, ...],
        context: EpisodeContextV1,
    ) -> dict[str, object]:
        mandatory = event.event_id in context.mandatory_event_ids
        supports_preference = any(
            item.reason.code == "category_preference" and item.contribution > 0
            for item in decisions
        )
        confidence = self.confidence_rule.calculate(
            event,
            mandatory=mandatory,
            supports_category_preference=supports_preference,
        )
        role = _role(position, len(selected))
        return {
            "position": position,
            "event_id": event.event_id,
            "canonical_title": event.canonical_title,
            "episode_role": role,
            "selection_reason": (
                "mandatory_event" if mandatory else "selected_by_rule_priority"
            ),
            "transition_reason": (
                None if position == 1 else "deterministic_flow_transition"
            ),
            "tone_recommendation": "Follow the configured episode tone.",
            "factual_editorial_risks": event.editorial_risks,
            "suggested_treatment_length": {"unit": "seconds", "value": duration},
            "editorial_confidence": confidence,
            "source_references": tuple(
                item.model_dump(mode="python") for item in event.source_provenance
            ),
            "inherited_scout_scores": _inherited_scores(event),
            "extensions": {},
        }

    def _backup_story(
        self,
        event: RankedEditorialEvent,
        position: int,
        selected: tuple[RankedEditorialEvent, ...],
        context: EpisodeContextV1,
    ) -> dict[str, object]:
        replacement = self._replacement_for(event, selected)
        confidence = self.confidence_rule.calculate(
            event,
            mandatory=False,
            supports_category_preference=False,
            backup=True,
        )
        duration = (
            context.target_runtime.value // context.target_story_count
            if context.target_story_count
            else 0
        )
        return {
            "position": position,
            "event_id": event.event_id,
            "canonical_title": event.canonical_title,
            "selection_reason": "highest_remaining_backup_quality",
            "tone_recommendation": "Follow the configured episode tone.",
            "factual_editorial_risks": event.editorial_risks,
            "suggested_treatment_length": {"unit": "seconds", "value": duration},
            "editorial_confidence": confidence,
            "replacement_for": replacement,
            "source_references": tuple(
                item.model_dump(mode="python") for item in event.source_provenance
            ),
            "inherited_scout_scores": _inherited_scores(event),
            "extensions": {},
        }

    def _flow_step(
        self,
        event: RankedEditorialEvent,
        position: int,
        selected: tuple[RankedEditorialEvent, ...],
    ) -> dict[str, object]:
        transition = None if position == 1 else "hard_cut"
        return {
            "position": position,
            "event_id": event.event_id,
            "role": _role(position, len(selected)),
            "placement_reason": (
                "opening_strength"
                if position == 1
                else (
                    "ending_strength"
                    if position == len(selected)
                    else "deterministic_middle_order"
                )
            ),
            "expected_transition_type": transition,
            "extensions": {},
        }

    def _replacement_for(
        self,
        backup: RankedEditorialEvent,
        selected: tuple[RankedEditorialEvent, ...],
    ) -> int | None:
        if not selected:
            return None
        return min(
            selected,
            key=lambda event: self.backup_rule.replacement_key(backup, event),
        ).event_id

    def _presentation_decisions(
        self,
        selected: tuple[RankedEditorialEvent, ...],
        backups: tuple[RankedEditorialEvent, ...],
    ) -> tuple[EditorialDecision, ...]:
        decisions: list[EditorialDecision] = []
        for event in selected:
            decisions.append(
                EditorialDecision(
                    rule=self.confidence_rule.name,
                    outcome=DecisionOutcome.APPLIED,
                    reason=EditorialReason(
                        code="editorial_confidence_assigned",
                        message="Editorial confidence was calculated deterministically.",
                    ),
                    event_id=event.event_id,
                )
            )
        decisions.extend(
            EditorialDecision(
                rule=self.backup_rule.name,
                outcome=DecisionOutcome.APPLIED,
                reason=EditorialReason(
                    code="backup_selected",
                    message="Backup quality rule selected this event.",
                ),
                event_id=event.event_id,
            )
            for event in backups
        )
        return tuple(decisions)


def _allocate_durations(count: int, requested: int, runtime: int) -> tuple[int, ...]:
    if count == 0:
        return ()
    base = runtime // requested
    durations = [base] * count
    if count == requested:
        for index in range(runtime - base * count):
            durations[index % count] += 1
    return tuple(durations)


def _timestamp(value: datetime | None) -> float:
    if value is None:
        return float("-inf")
    parsed = value
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.timestamp()


def _role(position: int, count: int) -> str:
    if position == 1:
        return "opening"
    if position == count:
        return "closing"
    return "development"


def _inherited_scores(event: RankedEditorialEvent) -> dict[str, object]:
    return {
        "deterministic_score": event.deterministic_score.score,
        "ai_editorial_score": (
            event.ai_editorial_score.score
            if event.ai_editorial_score is not None
            else None
        ),
        "final_score": event.final_score,
        "recommendation": event.recommendation,
    }
