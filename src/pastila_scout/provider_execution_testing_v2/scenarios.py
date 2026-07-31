"""Deterministic scenarios for the provider execution test harness."""

from enum import StrEnum


class ExecutionScenarioV2(StrEnum):
    """One deterministic execution-boundary outcome."""

    COMPLETED = "completed"
    PROVIDER_FAILURE = "provider_failure"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    INTERNAL_FAILURE = "internal_failure"


__all__ = ("ExecutionScenarioV2",)
