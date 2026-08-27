"""Exact native Semantic Draft V2 references consumed by Chief Editor."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from pastila_scout.editor.generation.semantic_draft_v2 import (
    PastilaEditorSemanticDraftV2,
)
from pastila_scout.editor_application_v1 import load_editor_operational_result_v1
from pastila_scout.voice_repetition_v2 import finalize_order_authority_v1
from pastila_scout.voice_repetition_v2.models import (
    EpisodeOrderAuthorityV1,
    PublicationStateV1,
)
from pastila_scout.voice_workflow_v2 import (
    PublicCommentaryStateV1,
    VoiceWorkflowSidecarStoreV1,
    semantic_draft_revision_identity,
    sha256_identity,
    voice_sidecar_identity,
)

CHIEF_EDITOR_V2_HANDOFF_SCHEMA_VERSION = "1"
_SHA256_PATTERN = r"^sha256:[0-9a-f]{64}$"


class ChiefEditorV2StoryReferenceV1(BaseModel):
    """Immutable reference to one exact persisted native V2 story revision."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    schema_version: Literal["1"] = CHIEF_EDITOR_V2_HANDOFF_SCHEMA_VERSION
    material_reference: str = Field(min_length=1)
    material_output_path: str = Field(min_length=1)
    material_payload_sha256: str = Field(min_length=1)
    semantic_draft_revision_identity: str = Field(pattern=_SHA256_PATTERN)
    event_id: int = Field(gt=0)
    story_position: int = Field(gt=0)
    story_revision_identity: str = Field(pattern=_SHA256_PATTERN)
    factual_summary_identity: str = Field(pattern=_SHA256_PATTERN)
    acid_commentary_identity: str | None = Field(default=None, pattern=_SHA256_PATTERN)
    commentary_state: PublicCommentaryStateV1
    voice_workflow_state_identity: str | None = Field(
        default=None, pattern=_SHA256_PATTERN
    )
    event_authority_identity: str = Field(min_length=1)
    commentary_background_authority_identity: str | None = None
    provenance_references: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ResolvedChiefEditorV2StoryV1:
    reference: ChiefEditorV2StoryReferenceV1
    factual_summary_text: str
    acid_commentary_text: str | None


def render_resolved_chief_editor_v2_story(
    value: ResolvedChiefEditorV2StoryV1,
) -> str:
    """Render exact authored bytes plus a truthful absent-commentary state."""

    sections = ["Rezumat factual", value.factual_summary_text, "Comentariu acid"]
    if value.acid_commentary_text is not None:
        sections.append(value.acid_commentary_text)
    else:
        labels = {
            PublicCommentaryStateV1.UNAVAILABLE: "Indisponibil",
            PublicCommentaryStateV1.UNGENERATED: "Negenerat",
            PublicCommentaryStateV1.FAILED: "Eșuat",
        }
        state = value.reference.commentary_state
        if state is PublicCommentaryStateV1.GENERATED:
            raise ValueError("Generated commentary text is missing")
        sections.append(labels[state])
    return "\n".join(sections)


def _canonical_identity(value: object) -> str:
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def voice_sidecar_path_for_material(material_path: Path) -> Path:
    return material_path.with_suffix(material_path.suffix + ".voice-workflow-v1.json")


