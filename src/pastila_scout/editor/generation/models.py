"""Private contracts for controlled component generation and episode drafts."""

from enum import StrEnum
from itertools import pairwise
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pastila_scout.expression_retrieval_v1.usage import UsageReceiptV1


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class StoryWordBudgetProfileV1(StrEnum):
    """Supported V1 editorial length profiles."""

    STANDARD = "STANDARD"


class StoryWordBudgetV1(FrozenModel):
    """Versioned target and hard ceiling for one generated story."""

    authority_version: Literal["story-word-budget-v1"] = "story-word-budget-v1"
    profile: StoryWordBudgetProfileV1 = Field(
        default=StoryWordBudgetProfileV1.STANDARD, frozen=True
    )
    target_words: Literal[150] = 150
    hard_max_words: Literal[170] = 170


STANDARD_STORY_WORD_BUDGET_V1 = StoryWordBudgetV1()


class GenerationMode(StrEnum):
    STANDARD = "standard"
    CONSTRAINED = "constrained"
    MINIMAL_SAFE = "minimal_safe"


class GenerationComponentType(StrEnum):
    STORY = "story"
    TRANSITION = "transition"
    OPENING = "opening"
    CLOSING = "closing"
    CALL_TO_ACTION = "call_to_action"
    ASSEMBLY = "assembly"
    TELEPROMPTER_FORMATTING = "teleprompter_formatting"


class ManifestItemStatus(StrEnum):
    PENDING = "pending"
    READY = "ready"
    RUNNING = "running"
    RETRYING = "retrying"
    COMPLETED = "completed"
    REQUIRES_REVIEW = "requires_review"
    FAILED = "failed"
    SKIPPED = "skipped"


class RetryReason(StrEnum):
    INVALID_SCHEMA = "invalid_schema"
    PROVIDER_ERROR = "provider_error"
    MISSING_FACT_ANCHOR = "missing_fact_anchor"
    UNKNOWN_FACT_REFERENCE = "unknown_fact_reference"
    MISSING_REQUIRED_INTENT = "missing_required_intent"
    UNKNOWN_INTENT_REFERENCE = "unknown_intent_reference"
    CEILING_EXCEEDED = "ceiling_exceeded"
    PROTECTED_TARGET_VIOLATION = "protected_target_violation"
    INVALID_ENDING = "invalid_ending"
    WORD_BUDGET_EXCEEDED = "word_budget_exceeded"
    RUNTIME_BUDGET_EXCEEDED = "runtime_budget_exceeded"
    REPETITION_BUDGET_EXCEEDED = "repetition_budget_exceeded"
    CALLBACK_VIOLATION = "callback_violation"
    STATE_CONFLICT = "state_conflict"


class LanguageGenerationConfig(FrozenModel):
    provider: str = Field(min_length=1)
    model_identifier: str = Field(min_length=1)
    model_revision: str | None = None
    temperature: float = Field(default=0.3, ge=0, le=2)
    top_p: float = Field(default=1, gt=0, le=1)
    max_output_tokens: int = Field(default=2000, gt=0)
    seed: int | None = None
    structured_output_mode: bool = True
    timeout_seconds: float = Field(default=30, gt=0)


class GenerationPolicy(FrozenModel):
    max_attempts_per_component: int = Field(default=3, ge=1, le=3)
    minimal_safe_enabled: bool = True
    validate_after_every_component: bool = True
    allow_parallel_components: bool = False
    default_generation_mode: GenerationMode = GenerationMode.STANDARD
    retry_strategy: str = Field(default="corrective_then_minimal_safe", min_length=1)
    assembly_mode: str = Field(default="deterministic", pattern="^deterministic$")


class TeleprompterProfile(FrozenModel):
    target_paragraph_length: int = Field(default=240, gt=0)
    maximum_line_length: int = Field(default=80, gt=10)
    preserve_numeric_notation: bool = True
    allow_pause_markers: bool = False
    quote_formatting: str = "preserve"
    abbreviation_policy: str = "preserve"


