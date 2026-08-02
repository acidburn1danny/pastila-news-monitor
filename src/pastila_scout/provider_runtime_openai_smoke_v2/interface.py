"""Private structural contracts for injected offline smoke execution."""

from typing import Protocol

from .models import OpenAISmokeTestConfigurationV2, OpenAISmokeTestResultV2


class _CredentialSourceV2(Protocol):  # noqa: PYI046
    def get_api_key(self) -> str: ...


class _SmokeExecutorV2(Protocol):
    def execute(self) -> str: ...


class _RuntimeCompositionV2(Protocol):
    @property
    def executor(self) -> _SmokeExecutorV2: ...

    def close(self) -> None: ...


class _RuntimeComposerV2(Protocol):  # noqa: PYI046
    def compose(
        self, *, api_key: str, model: str, timeout_seconds: float
    ) -> _RuntimeCompositionV2: ...


class _OpenAISmokeTestRunnerContractV2(Protocol):  # noqa: PYI046
    """Shape implemented by the public injected runner."""

    def run(
        self, configuration: OpenAISmokeTestConfigurationV2
    ) -> OpenAISmokeTestResultV2: ...


__all__: tuple[str, ...] = ()