def create_chief_editor_v2_story_reference(
    *,
    material_reference: str,
    event_id: int,
    output_path: Path,
    payload_sha256: str,
) -> ChiefEditorV2StoryReferenceV1 | None:
    """Create a V2 reference, or return ``None`` for a historical V1 artifact."""

    result = load_editor_operational_result_v1(
        path=output_path, payload_sha256=payload_sha256
    )
    if type(result.draft) is not PastilaEditorSemanticDraftV2:
        return None
    draft = result.draft
    stories = tuple(story for story in draft.stories if story.event_id == event_id)
    if len(stories) != 1:
        raise ValueError("Chief Editor V2 story is missing or ambiguous")
    story = stories[0]
    sidecar_path = voice_sidecar_path_for_material(output_path)
    sidecar = (
        VoiceWorkflowSidecarStoreV1(sidecar_path).load(draft=draft)
        if sidecar_path.is_file()
        else None
    )
    deterministic = (
        story.acid_commentary is not None
        and story.acid_commentary.execution_provenance is not None
        and story.acid_commentary.execution_provenance.backend_kind
        == "deterministic_renderer"
    )
    if story.acid_commentary is not None and sidecar is None and not deterministic:
        raise ValueError("Generated V2 commentary lacks workflow identity")
    state = (
        PublicCommentaryStateV1.GENERATED
        if deterministic
        else PublicCommentaryStateV1.UNAVAILABLE
        if sidecar is None
        else sidecar.commentary_state
    )
    background_identity = (
        None
        if sidecar is None
        else sidecar.binding.commentary_background_authority_identity
    )
    return ChiefEditorV2StoryReferenceV1(
        material_reference=material_reference,
        material_output_path=str(output_path),
        material_payload_sha256=payload_sha256,
        semantic_draft_revision_identity=semantic_draft_revision_identity(draft),
        event_id=event_id,
        story_position=story.position,
        story_revision_identity=_canonical_identity(story.model_dump(mode="json")),
        factual_summary_identity=sha256_identity(story.factual_summary.text),
        acid_commentary_identity=(
            None
            if story.acid_commentary is None
            else sha256_identity(story.acid_commentary.text)
        ),
        commentary_state=state,
        voice_workflow_state_identity=(
            (
                story.acid_commentary.execution_provenance.acceptance_transaction_identity
                if deterministic
                else None
            )
            if sidecar is None
            else voice_sidecar_identity(sidecar)
        ),
        event_authority_identity=story.factual_summary.authority_bundle_identity,
        commentary_background_authority_identity=background_identity,
        provenance_references=draft.provenance_references,
    )


def create_episode_order_authority_from_chief_editor_v2(
    *,
    episode_id: str,
    episode_ordinal: int,
    references: tuple[ChiefEditorV2StoryReferenceV1, ...],
    publication_state: PublicationStateV1 = PublicationStateV1.UNPUBLISHED,
    publication_authority_identity: str | None = None,
) -> EpisodeOrderAuthorityV1:
    """Freeze Chief Editor's exact selected order as repetition authority."""

    if not references:
        raise ValueError("Chief Editor order cannot be empty")
    event_ids = tuple(item.event_id for item in references)
    if len(event_ids) != len(set(event_ids)):
        raise ValueError("Chief Editor order contains duplicate stories")
    return finalize_order_authority_v1(
        EpisodeOrderAuthorityV1(
            episode_id=episode_id,
            episode_ordinal=episode_ordinal,
            ordered_event_ids=event_ids,
            publication_state=publication_state,
            publication_authority_identity=publication_authority_identity,
        )
    )


def resolve_chief_editor_v2_story_reference(
    reference: ChiefEditorV2StoryReferenceV1,
) -> ResolvedChiefEditorV2StoryV1:
    """Resolve and verify the exact original artifact without rebinding."""

    output_path = Path(reference.material_output_path)
    rebuilt = create_chief_editor_v2_story_reference(
        material_reference=reference.material_reference,
        event_id=reference.event_id,
        output_path=output_path,
        payload_sha256=reference.material_payload_sha256,
    )
    if rebuilt != reference:
        raise ValueError(
            "Chief Editor V2 reference no longer matches persisted material"
        )
    result = load_editor_operational_result_v1(
        path=output_path, payload_sha256=reference.material_payload_sha256
    )
    if type(result.draft) is not PastilaEditorSemanticDraftV2:
        raise ValueError("Chief Editor V2 reference resolved to historical material")
    story = next(
        item for item in result.draft.stories if item.event_id == reference.event_id
    )
    return ResolvedChiefEditorV2StoryV1(
        reference=reference,
        factual_summary_text=story.factual_summary.text,
        acid_commentary_text=(
            None if story.acid_commentary is None else story.acid_commentary.text
        ),
    )


__all__ = (
    "CHIEF_EDITOR_V2_HANDOFF_SCHEMA_VERSION",
    "ChiefEditorV2StoryReferenceV1",
    "ResolvedChiefEditorV2StoryV1",
    "create_chief_editor_v2_story_reference",
    "create_episode_order_authority_from_chief_editor_v2",
    "render_resolved_chief_editor_v2_story",
    "resolve_chief_editor_v2_story_reference",
    "voice_sidecar_path_for_material",
)
