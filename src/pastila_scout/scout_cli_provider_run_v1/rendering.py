"""Deterministic provider-neutral CLI rendering and exit codes."""

from pastila_scout.provider_execution_v2 import ExecutionOutcomeV2
from pastila_scout.provider_selection_v1 import ProviderChoiceV1
from pastila_scout.provider_v2 import ProviderResultStatusV2
from pastila_scout.scout_runtime_execution_v1 import ScoutRuntimeResultV1


def render_provider_run(
    provider: ProviderChoiceV1, result: ScoutRuntimeResultV1
) -> tuple[int, tuple[str, ...]]:
    """Render one neutral result without provider-specific interpretation."""
    execution = result.provider_result
    lines = [f"Provider: {provider.value}", f"Outcome: {execution.outcome.value}"]
    if execution.outcome is ExecutionOutcomeV2.COMPLETED:
        projection = execution.provider_result
        if projection is None:
            return 6, (*lines, "Failure: malformed execution result")
        lines.append(f"Status: {projection.status.value}")
        lines.extend(f"Output: {item.generated_text}" for item in projection.outputs)
        if projection.status is ProviderResultStatusV2.SUCCESS:
            return 0, tuple(lines)
        if projection.failure_code is not None:
            lines.append(f"Failure code: {projection.failure_code}")
        lines.append("Failure: provider execution was not fully successful")
        return 3, tuple(lines)
    if execution.failure_code is not None:
        lines.append(f"Failure code: {execution.failure_code}")
    lines.append("Failure: provider execution failed")
    exit_codes = {
        ExecutionOutcomeV2.PROVIDER_FAILURE: 3,
        ExecutionOutcomeV2.TIMEOUT: 4,
        ExecutionOutcomeV2.CANCELLED: 5,
        ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE: 6,
    }
    return exit_codes[execution.outcome], tuple(lines)


__all__ = ("render_provider_run",)
