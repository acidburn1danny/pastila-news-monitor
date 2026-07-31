"""Validated output envelope for a future independently executable Editor Agent."""

import re
from datetime import datetime

from pydantic import Field, field_validator, model_validator

from pastila_scout.contracts.common import (
    EDITOR_OUTPUT_VERSION,
    EDITORIAL_CONTRACT_VERSION,
    ContractIssue,
    ContractStatus,
    DurationValue,
    ExtensibleContractModel,
    InheritedScoutScores,
    NonEmptyText,
    ShortText,
    SourceReference,
)
from pastila_scout.contracts.episode_context import EpisodeContextV1
from pastila_scout.contracts.scout_editor import HashText, ReportId, ScoutEditorInputV1
from pastila_scout.contracts.selection_profile import SelectionProfileV1


class SelectedStory(ExtensibleContractModel):
    position: int = Field(gt=0)
    event_id: int = Field(gt=0)
    canonical_title: NonEmptyText
    episode_role: NonEmptyText
    selection_reason: NonEmptyText
    transition_reason: NonEmptyText | None = None
    tone_recommendation: NonEmptyText
    factual_editorial_risks: tuple[NonEmptyText, ...] = Field(default=(), max_length=20)
    suggested_treatment_length: DurationValue
    editorial_confidence: int = Field(ge=0, le=100)
    source_references: tuple[SourceReference, ...] = Field(min_length=1, max_length=3)
    inherited_scout_scores: InheritedScoutScores


class BackupStory(ExtensibleContractModel):
    position: int = Field(gt=0)
    event_id: int = Field(gt=0)
    canonical_title: NonEmptyText
    selection_reason: NonEmptyText
    tone_recommendation: NonEmptyText
    factual_editorial_risks: tuple[NonEmptyText, ...] = Field(default=(), max_length=20)
    suggested_treatment_length: DurationValue
    editorial_confidence: int = Field(ge=0, le=100)
    replacement_for: int | None = Field(default=None, gt=0)
    source_references: tuple[SourceReference, ...] = Field(min_length=1, max_length=3)
    inherited_scout_scores: InheritedScoutScores


class EpisodeFlowStep(ExtensibleContractModel):
    position: int = Field(gt=0)
    event_id: int = Field(gt=0)
    role: NonEmptyText
    placement_reason: NonEmptyText
    expected_transition_type: str | None = None

    @field_validator("role")
    @classmethod
    def validate_role(cls, value: str) -> str:
        standard = {
            "opening",
            "development",
            "escalation",
            "contrast",
            "comic_relief",
            "callback",
            "closing",
        }
        if value not in standard and not re.fullmatch(
            r"custom:[a-z0-9]+(?:-[a-z0-9]+)*", value
        ):
            raise ValueError("unsupported episode flow role")
        return value

    @field_validator("expected_transition_type")
    @classmethod
    def validate_transition(cls, value: str | None) -> str | None:
        if value is None:
            return None
        standard = {
            "continuation",
            "escalation",
            "contrast",
            "hard_cut",
            "tone_shift",
            "comic_relief",
            "callback",
        }
        if value not in standard and not re.fullmatch(
            r"custom:[a-z0-9]+(?:-[a-z0-9]+)*", value
        ):
            raise ValueError("unsupported expected transition type")
        return value


class NotableExclusion(ExtensibleContractModel):
    event_id: int = Field(gt=0)
    reason_code: NonEmptyText
    reason: NonEmptyText


class UnusedStrongCandidate(ExtensibleContractModel):
    event_id: int = Field(gt=0)
    canonical_title: NonEmptyText
    scout_recommendation: str = Field(
        pattern="^(STRONG_PICK|POSSIBLE_PICK|BACKUP|SKIP)$"
    )
    final_score: float = Field(ge=0, le=100)
    exclusion_reason_code: NonEmptyText
    exclusion_reason: NonEmptyText


