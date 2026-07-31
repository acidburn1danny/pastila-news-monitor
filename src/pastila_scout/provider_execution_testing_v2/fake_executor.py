"""Deterministic provider-neutral execution contract harness."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from pydantic import ValidationError

from pastila_scout.provider_execution_v2 import (
    ExecutionOutcomeV2,
    ProviderExecutionRequestV2,
    ProviderExecutionResultV2,
)
from pastila_scout.provider_v2 import ProviderResultProjectionV2

from .history import _ExecutionHistoryRecordV2
from .scenarios import ExecutionScenarioV2

_FINISHED_AT = datetime(2000, 1, 1, tzinfo=UTC)

_FAILURES = {
    ExecutionScenarioV2.PROVIDER_FAILURE: (
        "fake-provider-failure",
        "Deterministic provider failure.",
    ),
    ExecutionScenarioV2.TIMEOUT: (
        "fake-timeout",
        "Deterministic execution timeout.",
    ),
    ExecutionScenarioV2.CANCELLED: (
        "fake-cancelled",
        "Deterministic execution cancellation.",
    ),
    ExecutionScenarioV2.INTERNAL_FAILURE: (
        "fake-internal-execution-failure",
        "Deterministic internal execution failure.",
    ),
}


@dataclass(frozen=True, slots=True)
class FakeProviderExecutorV2:
    """Predictable implementation of the execution protocol for contract tests."""

    scenario: ExecutionScenarioV2
    provider_projection: ProviderResultProjectionV2 | None = None
    _history: list[_ExecutionHistoryRecordV2] = field(
        default_factory=list, init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if not isinstance(self.scenario, ExecutionScenarioV2):
            raise TypeError("scenario must be an ExecutionScenarioV2")
        projection = self.provider_projection
        if self.scenario is ExecutionScenarioV2.COMPLETED:
            if projection is None:
                raise ValueError("completed scenario requires a provider projection")
            try:
                projection = ProviderResultProjectionV2.model_validate(
                    projection.model_dump(mode="python", warnings=False), strict=True
                )
            except (AttributeError, TypeError, ValueError, ValidationError) as error:
                raise ValueError("invalid provider projection") from error
            object.__setattr__(self, "provider_projection", projection)
        elif projection is not None:
            raise ValueError("non-completed scenario forbids a provider projection")

    @property
    def execution_count(self) -> int:
        """Return the number of recorded invocations."""

        return len(self._history)

    @property
    def last_execution(self) -> _ExecutionHistoryRecordV2 | None:
        """Return the latest immutable record, if one exists."""

        return self._history[-1] if self._history else None

    @property
    def history(self) -> tuple[_ExecutionHistoryRecordV2, ...]:
        """Return an immutable ordered snapshot of execution history."""

        return tuple(self._history)

    def execute(self, request: ProviderExecutionRequestV2) -> ProviderExecutionResultV2:
        """Return the configured deterministic outcome and record it."""

        try:
            authority = ProviderExecutionRequestV2.model_validate(request)
        except (TypeError, ValueError, ValidationError) as error:
            raise ValueError("invalid provider execution request") from error
        result = self._result_for(authority)
        self._history.append(
            _ExecutionHistoryRecordV2(
                request=authority,
                scenario=self.scenario,
                result=result,
            )
        )
        return result

    def reset(self) -> None:
        """Clear recorded calls without changing configuration or contracts."""

        self._history.clear()

    def _result_for(
        self, request: ProviderExecutionRequestV2
    ) -> ProviderExecutionResultV2:
        common = {
            "request_id": request.context.request_id,
            "provider_id": request.provider.provider_id,
            "request_envelope_identity": request.request_envelope.identity,
            "finished_at": _FINISHED_AT,
        }
        if self.scenario is ExecutionScenarioV2.COMPLETED:
            return ProviderExecutionResultV2(
                **common,
                outcome=ExecutionOutcomeV2.COMPLETED,
                provider_result=self.provider_projection,
            )
        failure_code, failure_message = _FAILURES[self.scenario]
        outcomes = {
            ExecutionScenarioV2.PROVIDER_FAILURE: ExecutionOutcomeV2.PROVIDER_FAILURE,
            ExecutionScenarioV2.TIMEOUT: ExecutionOutcomeV2.TIMEOUT,
            ExecutionScenarioV2.CANCELLED: ExecutionOutcomeV2.CANCELLED,
            ExecutionScenarioV2.INTERNAL_FAILURE: (
                ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE
            ),
        }
        return ProviderExecutionResultV2(
            **common,
            outcome=outcomes[self.scenario],
            failure_code=failure_code,
            failure_message=failure_message,
        )


__all__ = ("FakeProviderExecutorV2",)
