from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass(frozen=True, slots=True)
class ExpressionRecordV1:
    expression_id: str
    text: str
    owner_class: str
    semantic_gloss: str
    semantic_families: tuple[str, ...] = ()
    keywords: tuple[str, ...] = ()
    risk_tags: tuple[str, ...] = ()
    preferred_surface: str | None = None
    regionalism: bool = False
    regions: tuple[str, ...] = ()
    raw: bool = False
    meme: bool = False
    max_per_episode: int = 1
    cooldown_episodes: int = 0
    enabled: bool = True
    active_from: datetime | None = None
    active_until: datetime | None = None


@dataclass(frozen=True, slots=True)
class PreferredSurfaceV1:
    surface_id: str
    source_expression_id: str
    surface: str
    relation_type: str


@dataclass(frozen=True, slots=True)
class ProductiveFamilyV1:
    family_id: str
    members: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ControlledTermRecordV1:
    term_id: str
    term: str
    domains: tuple[str, ...]
    triggers: tuple[str, ...]
    factual_constraints: tuple[str, ...]
    risk_tags: tuple[str, ...]
    temporal_sensitivity: str
    max_per_episode: int
    cooldown_episodes: int
    enabled: bool = True
    active_from: datetime | None = None
    active_until: datetime | None = None


@dataclass(frozen=True, slots=True)
class ComedyDeviceRecordV1:
    device_id: str
    device_type: str
    family: str
    structure: str
    semantic_affordances: tuple[str, ...]
    best_for: tuple[str, ...]
    bad_for: tuple[str, ...]
    replaceable_slots: tuple[str, ...]
    forbidden_transforms: tuple[str, ...]
    source_expression_ids: tuple[str, ...] = ()
    callback_capable: bool = False
    signature_capable: bool = False
    compound_capable: bool = False
    compound_component_device_ids: tuple[str, ...] = ()
    max_per_episode: int = 1
    recurrence_mode: str = "ordinary"
    risk_tags: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class SignatureDeviceRecordV1:
    signature_id: str
    device_id: str
    family: str
    recurrence_mode: str
    max_per_episode: int
    hard_cooldown: int
    preferred_spacing_episodes: int
    canonical_signature: bool


@dataclass(frozen=True, slots=True)
class ExpressionCatalogV1:
    bundle_version: int
    content_sha256: str
    expressions: tuple[ExpressionRecordV1, ...]
    preferred_surfaces: tuple[PreferredSurfaceV1, ...]
    productive_families: tuple[ProductiveFamilyV1, ...]
    controlled_terms: tuple[ControlledTermRecordV1, ...]
    comedy_devices: tuple[ComedyDeviceRecordV1, ...]
    signature_devices: tuple[SignatureDeviceRecordV1, ...]
    source_authority_ids: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class EditorialRetrievalContextV1:
    event_id: str
    title: str
    summary: str = ""
    categories: tuple[str, ...] = ()
    source_ids: tuple[str, ...] = ()
    source_names: tuple[str, ...] = ()
    source_count: int = 0
    language: str = "ro"
    episode_position: int = 0
    keywords: tuple[str, ...] = ()
    topic_tags: tuple[str, ...] = ()
    protected_dimensions: tuple[str, ...] = ()
    humor_intensity: int = 0
    roast_eligible: bool = False
    profanity_ceiling: int = 0
    raw_eligible: bool = False
    victim_sensitive: bool = False
    tragedy_sensitive: bool = False
    bureaucracy: bool = False
    patronage: bool = False
    unfinished_project: bool = False
    disinformation: bool = False
    entertainment: bool = False
    international: bool = False
    region: str | None = None
    political_context: bool = False
    meme_context: bool = False


@dataclass(frozen=True, slots=True)
class EpisodeVoiceStateV1:
    used_expression_ids: tuple[str, ...] = ()
    used_expression_families: tuple[str, ...] = ()
    used_device_ids: tuple[str, ...] = ()
    used_device_families: tuple[str, ...] = ()
    used_signature_families: tuple[str, ...] = ()
    raw_usage_count: int = 0
    meme_usage_count: int = 0
    regional_usage: tuple[str, ...] = ()
    controlled_term_usage: tuple[tuple[str, int], ...] = ()
    prior_episode_last_used: tuple[tuple[str, int], ...] = ()


@dataclass(frozen=True, slots=True)
class PaletteItemReasonV1:
    reason_codes: tuple[str, ...]
    score_components: tuple[tuple[str, int], ...]
    total_score: int


@dataclass(frozen=True, slots=True)
class PaletteItemV1:
    authority_id: str
    display_text: str
    family: str
    reason: PaletteItemReasonV1


@dataclass(frozen=True, slots=True)
class StoryVoicePaletteV1:
    event_id: str
    expressions: tuple[PaletteItemV1, ...] = ()
    controlled_terms: tuple[PaletteItemV1, ...] = ()
    comedy_devices: tuple[PaletteItemV1, ...] = ()
    signature_devices: tuple[PaletteItemV1, ...] = ()

    @classmethod
    def empty(cls, event_id: str) -> StoryVoicePaletteV1:
        return cls(event_id=event_id)

    @property
    def total_count(self) -> int:
        return sum(
            len(items)
            for items in (
                self.expressions,
                self.controlled_terms,
                self.comedy_devices,
                self.signature_devices,
            )
        )


@dataclass(frozen=True, slots=True)
class RetrievalTraceItemV1:
    authority_id: str
    selected: bool
    reason_codes: tuple[str, ...]
    score: int | None = None


@dataclass(frozen=True, slots=True)
class RetrievalTraceV1:
    items: tuple[RetrievalTraceItemV1, ...] = field(default_factory=tuple)
