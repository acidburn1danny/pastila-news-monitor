"""Offline OpenAI execution-to-SDK compatibility boundary."""

from .client import OpenAIExecutionSDKBridgeClientV2
from .errors import (
    OpenAIExecutionSDKBridgeConfigurationError,
    OpenAIExecutionSDKBridgeDependencyError,
    OpenAIExecutionSDKBridgeError,
)

__all__ = (  # noqa: RUF022 - public order is part of the frozen bridge contract
    "OpenAIExecutionSDKBridgeClientV2",
    "OpenAIExecutionSDKBridgeError",
    "OpenAIExecutionSDKBridgeConfigurationError",
    "OpenAIExecutionSDKBridgeDependencyError",
)
