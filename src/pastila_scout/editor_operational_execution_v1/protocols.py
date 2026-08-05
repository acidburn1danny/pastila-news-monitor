"""Package-private operational execution dependency protocols."""

from typing import Protocol

from pastila_scout.editor.generation.controlled_generator import ControlledGenerator
from pastila_scout.editor.generation.models import LanguageGenerationConfig
from pastila_scout.editor.generation.provider import LanguageModelProvider


class _EditorControlledGeneratorFactoryV1(Protocol):  # noqa: PYI046
    def create(
        self,
        *,
        provider: LanguageModelProvider,
        config: LanguageGenerationConfig,
    ) -> ControlledGenerator: ...


__all__: tuple[str, ...] = ()