class ApprovedFact(FrozenModel):
    fact_id: str
    field: str
    value: str


class EpisodeGenerationContext(FrozenModel):
    episode_id: str
    episode_type: str
    language: str = "ro"
    show_identity: str = "Pastila Acida"
    episode_theme: str
    optimized_story_order: tuple[int, ...]
    episode_voice_profile: dict[str, Any]
    teleprompter_profile: TeleprompterProfile
    global_budgets: dict[str, int]
    callback_policy: dict[str, Any]
    repetition_policy: dict[str, Any]
    audience_relationship: str
    language_generation_config: LanguageGenerationConfig


class StoryGenerationContext(FrozenModel):
    story_id: int = Field(gt=0)
    flow_position: int = Field(gt=0)
    approved_facts: tuple[ApprovedFact, ...] = Field(min_length=1)
    editorial_plan: dict[str, Any]
    conversation_plan: dict[str, Any]
    voice_plan: dict[str, Any]
    optional_editorial_toolkit: dict[str, Any] = Field(default_factory=dict)
    word_budget_authority: StoryWordBudgetV1
    provisional_word_budget_plan: dict[str, int] = Field(default_factory=dict)
    runtime_budget: int = Field(gt=0)
    protected_targets: tuple[str, ...]
    allowed_satire_targets: tuple[str, ...]
    forbidden_claims: tuple[str, ...]


class TransitionGenerationContext(FrozenModel):
    from_story_id: int
    to_story_id: int
    previous_story_ending_summary: str
    next_story_factual_summary: str
    transition_plan: dict[str, Any]
    voice_profile: dict[str, Any]
    callback_context: tuple[str, ...]
    word_budget: int = Field(gt=0)


class OpeningGenerationContext(FrozenModel):
    opening_plan: dict[str, Any]
    accepted_story_ids: tuple[int, ...]
    accepted_story_summaries: tuple[str, ...]
    protected_payoffs: tuple[str, ...]
    episode_voice_profile: dict[str, Any]
    word_budget: int = Field(gt=0)
    runtime_budget: int = Field(gt=0)


class ProviderSafeCTAPlacement(FrozenModel):
    """Narrow provider-visible CTA metadata with no static content field."""

    enabled: bool
    placement_kind: str
    after_story_id: int | None = None
    bridge_required: bool


class ClosingGenerationContext(FrozenModel):
    closing_plan: dict[str, Any]
    story_ending_summaries: tuple[str, ...]
    available_callback_anchors: tuple[str, ...]
    episode_theme: str
    emotional_arc: tuple[str, ...]
    cta_placement_plan: ProviderSafeCTAPlacement
    word_budget: int = Field(gt=0)


class CommentaryBlockResult(FrozenModel):
    block_type: str
    text: str = Field(min_length=1)
    sequence: int = Field(gt=0)
    source_fact_ids: tuple[str, ...]
    blueprint_intent_ids: tuple[str, ...]
    voice_plan_ids: tuple[str, ...]
    satire_target_ids: tuple[str, ...]
    protected_target_ids: tuple[str, ...]
    requires_qa: bool = False


class AuthoredCommentaryBlockResult(FrozenModel):
    """Only fields whose values can genuinely vary with generated content."""

    block_type: str
    text: str = Field(min_length=1)
    sequence: int = Field(gt=0)
    source_fact_ids: tuple[str, ...]
    satire_target_ids: tuple[str, ...]
    protected_target_ids: tuple[str, ...]
    requires_qa: bool = False


class GeneratedCallbackAnchor(FrozenModel):
    callback_id: str
    source_story_id: int
    anchor_summary: str
    allowed_target_component_ids: tuple[str, ...]
    maximum_uses: int = Field(default=1, gt=0)
    current_uses: int = Field(default=0, ge=0)


