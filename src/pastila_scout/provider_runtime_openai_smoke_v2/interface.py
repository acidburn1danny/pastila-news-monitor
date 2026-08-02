"""Private structural contract for the future smoke-test execution boundary."""

from typing import Never, Protocol

from .models import OpenAISmokeTestConfigurationV2


class _OpenAISmokeTestRunnerContractV2(Protocol):  # noqa: PYI046
    """Shape implemented by the public non-operational runner."""

    def run(self, configuration: OpenAISmokeTestConfigurationV2) -> Never: ...


__all__: tuple[str, ...] = ()
