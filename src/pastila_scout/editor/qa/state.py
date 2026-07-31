"""Deeply immutable Editorial QA execution state."""

from pydantic import Field

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.models import (
    AggregationStatus,
    ApprovalStatus,
    EditorialFinding,
    EditorialReviewResult,
    ReviewerFailure,
)


class EditorialQAState(FrozenModel):
    revision: int = Field(default=0, ge=0)
    completed_manifest_item_ids: tuple[str, ...] = ()
    review_results: tuple[EditorialReviewResult, ...] = ()
    accepted_findings: tuple[EditorialFinding, ...] = ()
    reviewer_failures: tuple[ReviewerFailure, ...] = ()
    warnings: tuple[str, ...] = ()
    aggregation_status: AggregationStatus = AggregationStatus.PENDING
    approval_status: ApprovalStatus = ApprovalStatus.PENDING

    def accept_result(self, item_id, result):
        if item_id in self.completed_manifest_item_ids:
            raise ValueError("manifest item already completed")
        existing = {item.finding_id for item in self.accepted_findings}
        incoming = {item.finding_id for item in result.findings}
        if existing & incoming:
            raise ValueError("duplicate finding ID across reviewer results")
        return self.model_copy(
            update={
                "revision": self.revision + 1,
                "completed_manifest_item_ids": (
                    *self.completed_manifest_item_ids,
                    item_id,
                ),
                "review_results": (*self.review_results, result),
                "accepted_findings": (*self.accepted_findings, *result.findings),
                "warnings": (*self.warnings, *result.warnings),
            }
        )

    def accept_failure(self, failure):
        if failure.manifest_item_id in self.completed_manifest_item_ids:
            raise ValueError("manifest item already completed")
        return self.model_copy(
            update={
                "revision": self.revision + 1,
                "completed_manifest_item_ids": (
                    *self.completed_manifest_item_ids,
                    failure.manifest_item_id,
                ),
                "reviewer_failures": (*self.reviewer_failures, failure),
            }
        )

    def accept_aggregation(self):
        return self.model_copy(
            update={
                "revision": self.revision + 1,
                "completed_manifest_item_ids": (
                    *self.completed_manifest_item_ids,
                    "aggregate-findings",
                ),
                "aggregation_status": AggregationStatus.COMPLETED,
            }
        )

    def accept_approval(self, status):
        return self.model_copy(
            update={
                "revision": self.revision + 1,
                "completed_manifest_item_ids": (
                    *self.completed_manifest_item_ids,
                    "approval-decision",
                ),
                "approval_status": status,
            }
        )
