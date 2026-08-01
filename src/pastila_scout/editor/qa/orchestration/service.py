"""Authoritative synchronous M6C.5D orchestration path."""

from pastila_scout.editor.qa.aggregation import ApprovalPolicyEngine, FindingAggregator
from pastila_scout.editor.qa.models import (
    EditorialQAResult,
    EditorialQATrace,
    fingerprint,
)
from pastila_scout.editor.qa.orchestration.models import (
    ORCHESTRATOR_ID,
    ORCHESTRATOR_VERSION,
    EditorialReviewCompleteness,
    EditorialReviewOrchestrationReport,
    EditorialReviewOrchestrationResult,
    HandoffEligibilityCode,
    OrchestrationDiagnostic,
    OrchestrationDiagnosticSeverity,
    OrchestrationLifecycle,
    OrchestrationPhase,
    OrchestrationStatus,
    OrchestrationTraceEvent,
    OrchestrationTraceEventType,
    ReviewHandoffEligibility,
)
from pastila_scout.editor.qa.pipeline.handoff import build_m6c5a_execution_state
from pastila_scout.editor.qa.pipeline.models import (
    ReviewerPipelineRequest,
    ReviewerPipelineStatus,
)


class EditorialReviewOrchestrator:
    orchestrator_id = ORCHESTRATOR_ID
    orchestrator_version = ORCHESTRATOR_VERSION

    def __init__(self, *, pipeline, manifest_provider, aggregator=None, approver=None):
        self.pipeline = pipeline
        self.manifest_provider = manifest_provider
        self.aggregator = aggregator or FindingAggregator()
        self.approver = approver or ApprovalPolicyEngine()

    def review(self, request):
        draft_fp = fingerprint(request.draft)
        trace = [
            _event(
                0,
                OrchestrationTraceEventType.REQUEST_VALIDATED,
                OrchestrationPhase.REQUEST,
            )
        ]
        diagnostics = []
        try:
            manifest = request.manifest or self.manifest_provider.resolve(
                request.draft, request.orchestration_policy
            )
        except Exception:  # noqa: BLE001 - manifest provider boundary
            return self._failed_before(
                request, draft_fp, trace, "MANIFEST_RESOLUTION_FAILED"
            )
        trace.append(
            _event(
                1,
                OrchestrationTraceEventType.MANIFEST_RESOLVED,
                OrchestrationPhase.MANIFEST,
            )
        )
        pipeline_request = ReviewerPipelineRequest(
            episode_draft=request.draft,
            review_manifest=manifest,
            pipeline_policy=request.pipeline_policy,
            requested_execution_ids=request.requested_execution_ids,
        )
        try:
            pipeline_result = self.pipeline.execute(pipeline_request)
        except Exception:  # noqa: BLE001 - pipeline boundary
            return self._failed_before(
                request, draft_fp, trace, "PIPELINE_INVOCATION_FAILED", manifest
            )
        trace.append(
            _event(
                2,
                OrchestrationTraceEventType.PIPELINE_COMPLETED,
                OrchestrationPhase.PIPELINE,
                pipeline_result.status.value,
            )
        )
        try:
            plan, _, _ = self.pipeline.prepare(pipeline_request)
            identity_valid = (
                plan.plan_fingerprint == pipeline_result.plan_fingerprint
                and plan.draft_fingerprint == draft_fp
            )
        except Exception:  # noqa: BLE001 - public pipeline preparation boundary
            identity_valid = False
        eligibility = evaluate_handoff_eligibility(
            pipeline_result, request.orchestration_policy, identity_valid
        )
        if not eligibility.eligible:
            diagnostics.append(
                _diagnostic(
                    "HANDOFF_INELIGIBLE",
                    OrchestrationDiagnosticSeverity.WARNING,
                    OrchestrationPhase.HANDOFF,
                    (("reason", eligibility.code.value),),
                )
            )
            trace.append(
                _event(
                    3,
                    OrchestrationTraceEventType.HANDOFF_DENIED,
                    OrchestrationPhase.HANDOFF,
                    eligibility.code.value,
                )
            )
            return self._finalize(
                request=request,
                draft_fp=draft_fp,
                manifest=manifest,
                pipeline_result=pipeline_result,
                eligibility=eligibility,
                editorial_result=None,
                status=(
                    OrchestrationStatus.FAILED_AFTER_PIPELINE
                    if pipeline_result.status is ReviewerPipelineStatus.FAILED
                    else OrchestrationStatus.COMPLETED_WITHOUT_EDITORIAL_OUTCOME
                ),
                diagnostics=tuple(diagnostics),
                trace=tuple(trace),
            )
        trace.append(
            _event(
                3,
                OrchestrationTraceEventType.HANDOFF_ELIGIBLE,
                OrchestrationPhase.HANDOFF,
            )
        )
        try:
            state = build_m6c5a_execution_state(pipeline_result, plan)
            report = self.aggregator.aggregate(
                draft=request.draft, manifest=manifest, state=state
            )
            state = state.accept_aggregation()
            decision = self.approver.decide(report, request.approval_policy)
            state = state.accept_approval(decision.status)
            editorial_result = EditorialQAResult(
                report=report,
                decision=decision,
                manifest=manifest,
                state=state,
                trace=EditorialQATrace(records=()),
            )
        except Exception:  # noqa: BLE001 - frozen editorial handoff boundary
            diagnostics.append(
                _diagnostic(
                    "EDITORIAL_HANDOFF_FAILED",
                    OrchestrationDiagnosticSeverity.ERROR,
                    OrchestrationPhase.EDITORIAL,
                )
            )
            return self._finalize(
                request=request,
                draft_fp=draft_fp,
                manifest=manifest,
                pipeline_result=pipeline_result,
                eligibility=eligibility,
                editorial_result=None,
                status=OrchestrationStatus.FAILED_DURING_EDITORIAL_HANDOFF,
                diagnostics=tuple(diagnostics),
                trace=tuple(trace),
            )
        trace.append(
            _event(
                4,
                OrchestrationTraceEventType.EDITORIAL_COMPLETED,
                OrchestrationPhase.EDITORIAL,
            )
        )
        limited = (
            pipeline_result.status is not ReviewerPipelineStatus.COMPLETED
            or bool(request.requested_execution_ids)
        )
        return self._finalize(
            request=request,
            draft_fp=draft_fp,
            manifest=manifest,
            pipeline_result=pipeline_result,
            eligibility=eligibility,
            editorial_result=editorial_result,
            status=(
                OrchestrationStatus.COMPLETED_WITH_LIMITED_REVIEW
                if limited
                else OrchestrationStatus.COMPLETED
            ),
            diagnostics=tuple(diagnostics),
            trace=tuple(trace),
        )

    def _failed_before(self, request, draft_fp, trace, code, manifest=None):
        diagnostic = _diagnostic(
            code,
            OrchestrationDiagnosticSeverity.ERROR,
            (
                OrchestrationPhase.MANIFEST
                if "MANIFEST" in code
                else OrchestrationPhase.PIPELINE
            ),
        )
        return self._finalize(
            request=request,
            draft_fp=draft_fp,
            manifest=manifest,
            pipeline_result=None,
            eligibility=None,
            editorial_result=None,
            status=OrchestrationStatus.FAILED_BEFORE_PIPELINE,
            diagnostics=(diagnostic,),
            trace=tuple(trace),
        )

    def _finalize(
        self,
        *,
        request,
        draft_fp,
        manifest,
        pipeline_result,
        eligibility,
        editorial_result,
        status,
        diagnostics,
        trace,
    ):
        completeness = _completeness(
            pipeline_result,
            editorial_result is not None,
            bool(request.requested_execution_ids),
        )
        trace = (
            *trace,
            _event(
                len(trace),
                OrchestrationTraceEventType.FINALIZED,
                OrchestrationPhase.FINALIZATION,
            ),
        )
        report_values = {
            "orchestrator_id": self.orchestrator_id,
            "orchestrator_version": self.orchestrator_version,
            "draft_fingerprint": draft_fp,
            "manifest_fingerprint": manifest.manifest_fingerprint if manifest else None,
            "pipeline_status": (
                pipeline_result.status.value if pipeline_result else None
            ),
            "orchestration_status": status,
            "editorial_status": (
                editorial_result.decision.status.value if editorial_result else None
            ),
            "handoff_performed": editorial_result is not None,
            "completeness": completeness,
            "diagnostic_codes": tuple(item.code for item in diagnostics),
        }
        report = EditorialReviewOrchestrationReport(
            **report_values, report_fingerprint=fingerprint(report_values)
        )
        return EditorialReviewOrchestrationResult.build(
            request_fingerprint=request.request_fingerprint,
            draft_fingerprint=draft_fp,
            manifest_fingerprint=manifest.manifest_fingerprint if manifest else None,
            pipeline_result=pipeline_result,
            handoff_eligibility=eligibility,
            editorial_result=editorial_result,
            status=status,
            lifecycle=(
                OrchestrationLifecycle.FINALIZED
                if status
                not in {
                    OrchestrationStatus.FAILED_BEFORE_PIPELINE,
                    OrchestrationStatus.FAILED_AFTER_PIPELINE,
                    OrchestrationStatus.FAILED_DURING_EDITORIAL_HANDOFF,
                }
                else OrchestrationLifecycle.FAILED
            ),
            diagnostics=diagnostics,
            trace=trace,
            report=report,
        )


