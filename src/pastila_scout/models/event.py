"""Storage-independent canonical event and provenance contracts."""

from pydantic import BaseModel, ConfigDict, Field


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ArticleProvenance(_FrozenModel):
    id: int
    event_id: int
    source_id: str
    source_name: str
    url: str
    normalized_url: str
    title: str
    normalized_title: str
    summary: str | None
    published_at: str | None
    discovered_at: str
    raw_payload: str | None = None
    source_categories: tuple[str, ...] = ()
    source_priority: int = 1


class SourceProvenance(_FrozenModel):
    id: str
    name: str
    article_ids: tuple[int, ...]


class EventSnapshot(_FrozenModel):
    id: int
    canonical_title: str
    canonical_summary: str | None
    categories: tuple[str, ...] = Field(max_length=3)
    first_publication_at: str | None
    last_publication_at: str | None
    first_seen_at: str
    last_seen_at: str
    article_count: int
    source_count: int
    sources: tuple[SourceProvenance, ...]
    articles: tuple[ArticleProvenance, ...]
    canonical_article_id: int
    canonical_selection_reason: str


class ExistingEventMetadata(_FrozenModel):
    id: int
    canonical_title: str
    summary: str | None
    categories: tuple[str, ...] = ()
    first_seen_at: str
    last_seen_at: str
    canonical_article_id: int | None = None


class EventCanonicalizationChange(_FrozenModel):
    event_id: int
    changed: bool
    categories_before: tuple[str, ...]
    categories_after: tuple[str, ...]
    title_changed: bool
    summary_changed: bool
    canonical_title: str
    canonical_summary: str | None
    first_publication_at: str | None
    last_publication_at: str | None
    canonical_article_id: int
    selection_reason: str


class EventCanonicalizationReport(_FrozenModel):
    generated_at: str
    database_path: str
    dry_run: bool
    events_checked: int
    events_changed: int
    categories_added: int
    canonical_titles_changed: int
    canonical_summaries_changed: int
    unresolved_categories: int
    unchanged_events: int
    remaining_historical_matches: int
    remaining_historical_event_groups: tuple[tuple[int, ...], ...]
    changes: tuple[EventCanonicalizationChange, ...]
