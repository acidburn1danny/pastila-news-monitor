"""Authoritative deterministic M6C.5F corrective-action decision service."""

from typing import Any

from pastila_scout.editor.qa.corrective_action.evaluation import (
    InvalidUpstreamStateError,
    UnsupportedUpstreamStatusError,
    evaluate_decision,
)
from pastila_scout.editor.qa.corrective_action.models import (
    CONTRACT_VERSION,
    ENGINE_ID,
    CorrectiveActionDecision,
    CorrectiveActionDecisionCompleteness,
    CorrectiveActionDecisionDescriptor,
    CorrectiveActionDecisionDiagnostic,
    CorrectiveActionDecisionDiagnosticCode,
    CorrectiveActionDecisionDiagnosticSeverity,
    CorrectiveActionDecisionLifecycle,
    CorrectiveActionDecisionOutcome,
    CorrectiveActionDecisionPhase,
    CorrectiveActionDecisionReport,
    CorrectiveActionDecisionRequest,
    CorrectiveActionDecisionResult,
    CorrectiveActionDecisionTraceEvent,
    CorrectiveActionDecisionTraceType,
)
from pastila_scout.editor.qa.corrective_action.state import DecisionRuntimeState
from pastila_scout.editor.qa.integration import EditorialReviewIntegrationResult
from pastila_scout.editor.qa.models import fingerprint


class CorrectiveActionDecisionService:
    """Map one frozen M6C.5E result to one requested action without executing it."""

    def decide(self, request: Any) -> CorrectiveActionDecisionResult:
        state = DecisionRuntimeState.prepared().advance(
            CorrectiveActionDecisionLifecycle.VALIDATING,
            CorrectiveActionDecisionTraceType.REQUEST_RECEIVED,
            CorrectiveActionDecisionPhase.REQUEST_VALIDATION,
        )
        if not isinstance(request, CorrectiveActionDecisionRequest):
            return _failure(
                request=None,
                state=state,
                code=CorrectiveActionDecisionDiagnosticCode.INVALID_DECISION_REQUEST,
                phase=CorrectiveActionDecisionPhase.REQUEST_VALIDATION,
                outcome=CorrectiveActionDecisionOutcome.FAILED_INVALID_INPUT,
            )
        try:
            type(request.policy).model_validate(
                request.policy.model_dump(mode="python")
            )
        except Exception:  # noqa: BLE001 - public policy validation boundary
            return _failure(
                request=request,
                state=state,
                code=CorrectiveActionDecisionDiagnosticCode.INVALID_DECISION_POLICY,
                phase=CorrectiveActionDecisionPhase.POLICY_VALIDATION,
                outcome=CorrectiveActionDecisionOutcome.FAILED_INVALID_INPUT,
            )
        expected_request_fingerprint = fingerprint(
            {
                "contract_version": request.contract_version,
                "integration_result_fingerprint": request.integration_result.result_fingerprint,
                "policy_fingerprint": request.policy.policy_fingerprint,
            }
        )
        if (
            request.contract_version != CONTRACT_VERSION
            or request.request_fingerprint != expected_request_fingerprint
        ):
            return _failure(
                request=None,
                state=state,
                code=CorrectiveActionDecisionDiagnosticCode.INVALID_DECISION_REQUEST,
                phase=CorrectiveActionDecisionPhase.REQUEST_VALIDATION,
                outcome=CorrectiveActionDecisionOutcome.FAILED_INVALID_INPUT,
            )
        state = state.advance(
            CorrectiveActionDecisionLifecycle.VALIDATING,
            CorrectiveActionDecisionTraceType.REQUEST_VALIDATED,
            CorrectiveActionDecisionPhase.REQUEST_VALIDATION,
        )
        try:
            EditorialReviewIntegrationResult.model_validate(
                request.integration_result.model_dump(mode="python")
            )
        except Exception:  # noqa: BLE001 - frozen upstream validation boundary
            return _failure(
                request=request,
                state=state,
                code=CorrectiveActionDecisionDiagnosticCode.INVALID_INTEGRATION_RESULT,
                phase=CorrectiveActionDecisionPhase.UPSTREAM_RESULT_VALIDATION,
                outcome=CorrectiveActionDecisionOutcome.FAILED_INVALID_INPUT,
            )
        state = state.advance(
            CorrectiveActionDecisionLifecycle.VALIDATING,
            CorrectiveActionDecisionTraceType.UPSTREAM_RESULT_VALIDATED,
            CorrectiveActionDecisionPhase.UPSTREAM_RESULT_VALIDATION,
        ).advance(
            CorrectiveActionDecisionLifecycle.DECIDING,
            CorrectiveActionDecisionTraceType.POLICY_RESOLVED,
            CorrectiveActionDecisionPhase.POLICY_VALIDATION,
        )
        try:
            evaluation = evaluate_decision(request.integration_result, request.policy)
        except UnsupportedUpstreamStatusError:
            return _failure(
                request=request,
                state=state,
                code=CorrectiveActionDecisionDiagnosticCode.UNSUPPORTED_INTEGRATION_STATUS,
                phase=CorrectiveActionDecisionPhase.DECISION_EVALUATION,
                outcome=CorrectiveActionDecisionOutcome.FAILED_DURING_DECISION,
            )
        except InvalidUpstreamStateError:
            return _failure(
                request=request,
                state=state,
                code=CorrectiveActionDecisionDiagnosticCode.INCONSISTENT_UPSTREAM_STATE,
                phase=CorrectiveActionDecisionPhase.UPSTREAM_RESULT_VALIDATION,
                outcome=CorrectiveActionDecisionOutcome.FAILED_INVALID_INPUT,
            )
        state = state.advance(
            CorrectiveActionDecisionLifecycle.DECIDING,
            CorrectiveActionDecisionTraceType.DECISION_EVALUATED,
            CorrectiveActionDecisionPhase.DECISION_EVALUATION,
        )
        try:
            decision = CorrectiveActionDecision.build(
                action=evaluation.action,
                reason=evaluation.reason,
                source_integration_fingerprint=request.integration_result.result_fingerprint,
                source_editorial_status=evaluation.source_editorial_status,
                policy_fingerprint=request.policy.policy_fingerprint,
                policy_applied=evaluation.policy_applied,
                decision_rule_id=evaluation.decision_rule_id,
            )
        except Exception:  # noqa: BLE001 - decision construction boundary
            return _failure(
                request=request,
                state=state,
                code=CorrectiveActionDecisionDiagnosticCode.DECISION_CONSTRUCTION_FAILED,
                phase=CorrectiveActionDecisionPhase.DECISION_CONSTRUCTION,
                outcome=CorrectiveActionDecisionOutcome.FAILED_DURING_DECISION,
            )
        state = state.advance(
            CorrectiveActionDecisionLifecycle.DECIDED,
            CorrectiveActionDecisionTraceType.DECISION_CONSTRUCTED,
            CorrectiveActionDecisionPhase.DECISION_CONSTRUCTION,
        )
        try:
            return _finalize(request=request, decision=decision, state=state)
        except Exception:  # noqa: BLE001 - final result construction boundary
            return _failure(
                request=request,
                state=state,
                code=CorrectiveActionDecisionDiagnosticCode.FINALIZATION_FAILED,
                phase=CorrectiveActionDecisionPhase.FINALIZATION,
                outcome=CorrectiveActionDecisionOutcome.FAILED_DURING_FINALIZATION,
            )