def evaluate_handoff_eligibility(result, policy, identity_valid=True):
    code = HandoffEligibilityCode.ELIGIBLE
    if result.status is ReviewerPipelineStatus.FAILED:
        code = HandoffEligibilityCode.PIPELINE_FAILED
    elif (
        result.status is ReviewerPipelineStatus.PARTIAL
        and not policy.permit_partial_handoff
    ):
        code = HandoffEligibilityCode.PIPELINE_PARTIAL_NOT_ALLOWED
    elif (
        result.status is ReviewerPipelineStatus.COMPLETED_WITH_SKIPS
        and not policy.permit_completed_with_skips
    ):
        code = HandoffEligibilityCode.PIPELINE_SKIPS_NOT_ALLOWED
    elif (
        policy.require_at_least_one_review_result and not result.accepted_review_results
    ):
        code = HandoffEligibilityCode.NO_ACCEPTED_REVIEW_RESULTS
    elif not identity_valid:
        code = HandoffEligibilityCode.IDENTITY_MISMATCH
    return ReviewHandoffEligibility.build(
        eligible=code is HandoffEligibilityCode.ELIGIBLE,
        code=code,
        accepted_review_result_fingerprints=tuple(
            item.review_fingerprint for item in result.accepted_review_results
        ),
    )


