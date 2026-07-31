"""Deterministic Editorial QA review manifest."""

from pydantic import Field, model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.models import (
    ManifestStatus,
    ReviewerCapabilities,
    ReviewScope,
    fingerprint,
)


class ReviewerPlan(FrozenModel):
    reviewer_id: str
    reviewer_version: str
    capabilities: ReviewerCapabilities
    scope: ReviewScope = ReviewScope.EPISODE
    target_component_ids: tuple[str, ...] = ()
    required: bool = True


class EditorialReviewManifestItem(FrozenModel):
    manifest_item_id: str
    reviewer_id: str | None
    reviewer_version: str | None
    scope: ReviewScope
    target_component_ids: tuple[str, ...]
    dependencies: tuple[str, ...]
    status: ManifestStatus = ManifestStatus.PENDING
    required: bool
    operation: str = Field(pattern="^(review|aggregate|approval)$")

    def derived_status(self, statuses):
        values = tuple(
            statuses.get(item, ManifestStatus.PENDING) for item in self.dependencies
        )
        if any(value is ManifestStatus.FAILED for value in values):
            return ManifestStatus.FAILED if self.required else ManifestStatus.SKIPPED
        if all(value is ManifestStatus.COMPLETED for value in values):
            return ManifestStatus.READY
        return ManifestStatus.PENDING


class EditorialReviewManifest(FrozenModel):
    items: tuple[EditorialReviewManifestItem, ...]
    manifest_fingerprint: str

    @classmethod
    def build(cls, plans: tuple[ReviewerPlan, ...]):
        ordered = tuple(sorted(plans, key=_plan_key))
        items = []
        combinations = set()
        for plan in ordered:
            combination = (plan.reviewer_id, plan.scope, plan.target_component_ids)
            if combination in combinations:
                raise InvalidReviewManifestError(
                    "duplicate reviewer/target combination"
                )
            combinations.add(combination)
            suffix = plan.scope.value
            if plan.target_component_ids:
                suffix += "-" + "-".join(plan.target_component_ids)
            item_id = f"review-{plan.reviewer_id}-{suffix}"
            items.append(
                EditorialReviewManifestItem(
                    manifest_item_id=item_id,
                    reviewer_id=plan.reviewer_id,
                    reviewer_version=plan.reviewer_version,
                    scope=plan.scope,
                    target_component_ids=plan.target_component_ids,
                    dependencies=(),
                    required=plan.required,
                    operation="review",
                )
            )
        review_ids = tuple(item.manifest_item_id for item in items if item.required)
        items.append(
            EditorialReviewManifestItem(
                manifest_item_id="aggregate-findings",
                reviewer_id=None,
                reviewer_version=None,
                scope=ReviewScope.EPISODE,
                target_component_ids=(),
                dependencies=review_ids,
                required=True,
                operation="aggregate",
            )
        )
        items.append(
            EditorialReviewManifestItem(
                manifest_item_id="approval-decision",
                reviewer_id=None,
                reviewer_version=None,
                scope=ReviewScope.EPISODE,
                target_component_ids=(),
                dependencies=("aggregate-findings",),
                required=True,
                operation="approval",
            )
        )
        payload = tuple(item.model_dump(mode="python") for item in items)
        return cls(items=tuple(items), manifest_fingerprint=fingerprint(payload))

    @model_validator(mode="after")
    def validate_graph(self):
        ids = tuple(item.manifest_item_id for item in self.items)
        if len(ids) != len(set(ids)):
            raise ValueError("manifest item IDs must be unique")
        known = set(ids)
        for item in self.items:
            if not set(item.dependencies) <= known:
                raise ValueError("manifest contains unknown dependency")
        _reject_cycles(self.items)
        expected = fingerprint(
            tuple(item.model_dump(mode="python") for item in self.items)
        )
        if self.manifest_fingerprint != expected:
            raise ValueError("manifest fingerprint is inconsistent")
        return self


class InvalidReviewManifestError(ValueError):
    pass


def _plan_key(plan):
    return (
        plan.reviewer_id,
        plan.scope.value,
        plan.target_component_ids,
        plan.reviewer_version,
    )


def _reject_cycles(items):
    graph = {item.manifest_item_id: item.dependencies for item in items}
    visiting = set()
    visited = set()

    def visit(node):
        if node in visiting:
            raise ValueError("manifest dependency cycle")
        if node in visited:
            return
        visiting.add(node)
        for dependency in graph[node]:
            visit(dependency)
        visiting.remove(node)
        visited.add(node)

    for node in graph:
        visit(node)
