"""Package-private command-time composition for the operational Editor."""

from __future__ import annotations

from typing import NoReturn

from pastila_scout.editor.engine import SelectionEngine
from pastila_scout.editor_generation_runtime_v1 import (
    EditorGenerationRuntimeCompositionError,
    EditorGenerationRuntimeSessionFactoryV1,
)
from pastila_scout.editor_generation_runtime_v1.composition import (
    _create_editor_generation_runtime_session_factory_v1,
)
from pastila_scout.editor_operational_execution_v1 import (
    EditorOperationalExecutionConfigurationError,
    EditorOperationalExecutionCoordinatorV1,
)
from pastila_scout.editor_operational_execution_v1.production import (
    _create_editor_operational_execution_coordinator_v1,
)
from pastila_scout.editor_operational_v1 import (
    EditorOperationalConfigurationError,
    EditorOperationalCoordinatorV1,
)

from .application import (
    EditorApplicationCoordinatorV1,
    _compose_editor_application_coordinator_v1,
)
from .errors import (
    EditorApplicationConfigurationError,
    EditorApplicationCoordinatorError,
)


class _EditorApplicationRuntimeCompositionDefectV1(Exception):
    __slots__ = ()


def _compose_editor_application_runtime_v1() -> EditorApplicationCoordinatorV1:
    failed = False
    try:
        preparation = EditorOperationalCoordinatorV1(SelectionEngine())
    except EditorOperationalConfigurationError:
        failed = True
        preparation = None
    if failed:
        _raise_configuration()
    failed = False
    try:
        runtime_factory = _create_editor_generation_runtime_session_factory_v1()
    except EditorGenerationRuntimeCompositionError:
        failed = True
        runtime_factory = None
    if failed:
        del preparation
        _raise_configuration()
    if type(runtime_factory) is not EditorGenerationRuntimeSessionFactoryV1:
        del preparation, runtime_factory
        _raise_defect()
    failed = False
    try:
        operational = _create_editor_operational_execution_coordinator_v1(
            session_factory=runtime_factory
        )
    except EditorOperationalExecutionConfigurationError:
        failed = True
        operational = None
    if failed:
        del preparation, runtime_factory
        _raise_configuration()
    if type(operational) is not EditorOperationalExecutionCoordinatorV1:
        del preparation, runtime_factory, operational
        _raise_defect()
    failed = False
    try:
        application = _compose_editor_application_coordinator_v1(
            preparation_coordinator=preparation,
            operational_execution_coordinator=operational,
        )
    except EditorApplicationConfigurationError:
        failed = True
        application = None
    if failed:
        del preparation, runtime_factory, operational
        _raise_configuration()
    if type(application) is not EditorApplicationCoordinatorV1:
        del preparation, runtime_factory, operational, application
        _raise_defect()
    del preparation, runtime_factory, operational
    return application


def _raise_configuration() -> NoReturn:
    error = EditorApplicationConfigurationError()
    raise error from None


def _raise_defect() -> NoReturn:
    defect = _EditorApplicationRuntimeCompositionDefectV1()
    del defect
    error = EditorApplicationCoordinatorError()
    raise error from None


__all__: tuple[str, ...] = ()
