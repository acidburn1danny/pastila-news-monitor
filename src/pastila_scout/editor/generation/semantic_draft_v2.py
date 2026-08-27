"""Pastila Editor semantic draft V2 contracts and deterministic assembly.

V2 separates factual news content, future voice commentary, and cross-story
transitions.  It deliberately coexists with the historical ``EpisodeDraft``
contract; loading V1 data never rewrites it into V2.
"""

from __future__ import annotations

import re
from enum import StrEnum
from itertools import pairwise
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pastila_scout.editor.generation.manifest import GenerationManifest
from pastila_scout.editor.generation.models import (
    ApprovedFact,
    EpisodeDraft,
    GenerationTrace,
)

SEMANTIC_DRAFT_V2_SCHEMA_NAME = "pastila-editor-semantic-draft"
SEMANTIC_DRAFT_V2_SCHEMA_VERSION = "2"

_SENTENCE = re.compile(r"[^.!?\n]+(?:[.!?]+|$)", re.UNICODE)


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class SemanticDraftModeV2(StrEnum):
    CORE_ONLY = "core_only"
    CORE_PLUS_VOICE = "core_plus_voice"


class AuthorityDensityV2(StrEnum):
    THIN = "thin"
    STANDARD = "standard"
    COMPLEMENTARY = "complementary"


class FactualSummaryLengthContractV2(_FrozenModel):
    normal_sentences: Literal[1] = 1
    maximum_sentences: Literal[2] = 2
    second_sentence_rule: Literal[
        "additional_supported_relevant_nonredundant_factual_value_only"
    ] = "additional_supported_relevant_nonredundant_factual_value_only"
    thin_authority: Literal["one_sentence"] = "one_sentence"
    multiple_sources_alone: Literal["does_not_justify_second_sentence"] = (
        "does_not_justify_second_sentence"
    )
    length_rule: Literal["LENGTH_FOLLOWS_FACTUAL_DENSITY_NOT_A_FIXED_QUOTA"] = (
        "LENGTH_FOLLOWS_FACTUAL_DENSITY_NOT_A_FIXED_QUOTA"
    )


class CoreFactualSummaryGenerationContextV2(_FrozenModel):
    """Model-visible local context for exactly one factual Core generation."""

    story_id: int = Field(gt=0)
    flow_position: int = Field(gt=0)
    approved_facts: tuple[ApprovedFact, ...] = Field(min_length=1)
    forbidden_claims: tuple[str, ...] = ()
    factual_summary_contract: FactualSummaryLengthContractV2 = (
        FactualSummaryLengthContractV2()
    )


class CoreFactualSummaryGenerationResultV2(_FrozenModel):
    """Transport result preserving the complete Core prose as one component."""

    text: str = Field(min_length=1)


class AcidCommentaryGenerationContextV2(_FrozenModel):
    """Model-visible authority for a nonfactual commentary-only call."""

    story_id: int = Field(gt=0)
    flow_position: int = Field(gt=0)
    immutable_factual_summary: str = Field(min_length=1)
    commentary_plan: dict[str, Any]
    authority_rule: Literal[
        "NONFACTUAL_COMMENTARY_ONLY_NO_FACTUAL_CLAIMS_OR_PARAPHRASES"
    ] = "NONFACTUAL_COMMENTARY_ONLY_NO_FACTUAL_CLAIMS_OR_PARAPHRASES"


class AcidCommentaryGenerationResultV2(_FrozenModel):
    """Transport result for commentary; it can never carry factual prose."""

    text: str = Field(min_length=1)


