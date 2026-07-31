"""OpenAI execution-boundary contract errors without SDK coupling."""

from pastila_scout.provider_execution_v2 import ProviderExecutionBoundaryError


class OpenAIExecutionBoundaryError(ProviderExecutionBoundaryError):
    """Base error for the OpenAI execution specification boundary."""


class OpenAIRequestMappingError(OpenAIExecutionBoundaryError):
    """A provider-neutral request could not be mapped to OpenAI."""


class OpenAIResponseMappingError(OpenAIExecutionBoundaryError):
    """An OpenAI response DTO could not be projected safely."""


class OpenAIClientContractError(OpenAIExecutionBoundaryError):
    """A future injected client violated its transport-neutral contract."""


class OpenAIConfigurationError(OpenAIExecutionBoundaryError):
    """OpenAI execution configuration was invalid."""


__all__ = (
    "OpenAIClientContractError",
    "OpenAIConfigurationError",
    "OpenAIExecutionBoundaryError",
    "OpenAIRequestMappingError",
    "OpenAIResponseMappingError",
)
