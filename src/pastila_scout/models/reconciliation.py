"""Portable contracts for planning and applying event reconciliation."""

from pydantic import BaseModel, ConfigDict, Field, model_validator

_ALLOWED_CATEGORIES = {
    "Politica",
    "Social",
    "Conspiratii",
    "Economie",
    "CanCan",
    "Externe",
    "Diverse",
}


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class ReconciliationArticle(_FrozenModel):
    id: int
    event_id: int
    source_id: str
    source_name: str
    url: str = ""
    normalized_url: str = ""
    title: str
    normalized_title: str
    summary: str | None
    published_at: str | None
    discovered_at: str
    raw_payload: str | None
    source_categories: tuple[str, ...] = ()
    source_priority: int = 1


class ReconciliationEvent(_FrozenModel):
    id: int
    canonical_title: str
    normalized_title: str
    summary: str | None
    categories: tuple[str, ...] = ()
    first_seen_at: str
    last_seen_at: str
    article_count: int
    source_count: int
    created_at: str
    updated_at: str
    canonical_article_id: int | None = None


class ReconciliationSnapshot(_FrozenModel):
    events: tuple[ReconciliationEvent, ...]
    articles: tuple[ReconciliationArticle, ...]


class PairwiseSimilarity(_FrozenModel):
    event_id: int
    related_event_id: int
    score: float


class CanonicalSelection(_FrozenModel):
    article_id: int
    title: str
    normalized_title: str
    summary: str | None
    reason: str


class ReconciliationProposal(_FrozenModel):
    event_ids: tuple[int, ...] = Field(min_length=2)
    article_ids: tuple[int, ...]
    canonical_titles: tuple[str, ...]
    publication_start: str | None
    publication_end: str | None
    sources: tuple[str, ...]
    source_ids: tuple[str, ...]
    current_categories: tuple[str, ...]
    proposed_categories: tuple[str, ...] = Field(max_length=3)
    unresolved_categories: bool
    pairwise_similarities: tuple[PairwiseSimilarity, ...]
    surviving_event_id: int
    resulting_article_count: int
    resulting_source_count: int
    canonical_selection: CanonicalSelection
    reason: str
    state_fingerprint: str

    @model_validator(mode="after")
    def validate_categories(self) -> ReconciliationProposal:
        """Require unique values from the controlled category vocabulary."""

        if len(self.proposed_categories) != len(set(self.proposed_categories)):
            raise ValueError("proposed categories must not contain duplicates")
        if not set(self.proposed_categories) <= _ALLOWED_CATEGORIES:
            raise ValueError("proposed categories contain unsupported values")
        if self.surviving_event_id not in self.event_ids:
            raise ValueError("surviving event must belong to the proposed group")
        if self.canonical_selection.article_id not in self.article_ids:
            raise ValueError("canonical article must belong to the proposed group")
        if len(self.article_ids) != len(set(self.article_ids)):
            raise ValueError("proposal article IDs must be unique")
        return self


class AmbiguousReconciliationGroup(_FrozenModel):
    event_ids: tuple[int, ...]
    matching_pairs: tuple[PairwiseSimilarity, ...]
    rejected_pairs: tuple[PairwiseSimilarity, ...]
    reason: str


class EventReconciliationPlan(_FrozenModel):
    format_version: int = 1
    generated_at: str
    database_path: str
    similarity_threshold: float
    lookback_hours: float
    proposals: tuple[ReconciliationProposal, ...]
    ambiguous_groups: tuple[AmbiguousReconciliationGroup, ...]

    @model_validator(mode="after")
    def validate_disjoint_proposals(self) -> EventReconciliationPlan:
        """Prevent one event from being applied through multiple groups."""

        event_ids = [event_id for item in self.proposals for event_id in item.event_ids]
        if len(event_ids) != len(set(event_ids)):
            raise ValueError("reconciliation proposals must contain disjoint events")
        return self


class ReconciliationApplicationReport(_FrozenModel):
    generated_at: str
    database_path: str
    plan_path: str
    dry_run: bool
    status: str
    proposals_validated: int
    proposals_applied: int
    surviving_event_ids: tuple[int, ...]
    merged_event_ids: tuple[int, ...]
    message: str
