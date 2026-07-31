"""Application-facing M6C.5E generation-to-review integration API."""

from pastila_scout.editor.qa.integration.composition import (
    build_standard_editorial_review_integration_service,
    generate_and_review_episode,
)
from pastila_scout.editor.qa.integration.models import (
    ControlledGenerationInvocation,
    EditorialReviewIntegrationDescriptor,
    EditorialReviewIntegrationOutcome,
    EditorialReviewIntegrationPolicy,
    EditorialReviewIntegrationRequest,
    EditorialReviewIntegrationResult,
    IntegrationLifecycle,
    IntegrationStatus,
)
from pastila_scout.editor.qa.integration.reporting import (
    render_integration_report,
    serialize_integration_report,
)
from pastila_scout.editor.qa.integration.service import (
    EditorialReviewIntegrationService,
)

__all__ = [
    "ControlledGenerationInvocation",
    "EditorialReviewIntegrationDescriptor",
    "EditorialReviewIntegrationOutcome",
    "EditorialReviewIntegrationPolicy",
    "EditorialReviewIntegrationRequest",
    "EditorialReviewIntegrationResult",
    "EditorialReviewIntegrationService",
    "IntegrationLifecycle",
    "IntegrationStatus",
    "build_standard_editorial_review_integration_service",
    "generate_and_review_episode",
    "render_integration_report",
    "serialize_integration_report",
]
