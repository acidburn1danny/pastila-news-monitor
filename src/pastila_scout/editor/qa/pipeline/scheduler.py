"""Pure deterministic selection and dependency scheduling."""

from pastila_scout.editor.qa.pipeline.models import (
    PipelineDiagnostic,
    PipelineDiagnosticPhase,
    PipelineDiagnosticSeverity,
    PipelineTraceEvent,
    PipelineTraceEventType,
    ReviewerExecutionOutcome,
    ReviewerExecutionSelection,
    ReviewerExecutionStatus,
    ReviewerPipelineLifecycleStatus,
    ReviewerPipelineState,
)


class ReviewerSchedulingError(ValueError):
    pass


class ReviewerScheduler:
    def select(self, plan, requested_ids, policy):
        units = {item.execution_id: item for item in plan.execution_units}
        requested = set(requested_ids) if requested_ids else set(units)
        if not requested <= set(units):
            raise ReviewerSchedulingError("REQUESTED_EXECUTION_UNKNOWN")
        if (
            requested_ids
            and not policy.allow_partial_selection
            and requested != set(units)
        ):
            raise ReviewerSchedulingError("PARTIAL_SELECTION_DISABLED")
        selected = set(requested)
        queue = sorted(requested)
        while queue:
            for dependency in units[queue.pop(0)].depends_on_execution_ids:
                if dependency not in selected:
                    selected.add(dependency)
                    queue.append(dependency)
        order = tuple(item.execution_id for item in plan.execution_units)
        selected_ids = tuple(item for item in order if item in selected)
        requested_canonical = tuple(item for item in order if item in requested)
        dependency_ids = tuple(item for item in selected_ids if item not in requested)
        excluded = tuple(item for item in order if item not in selected)
        return ReviewerExecutionSelection.build(
            plan_fingerprint=plan.plan_fingerprint,
            requested_execution_ids=requested_canonical,
            selected_execution_ids=selected_ids,
            dependency_execution_ids=dependency_ids,
            excluded_execution_ids=excluded,
        )

    def initialize(self, *, plan, policy, selection):
        selected = set(selection.selected_execution_ids)
        ready = tuple(
            unit.execution_id
            for unit in plan.execution_units
            if unit.execution_id in selected and not unit.depends_on_execution_ids
        )
        pending = tuple(
            item for item in selection.selected_execution_ids if item not in set(ready)
        )
        trace = (
            PipelineTraceEvent.build(
                sequence=0,
                event_type=PipelineTraceEventType.PIPELINE_INITIALIZED,
                revision=0,
            ),
        )
        return ReviewerPipelineState.build(
            draft_fingerprint=plan.draft_fingerprint,
            plan_fingerprint=plan.plan_fingerprint,
            registry_fingerprint=plan.registry_fingerprint,
            policy_fingerprint=policy.policy_fingerprint,
            selection_fingerprint=selection.selection_fingerprint,
            revision=0,
            lifecycle=ReviewerPipelineLifecycleStatus.INITIALIZED,
            selected_execution_ids=selection.selected_execution_ids,
            pending_execution_ids=pending,
            ready_execution_ids=ready,
            trace=trace,
        )

    def next_ready_execution(self, *, plan, state, policy):
        del policy
        ready = set(state.ready_execution_ids)
        return next(
            (unit for unit in plan.execution_units if unit.execution_id in ready), None
        )

    def apply_outcome(self, *, plan, state, outcome, policy):
        if outcome.execution_id not in state.ready_execution_ids:
            raise ReviewerSchedulingError("PIPELINE_STATE_TRANSITION_INVALID")
        outcomes = [*state.outcomes, outcome]
        terminal = {item.execution_id: item for item in outcomes}
        selected = set(state.selected_execution_ids)
        diagnostics = [*state.diagnostics, *outcome.diagnostics]
        propagated = []
        changed = True
        while changed:
            changed = False
            for unit in plan.execution_units:
                if unit.execution_id not in selected or unit.execution_id in terminal:
                    continue
                dependency_outcomes = [
                    terminal.get(item) for item in unit.depends_on_execution_ids
                ]
                unsatisfied = tuple(
                    sorted(
                        item.execution_id
                        for item in dependency_outcomes
                        if item and item.status is not ReviewerExecutionStatus.COMPLETED
                    )
                )
                if unsatisfied:
                    skip = ReviewerExecutionOutcome.build(
                        execution_id=unit.execution_id,
                        reviewer_id=unit.reviewer_id,
                        required=unit.required,
                        status=ReviewerExecutionStatus.SKIPPED,
                        skip_code="DEPENDENCY_UNSATISFIED",
                    )
                    outcomes.append(skip)
                    terminal[unit.execution_id] = skip
                    propagated.append(skip)
                    diagnostics.append(
                        PipelineDiagnostic.build(
                            code="DEPENDENCY_UNSATISFIED",
                            severity=PipelineDiagnosticSeverity.WARNING,
                            phase=PipelineDiagnosticPhase.SCHEDULING,
                            execution_id=unit.execution_id,
                            reviewer_id=unit.reviewer_id,
                            related_execution_ids=unsatisfied,
                        )
                    )
                    changed = True
        failures = sum(
            item.status is ReviewerExecutionStatus.FAILED for item in outcomes
        )
        halt = failures >= policy.maximum_pipeline_failures or (
            outcome.status is ReviewerExecutionStatus.FAILED
            and (
                (outcome.required and not policy.continue_after_required_failure)
                or (not outcome.required and not policy.continue_after_optional_failure)
            )
        )
        if halt:
            for unit in plan.execution_units:
                if unit.execution_id in selected and unit.execution_id not in terminal:
                    skipped = ReviewerExecutionOutcome.build(
                        execution_id=unit.execution_id,
                        reviewer_id=unit.reviewer_id,
                        required=unit.required,
                        status=ReviewerExecutionStatus.SKIPPED,
                        skip_code="PIPELINE_HALTED_BY_POLICY",
                    )
                    outcomes.append(skipped)
                    terminal[unit.execution_id] = skipped
        completed = {
            key
            for key, value in terminal.items()
            if value.status is ReviewerExecutionStatus.COMPLETED
        }
        remaining = selected - set(terminal)
        ready = tuple(
            unit.execution_id
            for unit in plan.execution_units
            if unit.execution_id in remaining
            and set(unit.depends_on_execution_ids) <= completed
        )
        pending = tuple(
            unit.execution_id
            for unit in plan.execution_units
            if unit.execution_id in remaining and unit.execution_id not in set(ready)
        )
        lifecycle = (
            ReviewerPipelineLifecycleStatus.HALTED
            if halt
            else (
                ReviewerPipelineLifecycleStatus.FINALIZED
                if not remaining
                else ReviewerPipelineLifecycleStatus.RUNNING
            )
        )
        events = list(state.trace)

        def event(event_type, item, code=None, related=()):
            events.append(
                PipelineTraceEvent.build(
                    sequence=len(events),
                    event_type=event_type,
                    revision=state.revision + 1,
                    execution_id=item.execution_id,
                    reviewer_id=item.reviewer_id,
                    related_execution_ids=related,
                    outcome_status=item.status,
                    code=code,
                )
            )

        event(
            {
                ReviewerExecutionStatus.COMPLETED: PipelineTraceEventType.EXECUTION_COMPLETED,
                ReviewerExecutionStatus.FAILED: PipelineTraceEventType.EXECUTION_FAILED,
                ReviewerExecutionStatus.SKIPPED: PipelineTraceEventType.EXECUTION_SKIPPED,
            }[outcome.status],
            outcome,
            outcome.failure_code or outcome.skip_code,
        )
        for item in propagated:
            event(PipelineTraceEventType.EXECUTION_SKIPPED, item, item.skip_code)
        if halt:
            event(
                PipelineTraceEventType.PIPELINE_HALTED,
                outcome,
                "PIPELINE_HALTED_BY_POLICY",
            )
        if not remaining:
            events.append(
                PipelineTraceEvent.build(
                    sequence=len(events),
                    event_type=PipelineTraceEventType.PIPELINE_FINALIZED,
                    revision=state.revision + 1,
                )
            )
        return ReviewerPipelineState.build(
            draft_fingerprint=state.draft_fingerprint,
            plan_fingerprint=state.plan_fingerprint,
            registry_fingerprint=state.registry_fingerprint,
            policy_fingerprint=state.policy_fingerprint,
            selection_fingerprint=state.selection_fingerprint,
            revision=state.revision + 1,
            lifecycle=lifecycle,
            selected_execution_ids=state.selected_execution_ids,
            pending_execution_ids=pending,
            ready_execution_ids=ready,
            outcomes=tuple(outcomes),
            diagnostics=tuple(diagnostics[: policy.maximum_diagnostics]),
            trace=tuple(events),
            halt_code="PIPELINE_HALTED_BY_POLICY" if halt else None,
        )