def decide_corrective_action(
    integration_result: EditorialReviewIntegrationResult,
    *,
    policy=None,
) -> CorrectiveActionDecisionResult:
    """Delegate convenience usage to the request-based service."""

    from pastila_scout.editor.qa.corrective_action.policy import (
        build_standard_corrective_action_decision_policy,
    )

    resolved = policy or build_standard_corrective_action_decision_policy()
    return CorrectiveActionDecisionService().decide(
        CorrectiveActionDecisionRequest.build(integration_result, resolved)
    )


def _finalize(*, request, decision, state):
    completeness = CorrectiveActionDecisionCompleteness.build(
        input_present=True,
        input_validated=True,
        upstream_operational_status_observed=True,
        editorial_status_observed=_editorial_status(request.integration_result)
        is not None,
        policy_applied=decision.policy_applied,
        decision_produced=True,
        report_produced=True,
        finalized=True,
    )
    report = CorrectiveActionDecisionReport.build(
        engine_id=ENGINE_ID,
        contract_version=CONTRACT_VERSION,
        source_integration_fingerprint=request.integration_result.result_fingerprint,
        source_integration_status=request.integration_result.status.value,
        source_editorial_status=_editorial_status(request.integration_result),
        operational_outcome=CorrectiveActionDecisionOutcome.COMPLETED,
        requested_action=decision.action,
        decision_reason=decision.reason,
        policy_fingerprint=request.policy.policy_fingerprint,
        decision_fingerprint=decision.decision_fingerprint,
        diagnostic_codes=(),
        completeness=completeness,
    )
    state = state.advance(
        CorrectiveActionDecisionLifecycle.DECIDED,
        CorrectiveActionDecisionTraceType.REPORT_CONSTRUCTED,
        CorrectiveActionDecisionPhase.REPORTING,
    ).advance(
        CorrectiveActionDecisionLifecycle.FINALIZED,
        CorrectiveActionDecisionTraceType.FINALIZED,
        CorrectiveActionDecisionPhase.FINALIZATION,
    )
    return CorrectiveActionDecisionResult.build(
        descriptor=CorrectiveActionDecisionDescriptor.build(),
        request_fingerprint=request.request_fingerprint,
        integration_result=request.integration_result,
        operational_outcome=CorrectiveActionDecisionOutcome.COMPLETED,
        decision=decision,
        lifecycle=CorrectiveActionDecisionLifecycle.FINALIZED,
        diagnostics=(),
        trace=state.trace,
        completeness=completeness,
        report=report,
    )