class RejectionSummary(ExtensibleContractModel):
    total_candidates: int = Field(ge=0)
    selected: int = Field(ge=0)
    backups: int = Field(ge=0)
    excluded_by_constraints: int = Field(ge=0)
    semantically_redundant: int = Field(ge=0)
    otherwise_not_selected: int = Field(ge=0)
    notable_exclusions: tuple[NotableExclusion, ...] = Field(default=(), max_length=5)
    unused_strong_candidates: tuple[UnusedStrongCandidate, ...] = Field(
        default=(), max_length=5
    )

    @model_validator(mode="after")
    def validate_arithmetic(self) -> RejectionSummary:
        accounted = (
            self.selected
            + self.backups
            + self.excluded_by_constraints
            + self.semantically_redundant
            + self.otherwise_not_selected
        )
        if accounted != self.total_candidates:
            raise ValueError("rejection summary counts must equal total_candidates")
        return self


class EpisodeProposalV1(ExtensibleContractModel):
    episode_title_suggestion: NonEmptyText
    editorial_angle: NonEmptyText
    estimated_total_runtime: DurationValue
    selected_stories: tuple[SelectedStory, ...]
    backup_stories: tuple[BackupStory, ...] = ()
    episode_flow: tuple[EpisodeFlowStep, ...]
    rejection_summary: RejectionSummary
    warnings: tuple[ContractIssue, ...] = ()
    editorial_notes: tuple[ShortText, ...] = Field(default=(), max_length=20)
    overall_selection_reasoning: NonEmptyText

    @model_validator(mode="after")
    def validate_proposal(self) -> EpisodeProposalV1:
        selected_ids = [story.event_id for story in self.selected_stories]
        backup_ids = [story.event_id for story in self.backup_stories]
        if len(selected_ids) != len(set(selected_ids)) or len(backup_ids) != len(
            set(backup_ids)
        ):
            raise ValueError("story event IDs must be unique within each collection")
        if set(selected_ids).intersection(backup_ids):
            raise ValueError("selected and backup event IDs must be disjoint")
        expected_positions = list(range(1, len(selected_ids) + 1))
        if [story.position for story in self.selected_stories] != expected_positions:
            raise ValueError("selected story positions must be contiguous")
        if [step.position for step in self.episode_flow] != expected_positions:
            raise ValueError("episode flow positions must be contiguous")
        if [step.event_id for step in self.episode_flow] != selected_ids:
            raise ValueError("episode flow must map selected stories in order")
        if any(
            backup.replacement_for is not None
            and backup.replacement_for not in selected_ids
            for backup in self.backup_stories
        ):
            raise ValueError("replacement_for must reference a selected story")
        runtime = sum(
            story.suggested_treatment_length.value for story in self.selected_stories
        )
        if runtime != self.estimated_total_runtime.value:
            raise ValueError("estimated runtime must equal selected treatment lengths")
        if self.rejection_summary.selected != len(self.selected_stories):
            raise ValueError("rejection selected count does not match selected stories")
        if self.rejection_summary.backups != len(self.backup_stories):
            raise ValueError("rejection backup count does not match backup stories")
        used = set(selected_ids).union(backup_ids)
        if any(
            candidate.event_id in used
            for candidate in self.rejection_summary.unused_strong_candidates
        ):
            raise ValueError("unused strong candidates cannot be selected or backups")
        return self


class SelectionProfileReference(ExtensibleContractModel):
    name: NonEmptyText
    version: NonEmptyText


class EditorAgentOutputV1(ExtensibleContractModel):
    contract_version: str = Field(
        default=EDITOR_OUTPUT_VERSION, pattern="^editor-agent-output-v1$"
    )
    editorial_contract_version: str = Field(
        default=EDITORIAL_CONTRACT_VERSION,
        pattern="^scout-editorial-semantics-v1$",
    )
    generated_at: datetime
    editor_agent_version: NonEmptyText
    source_report_id: ReportId
    source_contract_version: str = Field(pattern="^scout-editor-input-v1$")
    source_content_fingerprint: HashText
    selection_profile: SelectionProfileReference
    requested_episode_size: int = Field(gt=0)
    status: ContractStatus
    episode_proposal: EpisodeProposalV1 | None
    errors: tuple[ContractIssue, ...] = ()

    @model_validator(mode="after")
    def validate_status_payload(self) -> EditorAgentOutputV1:
        if self.status == ContractStatus.SUCCESS and self.episode_proposal is None:
            raise ValueError("success status requires an episode proposal")
        if self.status == ContractStatus.SUCCESS and self.errors:
            raise ValueError("success status cannot contain errors")
        return self


