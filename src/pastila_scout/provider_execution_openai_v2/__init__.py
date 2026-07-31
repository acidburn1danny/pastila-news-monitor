"""Contracts and pure mappings for a future OpenAI execution adapter."""

from .errors import (
    OpenAIClientContractError,
    OpenAIConfigurationError,
    OpenAIExecutionBoundaryError,
    OpenAIRequestMappingError,
    OpenAIResponseMappingError,
)
from .executor import OpenAIProviderExecutorV2
from .interface import OpenAIExecutionClientV2
from .mapping import build_openai_execution_request, project_openai_execution_response
from .models import (
    OpenAIClientErrorCategoryV2,
    OpenAIExecutionConfigV2,
    OpenAIExecutionMessageV2,
    OpenAIExecutionOutputV2,
    OpenAIExecutionRequestV2,
    OpenAIExecutionResponseV2,
)

__all__ = (
    "OpenAIClientContractError",
    "OpenAIClientErrorCategoryV2",
    "OpenAIConfigurationError",
    "OpenAIExecutionBoundaryError",
    "OpenAIExecutionClientV2",
    "OpenAIExecutionConfigV2",
    "OpenAIExecutionMessageV2",
    "OpenAIExecutionOutputV2",
    "OpenAIExecutionRequestV2",
    "OpenAIExecutionResponseV2",
    "OpenAIProviderExecutorV2",
    "OpenAIRequestMappingError",
    "OpenAIResponseMappingError",
    "build_openai_execution_request",
    "project_openai_execution_response",
)