def _failure(*, request, state, code, phase, outcome):
    diagnostic = CorrectiveActionDecisionDiagnostic.build(
        code=code,
        severity=CorrectiveActionDecisionDiagnosticSeverity.ERROR,
        phase=phase,
    )
    state = state.advance(
        CorrectiveActionDecisionLifecycle.FAILED,
        CorrectiveActionDecisionTraceType.FAILED,
        phase,
        code.value,
    )
    integration_result = request.integration_result if request else None
    completeness = CorrectiveActionDecisionCompleteness.build(
        input_present=integration_result is not None,
        input_validated=request is not None,
        upstream_operational_status_observed=request is not None,
        editorial_status_observed=bool(
            integration_result and _editorial_status(integration_result)
        ),
        policy_applied=False,
        decision_produced=False,
        report_produced=True,
        finalized=True,
    )
    report = CorrectiveActionDecisionReport.build(
        engine_id=ENGINE_ID,
        contract_version=CONTRACT_VERSION,
        source_integration_fingerprint=(
            integration_result.result_fingerprint if integration_result else None
        ),
        source_integration_status=(
            integration_result.status.value if integration_result else None
        ),
        source_editorial_status=(
            _editorial_status(integration_result) if integration_result else None
        ),
        operational_outcome=outcome,
        requested_action=None,
        decision_reason=None,
        policy_fingerprint=request.policy.policy_fingerprint if request else None,
        decision_fingerprint=None,
        diagnostic_codes=(code,),
        completeness=completeness,
    )
    return CorrectiveActionDecisionResult.build(
        descriptor=CorrectiveActionDecisionDescriptor.build(),
        request_fingerprint=request.request_fingerprint if request else None,
        integration_result=integration_result,
        operational_outcome=outcome,
        decision=None,
        lifecycle=CorrectiveActionDecisionLifecycle.FAILED,
        diagnostics=(diagnostic,),
        trace=state.trace,
        completeness=completeness,
        report=report,
    )


def _trace(
    sequence,
    event_type,
    *,
    phase=None,
    code=None,
):
    phases = {
        CorrectiveActionDecisionTraceType.REQUEST_RECEIVED: CorrectiveActionDecisionPhase.REQUEST_VALIDATION,
        CorrectiveActionDecisionTraceType.REQUEST_VALIDATED: CorrectiveActionDecisionPhase.REQUEST_VALIDATION,
        CorrectiveActionDecisionTraceType.UPSTREAM_RESULT_VALIDATED: CorrectiveActionDecisionPhase.UPSTREAM_RESULT_VALIDATION,
        CorrectiveActionDecisionTraceType.POLICY_RESOLVED: CorrectiveActionDecisionPhase.POLICY_VALIDATION,
        CorrectiveActionDecisionTraceType.DECISION_EVALUATED: CorrectiveActionDecisionPhase.DECISION_EVALUATION,
        CorrectiveActionDecisionTraceType.DECISION_CONSTRUCTED: CorrectiveActionDecisionPhase.DECISION_CONSTRUCTION,
        CorrectiveActionDecisionTraceType.REPORT_CONSTRUCTED: CorrectiveActionDecisionPhase.REPORTING,
        CorrectiveActionDecisionTraceType.FINALIZED: CorrectiveActionDecisionPhase.FINALIZATION,
    }
    return CorrectiveActionDecisionTraceEvent.build(
        sequence=sequence,
        event_type=event_type,
        phase=phase or phases[event_type],
        code=code,
    )


def _editorial_status(result):
    if result.review_result and result.review_result.editorial_result:
        return result.review_result.editorial_result.decision.status.value
    return None
