"""Isolated specification boundary for a future official OpenAI SDK client."""

from .client import (
    OpenAISDKCapabilityV2,
    OpenAISDKClientV2,
    classify_openai_sdk_exception,
)
from .errors import (
    OpenAISDKBoundaryError,
    OpenAISDKConfigurationError,
    OpenAISDKDependencyError,
    OpenAISDKResponseError,
)
from .mapping import build_openai_sdk_request, reconstruct_openai_sdk_response
from .models import OpenAISDKRequestV2

__all__ = (
    "OpenAISDKBoundaryError",
    "OpenAISDKCapabilityV2",
    "OpenAISDKClientV2",
    "OpenAISDKConfigurationError",
    "OpenAISDKDependencyError",
    "OpenAISDKRequestV2",
    "OpenAISDKResponseError",
    "build_openai_sdk_request",
    "classify_openai_sdk_exception",
    "reconstruct_openai_sdk_response",
)
