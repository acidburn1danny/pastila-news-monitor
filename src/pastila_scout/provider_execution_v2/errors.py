"""Provider-neutral execution boundary errors."""


class ProviderExecutionBoundaryError(RuntimeError):
    """Base error for failures at the provider execution boundary."""


class ExecutionTimeoutError(ProviderExecutionBoundaryError):
    """The execution exceeded its declared timeout policy."""


class ExecutionCancelledError(ProviderExecutionBoundaryError):
    """The execution was cancelled before completion."""


class ProviderExecutionError(ProviderExecutionBoundaryError):
    """A provider reported an execution-layer failure."""


class InternalExecutionError(ProviderExecutionBoundaryError):
    """The execution boundary failed independently of the provider."""


class ExecutionConfigurationError(ProviderExecutionBoundaryError):
    """Execution could not start because its contract was invalid."""


__all__ = (
    "ExecutionCancelledError",
    "ExecutionConfigurationError",
    "ExecutionTimeoutError",
    "InternalExecutionError",
    "ProviderExecutionBoundaryError",
    "ProviderExecutionError",
)
