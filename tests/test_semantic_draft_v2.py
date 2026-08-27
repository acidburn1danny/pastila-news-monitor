from __future__ import annotations

import pytest
from pydantic import ValidationError

from pastila_scout.editor.generation.models import DraftStory, EpisodeDraft
from pastila_scout.editor.generation.semantic_draft_v2 import (
    AcidCommentaryV2,
    AuthorityDensityV2,
    CrossStoryTransitionV2,
    EpisodeIntroV2,
    FactualNucleusBindingV2,
    FactualSummaryV2,
    PastilaEditorSemanticDraftV2,
    SemanticDraftModeV2,
    SemanticStoryV2,
    load_semantic_draft_compatible,
    project_semantic_draft_v2_to_legacy_v1,
)


def _summary(
    text: str = "Faptul principal este confirmat.",
    *,
    density: AuthorityDensityV2 = AuthorityDensityV2.STANDARD,
    bindings: tuple[FactualNucleusBindingV2, ...] | None = None,
) -> FactualSummaryV2:
    return FactualSummaryV2(
        text=text,
        authority_bundle_identity="sha256:authority",
        authority_density=density,
        nucleus_bindings=bindings
        or (
            FactualNucleusBindingV2(
                nucleus_id="nucleus-1",
                sentence_number=1,
                authority_fact_ids=("fact-1",),
            ),
        ),
        model_identifier="pastila-editor-core-v1.2-experimental",
        provider="ollama",
        validation_receipt="sha256:validation",
    )


def _story(event_id: int, position: int, *, text: str | None = None):
    return SemanticStoryV2(
        event_id=event_id,
        position=position,
        factual_summary=_summary(text or f"Fapt confirmat pentru {event_id}."),
        acid_commentary=None,
        acid_commentary_status="absent_voice_layer_unavailable",
    )


def test_density_rule_prefers_one_and_allows_supported_nonredundant_second_sentence():
    one = _summary()
    assert one.text == "Faptul principal este confirmat."

    two = _summary(
        "Faptul principal este confirmat. A doua sursă adaugă un detaliu relevant.",
        density=AuthorityDensityV2.COMPLEMENTARY,
        bindings=(
            FactualNucleusBindingV2(
                nucleus_id="nucleus-1",
                sentence_number=1,
                authority_fact_ids=("fact-1",),
            ),
            FactualNucleusBindingV2(
                nucleus_id="nucleus-2",
                sentence_number=2,
                authority_fact_ids=("fact-2",),
            ),
        ),
    )
    assert two.authority_density is AuthorityDensityV2.COMPLEMENTARY


def test_density_rule_rejects_padding_thin_and_more_than_two_sentences():
    repeated_binding = (
        FactualNucleusBindingV2(
            nucleus_id="nucleus-1",
            sentence_number=1,
            authority_fact_ids=("fact-1",),
        ),
        FactualNucleusBindingV2(
            nucleus_id="nucleus-2",
            sentence_number=2,
            authority_fact_ids=("fact-1",),
        ),
    )
    with pytest.raises(ValidationError, match="additional supported nonredundant"):
        _summary("Un fapt. Același fapt repetat.", bindings=repeated_binding)
    with pytest.raises(ValidationError, match="thin authority"):
        _summary(
            "Un fapt. Încă un fapt.",
            density=AuthorityDensityV2.THIN,
            bindings=(
                repeated_binding[0],
                repeated_binding[1].model_copy(
                    update={"authority_fact_ids": ("fact-2",)}
                ),
            ),
        )
    with pytest.raises(ValidationError, match="one or two sentences"):
        _summary("Unu. Doi. Trei.")


def test_multiple_sources_alone_do_not_require_second_sentence():
    summary = _summary(
        "Mai multe surse confirmă același fapt.",
        density=AuthorityDensityV2.COMPLEMENTARY,
        bindings=(
            FactualNucleusBindingV2(
                nucleus_id="same-event-fact",
                sentence_number=1,
                authority_fact_ids=("source-a:fact-1", "source-b:fact-1"),
            ),
        ),
    )
    assert summary.text.count(".") == 1


def test_core_only_assembly_has_no_opening_closing_or_synthetic_story_parts():
    stories = (_story(10, 1), _story(20, 2))
    draft = PastilaEditorSemanticDraftV2.assemble(
        episode_id="episode-1",
        mode=SemanticDraftModeV2.CORE_ONLY,
        stories=stories,
    )
    assert draft.intro is None
    assert draft.final_monologue is None
    assert draft.transitions == ()
    assert draft.assembled_text == (
        "Fapt confirmat pentru 10.\n\nFapt confirmat pentru 20."
    )
    assert "commentary" not in draft.assembled_text


