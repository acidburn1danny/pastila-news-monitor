"""Article and legacy review data contracts."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

QueueStatus = Literal["pending", "claimed", "reviewed", "rejected"]
ReviewDecision = Literal["keep", "reject", "backup"]


class ArticleCandidate(BaseModel):
    """A normalized article discovered by a source parser."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    source_id: str
    url: str
    title: str
    summary: str | None
    published_at: str | None
    raw_payload: dict[str, object] | None
