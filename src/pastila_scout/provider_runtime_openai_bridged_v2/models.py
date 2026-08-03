"""Private safe outcomes for bridged OpenAI runtime composition."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class _SafeAssemblyFailure:
    category: str


__all__: tuple[str, ...] = ()
