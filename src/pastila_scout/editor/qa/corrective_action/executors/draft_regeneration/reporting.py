"""Safe deterministic regeneration reports and serialization."""

import json

from pastila_scout.editor.qa.models import fingerprint

from .models import DraftRegenerationReport, DraftRegenerationResult
from .preparation import DraftRegenerationPreparationResult


def build_draft_regeneration_preparation_report(
    result: DraftRegenerationPreparationResult,
) -> dict:
    """Return a content-free, deterministic preparation projection."""

    request = result.executor_request
    regeneration = result.regeneration_request
    evaluation = result.precondition_evaluation
    return {
        "report_version": "1",
        "outcome": result.operational_outcome.value,
        "status": result.status.value,
        "executor_id": request.executor_descriptor.executor_id,
        "plan_type": request.plan.plan_type.value,
        "execution_mode": request.plan.execution_mode.value,
        "capability": request.plan.required_capability.value,
        "authorization_state": request.execution_context.authorization_state.value,
        "policy_version": regeneration.policy.policy_version if regeneration else None,
        "source_draft_present": bool(
            regeneration and regeneration.regeneration_input.source_draft
        ),
        "controlled_generation_request_version": (
            regeneration.regeneration_input.controlled_generation_contract_version
            if regeneration
            else None
        ),
        "overall_precondition_status": (
            evaluation.overall_status.value if evaluation else None
        ),
        "failed_preconditions": (
            [
                item.precondition.value
                for item in evaluation.evaluations
                if item.status.value != "satisfied"
            ]
            if evaluation
            else []
        ),
        "diagnostic_code": result.diagnostic.code.value if result.diagnostic else None,
        "final_phase": result.terminal_state.phase.value,
        "revision": result.terminal_state.revision,
        "executor_request_fingerprint": request.request_fingerprint,
        "regeneration_request_fingerprint": (
            regeneration.request_fingerprint if regeneration else None
        ),
        "controlled_generation_request_fingerprint": (
            result.controlled_generation_request.invocation_fingerprint
            if result.controlled_generation_request
            else None
        ),
        "precondition_evaluation_fingerprint": (
            evaluation.evaluation_fingerprint if evaluation else None
        ),
        "state_fingerprint": result.terminal_state.state_fingerprint,
        "result_fingerprint": result.result_fingerprint,
    }


def serialize_draft_regeneration_preparation_report(report: dict) -> str:
    """Serialize only an approved preparation projection."""

    return json.dumps(report, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def build_draft_regeneration_report(
    result: DraftRegenerationResult,
) -> DraftRegenerationReport:
    """Project only safe authoritative lineage and outcome fields."""

    request = result.request
    executor_request = request.executor_request
    plan = executor_request.plan
    source = request.regeneration_input.source_draft
    return DraftRegenerationReport.build(
        outcome=result.operational_outcome,
        status=result.status,
        plan_type=plan.plan_type.value,
        execution_mode=plan.execution_mode.value,
        required_capability=plan.required_capability.value,
        executor_id=executor_request.executor_descriptor.executor_id,
        policy_version=request.policy.policy_version,
        controlled_generation_contract_version=(
            request.regeneration_input.controlled_generation_contract_version
        ),
        executor_request_fingerprint=executor_request.request_fingerprint,
        planning_result_fingerprint=executor_request.planning_result.result_fingerprint,
        plan_fingerprint=plan.plan_fingerprint,
        source_draft_fingerprint=fingerprint(source) if source else None,
        regenerated_draft_fingerprint=(
            fingerprint(result.regenerated_draft) if result.regenerated_draft else None
        ),
        generation_result_fingerprint=(
            fingerprint(result.generation_result) if result.generation_result else None
        ),
        output_reference_fingerprint=(
            result.output_reference.output_reference_fingerprint
            if result.output_reference
            else None
        ),
        diagnostic_code=result.diagnostic.code if result.diagnostic else None,
    )


def validate_draft_regeneration_report(
    report: DraftRegenerationReport, result: DraftRegenerationResult
) -> None:
    """Reject any report that contradicts its authoritative result."""

    if report != build_draft_regeneration_report(result):
        raise ValueError("draft-regeneration report contradicts result")


def serialize_draft_regeneration_report(report: DraftRegenerationReport) -> str:
    """Serialize only the safe projection using deterministic UTF-8 JSON."""

    return json.dumps(
        report.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def render_draft_regeneration_report(report: DraftRegenerationReport) -> str:
    """Render safe outcome and lineage without draft content."""

    return (
        f"Regeneration outcome: {report.outcome.value}\n"
        f"Regeneration status: {report.status.value}\n"
        f"Plan type: {report.plan_type}\n"
        f"Capability: {report.required_capability}\n"
        f"Executor: {report.executor_id}\n"
        f"Diagnostic: {report.diagnostic_code.value if report.diagnostic_code else 'absent'}\n"
    )