def test_transition_is_optional_and_must_connect_adjacent_stories():
    stories = (_story(10, 1), _story(20, 2), _story(30, 3))
    transition = CrossStoryTransitionV2(
        transition_id="transition-10-20",
        from_event_id=10,
        to_event_id=20,
        text="De la primul subiect trecem la următorul.",
        source_story_fingerprints=("sha256:10", "sha256:20"),
        validation_receipt="sha256:transition",
    )
    draft = PastilaEditorSemanticDraftV2.assemble(
        episode_id="episode-2",
        mode=SemanticDraftModeV2.CORE_ONLY,
        stories=stories,
        transitions=(transition,),
    )
    assert draft.assembled_text.split("\n\n")[1] == transition.text

    invalid = transition.model_copy(
        update={"transition_id": "transition-10-30", "to_event_id": 30}
    )
    with pytest.raises(ValueError, match="adjacent"):
        PastilaEditorSemanticDraftV2.assemble(
            episode_id="episode-2",
            mode=SemanticDraftModeV2.CORE_ONLY,
            stories=stories,
            transitions=(invalid,),
        )


def test_core_only_rejects_voice_but_episode_framing_remains_optional():
    voice_story = _story(10, 1).model_copy(
        update={
            "acid_commentary": AcidCommentaryV2(
                text="Comentariu acid.",
                voice_model_identity="voice-v1",
                factual_boundary_receipt="sha256:boundary",
            ),
            "acid_commentary_status": "present",
        }
    )
    with pytest.raises(ValidationError, match="acid commentary"):
        PastilaEditorSemanticDraftV2.assemble(
            episode_id="episode-3",
            mode=SemanticDraftModeV2.CORE_ONLY,
            stories=(voice_story,),
        )
    framed = PastilaEditorSemanticDraftV2.assemble(
        episode_id="episode-3",
        mode=SemanticDraftModeV2.CORE_ONLY,
        stories=(_story(10, 1),),
        intro=EpisodeIntroV2(text="Introducere.", provenance_reference="sha256:intro"),
    )
    assert framed.intro is not None
    assert framed.final_monologue is None


def test_legacy_projection_marks_absence_and_invents_no_prose():
    draft = PastilaEditorSemanticDraftV2.assemble(
        episode_id="episode-4",
        mode=SemanticDraftModeV2.CORE_ONLY,
        stories=(_story(10, 1),),
    )
    projection = project_semantic_draft_v2_to_legacy_v1(draft)
    assert projection.opening is None
    assert projection.closing is None
    assert projection.stories[0].commentary_blocks == ()
    assert projection.stories[0].ending is None
    assert projection.assembled_text == draft.assembled_text
    assert set(projection.omitted_legacy_fields) == {
        "opening",
        "closing",
        "commentary_blocks",
        "ending",
    }


def test_compatible_loader_preserves_v1_and_round_trips_v2():
    v1 = EpisodeDraft(
        episode_id="historical",
        opening="Deschidere istorică.",
        stories=(
            DraftStory(
                story_id=1,
                factual_summary="Fapt istoric.",
                commentary_blocks=(),
                ending="Final istoric.",
            ),
        ),
        transitions=(),
        closing="Închidere istorică.",
        cta=None,
        assembled_text=(
            "Deschidere istorică.\n\nFapt istoric.\n\nFinal istoric."
            "\n\nÎnchidere istorică."
        ),
        teleprompter_text=(
            "Deschidere istorică.\n\nFapt istoric.\n\nFinal istoric."
            "\n\nÎnchidere istorică."
        ),
    )
    loaded_v1 = load_semantic_draft_compatible(v1.model_dump(mode="python"))
    assert type(loaded_v1) is EpisodeDraft
    assert loaded_v1 == v1

    v2 = PastilaEditorSemanticDraftV2.assemble(
        episode_id="new",
        mode=SemanticDraftModeV2.CORE_ONLY,
        stories=(_story(2, 1),),
    )
    loaded_v2 = load_semantic_draft_compatible(v2.model_dump(mode="python"))
    assert type(loaded_v2) is PastilaEditorSemanticDraftV2
    assert loaded_v2 == v2