class StoryGenerationResult(FrozenModel):
    story_id: int
    factual_summary: str = Field(min_length=1)
    commentary_blocks: tuple[CommentaryBlockResult, ...] = Field(min_length=1)
    ending: str = Field(min_length=1)
    ending_type: str = Field(min_length=1)
    declared_fact_usage: tuple[str, ...]
    declared_editorial_intent_usage: tuple[str, ...]
    declared_conversation_intent_usage: tuple[str, ...]
    declared_voice_intent_usage: tuple[str, ...]
    generated_callback_anchors: tuple[GeneratedCallbackAnchor, ...] = ()
    used_callbacks: tuple[str, ...] = ()
    used_humor_mechanisms: tuple[str, ...] = ()
    used_expression_families: tuple[str, ...] = ()
    used_reference_families: tuple[str, ...] = ()
    used_vocatives: int = Field(default=0, ge=0)
    profanity_usage: int = Field(default=0, ge=0)
    rhetorical_question_functions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


class StoryAuthoredContentResult(FrozenModel):
    """Provider-authored story content without application-owned identity echoes."""

    factual_summary: str = Field(min_length=1)
    commentary_blocks: tuple[AuthoredCommentaryBlockResult, ...] = Field(min_length=1)
    ending: str = Field(min_length=1)
    ending_type: str = Field(min_length=1)
    declared_fact_usage: tuple[str, ...]
    generated_callback_anchors: tuple[GeneratedCallbackAnchor, ...] = ()
    used_callbacks: tuple[str, ...] = ()
    used_humor_mechanisms: tuple[str, ...] = ()
    used_expression_families: tuple[str, ...] = ()
    used_reference_families: tuple[str, ...] = ()
    used_vocatives: int = Field(default=0, ge=0)
    profanity_usage: int = Field(default=0, ge=0)
    rhetorical_question_functions: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


class TransitionGenerationResult(FrozenModel):
    from_story_id: int
    to_story_id: int
    text: str = Field(min_length=1)
    transition_type: str
    callback_usage: tuple[str, ...] = ()
    declared_plan_references: tuple[str, ...]
    fact_references: tuple[str, ...] = ()
    warnings: tuple[str, ...] = ()


class OpeningGenerationResult(FrozenModel):
    text: str = Field(min_length=1)
    referenced_story_ids: tuple[int, ...]
    teased_reveal_ids: tuple[str, ...] = ()
    opening_mechanism: str
    declared_plan_references: tuple[str, ...]
    warnings: tuple[str, ...] = ()


class ClosingGenerationResult(FrozenModel):
    text: str = Field(min_length=1)
    callback_executions: tuple[str, ...] = ()
    closing_mechanism: str
    declared_plan_references: tuple[str, ...]
    warnings: tuple[str, ...] = ()


class CallToActionGenerationResult(FrozenModel):
    bridge_text: str = Field(min_length=1)
    declared_plan_references: tuple[str, ...]
    warnings: tuple[str, ...] = ()


class DraftStory(FrozenModel):
    story_id: int
    factual_summary: str
    commentary_blocks: tuple[CommentaryBlockResult, ...]
    ending: str

    @property
    def text(self) -> str:
        return "\n\n".join(
            (
                self.factual_summary,
                *(b.text for b in self.commentary_blocks),
                self.ending,
            )
        )


class DraftTransition(FrozenModel):
    from_story_id: int
    to_story_id: int
    text: str


class CTAPlacement(StrEnum):
    AFTER_OPENING = "after_opening"
    AFTER_STORY = "after_story"
    BEFORE_FINAL_STORY = "before_final_story"
    BEFORE_CLOSING = "before_closing"
    AFTER_CLOSING = "after_closing"
    OMITTED = "omitted"


class CallToActionPlacementPlan(FrozenModel):
    placement: CTAPlacement
    after_story_id: int | None = None
    cta_type: str = "support"
    static_content: str = ""

    def to_provider_context(self) -> ProviderSafeCTAPlacement:
        """Return placement metadata that structurally excludes local static text."""

        return ProviderSafeCTAPlacement(
            enabled=self.placement is not CTAPlacement.OMITTED,
            placement_kind=self.placement.value,
            after_story_id=self.after_story_id,
            bridge_required=self.placement is not CTAPlacement.OMITTED,
        )