class FactualNucleusBindingV2(_FrozenModel):
    """Sidecar binding of one target nucleus to same-event authority facts."""

    nucleus_id: str = Field(min_length=1)
    sentence_number: Literal[1, 2]
    authority_fact_ids: tuple[str, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_identity(self):
        if len(set(self.authority_fact_ids)) != len(self.authority_fact_ids):
            raise ValueError("duplicate authority fact binding")
        return self


class FactualSummaryV2(_FrozenModel):
    """Factual prose with an explicit Core or deterministic-source owner."""

    text: str = Field(min_length=1)
    authority_bundle_identity: str = Field(min_length=1)
    authority_density: AuthorityDensityV2
    nucleus_bindings: tuple[FactualNucleusBindingV2, ...] = Field(min_length=1)
    authoring_owner: Literal[
        "core_v1_2",
        "zero_model_source_projection_v1",
        "governed_scout_projection_v1",
    ] = "core_v1_2"
    model_identifier: str = Field(min_length=1)
    provider: str = Field(min_length=1)
    validation_receipt: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_density_bound_length(self):
        if self.authoring_owner == "zero_model_source_projection_v1" and (
            self.model_identifier
            != "pastilaacida-voice:zero-model-native-v2-bootstrap:v1"
            or self.provider != "none"
        ):
            raise ValueError("zero-model source projection has false execution identity")
        if self.authoring_owner == "governed_scout_projection_v1" and (
            self.model_identifier != "governed-scout-factual-summary-v1"
            or self.provider != "none"
        ):
            raise ValueError("governed factual projection has false execution identity")
        if self.authoring_owner == "core_v1_2" and self.provider == "none":
            raise ValueError("Core-authored factual prose requires a provider identity")
        if not self.text.strip() or (
            self.authoring_owner != "governed_scout_projection_v1"
            and self.text.rstrip()[-1] not in ".!?"
        ):
            raise ValueError("factual summary must end naturally")
        sentence_count = _sentence_count(self.text)
        if (
            self.authoring_owner != "governed_scout_projection_v1"
            and sentence_count not in (1, 2)
        ):
            raise ValueError("factual summary must contain one or two sentences")
        if self.authority_density is AuthorityDensityV2.THIN and sentence_count != 1:
            raise ValueError("thin authority must remain one sentence")

        nucleus_ids = tuple(item.nucleus_id for item in self.nucleus_bindings)
        if len(set(nucleus_ids)) != len(nucleus_ids):
            raise ValueError("duplicate factual nucleus identity")
        if any(item.sentence_number > sentence_count for item in self.nucleus_bindings):
            raise ValueError("factual nucleus references an absent sentence")

        first_facts = {
            fact_id
            for item in self.nucleus_bindings
            if item.sentence_number == 1
            for fact_id in item.authority_fact_ids
        }
        second_facts = {
            fact_id
            for item in self.nucleus_bindings
            if item.sentence_number == 2
            for fact_id in item.authority_fact_ids
        }
        if sentence_count == 2 and not second_facts.difference(first_facts):
            raise ValueError(
                "second sentence requires additional supported nonredundant factual value"
            )
        return self


class AcidCommentaryExecutionProvenanceV2(_FrozenModel):
    backend_kind: Literal["deterministic_renderer", "model"]
    backend_identity: str = Field(min_length=1)
    canonical_ir_identity: str | None = None
    character_provenance_identity: str = Field(min_length=1)
    acceptance_transaction_identity: str = Field(min_length=1)
    model_calls: int = Field(ge=0)
    provider_calls: int = Field(ge=0)
    model_loads: int = Field(ge=0)

    @model_validator(mode="after")
    def truthful_backend(self):
        if self.backend_kind == "deterministic_renderer" and (
            self.model_calls or self.provider_calls or self.model_loads
        ):
            raise ValueError("deterministic commentary cannot report model activity")
        return self


class AcidCommentaryV2(_FrozenModel):
    text: str = Field(min_length=1)
    authoring_owner: Literal["pastila_voice"] = "pastila_voice"
    voice_model_identity: str | None = Field(default=None, min_length=1)
    factual_boundary_receipt: str = Field(min_length=1)
    execution_provenance: AcidCommentaryExecutionProvenanceV2 | None = None

    @model_validator(mode="after")
    def truthful_execution_owner(self):
        if (self.voice_model_identity is None) == (self.execution_provenance is None):
            raise ValueError("commentary requires exactly one execution identity class")
        return self


class SemanticStoryV2(_FrozenModel):
    event_id: int = Field(gt=0)
    position: int = Field(gt=0)
    factual_summary: FactualSummaryV2
    acid_commentary: AcidCommentaryV2 | None = None
    acid_commentary_status: Literal[
        "present", "absent_voice_layer_unavailable", "absent_owner_removed"
    ]

    @model_validator(mode="after")
    def validate_commentary_status(self):
        if (
            self.acid_commentary is not None
            and self.acid_commentary_status != "present"
        ):
            raise ValueError("acid commentary status does not match content")
        if self.acid_commentary is None and self.acid_commentary_status == "present":
            raise ValueError("acid commentary status does not match content")
        return self

    @property
    def text(self) -> str:
        parts = [self.factual_summary.text]
        if self.acid_commentary is not None:
            parts.append(self.acid_commentary.text)
        return "\n\n".join(parts)


class CrossStoryTransitionV2(_FrozenModel):
    transition_id: str = Field(min_length=1)
    from_event_id: int = Field(gt=0)
    to_event_id: int = Field(gt=0)
    text: str = Field(min_length=1)
    generation_owner: Literal["editorial_transition_component"] = (
        "editorial_transition_component"
    )
    source_story_fingerprints: tuple[str, str]
    factual_reference_ids: tuple[str, ...] = ()
    validation_receipt: str = Field(min_length=1)

    @model_validator(mode="after")
    def validate_transition(self):
        if self.from_event_id == self.to_event_id:
            raise ValueError("transition endpoints must differ")
        if any(not value for value in self.source_story_fingerprints):
            raise ValueError("transition source fingerprints must be nonempty")
        if len(set(self.factual_reference_ids)) != len(self.factual_reference_ids):
            raise ValueError("duplicate transition factual reference")
        return self


class EpisodeIntroV2(_FrozenModel):
    text: str = Field(min_length=1)
    provenance_reference: str = Field(min_length=1)


class FinalMonologueV2(_FrozenModel):
    text: str = Field(min_length=1)
    provenance_reference: str = Field(min_length=1)


def derive_semantic_assembled_text_v2(
    *,
    intro: EpisodeIntroV2 | None,
    stories: tuple[SemanticStoryV2, ...],
    transitions: tuple[CrossStoryTransitionV2, ...],
    final_monologue: FinalMonologueV2 | None,
) -> str:
    """Assemble only accepted components, without inventing compatibility prose."""

    if not stories:
        raise ValueError("semantic draft requires at least one story")
    story_ids = tuple(item.event_id for item in stories)
    if len(story_ids) != len(set(story_ids)):
        raise ValueError("semantic draft stories must be unique")
    if tuple(item.position for item in stories) != tuple(range(1, len(stories) + 1)):
        raise ValueError("semantic draft story positions must be contiguous")

    transition_map = {
        (item.from_event_id, item.to_event_id): item for item in transitions
    }
    if len(transition_map) != len(transitions):
        raise ValueError("duplicate semantic transition slot")
    expected_slots = set(pairwise(story_ids))
    if not set(transition_map).issubset(expected_slots):
        raise ValueError("semantic transitions must connect adjacent stories")

    parts: list[str] = []
    if intro is not None:
        parts.append(intro.text)
    for index, story in enumerate(stories):
        parts.append(story.text)
        if index + 1 < len(stories):
            transition = transition_map.get(
                (story.event_id, stories[index + 1].event_id)
            )
            if transition is not None:
                parts.append(transition.text)
    if final_monologue is not None:
        parts.append(final_monologue.text)
    return "\n\n".join(parts)


class PastilaEditorSemanticDraftV2(_FrozenModel):
    schema_name: Literal["pastila-editor-semantic-draft"] = (
        SEMANTIC_DRAFT_V2_SCHEMA_NAME
    )
    schema_version: Literal["2"] = SEMANTIC_DRAFT_V2_SCHEMA_VERSION
    episode_id: str = Field(min_length=1)
    mode: SemanticDraftModeV2
    intro: EpisodeIntroV2 | None = None
    stories: tuple[SemanticStoryV2, ...] = Field(min_length=1)
    transitions: tuple[CrossStoryTransitionV2, ...] = ()
    final_monologue: FinalMonologueV2 | None = None
    assembled_text: str = Field(min_length=1)
    teleprompter_text: str = Field(min_length=1)
    provenance_references: tuple[str, ...] = ()
    generation_receipts: tuple[str, ...] = ()

    @model_validator(mode="after")
    def validate_semantics(self):
        if self.mode is SemanticDraftModeV2.CORE_ONLY and any(
            item.acid_commentary is not None for item in self.stories
        ):
            raise ValueError("Core-only mode cannot contain acid commentary")
        expected = derive_semantic_assembled_text_v2(
            intro=self.intro,
            stories=self.stories,
            transitions=self.transitions,
            final_monologue=self.final_monologue,
        )
        if self.assembled_text != expected:
            raise ValueError("assembled_text must equal deterministic V2 assembly")
        return self

    @classmethod
    def assemble(
        cls,
        *,
        episode_id: str,
        mode: SemanticDraftModeV2,
        stories: tuple[SemanticStoryV2, ...],
        transitions: tuple[CrossStoryTransitionV2, ...] = (),
        intro: EpisodeIntroV2 | None = None,
        final_monologue: FinalMonologueV2 | None = None,
        provenance_references: tuple[str, ...] = (),
        generation_receipts: tuple[str, ...] = (),
    ) -> PastilaEditorSemanticDraftV2:
        assembled = derive_semantic_assembled_text_v2(
            intro=intro,
            stories=stories,
            transitions=transitions,
            final_monologue=final_monologue,
        )
        return cls(
            episode_id=episode_id,
            mode=mode,
            intro=intro,
            stories=stories,
            transitions=transitions,
            final_monologue=final_monologue,
            assembled_text=assembled,
            teleprompter_text=assembled,
            provenance_references=provenance_references,
            generation_receipts=generation_receipts,
        )


class SemanticGenerationStateV2(_FrozenModel):
    revision: int = Field(ge=0)
    accepted_event_ids: tuple[int, ...]


class ControlledSemanticGenerationResultV2(_FrozenModel):
    draft: PastilaEditorSemanticDraftV2
    trace: GenerationTrace
    manifest: GenerationManifest
    final_state: SemanticGenerationStateV2


class LegacyStoryProjectionV1(_FrozenModel):
    story_id: int = Field(gt=0)
    factual_summary: str = Field(min_length=1)
    commentary_blocks: tuple[str, ...] = ()
    ending: str | None = None


class LegacyTransitionProjectionV1(_FrozenModel):
    from_story_id: int = Field(gt=0)
    to_story_id: int = Field(gt=0)
    text: str = Field(min_length=1)


class LegacyEpisodeDraftProjectionV1(_FrozenModel):
    """Outbound-only V1-shaped projection that never fabricates missing prose."""

    episode_id: str = Field(min_length=1)
    opening: str | None = None
    stories: tuple[LegacyStoryProjectionV1, ...] = Field(min_length=1)
    transitions: tuple[LegacyTransitionProjectionV1, ...] = ()
    closing: str | None = None
    assembled_text: str = Field(min_length=1)
    teleprompter_text: str = Field(min_length=1)
    omitted_legacy_fields: tuple[str, ...] = ()


def project_semantic_draft_v2_to_legacy_v1(
    draft: PastilaEditorSemanticDraftV2,
) -> LegacyEpisodeDraftProjectionV1:
    """Project real V2 content only; absence stays absence."""

    omitted = []
    if draft.intro is None:
        omitted.append("opening")
    if draft.final_monologue is None:
        omitted.append("closing")
    if any(item.acid_commentary is None for item in draft.stories):
        omitted.append("commentary_blocks")
    omitted.append("ending")
    return LegacyEpisodeDraftProjectionV1(
        episode_id=draft.episode_id,
        opening=draft.intro.text if draft.intro is not None else None,
        stories=tuple(
            LegacyStoryProjectionV1(
                story_id=item.event_id,
                factual_summary=item.factual_summary.text,
                commentary_blocks=(
                    (item.acid_commentary.text,)
                    if item.acid_commentary is not None
                    else ()
                ),
                ending=None,
            )
            for item in draft.stories
        ),
        transitions=tuple(
            LegacyTransitionProjectionV1(
                from_story_id=item.from_event_id,
                to_story_id=item.to_event_id,
                text=item.text,
            )
            for item in draft.transitions
        ),
        closing=(
            draft.final_monologue.text if draft.final_monologue is not None else None
        ),
        assembled_text=draft.assembled_text,
        teleprompter_text=draft.teleprompter_text,
        omitted_legacy_fields=tuple(dict.fromkeys(omitted)),
    )


def load_semantic_draft_compatible(
    value: dict[str, Any],
) -> EpisodeDraft | PastilaEditorSemanticDraftV2:
    """Read V2 explicitly and preserve all historical V1 semantics unchanged."""

    if value.get("schema_name") == SEMANTIC_DRAFT_V2_SCHEMA_NAME:
        return PastilaEditorSemanticDraftV2.model_validate(value)
    return EpisodeDraft.model_validate(value)


def _sentence_count(value: str) -> int:
    return sum(bool(item.strip()) for item in _SENTENCE.findall(value))


__all__ = [
    "SEMANTIC_DRAFT_V2_SCHEMA_NAME",
    "SEMANTIC_DRAFT_V2_SCHEMA_VERSION",
    "AcidCommentaryExecutionProvenanceV2",
    "AcidCommentaryGenerationContextV2",
    "AcidCommentaryGenerationResultV2",
    "AcidCommentaryV2",
    "AuthorityDensityV2",
    "ControlledSemanticGenerationResultV2",
    "CoreFactualSummaryGenerationContextV2",
    "CoreFactualSummaryGenerationResultV2",
    "CrossStoryTransitionV2",
    "EpisodeIntroV2",
    "FactualNucleusBindingV2",
    "FactualSummaryLengthContractV2",
    "FactualSummaryV2",
    "FinalMonologueV2",
    "LegacyEpisodeDraftProjectionV1",
    "LegacyStoryProjectionV1",
    "LegacyTransitionProjectionV1",
    "PastilaEditorSemanticDraftV2",
    "SemanticDraftModeV2",
    "SemanticGenerationStateV2",
    "SemanticStoryV2",
    "derive_semantic_assembled_text_v2",
    "load_semantic_draft_compatible",
    "project_semantic_draft_v2_to_legacy_v1",
]
