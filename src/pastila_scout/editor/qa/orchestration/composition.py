"""Explicit standard M6C.5D composition root and convenience API."""

from pastila_scout.editor.qa.orchestration.manifest import (
    StandardReviewManifestProvider,
)
from pastila_scout.editor.qa.orchestration.models import (
    EditorialReviewOrchestrationRequest,
)
from pastila_scout.editor.qa.orchestration.service import EditorialReviewOrchestrator
from pastila_scout.editor.qa.pipeline import (
    DeterministicReviewerPipeline,
    ReviewerRegistry,
)
from pastila_scout.editor.qa.rules import DeterministicRulesReviewer


def build_standard_editorial_review_orchestrator(
    *, reviewer=None, registry=None, pipeline=None, manifest_provider=None
):
    reviewer = reviewer or DeterministicRulesReviewer()
    registry = registry or ReviewerRegistry.build((reviewer,))
    pipeline = pipeline or DeterministicReviewerPipeline(registry)
    manifest_provider = manifest_provider or StandardReviewManifestProvider(reviewer)
    return EditorialReviewOrchestrator(
        pipeline=pipeline,
        manifest_provider=manifest_provider,
    )


def review_episode_draft(draft, **values):
    """Delegate convenience usage to the single request-based execution path."""

    return build_standard_editorial_review_orchestrator().review(
        EditorialReviewOrchestrationRequest(draft=draft, **values)
    )
