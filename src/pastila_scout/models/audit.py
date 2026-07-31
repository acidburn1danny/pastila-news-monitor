"""Pure contracts for read-only event integrity analysis."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

FindingSeverity = Literal["error", "warning"]


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class AuditArticle(_FrozenModel):
    """Minimal persisted article state required by the integrity audit."""

    id: int
    event_id: int | None
    source_id: str
    source_name: str | None = None
    title: str
    published_at: str | None = None


class AuditEvent(_FrozenModel):
    """Minimal persisted event state required by the integrity audit."""

    id: int
    canonical_title: str
    summary: str | None
    category: str | None
    first_seen_at: str
    last_seen_at: str
    article_count: int
    source_count: int


class EventIntegritySnapshot(_FrozenModel):
    """Storage-independent snapshot consumed by the audit service."""

    articles: tuple[AuditArticle, ...]
    events: tuple[AuditEvent, ...]


class EventIntegrityFinding(_FrozenModel):
    """One structural error or non-blocking warning."""

    severity: FindingSeverity
    code: str
    message: str
    event_id: int | None = None
    article_id: int | None = None


class HistoricalMatchProposal(_FrozenModel):
    """A read-only proposal that two existing events may be related."""

    event_id: int
    related_event_id: int
    score: float


class EventIntegrityReport(_FrozenModel):
    """Complete result of a read-only event integrity audit."""

    article_count: int
    event_count: int
    errors: tuple[EventIntegrityFinding, ...]
    warnings: tuple[EventIntegrityFinding, ...]
    historical_matches: tuple[HistoricalMatchProposal, ...]
