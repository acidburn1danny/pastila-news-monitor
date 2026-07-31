"""Offline tests for M6C.4D controlled component generation."""

import pytest
from pydantic import ValidationError
from test_voice_model import voice_pipeline

from pastila_scout.editor.generation import (
    ControlledGenerator,
    DraftAssembler,
    EpisodeGenerationState,
    GenerationManifest,
    PromptBuilder,
    ScriptedLanguageModelProvider,
    TeleprompterFormatter,
)
from pastila_scout.editor.generation.models import (
    ApprovedFact,
    CommentaryBlockResult,
    DraftStory,
    DraftTransition,
    GenerationComponentType,
    GenerationMode,
    GenerationPolicy,
    LanguageGenerationConfig,
    ManifestItemStatus,
    StoryGenerationContext,
    StoryGenerationResult,
    TeleprompterProfile,
)
from pastila_scout.editor.generation.prompt import PromptLayer
from pastila_scout.editor.generation.provider import ProviderTimeoutError


def config():
    return LanguageGenerationConfig(provider="scripted", model_identifier="offline-v1")


def story_result(story_id: int, position: int) -> dict:
    fact = f"event-{story_id}-title"
    return {
        "story_id": story_id,
        "factual_summary": f"Fapt confirmat {story_id}.",
        "commentary_blocks": [
            {
                "block_type": "why_it_matters",
                "text": f"Comentariu controlat {story_id}.",
                "sequence": 1,
                "source_fact_ids": [fact],
                "blueprint_intent_ids": [f"editorial:{story_id}"],
                "voice_plan_ids": [f"voice:{story_id}"],
                "satire_target_ids": ["systemic_failure"],
                "protected_target_ids": [],
            }
        ],
        "ending": f"Final controlat {story_id}.",
        "ending_type": "reflection",
        "declared_fact_usage": [fact],
        "declared_editorial_intent_usage": [f"editorial:{story_id}"],
        "declared_conversation_intent_usage": [f"conversation:{story_id}"],
        "declared_voice_intent_usage": [f"voice:{story_id}"],
    }


def test_policy_config_and_contexts_are_frozen() -> None:
    assert GenerationPolicy().max_attempts_per_component == 3
    assert config().temperature == 0.3
    with pytest.raises(ValueError):
        GenerationPolicy(max_attempts_per_component=4)
    with pytest.raises(ValueError):
        LanguageGenerationConfig(provider="x", model_identifier="x", temperature=3)
    state = EpisodeGenerationState()
    with pytest.raises(ValidationError):
        state.revision = 2


def test_manifest_ids_order_dependencies_and_readiness() -> None:
    manifest = GenerationManifest.build((11, 22), include_cta=True, maximum_attempts=3)
    ids = tuple(item.item_id for item in manifest.items)

    assert ids == (
        "story-01",
        "story-02",
        "transition-01-02",
        "opening",
        "closing",
        "cta",
        "assembly",
        "teleprompter-formatting",
    )
    transition = manifest.items[2]
    assert transition.dependency_ids == ("story-01", "story-02")
    assert (
        transition.derived_status(
            {
                "story-01": ManifestItemStatus.COMPLETED,
                "story-02": ManifestItemStatus.COMPLETED,
            }
        )
        == ManifestItemStatus.READY
    )
    assert manifest.items[5].dependency_ids == ("closing",)


