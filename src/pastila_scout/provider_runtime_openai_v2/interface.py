"""Narrow injected contracts for future trusted runtime composition."""

from typing import Protocol


class OpenAICredentialSourceV2(Protocol):
    """Trusted source that supplies one API key on operational composition."""

    def get_api_key(self) -> str: ...


class OpenAISDKFactoryV2(Protocol):
    """Trusted synchronous factory for an official SDK client."""

    def create_client(self, *, api_key: str, max_retries: int) -> object: ...

    def close_client(self, client: object) -> None: ...


class OpenAIRuntimeLifecycleV2(Protocol):
    """Idempotent owner of one successfully constructed SDK client."""

    def close(self) -> None: ...


__all__ = (
    "OpenAICredentialSourceV2",
    "OpenAIRuntimeLifecycleV2",
    "OpenAISDKFactoryV2",
)
