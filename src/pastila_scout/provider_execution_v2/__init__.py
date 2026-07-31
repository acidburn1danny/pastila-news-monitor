"""Provider-neutral execution contracts for Module 2.9 Phase 7.2."""

from .errors import (
    ExecutionCancelledError,
    ExecutionConfigurationError,
    ExecutionTimeoutError,
    InternalExecutionError,
    ProviderExecutionBoundaryError,
    ProviderExecutionError,
)
from .interface import ProviderExecutorV2
from .models import (
    CancellationTokenV2,
    ExecutionContextV2,
    ExecutionOutcomeV2,
    ProviderExecutionRequestV2,
    ProviderExecutionResultV2,
    TimeoutPolicyV2,
)

__all__ = (
    "CancellationTokenV2",
    "ExecutionCancelledError",
    "ExecutionConfigurationError",
    "ExecutionContextV2",
    "ExecutionOutcomeV2",
    "ExecutionTimeoutError",
    "InternalExecutionError",
    "ProviderExecutionBoundaryError",
    "ProviderExecutionError",
    "ProviderExecutionRequestV2",
    "ProviderExecutionResultV2",
    "ProviderExecutorV2",
    "TimeoutPolicyV2",
)
