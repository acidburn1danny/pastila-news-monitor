"""Safe deterministic operational report rendering."""

from pastila_scout.editor.qa.pipeline.models import ReviewerPipelineExecutionReport


def build_execution_report(result):
    return ReviewerPipelineExecutionReport.from_result(result)


def render_execution_report(report):
    result = report.result
    lines = [
        f"Pipeline: {result.pipeline_id}@{result.pipeline_version}",
        f"Status: {result.status.value}",
        f"Selected: {len(result.coverage.selected_execution_ids)}",
    ]
    lines.extend(f"{name}: {count}" for name, count in report.outcome_counts)
    for diagnostic in result.diagnostics:
        lines.append(
            f"{diagnostic.severity.value.upper()} {diagnostic.code} {diagnostic.execution_id or '-'}"
        )
    return "\n".join(lines) + "\n"