def test_prompt_layers_fingerprint_retry_and_minimal_safe_are_deterministic() -> None:
    context = StoryGenerationContext(
        story_id=1,
        flow_position=1,
        approved_facts=(ApprovedFact(fact_id="f1", field="title", value="2.4 km"),),
        editorial_plan={"b": 2, "a": 1},
        conversation_plan={"intent": "peer"},
        voice_plan={"ceiling": "clean"},
        word_budget=100,
        runtime_budget=60,
        protected_targets=(),
        allowed_satire_targets=("systemic_failure",),
        forbidden_claims=("invented_quote",),
    )
    builder = PromptBuilder()
    episode = {"episode_id": "episode"}
    first = builder.build(
        component_type=GenerationComponentType.STORY,
        episode_context=episode,
        component_context=context,
        state=EpisodeGenerationState(),
        output_schema=StoryGenerationResult,
    )
    repeated = builder.build(
        component_type=GenerationComponentType.STORY,
        episode_context=episode,
        component_context=context,
        state=EpisodeGenerationState(),
        output_schema=StoryGenerationResult,
    )
    retry = builder.build(
        component_type=GenerationComponentType.STORY,
        episode_context=episode,
        component_context=context,
        state=EpisodeGenerationState(),
        output_schema=StoryGenerationResult,
        mode=GenerationMode.MINIMAL_SAFE,
        failures=("missing_fact",),
    )

    assert first == repeated
    assert PromptLayer.VALIDATION_FAILURES not in {
        item.layer for item in first.sections
    }
    assert PromptLayer.CORRECTIVE_INSTRUCTIONS in {
        item.layer for item in retry.sections
    }
    assert first.prompt_fingerprint != retry.prompt_fingerprint
    assert "2.4 km" in first.text
    assert "raw_payload" not in first.text


def test_scripted_provider_records_calls_and_retries_timeout_without_editorial_attempt() -> (
    None
):
    valid = story_result(1, 1)
    provider = ScriptedLanguageModelProvider([ProviderTimeoutError("slow"), valid])
    prompt_context = StoryGenerationContext(
        story_id=1,
        flow_position=1,
        approved_facts=(
            ApprovedFact(fact_id="event-1-title", field="title", value="Titlu"),
        ),
        editorial_plan={"intent_id": "editorial:1"},
        conversation_plan={"intent_id": "conversation:1"},
        voice_plan={
            "intent_id": "voice:1",
            "vocatives": {"maximum_per_story": 0},
            "profanity_ceiling": "clean",
        },
        word_budget=100,
        runtime_budget=60,
        protected_targets=(),
        allowed_satire_targets=("systemic_failure",),
        forbidden_claims=(),
    )
    prompt = PromptBuilder().build(
        component_type=GenerationComponentType.STORY,
        episode_context={},
        component_context=prompt_context,
        state=EpisodeGenerationState(),
        output_schema=StoryGenerationResult,
    )
    generator = ControlledGenerator(provider, config=config())
    result = generator._provider_call(prompt, StoryGenerationResult)
    assert result.story_id == 1
    assert len(provider.prompts) == 2


def test_state_updates_are_immutable_and_failed_attempts_do_not_register_anchor() -> (
    None
):
    state = EpisodeGenerationState()
    result = StoryGenerationResult.model_validate(story_result(1, 1))
    next_state = state.accept_story("story-01", result)

    assert state.revision == 0 and not state.generated_story_ids
    assert next_state.revision == 1 and next_state.generated_story_ids == (1,)


def test_assembly_and_teleprompter_preserve_order_and_numeric_notation() -> None:
    block = CommentaryBlockResult(
        block_type="commentary",
        text="Distanța este 2.4 km.",
        sequence=1,
        source_fact_ids=("f",),
        blueprint_intent_ids=("e",),
        voice_plan_ids=("v",),
        satire_target_ids=(),
        protected_target_ids=(),
    )
    stories = (
        DraftStory(
            story_id=1,
            factual_summary="Fapt 1.",
            commentary_blocks=(block,),
            ending="Final 1.",
        ),
        DraftStory(
            story_id=2,
            factual_summary="Fapt 2.",
            commentary_blocks=(block,),
            ending="Final 2.",
        ),
    )
    transitions = (DraftTransition(from_story_id=1, to_story_id=2, text="Tranziție."),)
    draft = DraftAssembler().assemble(
        episode_id="e",
        story_order=(1, 2),
        opening="Deschidere.",
        stories=stories,
        transitions=transitions,
        closing="Închidere.",
        cta=None,
    )
    formatter = TeleprompterFormatter()
    formatted = formatter.format(
        draft.assembled_text, TeleprompterProfile(maximum_line_length=20)
    )

    assert (
        draft.assembled_text.index("Fapt 1")
        < draft.assembled_text.index("Tranziție")
        < draft.assembled_text.index("Fapt 2")
    )
    assert "2.4 km" in formatted
    assert (
        formatter.format(formatted, TeleprompterProfile(maximum_line_length=20))
        == formatted
    )
    with pytest.raises(ValueError):
        DraftAssembler().assemble(
            episode_id="e",
            story_order=(1, 2),
            opening="x",
            stories=(stories[0], stories[0]),
            transitions=transitions,
            closing="x",
            cta=None,
        )