def validate_editor_output_against_input(
    output: EditorAgentOutputV1,
    source: ScoutEditorInputV1,
    *,
    selection_profile: SelectionProfileV1 | None = None,
    episode_context: EpisodeContextV1 | None = None,
) -> None:
    """Validate inherited facts that require both contract documents."""

    if output.source_report_id != source.report_id:
        raise ValueError("source report ID does not match Scout input")
    if output.source_content_fingerprint != source.content_fingerprint:
        raise ValueError("source content fingerprint does not match Scout input")
    if selection_profile is not None:
        if (
            output.selection_profile.name != selection_profile.profile_name
            or output.selection_profile.version != selection_profile.profile_version
        ):
            raise ValueError("selection profile reference does not match")
        if output.requested_episode_size != selection_profile.target_story_count:
            raise ValueError("requested episode size does not match selection profile")
    if episode_context is not None and (
        output.requested_episode_size != episode_context.target_story_count
    ):
        raise ValueError("requested episode size does not match episode context")
    if output.episode_proposal is None:
        return
    source_events = {event.event_id: event for event in source.ranked_events}
    proposal = output.episode_proposal
    referenced = (*proposal.selected_stories, *proposal.backup_stories)
    for story in referenced:
        event = source_events.get(story.event_id)
        if event is None:
            raise ValueError(f"event {story.event_id} is absent from Scout input")
        if story.canonical_title != event.canonical_title:
            raise ValueError(f"canonical title changed for event {story.event_id}")
        expected = (
            event.deterministic_score.score,
            event.ai_editorial_score.score if event.ai_editorial_score else None,
            event.final_score,
            event.recommendation,
        )
        actual = (
            story.inherited_scout_scores.deterministic_score,
            story.inherited_scout_scores.ai_editorial_score,
            story.inherited_scout_scores.final_score,
            story.inherited_scout_scores.recommendation,
        )
        if actual != expected:
            raise ValueError(
                f"inherited Scout scores changed for event {story.event_id}"
            )
        expected_sources = {
            (
                item.source_id,
                item.source_name,
                item.url,
                item.title,
                item.published_at,
            )
            for item in event.source_provenance
        }
        actual_sources = {
            (
                item.source_id,
                item.source_name,
                item.url,
                item.title,
                item.published_at,
            )
            for item in story.source_references
        }
        if not actual_sources.issubset(expected_sources):
            raise ValueError(f"source provenance changed for event {story.event_id}")
    for candidate in proposal.rejection_summary.unused_strong_candidates:
        event = source_events.get(candidate.event_id)
        if event is None or (
            candidate.canonical_title,
            candidate.final_score,
            candidate.scout_recommendation,
        ) != (event.canonical_title, event.final_score, event.recommendation):
            raise ValueError(
                f"unused candidate data changed for event {candidate.event_id}"
            )
    used_ids = {story.event_id for story in referenced}
    selected_ids = {story.event_id for story in proposal.selected_stories}
    if output.status == ContractStatus.SUCCESS and (
        len(selected_ids) != output.requested_episode_size
    ):
        raise ValueError("successful output must contain the requested episode size")
    if episode_context is not None:
        excluded = set(episode_context.excluded_event_ids)
        if used_ids.intersection(excluded):
            raise ValueError("excluded events cannot be selected or backups")
        mandatory = set(episode_context.mandatory_event_ids)
        if output.status == ContractStatus.SUCCESS and not mandatory.issubset(
            selected_ids
        ):
            raise ValueError("successful output must include mandatory events")
    for exclusion in proposal.rejection_summary.notable_exclusions:
        if exclusion.event_id not in source_events:
            raise ValueError(
                f"excluded event {exclusion.event_id} is absent from Scout input"
            )
        if exclusion.event_id in used_ids:
            raise ValueError(
                f"excluded event {exclusion.event_id} is selected or backup"
            )
