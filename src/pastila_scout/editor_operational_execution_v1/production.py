"""Private production composition for operational Editor execution."""

from __future__ import annotations

from pastila_scout.editor.generation.controlled_generator import ControlledGenerator
from pastila_scout.editor.generation.models import LanguageGenerationConfig
from pastila_scout.editor.generation.provider import LanguageModelProvider
from pastila_scout.editor_generation_runtime_v1 import (
    EditorGenerationRuntimeSessionFactoryV1,
)

from .coordinator import EditorOperationalExecutionCoordinatorV1


class _EditorControlledGeneratorFactoryV1Impl:
    __slots__ = ()

    def __init_subclass__(cls, **kwargs):
        del cls, kwargs
        raise TypeError("Editor controlled-generator factory cannot be subclassed.")

    def create(
        self,
        *,
        provider: LanguageModelProvider,
        config: LanguageGenerationConfig,
    ) -> ControlledGenerator:
        return ControlledGenerator(provider, config=config)

    def __repr__(self) -> str:
        return "_EditorControlledGeneratorFactoryV1Impl()"

    def __eq__(self, other: object) -> bool:
        return type(self) is _EditorControlledGeneratorFactoryV1Impl and type(
            other
        ) is type(self)

    def __copy__(self):
        return type(self)()

    def __deepcopy__(self, memo):
        del memo
        return self.__copy__()

    def __reduce_ex__(self, protocol):
        del self, protocol
        raise TypeError(
            "Editor application runtime composition values cannot be pickled."
        )


def _create_editor_operational_execution_coordinator_v1(
    *, session_factory: EditorGenerationRuntimeSessionFactoryV1
) -> EditorOperationalExecutionCoordinatorV1:
    return EditorOperationalExecutionCoordinatorV1(
        session_factory=session_factory,
        generator_factory=_EditorControlledGeneratorFactoryV1Impl(),
    )


__all__: tuple[str, ...] = ()
