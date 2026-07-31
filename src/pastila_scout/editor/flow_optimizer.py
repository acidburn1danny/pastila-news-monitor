"""Bounded deterministic episode-flow optimization over a frozen selected set."""

from __future__ import annotations

import math
from itertools import pairwise

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
from pastila_scout.contracts.selection_profile import SelectionProfileV1
from pastila_scout.editor.engine import EditorialSelectionResult
from pastila_scout.editor.flow_models import (
    FlowCandidate,
    FlowDecision,
    FlowDecisionOutcome,
    FlowDecisionTrace,
    FlowEnvironment,
    FlowObjectiveBreakdown,
    FlowOptimizationResult,
    FlowReason,
    RuntimeAllocation,
)
from pastila_scout.editor.flow_rules import (
    DEFAULT_FLOW_CONSTRAINTS,
    DEFAULT_FLOW_RULES,
    FlowConstraint,
    FlowRule,
    ai_dimension,
    transition_type,
)


class EpisodeFlowOptimizer:
    """Optimize order, flow roles, transitions, and runtime with a fixed beam."""

    def __init__(
        self,
        rules: tuple[FlowRule, ...] = DEFAULT_FLOW_RULES,
        constraints: tuple[FlowConstraint, ...] = DEFAULT_FLOW_CONSTRAINTS,
        *,
        beam_width: int = 32,
        minimum_story_seconds: int = 60,
    ) -> None:
        if beam_width <= 0:
            raise ValueError("beam_width must be positive")
        if minimum_story_seconds <= 0:
            raise ValueError("minimum_story_seconds must be positive")
        self.rules = rules
        self.constraints = constraints
        self.beam_width = beam_width
        self.minimum_story_seconds = minimum_story_seconds

    def optimize(
        self,
        scout_input: ScoutEditorInputV1,
        profile: SelectionProfileV1,
        context: EpisodeContextV1,
        selection_result: EditorialSelectionResult,
    ) -> FlowOptimizationResult:
        """Return a revised output while preserving selection and Scout facts."""

        initial_output = selection_result.output
        validate_editor_output_against_input(
            initial_output,
            scout_input,
            selection_profile=profile,
            episode_context=context,
        )
        proposal = initial_output.episode_proposal
        if proposal is None:
            failure = self._failure_trace(
                (),
                "selection_proposal_unavailable",
                "Flow optimization requires an existing selection proposal.",
            )
            return FlowOptimizationResult(output=initial_output, trace=failure)

        event_map = {event.event_id: event for event in scout_input.ranked_events}
        initial_ids = tuple(story.event_id for story in proposal.selected_stories)
        selected = tuple(event_map[event_id] for event_id in initial_ids)
        environment = FlowEnvironment(
            all_selected=selected,
            mandatory_event_ids=frozenset(context.mandatory_event_ids),
            avoid_recent_event_ids=frozenset(context.avoid_recent_event_ids),
            previous_episode_reference=context.previous_episode_reference,
            preferred_categories=frozenset(
                category
                for category, constraint in profile.category_constraints.items()
                if constraint.preferred > 0
            ),
        )
        runtime_failure = self._runtime_failure(selected, context)
        if runtime_failure is not None:
            output = self._conflict_output(initial_output, runtime_failure)
            trace = FlowDecisionTrace(
                initial_order=initial_ids,
                final_order=initial_ids,
                evaluated_candidate_count=0,
                summarized_alternatives=(),
                applied_rules=(),
                hard_constraint_failures=(runtime_failure,),
                adjacency_decisions=(),
                opening_decision=None,
                ending_decision=None,
                runtime_allocations=(),
                winning_objective=None,
            )
            return FlowOptimizationResult(output=output, trace=trace)

        order, alternatives, evaluated = self._search(selected, environment)
        constraint_failures = self._constraint_failures(order, environment)
        if constraint_failures:
            output = self._conflict_output(initial_output, constraint_failures[0])
            trace = FlowDecisionTrace(
                initial_order=initial_ids,
                final_order=tuple(event.event_id for event in order),
                evaluated_candidate_count=evaluated,
                summarized_alternatives=alternatives,
                applied_rules=(),
                hard_constraint_failures=constraint_failures,
                adjacency_decisions=(),
                opening_decision=None,
                ending_decision=None,
                runtime_allocations=(),
                winning_objective=self._objective(order, environment),
            )
            return FlowOptimizationResult(output=output, trace=trace)

        allocations = self._allocate_runtime(order, context)
        adjacency = self._adjacency_decisions(order, environment)
        objective = self._objective(order, environment)
        applied = self._applied_rule_decisions(order, environment, objective)
        opening = self._position_decision(order, objective, opening=True)
        ending = self._position_decision(order, objective, opening=False)
        output = self._rebuild_output(
            initial_output,
            order,
            allocations,
            adjacency,
            environment,
        )
        validate_editor_output_against_input(
            output,
            scout_input,
            selection_profile=profile,
            episode_context=context,
        )
        self._assert_sets_preserved(initial_output, output)
        trace = FlowDecisionTrace(
            initial_order=initial_ids,
            final_order=tuple(event.event_id for event in order),
            evaluated_candidate_count=evaluated,
            summarized_alternatives=alternatives,
            applied_rules=applied,
            hard_constraint_failures=(),
            adjacency_decisions=adjacency,
            opening_decision=opening,
            ending_decision=ending,
            runtime_allocations=allocations,
            winning_objective=objective,
        )
        return FlowOptimizationResult(output=output, trace=trace)

    def _search(
        self,
        selected: tuple[RankedEditorialEvent, ...],
        environment: FlowEnvironment,
    ) -> tuple[tuple[RankedEditorialEvent, ...], tuple[FlowCandidate, ...], int]:
        if not selected:
            return (), (), 0
        beam: list[tuple[RankedEditorialEvent, ...]] = [()]
        evaluated = 0
        for _ in range(len(selected)):
            expanded: list[tuple[RankedEditorialEvent, ...]] = []
            for partial in beam:
                used = {event.event_id for event in partial}
                for event in selected:
                    if event.event_id not in used:
                        expanded.append((*partial, event))
                        evaluated += 1
            expanded.sort(key=lambda order: self._order_sort_key(order, environment))
            beam = expanded[: self.beam_width]
        valid = [
            order for order in beam if not self._constraint_failures(order, environment)
        ]
        finalists = valid or beam
        finalists.sort(key=lambda order: self._order_sort_key(order, environment))
        winner = finalists[0]
        alternatives = tuple(
            FlowCandidate(
                event_ids=tuple(event.event_id for event in order),
                objective=self._objective(order, environment),
            )
            for order in finalists[:5]
        )
        return winner, alternatives, evaluated

    def _order_sort_key(
        self,
        order: tuple[RankedEditorialEvent, ...],
        environment: FlowEnvironment,
    ) -> tuple[object, ...]:
        objective = self._objective(order, environment)
        descending = tuple(-value for value in objective.comparison_values())
        stable = tuple((event.rank, event.event_id) for event in order)
        return (*descending, stable)

    def _objective(
        self,
        order: tuple[RankedEditorialEvent, ...],
        environment: FlowEnvironment,
    ) -> FlowObjectiveBreakdown:
        scores = {rule.name: rule.score(order, environment) for rule in self.rules}
        hard_ok = not (
            len(order) == len(environment.all_selected)
            and self._constraint_failures(order, environment)
        )
        return FlowObjectiveBreakdown(
            hard_constraints_satisfied=hard_ok,
            mandatory_placement=scores.get("mandatory_placement", 0),
            opening_strength=scores.get("opening_strength", 0),
            ending_strength=scores.get("ending_strength", 0),
            early_momentum=scores.get("early_episode_momentum", 0),
            category_rhythm=scores.get("category_rhythm", 0),
            tone_rhythm=scores.get("tone_rhythm", 0),
            score_cliff=scores.get("score_cliff", 0),
            continuity=scores.get("previous_episode_continuity", 0),
            inherited_strength=scores.get("inherited_editorial_strength", 0),
        )

    def _constraint_failures(
        self,
        order: tuple[RankedEditorialEvent, ...],
        environment: FlowEnvironment,
    ) -> tuple[FlowDecision, ...]:
        failures = []
        for constraint in self.constraints:
            message = constraint.validate(order, environment)
            if message is not None:
                failures.append(
                    FlowDecision(
                        rule=constraint.name,
                        outcome=FlowDecisionOutcome.CONFLICT,
                        reason=FlowReason(
                            code="hard_flow_constraint_failed", message=message
                        ),
                        event_ids=tuple(event.event_id for event in order),
                        hard=True,
                    )
                )
        return tuple(failures)

    def _runtime_failure(
        self,
        selected: tuple[RankedEditorialEvent, ...],
        context: EpisodeContextV1,
    ) -> FlowDecision | None:
        required = len(selected) * self.minimum_story_seconds
        if required <= context.target_runtime.value:
            return None
        return FlowDecision(
            rule="runtime_budget",
            outcome=FlowDecisionOutcome.CONFLICT,
            reason=FlowReason(
                code="flow_runtime_impossible",
                message="Selected stories cannot fit the minimum flow treatment runtime.",
            ),
            event_ids=tuple(event.event_id for event in selected),
            hard=True,
        )

    def _allocate_runtime(
        self,
        order: tuple[RankedEditorialEvent, ...],
        context: EpisodeContextV1,
    ) -> tuple[RuntimeAllocation, ...]:
        if not order:
            return ()
        remaining = (
            context.target_runtime.value - len(order) * self.minimum_story_seconds
        )
        weights = [
            self._runtime_weight(event, index, len(order), context)
            for index, event in enumerate(order)
        ]
        total_weight = sum(weights)
        exact = [remaining * weight / total_weight for weight in weights]
        extras = [math.floor(value) for value in exact]
        unallocated = remaining - sum(extras)
        remainder_order = sorted(
            range(len(order)),
            key=lambda index: (
                -(exact[index] - extras[index]),
                order[index].rank,
                order[index].event_id,
            ),
        )
        for index in remainder_order[:unallocated]:
            extras[index] += 1
        return tuple(
            RuntimeAllocation(
                event_id=event.event_id,
                position=index + 1,
                seconds=self.minimum_story_seconds + extras[index],
                weight=round(weights[index], 6),
                reason=FlowReason(
                    code="weighted_runtime_allocation",
                    message="Runtime follows strength, mandatory status, and flow role.",
                ),
            )
            for index, event in enumerate(order)
        )

    @staticmethod
    def _runtime_weight(
        event: RankedEditorialEvent,
        index: int,
        count: int,
        context: EpisodeContextV1,
    ) -> float:
        return (
            1
            + event.final_score / 100
            + ai_dimension(event, "importance") / 20
            + (0.25 if event.event_id in context.mandatory_event_ids else 0)
            + (0.2 if index == 0 else 0)
            + (0.2 if index == count - 1 else 0)
        )

    def _adjacency_decisions(
        self,
        order: tuple[RankedEditorialEvent, ...],
        environment: FlowEnvironment,
    ) -> tuple[FlowDecision, ...]:
        decisions = []
        for index, (previous, current) in enumerate(pairwise(order), start=1):
            transition, reason_code = transition_type(previous, current, environment)
            decisions.append(
                FlowDecision(
                    rule="transition_typing",
                    outcome=FlowDecisionOutcome.APPLIED,
                    reason=FlowReason(
                        code=reason_code,
                        message=f"Deterministic transition type: {transition}.",
                    ),
                    event_ids=(previous.event_id, current.event_id),
                    positions=(index, index + 1),
                )
            )
        return tuple(decisions)

    def _applied_rule_decisions(
        self,
        order: tuple[RankedEditorialEvent, ...],
        environment: FlowEnvironment,
        objective: FlowObjectiveBreakdown,
    ) -> tuple[FlowDecision, ...]:
        values = dict(
            zip(
                (
                    "mandatory_placement",
                    "opening_strength",
                    "ending_strength",
                    "early_episode_momentum",
                    "category_rhythm",
                    "tone_rhythm",
                    "score_cliff",
                    "previous_episode_continuity",
                    "inherited_editorial_strength",
                ),
                objective.comparison_values()[1:],
                strict=True,
            )
        )
        return tuple(
            FlowDecision(
                rule=rule.name,
                outcome=FlowDecisionOutcome.APPLIED,
                reason=FlowReason(
                    code="flow_objective_component",
                    message="Rule contributed to the winning lexicographic objective.",
                ),
                event_ids=tuple(event.event_id for event in order),
                contribution=values.get(rule.name, 0),
            )
            for rule in self.rules
        )

    @staticmethod
    def _position_decision(
        order: tuple[RankedEditorialEvent, ...],
        objective: FlowObjectiveBreakdown,
        *,
        opening: bool,
    ) -> FlowDecision | None:
        if not order:
            return None
        event = order[0] if opening else order[-1]
        return FlowDecision(
            rule="opening_strength" if opening else "ending_strength",
            outcome=FlowDecisionOutcome.APPLIED,
            reason=FlowReason(
                code="opening_selected" if opening else "ending_selected",
                message=(
                    "Winning objective selected the opening event."
                    if opening
                    else "Winning objective selected the ending event."
                ),
            ),
            event_ids=(event.event_id,),
            positions=(1 if opening else len(order),),
            contribution=(
                objective.opening_strength if opening else objective.ending_strength
            ),
        )

    def _rebuild_output(
        self,
        initial: EditorAgentOutputV1,
        order: tuple[RankedEditorialEvent, ...],
        allocations: tuple[RuntimeAllocation, ...],
        adjacency: tuple[FlowDecision, ...],
        environment: FlowEnvironment,
    ) -> EditorAgentOutputV1:
        assert initial.episode_proposal is not None
        proposal = initial.episode_proposal
        stories = {story.event_id: story for story in proposal.selected_stories}
        transitions = {decision.event_ids[1]: decision for decision in adjacency}
        selected_data = []
        flow_data = []
        for position, (event, allocation) in enumerate(
            zip(order, allocations, strict=True), start=1
        ):
            transition_decision = transitions.get(event.event_id)
            transition = None
            if transition_decision is not None:
                transition, _ = transition_type(order[position - 2], event, environment)
            role = _segment_role(position, len(order), transition)
            story = stories[event.event_id].model_dump(mode="json")
            story.update(
                {
                    "position": position,
                    "episode_role": role,
                    "transition_reason": (
                        None
                        if transition_decision is None
                        else transition_decision.reason.code
                    ),
                    "suggested_treatment_length": {
                        "unit": "seconds",
                        "value": allocation.seconds,
                    },
                }
            )
            selected_data.append(story)
            flow_data.append(
                {
                    "position": position,
                    "event_id": event.event_id,
                    "role": role,
                    "placement_reason": (
                        "opening_selected"
                        if position == 1
                        else (
                            "ending_selected"
                            if position == len(order)
                            else "flow_objective_order"
                        )
                    ),
                    "expected_transition_type": transition,
                    "extensions": {},
                }
            )
        notes = list(proposal.editorial_notes)
        reason_codes = {decision.reason.code for decision in adjacency}
        catalog = (
            (
                "grave_to_comic_relief",
                "Flow uses comic relief after a grave segment.",
            ),
            (
                "category_continuation",
                "Adjacent category repetition is retained as a continuation.",
            ),
            (
                "previous_episode_callback",
                "Flow marks an unavoidable recent event as a callback.",
            ),
            ("score_cliff_hard_cut", "Flow marks a score cliff with a hard cut."),
        )
        for code, note in catalog:
            if code in reason_codes and note not in notes and len(notes) < 20:
                notes.append(note)
        data = initial.model_dump(mode="json")
        proposal_data = proposal.model_dump(mode="json")
        proposal_data.update(
            {
                "selected_stories": selected_data,
                "episode_flow": flow_data,
                "estimated_total_runtime": {
                    "unit": "seconds",
                    "value": sum(item.seconds for item in allocations),
                },
                "editorial_notes": notes,
            }
        )
        data["episode_proposal"] = proposal_data
        return EditorAgentOutputV1.model_validate_json(canonical_json_bytes(data))

    @staticmethod
    def _assert_sets_preserved(
        before: EditorAgentOutputV1, after: EditorAgentOutputV1
    ) -> None:
        assert before.episode_proposal is not None
        assert after.episode_proposal is not None
        before_selected = {
            item.event_id for item in before.episode_proposal.selected_stories
        }
        after_selected = {
            item.event_id for item in after.episode_proposal.selected_stories
        }
        before_backups = {
            item.event_id for item in before.episode_proposal.backup_stories
        }
        after_backups = {
            item.event_id for item in after.episode_proposal.backup_stories
        }
        if before_selected != after_selected or before_backups != after_backups:
            raise ValueError("flow optimization changed selected or backup event sets")

    @staticmethod
    def _conflict_output(
        initial: EditorAgentOutputV1, failure: FlowDecision
    ) -> EditorAgentOutputV1:
        data = initial.model_dump(mode="json")
        data["status"] = ContractStatus.INVALID_INPUT
        errors = list(data["errors"])
        errors.append(
            {
                "code": failure.reason.code,
                "message": failure.reason.message,
                "event_id": None,
                "recoverable": False,
            }
        )
        data["errors"] = errors
        return EditorAgentOutputV1.model_validate_json(canonical_json_bytes(data))

    @staticmethod
    def _failure_trace(
        initial_order: tuple[int, ...], code: str, message: str
    ) -> FlowDecisionTrace:
        failure = FlowDecision(
            rule="flow_precondition",
            outcome=FlowDecisionOutcome.CONFLICT,
            reason=FlowReason(code=code, message=message),
            event_ids=initial_order,
            hard=True,
        )
        return FlowDecisionTrace(
            initial_order=initial_order,
            final_order=initial_order,
            evaluated_candidate_count=0,
            summarized_alternatives=(),
            applied_rules=(),
            hard_constraint_failures=(failure,),
            adjacency_decisions=(),
            opening_decision=None,
            ending_decision=None,
            runtime_allocations=(),
            winning_objective=None,
        )


def _segment_role(position: int, count: int, transition: str | None) -> str:
    if position == 1:
        return "opening"
    if position == count:
        return "closing"
    if transition in {"escalation", "contrast", "comic_relief", "callback"}:
        return transition
    return "development"
