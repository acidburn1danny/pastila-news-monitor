"""Private CLI bridge to verified Editor application composition."""

from pastila_scout.editor_application_v1 import EditorApplicationCoordinatorV1
from pastila_scout.editor_application_v1.runtime_composition import (
    _compose_editor_application_runtime_v1,
)


def _compose_editor_cli_application_v1() -> EditorApplicationCoordinatorV1:
    """Compose one fresh verified Editor application coordinator."""

    return _compose_editor_application_runtime_v1()


__all__: tuple[str, ...] = ()