class CallToActionDraft(FrozenModel):
    placement: CTAPlacement
    after_story_id: int | None
    bridge_text: str
    static_content: str

    @property
    def text(self) -> str:
        return " ".join(
            item for item in (self.bridge_text, self.static_content) if item
        )


def derive_assembled_text(
    *,
    opening: str,
    stories: tuple[DraftStory, ...],
    transitions: tuple[DraftTransition, ...],
    closing: str,
    cta: CallToActionDraft | None,
) -> str:
    """Derive the sole semantic episode text from accepted draft components."""

    story_ids = tuple(story.story_id for story in stories)
    if len(story_ids) != len(set(story_ids)):
        raise ValueError("draft stories must be unique")
    transition_map = {
        (item.from_story_id, item.to_story_id): item for item in transitions
    }
    expected = set(pairwise(story_ids))
    if set(transition_map) != expected:
        raise ValueError("draft transitions do not match story adjacencies")
    if (
        cta
        and cta.placement is CTAPlacement.AFTER_STORY
        and cta.after_story_id not in story_ids[:-1]
    ):
        raise ValueError("after-story CTA must target a non-final draft story")
    parts = [opening]
    if cta and cta.placement is CTAPlacement.AFTER_OPENING:
        parts.append(cta.text)
    for index, story in enumerate(stories):
        if (
            cta
            and cta.placement is CTAPlacement.BEFORE_FINAL_STORY
            and index == len(stories) - 1
        ):
            parts.append(cta.text)
        parts.append(story.text)
        if (
            cta
            and cta.placement is CTAPlacement.AFTER_STORY
            and cta.after_story_id == story.story_id
        ):
            parts.append(cta.text)
        if index + 1 < len(stories):
            parts.append(
                transition_map[(story.story_id, stories[index + 1].story_id)].text
            )
    if cta and cta.placement is CTAPlacement.BEFORE_CLOSING:
        parts.append(cta.text)
    parts.append(closing)
    if cta and cta.placement is CTAPlacement.AFTER_CLOSING:
        parts.append(cta.text)
    return "\n\n".join(parts)


class EpisodeDraft(FrozenModel):
    episode_id: str
    opening: str
    stories: tuple[DraftStory, ...]
    transitions: tuple[DraftTransition, ...]
    closing: str
    cta: CallToActionDraft | None
    assembled_text: str
    teleprompter_text: str
    usage_receipts: tuple[UsageReceiptV1, ...] = ()

    @model_validator(mode="after")
    def validate_derived_text(self) -> EpisodeDraft:
        expected = derive_assembled_text(
            opening=self.opening,
            stories=self.stories,
            transitions=self.transitions,
            closing=self.closing,
            cta=self.cta,
        )
        if self.assembled_text != expected:
            raise ValueError("assembled_text must equal the derived component text")
        return self

    def model_copy(self, *, update=None, deep=False):
        """Copy with validation so derived text cannot silently diverge."""

        del deep
        data = self.model_dump(mode="python")
        if update:
            data.update(update)
        return type(self).model_validate(data)


class ComponentAttemptTrace(FrozenModel):
    manifest_item_id: str
    component_type: GenerationComponentType
    target_id: str
    attempt_number: int
    generation_mode: GenerationMode
    prompt_fingerprint: str
    provider_identifier: str
    model_identifier: str
    validation_errors: tuple[str, ...]
    validation_warnings: tuple[str, ...]
    retry_reason: RetryReason | None
    acceptance_status: ManifestItemStatus
    state_revision_before: int
    state_revision_after: int


class GenerationTrace(FrozenModel):
    attempts: tuple[ComponentAttemptTrace, ...]


class ControlledGenerationResult(FrozenModel):
    draft: EpisodeDraft
    trace: GenerationTrace
    manifest: Any
    final_state: Any
