"""Synchronous deterministic M6C.5C reviewer pipeline."""

from pastila_scout.editor.qa.pipeline.executor import ReviewerExecutor
from pastila_scout.editor.qa.pipeline.models import (
    ReviewerExecutionStatus,
    ReviewerPipelineCoverage,
    ReviewerPipelineLifecycleStatus,
    ReviewerPipelineResult,
    ReviewerPipelineStatus,
)
from pastila_scout.editor.qa.pipeline.resolver import ReviewerPlanResolver
from pastila_scout.editor.qa.pipeline.scheduler import ReviewerScheduler


class DeterministicReviewerPipeline:
    pipeline_id = "editorial-reviewer-pipeline"
    pipeline_version = "1.0.0"

    def __init__(self, registry, *, resolver=None, scheduler=None, executor=None):
        self.registry = registry
        self.resolver = resolver or ReviewerPlanResolver()
        self.scheduler = scheduler or ReviewerScheduler()
        self.executor = executor or ReviewerExecutor()

    def prepare(self, request):
        plan = self.resolver.resolve(
            manifest=request.review_manifest,
            draft=request.episode_draft,
            registry=self.registry,
            policy=request.pipeline_policy,
        )
        selection = self.scheduler.select(
            plan, request.requested_execution_ids, request.pipeline_policy
        )
        state = self.scheduler.initialize(
            plan=plan, policy=request.pipeline_policy, selection=selection
        )
        return plan, selection, state

    def continue_execution(self, request, plan, selection, state):
        if (
            state.plan_fingerprint != plan.plan_fingerprint
            or state.registry_fingerprint != self.registry.registry_fingerprint
            or state.policy_fingerprint != request.pipeline_policy.policy_fingerprint
            or state.selection_fingerprint != selection.selection_fingerprint
        ):
            raise ValueError("PIPELINE_STATE_IDENTITY_MISMATCH")
        unit = self.scheduler.next_ready_execution(
            plan=plan, state=state, policy=request.pipeline_policy
        )
        if unit is None:
            return state
        reviewer = self.registry.resolve(unit.reviewer_id, unit.reviewer_version)
        outcome = self.executor.execute(
            unit=unit, pipeline_request=request, reviewer=reviewer
        )
        return self.scheduler.apply_outcome(
            plan=plan, state=state, outcome=outcome, policy=request.pipeline_policy
        )

    def execute(self, request):
        plan, selection, state = self.prepare(request)
        while (
            state.lifecycle is not ReviewerPipelineLifecycleStatus.FINALIZED
            and state.lifecycle is not ReviewerPipelineLifecycleStatus.HALTED
        ):
            previous = state.state_fingerprint
            state = self.continue_execution(request, plan, selection, state)
            if state.state_fingerprint == previous:
                raise RuntimeError("SCHEDULER_STALLED")
        return self.finalize(request, plan, selection, state)

    def finalize(self, request, plan, selection, state):
        if state.pending_execution_ids or state.ready_execution_ids:
            raise ValueError("PIPELINE_NOT_TERMINAL")
        outcomes = tuple(
            sorted(
                state.outcomes, key=lambda item: _plan_order(plan, item.execution_id)
            )
        )
        completed = tuple(
            item.execution_id
            for item in outcomes
            if item.status is ReviewerExecutionStatus.COMPLETED
        )
        skipped = tuple(
            item.execution_id
            for item in outcomes
            if item.status is ReviewerExecutionStatus.SKIPPED
        )
        failed = tuple(
            item.execution_id
            for item in outcomes
            if item.status is ReviewerExecutionStatus.FAILED
        )
        units = {item.execution_id: item for item in plan.execution_units}
        coverage = ReviewerPipelineCoverage.build(
            full_plan_execution_ids=tuple(units),
            selected_execution_ids=selection.selected_execution_ids,
            requested_execution_ids=selection.requested_execution_ids,
            dependency_execution_ids=selection.dependency_execution_ids,
            excluded_execution_ids=selection.excluded_execution_ids,
            completed_execution_ids=completed,
            skipped_execution_ids=skipped,
            failed_execution_ids=failed,
            required_execution_ids=tuple(
                item
                for item in selection.selected_execution_ids
                if units[item].required
            ),
            optional_execution_ids=tuple(
                item
                for item in selection.selected_execution_ids
                if not units[item].required
            ),
        )
        if completed and not failed and not skipped:
            status = ReviewerPipelineStatus.COMPLETED
        elif completed and not failed:
            status = ReviewerPipelineStatus.COMPLETED_WITH_SKIPS
        elif completed:
            status = ReviewerPipelineStatus.PARTIAL
        else:
            status = ReviewerPipelineStatus.FAILED
        return ReviewerPipelineResult.build(
            pipeline_id=self.pipeline_id,
            pipeline_version=self.pipeline_version,
            status=status,
            lifecycle=state.lifecycle,
            request_fingerprint=request.request_fingerprint,
            plan_fingerprint=plan.plan_fingerprint,
            registry_fingerprint=self.registry.registry_fingerprint,
            policy_fingerprint=request.pipeline_policy.policy_fingerprint,
            selection_fingerprint=selection.selection_fingerprint,
            execution_outcomes=outcomes,
            accepted_review_results=tuple(
                item.review_result
                for item in outcomes
                if item.review_result is not None
            ),
            coverage=coverage,
            diagnostics=state.diagnostics,
            trace=state.trace,
            state_fingerprint=state.state_fingerprint,
        )


def _plan_order(plan, execution_id):
    return next(
        index
        for index, item in enumerate(plan.execution_units)
        if item.execution_id == execution_id
    )
