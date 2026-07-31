"""Explicit M6C.5E application composition root."""

from pastila_scout.editor.qa.integration.models import EditorialReviewIntegrationRequest
from pastila_scout.editor.qa.integration.service import (
    EditorialReviewIntegrationService,
)
from pastila_scout.editor.qa.orchestration import (
    build_standard_editorial_review_orchestrator,
)


def build_standard_editorial_review_integration_service(
    *, generator, review_orchestrator=None
):
    return EditorialReviewIntegrationService(
        generator=generator,
        review_orchestrator=(
            review_orchestrator or build_standard_editorial_review_orchestrator()
        ),
    )


def generate_and_review_episode(*, generator, generation, **values):
    return build_standard_editorial_review_integration_service(
        generator=generator
    ).execute(EditorialReviewIntegrationRequest(generation=generation, **values))
