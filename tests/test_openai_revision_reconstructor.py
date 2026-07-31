"""Focused authorization and reconstruction tests for the OpenAI provider patch."""

from test_controlled_revision_contracts import FP, _request

from pastila_scout.editor.generation.ai_provider_adapter.openai import (
    OpenAIControlledRevisionProviderOutput,
    OpenAIControlledRevisionReconstructor,
    OpenAIReconstructionError,
)
from pastila_scout.editor.generation.models import (
    CallToActionDraft,
    CTAPlacement,
    DraftStory,
    DraftTransition,
    EpisodeDraft,
    derive_assembled_text,
)
from pastila_scout.editor.generation.revision import (
    ControlledRevisionInvocation,
    ControlledRevisionTarget,
    RevisionTargetType,
)


def _source():
    stories = (
        DraftStory(
            story_id=1,
            factual_summary="Rezumat unu.",
            commentary_blocks=(),
            ending="Final unu.",
        ),
        DraftStory(
            story_id=2,
            factual_summary="Rezumat doi.",
            commentary_blocks=(),
            ending="Final doi.",
        ),
    )
    transitions = (DraftTransition(from_story_id=1, to_story_id=2, text="Tranziție."),)
    cta = CallToActionDraft(
        placement=CTAPlacement.BEFORE_CLOSING,
        after_story_id=None,
        bridge_text="Pod CTA.",
        static_content="Text static.",
    )
    assembled = derive_assembled_text(
        opening="Deschidere.",
        stories=stories,
        transitions=transitions,
        closing="Închidere.",
        cta=cta,
    )
    return EpisodeDraft(
        episode_id="episod-autoritativ",
        opening="Deschidere.",
        stories=stories,
        transitions=transitions,
        closing="Închidere.",
        cta=cta,
        assembled_text=assembled,
        teleprompter_text="Formatare teleprompter veche.",
    )


def _invocation(*targets):
    request = _request(source=_source(), targets=targets)
    return ControlledRevisionInvocation.build(request=request)


def _target(target_type, **values):
    return ControlledRevisionTarget.build(
        target_type=target_type,
        upstream_target_fingerprint=FP,
        **values,
    )


def test_reconstruction_patches_all_component_kinds_without_changing_structure():
    invocation = _invocation(
        _target(RevisionTargetType.STORY, story_id=1),
        _target(RevisionTargetType.TRANSITION, from_story_id=1, to_story_id=2),
        _target(RevisionTargetType.CALL_TO_ACTION),
    )
    output = OpenAIControlledRevisionProviderOutput.model_validate(
        {
            "revised_components": [
                {
                    "component_type": "story",
                    "component_reference": "story:1",
                    "factual_summary": "Rezumat unu revizuit.",
                    "commentary_block_texts": [],
                    "ending": "Final unu revizuit.",
                },
                {
                    "component_type": "transition",
                    "component_reference": "transition:1:2",
                    "revised_text": "Tranziție revizuită.",
                },
                {
                    "component_type": "call_to_action",
                    "component_reference": "call_to_action",
                    "bridge_text": "Pod CTA revizuit.",
                },
            ]
        }
    )

    revised = OpenAIControlledRevisionReconstructor().reconstruct(invocation, output)
    source = invocation.request.source_draft
    assert revised.episode_id == source.episode_id
    assert tuple(item.story_id for item in revised.stories) == (1, 2)
    assert revised.stories[1] == source.stories[1]
    assert revised.transitions[0].from_story_id == 1
    assert revised.transitions[0].to_story_id == 2
    assert revised.cta.placement == source.cta.placement
    assert revised.cta.static_content == source.cta.static_content
    assert revised.assembled_text == revised.teleprompter_text


def test_missing_required_component_is_rejected():
    invocation = _invocation(
        _target(RevisionTargetType.OPENING),
        _target(RevisionTargetType.CLOSING),
    )
    output = OpenAIControlledRevisionProviderOutput.model_validate(
        {
            "revised_components": [
                {
                    "component_type": "opening",
                    "component_reference": "opening",
                    "revised_text": "Deschidere revizuită.",
                }
            ]
        }
    )
    try:
        OpenAIControlledRevisionReconstructor().reconstruct(invocation, output)
    except OpenAIReconstructionError as error:
        assert (
            error.diagnostic_code == "openai_provider_output_required_component_missing"
        )
    else:  # pragma: no cover
        raise AssertionError("missing provider component was accepted")
