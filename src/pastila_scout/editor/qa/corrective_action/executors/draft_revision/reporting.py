"""Content-safe deterministic draft-revision reporting."""

import json

from .models import DraftRevisionReport, DraftRevisionResult


def build_draft_revision_report(result: DraftRevisionResult) -> DraftRevisionReport:
    request = result.revision_request
    reference = result.output_reference
    return DraftRevisionReport.build(
        capability=request.executor_request.plan.required_capability.value,
        plan_type=request.executor_request.plan.plan_type.value,
        target_count=len(request.scope.targets),
        revision_outcome=result.revision_outcome,
        revision_status=result.revision_status,
        diagnostic_code=result.diagnostic.code if result.diagnostic else None,
        revision_request_fingerprint=request.request_fingerprint,
        revision_result_fingerprint=result.result_fingerprint,
        output_reference_fingerprint=(
            reference.output_reference_fingerprint if reference else None
        ),
    )


def serialize_draft_revision_report(report: DraftRevisionReport) -> str:
    return json.dumps(
        report.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def render_draft_revision_report(report: DraftRevisionReport) -> str:
    return (
        f"Revision outcome: {report.revision_outcome.value}\n"
        f"Revision status: {report.revision_status.value}\n"
        f"Targets: {report.target_count}\n"
        f"Diagnostic: {report.diagnostic_code.value if report.diagnostic_code else 'absent'}\n"
    )