def test_full_offline_generation_uses_separate_calls_and_required_order() -> None:
    scout, flow, generic, commentary, voice = voice_pipeline(
        [{"event_id": 1}, {"event_id": 2}]
    )
    order = commentary.blueprint.flow_order
    responses = [
        story_result(story_id, position) for position, story_id in enumerate(order, 1)
    ]
    responses.extend(
        [
            {
                "from_story_id": order[0],
                "to_story_id": order[1],
                "text": "Tranziție controlată.",
                "transition_type": "contrast",
                "declared_plan_references": ["transition"],
            },
            {
                "text": "Deschidere controlată.",
                "referenced_story_ids": list(order),
                "opening_mechanism": "fact_first",
                "declared_plan_references": ["opening"],
            },
            {
                "text": "Închidere controlată.",
                "closing_mechanism": "reflection",
                "declared_plan_references": ["closing"],
            },
            {
                "bridge_text": "Un scurt sprijin.",
                "declared_plan_references": ["cta"],
            },
        ]
    )
    provider = ScriptedLanguageModelProvider(responses)
    result = ControlledGenerator(provider, config=config()).generate(
        scout_input=scout,
        selection_profile=profile_from_pipeline(scout),
        episode_context=context_from_pipeline(scout),
        flow_result=flow,
        editorial_blueprint=generic.blueprint,
        commentary_blueprint=commentary.blueprint,
        voice_plan=voice.plan,
        static_cta_content="RO49AAAA1B31007593840000",
    )

    assert provider.call_order == [
        GenerationComponentType.STORY,
        GenerationComponentType.STORY,
        GenerationComponentType.TRANSITION,
        GenerationComponentType.OPENING,
        GenerationComponentType.CLOSING,
        GenerationComponentType.CALL_TO_ACTION,
    ]
    assert tuple(story.story_id for story in result.draft.stories) == order
    assert result.final_state.revision == 8
    assert result.draft.cta.static_content == "RO49AAAA1B31007593840000"
    assert "RO49AAAA1B31007593840000" in result.draft.assembled_text
    assert all(
        item.status is ManifestItemStatus.COMPLETED for item in result.manifest.items
    )
    assert all(
        item.state_revision_after >= item.state_revision_before
        for item in result.trace.attempts
    )


def test_corrective_retry_then_success_does_not_mutate_failed_attempt_state() -> None:
    scout, flow, generic, commentary, voice = voice_pipeline([{"event_id": 1}])
    story_id = commentary.blueprint.flow_order[0]
    invalid = story_result(story_id, 1)
    invalid["declared_fact_usage"] = ["unknown-fact"]
    responses = [
        invalid,
        story_result(story_id, 1),
        {
            "text": "Deschidere.",
            "referenced_story_ids": [story_id],
            "opening_mechanism": "fact_first",
            "declared_plan_references": ["opening"],
        },
        {
            "text": "Închidere.",
            "closing_mechanism": "reflection",
            "declared_plan_references": ["closing"],
        },
    ]
    provider = ScriptedLanguageModelProvider(responses)
    result = ControlledGenerator(provider, config=config()).generate(
        scout_input=scout,
        selection_profile=profile_from_pipeline(scout),
        episode_context=context_from_pipeline(scout),
        flow_result=flow,
        editorial_blueprint=generic.blueprint,
        commentary_blueprint=commentary.blueprint,
        voice_plan=voice.plan,
    )

    first, second = result.trace.attempts[:2]
    assert first.acceptance_status is ManifestItemStatus.RETRYING
    assert first.state_revision_before == first.state_revision_after == 0
    assert second.generation_mode is GenerationMode.CONSTRAINED
    assert second.state_revision_before == 0 and second.state_revision_after == 1
    assert PromptLayer.VALIDATION_FAILURES in {
        section.layer for section in provider.prompts[1].sections
    }


def profile_from_pipeline(scout):
    from test_editor_selection import profile

    return profile(target=len(scout.ranked_events))


def context_from_pipeline(scout):
    from test_editor_selection import context

    return context(target=len(scout.ranked_events))
