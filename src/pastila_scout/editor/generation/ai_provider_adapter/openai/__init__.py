"""Concrete OpenAI Controlled Revision adapter."""

from .client import OpenAIProviderClient
from .composition import (
    OpenAIControlledRevisionAdapter,
    OpenAIControlledRevisionComposition,
    compose_openai_controlled_revision_adapter,
)
from .errors import OpenAIExceptionNormalizer
from .interpreter import (
    OpenAIControlledRevisionInterpreter,
    OpenAIProviderOutputValidationFailure,
)
from .models import (
    OpenAIControlledRevisionProviderOutput,
    OpenAIExpectedOutputContractProjection,
    OpenAIResponsesPayload,
    OpenAIRevisedCallToActionComponent,
    OpenAIRevisedStoryComponent,
    OpenAIRevisedTextComponent,
    controlled_revision_schema_json,
    projected_controlled_revision_schema_json,
)
from .projector import OpenAIControlledRevisionProjector
from .reconstructor import (
    OpenAIControlledRevisionReconstructor,
    OpenAIReconstructionError,
)

__all__ = [
    "OpenAIControlledRevisionAdapter",
    "OpenAIControlledRevisionComposition",
    "OpenAIControlledRevisionInterpreter",
    "OpenAIControlledRevisionProjector",
    "OpenAIControlledRevisionProviderOutput",
    "OpenAIControlledRevisionReconstructor",
    "OpenAIExceptionNormalizer",
    "OpenAIExpectedOutputContractProjection",
    "OpenAIProviderClient",
    "OpenAIProviderOutputValidationFailure",
    "OpenAIReconstructionError",
    "OpenAIResponsesPayload",
    "OpenAIRevisedCallToActionComponent",
    "OpenAIRevisedStoryComponent",
    "OpenAIRevisedTextComponent",
    "compose_openai_controlled_revision_adapter",
    "controlled_revision_schema_json",
    "projected_controlled_revision_schema_json",
]
