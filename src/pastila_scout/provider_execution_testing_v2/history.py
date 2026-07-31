"""Private immutable history records for deterministic test execution."""

from dataclasses import dataclass

from pastila_scout.provider_execution_v2 import (
    ProviderExecutionRequestV2,
    ProviderExecutionResultV2,
)

from .scenarios import ExecutionScenarioV2


@dataclass(frozen=True, slots=True)
class _ExecutionHistoryRecordV2:
    request: ProviderExecutionRequestV2
    scenario: ExecutionScenarioV2
    result: ProviderExecutionResultV2


__all__: tuple[str, ...] = ()
