"""Deterministic configuration-driven standard manifest provider."""

from pastila_scout.editor.qa.manifest import EditorialReviewManifest, ReviewerPlan
from pastila_scout.editor.qa.orchestration.models import ManifestProviderDescriptor
from pastila_scout.editor.qa.validation import draft_component_ids


class StandardReviewManifestProvider:
    descriptor = ManifestProviderDescriptor(
        provider_id="standard-editorial-review-manifest",
        provider_version="1.0.0",
    )

    def __init__(self, reviewer):
        self.reviewer_id = reviewer.reviewer_id
        self.reviewer_version = reviewer.reviewer_version
        self.capabilities = reviewer.capabilities

    def resolve(self, draft, policy):
        del policy
        return EditorialReviewManifest.build(
            (
                ReviewerPlan(
                    reviewer_id=self.reviewer_id,
                    reviewer_version=self.reviewer_version,
                    capabilities=self.capabilities,
                    target_component_ids=draft_component_ids(draft),
                    required=True,
                ),
            )
        )
