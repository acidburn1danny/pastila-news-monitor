"""Single authoritative generation-to-review application workflow."""

from typing import Any

from pastila_scout.editor.generation.models import ControlledGenerationResult
from pastila_scout.editor.qa.integration.models import (
    INTEGRATION_ID,
    INTEGRATION_VERSION,
    EditorialReviewIntegrationOutcome,
    EditorialReviewIntegrationReport,
    EditorialReviewIntegrationRequest,
    EditorialReviewIntegrationResult,
    IntegrationCompleteness,
    IntegrationDiagnostic,
    IntegrationDiagnosticSeverity,
    IntegrationLifecycle,
    IntegrationPhase,
    IntegrationStatus,
    IntegrationTraceEvent,
    IntegrationTraceEventType,
)
from pastila_scout.editor.qa.models import fingerprint
from pastila_scout.editor.qa.orchestration.models import (
    EditorialReviewOrchestrationRequest,
    EditorialReviewOrchestrationResult,
    OrchestrationStatus,
)


class EditorialReviewIntegrationService:
    integration_id = INTEGRATION_ID
    integration_version = INTEGRATION_VERSION

    def __init__(self, *, generator: Any, review_orchestrator: Any) -> None:
        self.generator = generator
        self.review_orchestrator = review_orchestrator

    def execute(
        self, request: EditorialReviewIntegrationRequest
    ) -> EditorialReviewIntegrationResult:
        trace = [
            _event(
                0, IntegrationTraceEventType.REQUEST_VALIDATED, IntegrationPhase.REQUEST
            ),
            _event(
                1,
                IntegrationTraceEventType.GENERATION_STARTED,
                IntegrationPhase.GENERATION,
            ),
        ]
        try:
            generation_result = self.generator.generate(
                **request.generation.keyword_arguments()
            )
        except Exception:  # noqa: BLE001 - generation service boundary
            trace.append(
                _event(
                    2,
                    IntegrationTraceEventType.GENERATION_FAILED,
                    IntegrationPhase.GENERATION,
                    "GENERATION_INVOCATION_FAILED",
                )
            )
            return self._finalize(
                request,
                generation_result=None,
                draft_fingerprint=None,
                review_result=None,
                status=IntegrationStatus.FAILED_DURING_GENERATION,
                diagnostic=_diagnostic(
                    "GENERATION_INVOCATION_FAILED", IntegrationPhase.GENERATION
                ),
                trace=trace,
            )
        if not isinstance(generation_result, ControlledGenerationResult):
            trace.append(
                _event(
                    2,
                    IntegrationTraceEventType.GENERATION_FAILED,
                    IntegrationPhase.GENERATION,
                    "GENERATION_RESULT_INVALID",
                )
            )
            return self._finalize(
                request,
                generation_result=None,
                draft_fingerprint=None,
                review_result=None,
                status=IntegrationStatus.FAILED_DURING_GENERATION,
                diagnostic=_diagnostic(
                    "GENERATION_RESULT_INVALID", IntegrationPhase.GENERATION
                ),
                trace=trace,
            )
        trace.append(
            _event(
                2,
                IntegrationTraceEventType.GENERATION_COMPLETED,
                IntegrationPhase.GENERATION,
            )
        )
        draft = generation_result.draft
        try:
            draft_fingerprint = fingerprint(draft)
            type(draft).model_validate(draft.model_dump(mode="python"))
        except Exception:  # noqa: BLE001 - frozen draft validation boundary
            trace.append(
                _event(
                    3,
                    IntegrationTraceEventType.DRAFT_REJECTED,
                    IntegrationPhase.DRAFT_VALIDATION,
                    "GENERATED_DRAFT_INVALID",
                )
            )
            return self._finalize(
                request,
                generation_result=generation_result,
                draft_fingerprint=None,
                review_result=None,
                status=IntegrationStatus.FAILED_BEFORE_REVIEW,
                diagnostic=_diagnostic(
                    "GENERATED_DRAFT_INVALID", IntegrationPhase.DRAFT_VALIDATION
                ),
                trace=trace,
            )
        trace.append(
            _event(
                3,
                IntegrationTraceEventType.DRAFT_VALIDATED,
                IntegrationPhase.DRAFT_VALIDATION,
            )
        )
        if not request.integration_policy.require_review_after_generation:
            return self._finalize(
                request,
                generation_result=generation_result,
                draft_fingerprint=draft_fingerprint,
                review_result=None,
                status=IntegrationStatus.COMPLETED_WITHOUT_REVIEW,
                diagnostic=None,
                trace=trace,
            )
        try:
            review_request = EditorialReviewOrchestrationRequest(
                draft=draft,
                manifest=request.review_manifest,
                pipeline_policy=request.pipeline_policy,
                orchestration_policy=request.orchestration_policy,
                approval_policy=request.approval_policy,
                requested_execution_ids=request.requested_execution_ids,
            )
        except Exception:  # noqa: BLE001 - frozen review-request boundary
            trace.append(
                _event(
                    4,
                    IntegrationTraceEventType.REVIEW_FAILED,
                    IntegrationPhase.REVIEW_PREPARATION,
                    "REVIEW_REQUEST_PREPARATION_FAILED",
                )
            )
            return self._finalize(
                request,
                generation_result=generation_result,
                draft_fingerprint=draft_fingerprint,
                review_result=None,
                status=IntegrationStatus.FAILED_BEFORE_REVIEW,
                diagnostic=_diagnostic(
                    "REVIEW_REQUEST_PREPARATION_FAILED",
                    IntegrationPhase.REVIEW_PREPARATION,
                ),
                trace=trace,
            )
        trace.extend(
            (
                _event(
                    4,
                    IntegrationTraceEventType.REVIEW_REQUEST_PREPARED,
                    IntegrationPhase.REVIEW_PREPARATION,
                ),
                _event(
                    5, IntegrationTraceEventType.REVIEW_STARTED, IntegrationPhase.REVIEW
                ),
            )
        )
        try:
            review_result = self.review_orchestrator.review(review_request)
        except Exception:  # noqa: BLE001 - M6C.5D public boundary
            trace.append(
                _event(
                    6,
                    IntegrationTraceEventType.REVIEW_FAILED,
                    IntegrationPhase.REVIEW,
                    "REVIEW_INVOCATION_FAILED",
                )
            )
            return self._finalize(
                request,
                generation_result=generation_result,
                draft_fingerprint=draft_fingerprint,
                review_result=None,
                status=IntegrationStatus.FAILED_DURING_REVIEW,
                diagnostic=_diagnostic(
                    "REVIEW_INVOCATION_FAILED", IntegrationPhase.REVIEW
                ),
                trace=trace,
            )
        if (
            not isinstance(review_result, EditorialReviewOrchestrationResult)
            or review_result.draft_fingerprint != draft_fingerprint
        ):
            trace.append(
                _event(
                    6,
                    IntegrationTraceEventType.REVIEW_FAILED,
                    IntegrationPhase.REVIEW,
                    "REVIEW_RESULT_INVALID",
                )
            )
            return self._finalize(
                request,
                generation_result=generation_result,
                draft_fingerprint=draft_fingerprint,
                review_result=None,
                status=IntegrationStatus.FAILED_DURING_REVIEW,
                diagnostic=_diagnostic(
                    "REVIEW_RESULT_INVALID", IntegrationPhase.REVIEW
                ),
                trace=trace,
            )
        trace.append(
            _event(
                6, IntegrationTraceEventType.REVIEW_COMPLETED, IntegrationPhase.REVIEW
            )
        )
        failed_statuses = {
            OrchestrationStatus.FAILED_BEFORE_PIPELINE,
            OrchestrationStatus.FAILED_AFTER_PIPELINE,
            OrchestrationStatus.FAILED_DURING_EDITORIAL_HANDOFF,
        }
        operational_failure = review_result.status in failed_statuses
        return self._finalize(
            request,
            generation_result=generation_result,
            draft_fingerprint=draft_fingerprint,
            review_result=review_result,
            status=(
                IntegrationStatus.FAILED_DURING_REVIEW
                if operational_failure
                else IntegrationStatus.COMPLETED
            ),
            diagnostic=(
                _diagnostic("REVIEW_OPERATIONAL_FAILURE", IntegrationPhase.REVIEW)
                if operational_failure
                else None
            ),
            trace=trace,
        )

    def _finalize(
        self,
        request,
        *,
        generation_result,
        draft_fingerprint,
        review_result,
        status,
        diagnostic,
        trace,
    ):
        diagnostics = (diagnostic,) if diagnostic else ()
        trace = (
            *trace,
            _event(
                len(trace),
                IntegrationTraceEventType.FINALIZED,
                IntegrationPhase.FINALIZATION,
            ),
        )
        review_invoked = any(
            item.event_type is IntegrationTraceEventType.REVIEW_STARTED
            for item in trace
        )
        review_completed = review_result is not None
        review_completed_operationally = review_completed and status is not (
            IntegrationStatus.FAILED_DURING_REVIEW
        )
        editorial_present = bool(review_result and review_result.editorial_result)
        completeness = IntegrationCompleteness(
            generation_requested=True,
            generation_completed=generation_result is not None,
            generation_succeeded=draft_fingerprint is not None,
            draft_validated=draft_fingerprint is not None,
            review_required=request.integration_policy.require_review_after_generation,
            review_eligible=draft_fingerprint is not None,
            review_invoked=review_invoked,
            review_completed=review_completed,
            editorial_outcome_present=editorial_present,
            limited_completion=status is IntegrationStatus.COMPLETED_WITHOUT_REVIEW
            or bool(review_result and review_result.report.completeness.limited_review),
        )
        outcome = EditorialReviewIntegrationOutcome.build(
            generation_succeeded=draft_fingerprint is not None,
            review_performed=review_invoked,
            review_completed_operationally=review_completed_operationally,
            editorial_outcome_present=editorial_present,
            integration_completed=status
            in {
                IntegrationStatus.COMPLETED,
                IntegrationStatus.COMPLETED_WITHOUT_REVIEW,
            },
            limited_completion=completeness.limited_completion,
        )
        report_values = {
            "integration_id": self.integration_id,
            "integration_version": self.integration_version,
            "request_fingerprint": request.request_fingerprint,
            "generation_request_fingerprint": request.generation.invocation_fingerprint,
            "generation_present": generation_result is not None,
            "generation_result_fingerprint": _identity(generation_result),
            "draft_fingerprint": draft_fingerprint,
            "review_required": request.integration_policy.require_review_after_generation,
            "review_status": review_result.status.value if review_result else None,
            "review_result_fingerprint": (
                review_result.result_fingerprint if review_result else None
            ),
            "editorial_status": (
                review_result.editorial_result.decision.status.value
                if editorial_present
                else None
            ),
            "integration_status": status,
            "review_performed": review_invoked,
            "limited_completion": completeness.limited_completion,
            "diagnostic_codes": tuple(item.code for item in diagnostics),
            "completeness": completeness,
        }
        report = EditorialReviewIntegrationReport(
            **report_values, report_fingerprint=fingerprint(report_values)
        )
        return EditorialReviewIntegrationResult.build(
            request_fingerprint=request.request_fingerprint,
            generation_result=generation_result,
            draft_fingerprint=draft_fingerprint,
            review_result=review_result,
            status=status,
            lifecycle=(
                IntegrationLifecycle.FINALIZED
                if status
                in {
                    IntegrationStatus.COMPLETED,
                    IntegrationStatus.COMPLETED_WITHOUT_REVIEW,
                }
                else IntegrationLifecycle.FAILED
            ),
            diagnostics=diagnostics,
            trace=trace,
            outcome=outcome,
            report=report,
        )


def _diagnostic(code: str, phase: IntegrationPhase) -> IntegrationDiagnostic:
    return IntegrationDiagnostic.build(
        code=code, severity=IntegrationDiagnosticSeverity.ERROR, phase=phase
    )


def _event(
    sequence: int,
    event_type: IntegrationTraceEventType,
    phase: IntegrationPhase,
    code: str | None = None,
) -> IntegrationTraceEvent:
    return IntegrationTraceEvent.build(
        sequence=sequence, event_type=event_type, phase=phase, code=code
    )


def _identity(value: Any) -> str | None:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        return fingerprint(value.model_dump(mode="json"))
    return fingerprint(value)
