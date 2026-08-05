"""Application-owned Editor configuration and immutable contracts."""

from .configuration import (
    EditorApplicationGenerationConfigurationAuthorityV1,
    EditorEpisodeContextAuthorityV1,
    EditorSelectionProfileAuthorityV1,
)
from .errors import (
    EditorApplicationConfigurationError,
    EditorApplicationCoordinatorError,
    EditorApplicationExportError,
    EditorApplicationSerializationError,
)
from .models import (
    EditorApplicationExitCodeV1,
    EditorApplicationFailureCodeV1,
    EditorApplicationFailureV1,
    EditorApplicationGenerationConfigurationV1,
    EditorApplicationLifecycleStateV1,
    EditorApplicationRequestV1,
    EditorApplicationResultV1,
    EditorApplicationStatusV1,
    EditorOutputDestinationV1,
    EditorOverwritePolicyV1,
)

__all__ = (  # noqa: RUF022 - frozen specification order
    "EditorApplicationConfigurationError",
    "EditorApplicationCoordinatorError",
    "EditorApplicationExitCodeV1",
    "EditorApplicationExportError",
    "EditorApplicationFailureCodeV1",
    "EditorApplicationFailureV1",
    "EditorApplicationGenerationConfigurationV1",
    "EditorApplicationGenerationConfigurationAuthorityV1",
    "EditorApplicationLifecycleStateV1",
    "EditorApplicationRequestV1",
    "EditorApplicationResultV1",
    "EditorApplicationSerializationError",
    "EditorApplicationStatusV1",
    "EditorEpisodeContextAuthorityV1",
    "EditorOutputDestinationV1",
    "EditorOverwritePolicyV1",
    "EditorSelectionProfileAuthorityV1",
)
