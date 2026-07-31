"""Provider-independent Editorial QA reviewer protocol and offline test doubles."""

from collections import deque
from typing import Protocol

from pastila_scout.editor.qa.models import (
    EditorialReviewRequest,
    EditorialReviewResult,
    ReviewerCapabilities,
    ReviewExecutionStatus,
)


class EditorialReviewer(Protocol):
    reviewer_id: str
    reviewer_version: str
    capabilities: ReviewerCapabilities

    def review(self, request: EditorialReviewRequest) -> EditorialReviewResult: ...


class ReviewerExecutionError(RuntimeError):
    pass


class NoOpEditorialReviewer:
    """Architectural reviewer that deterministically accepts its requested coverage."""

    def __init__(self, reviewer_id="noop", reviewer_version="1", capabilities=None):
        self.reviewer_id = reviewer_id
        self.reviewer_version = reviewer_version
        self.capabilities = capabilities or ReviewerCapabilities(values=("structure",))
        self.calls = []

    def review(self, request):
        self.calls.append(request)
        return EditorialReviewResult.build(
            reviewer_id=self.reviewer_id,
            reviewer_version=self.reviewer_version,
            status=ReviewExecutionStatus.COMPLETED,
            findings=(),
            warnings=(),
            reviewed_component_ids=request.component_ids,
        )


class ScriptedEditorialReviewer:
    """Return queued structured results/errors and record immutable requests."""

    def __init__(
        self, reviewer_id, responses, *, reviewer_version="1", capabilities=None
    ):
        self.reviewer_id = reviewer_id
        self.reviewer_version = reviewer_version
        self.capabilities = capabilities or ReviewerCapabilities(values=("structure",))
        self._responses = deque(responses)
        self.calls = []

    def review(self, request):
        self.calls.append(request)
        if not self._responses:
            raise ReviewerExecutionError("scripted reviewer response queue exhausted")
        response = self._responses.popleft()
        if isinstance(response, BaseException):
            raise response
        return (
            response
            if isinstance(response, EditorialReviewResult)
            else EditorialReviewResult.model_validate(response)
        )