def _completeness(result, handed_off, subset):
    if result is None:
        return EditorialReviewCompleteness(
            requested_execution_count=0,
            selected_execution_count=0,
            accepted_result_count=0,
            failed_execution_count=0,
            skipped_execution_count=0,
            required_execution_count=0,
            completed_required_count=0,
            editorial_handoff_performed=False,
            editorial_outcome_present=False,
            limited_review=True,
        )
    coverage = result.coverage
    completed_required = len(
        set(coverage.completed_execution_ids) & set(coverage.required_execution_ids)
    )
    return EditorialReviewCompleteness(
        requested_execution_count=len(coverage.requested_execution_ids),
        selected_execution_count=len(coverage.selected_execution_ids),
        accepted_result_count=len(result.accepted_review_results),
        failed_execution_count=len(coverage.failed_execution_ids),
        skipped_execution_count=len(coverage.skipped_execution_ids),
        required_execution_count=len(coverage.required_execution_ids),
        completed_required_count=completed_required,
        editorial_handoff_performed=handed_off,
        editorial_outcome_present=handed_off,
        limited_review=subset or result.status is not ReviewerPipelineStatus.COMPLETED,
    )


def _diagnostic(code, severity, phase, context=()):
    return OrchestrationDiagnostic.build(
        code=code, severity=severity, phase=phase, safe_context=context
    )


def _event(sequence, event_type, phase, code=None):
    return OrchestrationTraceEvent.build(
        sequence=sequence, event_type=event_type, phase=phase, code=code
    )
