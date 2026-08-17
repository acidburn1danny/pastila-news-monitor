"""Offline tests for M6C.4D controlled component generation."""

import json

import pytest
from pydantic import ValidationError
from test_voice_model import voice_pipeline

from pastila_scout.editor.generation import (
    ControlledGenerationError,
    ControlledGenerator,
    DraftAssembler,
    EpisodeGenerationState,
    GenerationManifest,
    PromptBuilder,
    ScriptedLanguageModelProvider,
    TeleprompterFormatter,
)
from pastila_scout.editor.generation.controlled_generator import (
    _bind_story_authority,
    _provisional_story_word_budget_plan,
    _story_context,
)
from pastila_scout.editor.generation.models import (
    STANDARD_STORY_WORD_BUDGET_V1,
    ApprovedFact,
    CommentaryBlockResult,
    DraftStory,
    DraftTransition,
    GenerationComponentType,
    GenerationMode,
    GenerationPolicy,
    LanguageGenerationConfig,
    ManifestItemStatus,
    StoryAuthoredContentResult,
    StoryGenerationContext,
    StoryGenerationResult,
    TeleprompterProfile,
)
from pastila_scout.editor.generation.prompt import PromptLayer
from pastila_scout.editor.generation.provider import ProviderTimeoutError
from pastila_scout.editor.generation.validation import validate_story


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


def authored_story_result(story_id: int, position: int) -> dict:
    value = story_result(story_id, position)
    del value["story_id"]
    del value["declared_editorial_intent_usage"]
    del value["declared_conversation_intent_usage"]
    del value["declared_voice_intent_usage"]
    for block in value["commentary_blocks"]:
        del block["blueprint_intent_ids"]
        del block["voice_plan_ids"]
    return value


def test_application_binds_story_and_intent_authority_outside_model_output():
    authored = StoryAuthoredContentResult.model_validate(authored_story_result(7, 1))
    context = StoryGenerationContext(
        story_id=7,
        flow_position=1,
        approved_facts=(
            ApprovedFact(fact_id="event-7-title", field="title", value="Titlu"),
        ),
        editorial_plan={"intent_id": "editorial:7"},
        conversation_plan={"intent_id": "conversation:7"},
        voice_plan={"intent_id": "voice:7"},
        word_budget_authority=STANDARD_STORY_WORD_BUDGET_V1,
        provisional_word_budget_plan={
            "factual_summary": 37,
            "commentary_blocks_total": 85,
            "ending": 28,
        },
        runtime_budget=120,
        protected_targets=(),
        allowed_satire_targets=("systemic_failure",),
        forbidden_claims=(),
    )
    bound = _bind_story_authority(authored, context)
    assert bound.story_id == 7
    assert bound.declared_editorial_intent_usage == ("editorial:7",)
    assert bound.declared_conversation_intent_usage == ("conversation:7",)
    assert bound.declared_voice_intent_usage == ("voice:7",)
    assert bound.commentary_blocks[0].blueprint_intent_ids == ("editorial:7",)
    assert bound.commentary_blocks[0].voice_plan_ids == ("voice:7",)


def test_authored_schema_rejects_model_attempt_to_supply_application_authority():
    forged = authored_story_result(7, 1)
    forged["story_id"] = 99
    forged["declared_editorial_intent_usage"] = ["editorial:99"]
    with pytest.raises(ValidationError):
        StoryAuthoredContentResult.model_validate(forged)


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
        word_budget_authority=STANDARD_STORY_WORD_BUDGET_V1,
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


def test_story_validation_rejects_unresolved_template_placeholder() -> None:
    context = StoryGenerationContext(
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
        word_budget_authority=STANDARD_STORY_WORD_BUDGET_V1,
        runtime_budget=60,
        protected_targets=(),
        allowed_satire_targets=("systemic_failure",),
        forbidden_claims=(),
    )
    valid = StoryGenerationResult.model_validate(story_result(1, 1))
    unresolved = valid.model_copy(update={"ending": "Absolut {cadru/eveniment}."})

    assert validate_story(valid, context, EpisodeGenerationState()).accepted
    outcome = validate_story(unresolved, context, EpisodeGenerationState())
    assert outcome.errors == ("unresolved_template_placeholder",)


def test_corrective_prompt_does_not_reinforce_unresolved_placeholder() -> None:
    context = _toolkit_context(
        "comedy_devices",
        "device:test",
        "{AȘTEPTARE}; realitatea: duș rece.",
    )
    prompt = PromptBuilder().build(
        component_type=GenerationComponentType.STORY,
        episode_context=None,
        component_context=context,
        state=EpisodeGenerationState(),
        output_schema=StoryAuthoredContentResult,
        mode=GenerationMode.CONSTRAINED,
        failures=("unresolved_template_placeholder",),
    )

    corrective = next(
        json.loads(section.content)
        for section in prompt.sections
        if section.layer is PromptLayer.CORRECTIVE_INSTRUCTIONS
    )
    assert "{AȘTEPTARE}" not in corrective["template_resolution_repair"]
    assert "omit that optional tool" in corrective["template_resolution_repair"]


def _toolkit_context(section: str, identity: str, text: str) -> StoryGenerationContext:
    return StoryGenerationContext(
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
        optional_editorial_toolkit={
            section: ({"id": identity, "text": text, "affordance": "test"},)
        },
        word_budget_authority=STANDARD_STORY_WORD_BUDGET_V1,
        runtime_budget=60,
        protected_targets=(),
        allowed_satire_targets=("systemic_failure",),
        forbidden_claims=(),
    )


def _result_with_text(text: str) -> StoryGenerationResult:
    result = StoryGenerationResult.model_validate(story_result(1, 1))
    block = result.commentary_blocks[0].model_copy(update={"text": text})
    return result.model_copy(update={"commentary_blocks": (block,)})


@pytest.mark.parametrize(
    ("section", "surface", "single", "duplicate"),
    [
        (
            "expressions",
            "a face toți banii",
            "Detaliul poate a face toți banii.",
            "Asta poate a face toți banii. Și finalul poate a face toți banii.",
        ),
        (
            "controlled_terms",
            "vibe-ul",
            "Vibe-ul este comercial.",
            "Vibe-ul este comercial, iar vibe-ul rămâne calculat.",
        ),
        (
            "comedy_devices",
            "Absolut {cadru/eveniment}.",
            "Absolut cinema.",
            "Absolut cinema. Absolut spectacol.",
        ),
        (
            "comedy_devices",
            "Legenda spune că {CLAUZĂ}.",
            "Legenda spune că proiectul va fi gata.",
            "Legenda spune că vine. Legenda spune că pleacă.",
        ),
        (
            "signature_devices",
            "Cum zicea un mare clasic în viață... {CLAUZĂ}.",
            "Cum zicea un mare clasic în viață... treaba merge.",
            "Cum zicea un mare clasic în viață... vine. Cum zicea un mare clasic în viață... pleacă.",
        ),
    ],
)
def test_duplicate_offered_tool_validation(
    section: str, surface: str, single: str, duplicate: str
) -> None:
    context = _toolkit_context(section, "tool-id", surface)
    state = EpisodeGenerationState()

    assert validate_story(_result_with_text(single), context, state).accepted
    outcome = validate_story(_result_with_text(duplicate), context, state)
    assert outcome.errors == (f"duplicate_offered_tool_usage:{section}:tool-id:2",)
    assert outcome.fatal is True


def test_duplicate_validator_undercounts_ambiguous_and_unoffered_text() -> None:
    expression_context = _toolkit_context(
        "expressions", "expression-id", "a face toți banii"
    )
    empty_context = _toolkit_context("expressions", "other-id", "altă expresie")

    assert validate_story(
        _result_with_text("Banii vin, iar banii pleacă."),
        expression_context,
        EpisodeGenerationState(),
    ).accepted
    assert validate_story(
        _result_with_text("Vibe-ul vine, iar vibe-ul pleacă."),
        empty_context,
        EpisodeGenerationState(),
    ).accepted


def test_device_prefix_is_not_a_complete_duplicate_and_compound_counts_as_one() -> None:
    device = _toolkit_context("comedy_devices", "legend", "Legenda spune că {CLAUZĂ}.")
    compound = _toolkit_context(
        "comedy_devices",
        "compound",
        "Ai, n-ai {X}, {Y}. Să fie bine, să nu fie rău.",
    )

    assert validate_story(
        _result_with_text("Legenda spune, dar nimeni nu termină formula."),
        device,
        EpisodeGenerationState(),
    ).accepted
    assert validate_story(
        _result_with_text(
            "Ai, n-ai autorizație, ridici blocul. Să fie bine, să nu fie rău."
        ),
        compound,
        EpisodeGenerationState(),
    ).accepted


def test_duplicate_failure_retries_clean_output_without_mutating_input_state() -> None:
    context = _toolkit_context(
        "comedy_devices", "absolute", "Absolut {cadru/eveniment}."
    )
    duplicate = story_result(1, 1)
    duplicate["commentary_blocks"][0]["text"] = "Absolut cinema. Absolut spectacol."
    clean = story_result(1, 1)
    clean["commentary_blocks"][0]["text"] = "Absolut cinema."
    provider = ScriptedLanguageModelProvider((duplicate, clean))
    generator = ControlledGenerator(provider, config=config())
    state = EpisodeGenerationState()

    result, traces, status = generator._component(
        item_id="story-01",
        component_type=GenerationComponentType.STORY,
        target_id="1",
        episode_context={"episode_id": "test"},
        component_context=context,
        output_schema=StoryGenerationResult,
        validator=lambda value: validate_story(value, context, state),
        state=state,
    )

    assert result.commentary_blocks[0].text == "Absolut cinema."
    assert status is ManifestItemStatus.COMPLETED
    assert len(provider.prompts) == 2
    assert traces[0].acceptance_status is ManifestItemStatus.RETRYING
    assert traces[1].acceptance_status is ManifestItemStatus.COMPLETED
    assert state.revision == 0


def test_three_duplicate_attempts_end_terminal_failed_without_state_change() -> None:
    context = _toolkit_context(
        "comedy_devices", "absolute", "Absolut {cadru/eveniment}."
    )
    duplicate = story_result(1, 1)
    duplicate["commentary_blocks"][0]["text"] = "Absolut cinema. Absolut spectacol."
    provider = ScriptedLanguageModelProvider((duplicate, duplicate, duplicate))
    generator = ControlledGenerator(provider, config=config())
    state = EpisodeGenerationState()

    _, traces, status = generator._component(
        item_id="story-01",
        component_type=GenerationComponentType.STORY,
        target_id="1",
        episode_context={"episode_id": "test"},
        component_context=context,
        output_schema=StoryGenerationResult,
        validator=lambda value: validate_story(value, context, state),
        state=state,
    )

    assert status is ManifestItemStatus.FAILED
    assert len(provider.prompts) == 3
    assert traces[-1].acceptance_status is ManifestItemStatus.FAILED
    assert state.revision == 0


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
        word_budget_authority=STANDARD_STORY_WORD_BUDGET_V1,
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
        authored_story_result(story_id, position)
        for position, story_id in enumerate(order, 1)
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
    assert tuple(item.event_id for item in result.draft.usage_receipts) == tuple(
        str(item) for item in order
    )

    story_sections = {
        section.layer: json.loads(section.content)
        for section in provider.prompts[0].sections
    }
    assert {fact["field"] for fact in story_sections[PromptLayer.APPROVED_FACTS]} == {
        "canonical_title",
        "canonical_summary",
        "categories",
    }
    editorial = story_sections[PromptLayer.EDITORIAL_INTENTIONS]
    assert {"intent", "angles", "narrative_function", "levels"} <= set(editorial)
    assert "event_id" not in editorial and "intent_id" not in editorial
    conversation = story_sections[PromptLayer.CONVERSATION_INTENTIONS]
    assert {"audience_strategy", "beats", "punchline", "why_it_matters"} <= set(
        conversation
    )
    assert "event_id" not in conversation and "intent_id" not in conversation
    voice_guidance = story_sections[PromptLayer.VOICE_INTENTIONS]
    assert {"orality", "sentence_rhythm", "prohibited_voice_modes"} <= set(
        voice_guidance
    )
    assert "event_id" not in voice_guidance and "intent_id" not in voice_guidance
    local = story_sections[PromptLayer.COMPONENT_CONTEXT]
    assert sum(local["provisional_word_budget_plan"].values()) == 150
    assert local["word_budget"] == {
        "profile": "STANDARD",
        "target": 150,
        "hard_max": 170,
    }
    toolkit = local["optional_editorial_toolkit"]
    assert "rules" in toolkit and "preserve_facts" in toolkit["rules"]
    schema_hint = story_sections[PromptLayer.OUTPUT_SCHEMA]
    assert schema_hint == {
        "native_schema": "StoryAuthoredContentResult",
        "return_only_structured_result": True,
    }


def test_corrective_retry_then_success_does_not_mutate_failed_attempt_state() -> None:
    scout, flow, generic, commentary, voice = voice_pipeline([{"event_id": 1}])
    story_id = commentary.blueprint.flow_order[0]
    invalid = authored_story_result(story_id, 1)
    invalid["declared_fact_usage"] = ["unknown-fact"]
    responses = [
        invalid,
        authored_story_result(story_id, 1),
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
    assert len(result.draft.usage_receipts) == 1


def test_retry_feedback_names_exact_mechanical_budget_repairs_only():
    context = StoryGenerationContext(
        story_id=7,
        flow_position=1,
        approved_facts=(
            ApprovedFact(fact_id="event-7-title", field="title", value="Titlu"),
        ),
        editorial_plan={"intent_id": "editorial:7"},
        conversation_plan={"intent_id": "conversation:7"},
        voice_plan={"intent_id": "voice:7"},
        word_budget_authority=STANDARD_STORY_WORD_BUDGET_V1,
        runtime_budget=120,
        protected_targets=(),
        allowed_satire_targets=("systemic_failure",),
        forbidden_claims=(),
    )
    prompt = PromptBuilder().build(
        component_type=GenerationComponentType.STORY,
        episode_context={},
        component_context=context,
        state=EpisodeGenerationState(),
        output_schema=StoryGenerationResult,
        mode=GenerationMode.MINIMAL_SAFE,
        failures=(
            "word_budget_exceeded",
            "word_budget_actual:184",
        ),
    )
    corrective = next(
        section
        for section in prompt.sections
        if section.layer is PromptLayer.CORRECTIVE_INSTRUCTIONS
    )
    assert '"maximum_content_words":170' in corrective.content
    assert '"previous_content_words":184' in corrective.content
    assert '"minimum_words_to_remove":14' in corrective.content
    assert '"maximum_content_words":150' not in corrective.content
    assert "intent_id" not in corrective.content


def test_provisional_budget_plan_is_deterministic_and_preserves_total():
    assert _provisional_story_word_budget_plan(150) == {
        "factual_summary": 37,
        "commentary_blocks_total": 85,
        "ending": 28,
    }
    assert sum(_provisional_story_word_budget_plan(81).values()) == 81


def test_standard_story_budget_is_versioned_fixed_product_authority():
    authority = STANDARD_STORY_WORD_BUDGET_V1

    assert authority.authority_version == "story-word-budget-v1"
    assert authority.profile.value == "STANDARD"
    assert authority.target_words == 150
    assert authority.hard_max_words == 170
    with pytest.raises(ValidationError):
        type(authority)(target_words=149)
    with pytest.raises(ValidationError):
        type(authority)(hard_max_words=171)


@pytest.mark.parametrize(
    ("word_count", "accepted"),
    ((149, True), (150, True), (158, True), (169, True), (170, True), (171, False)),
)
def test_story_validation_uses_hard_max_not_target(word_count, accepted):
    context = StoryGenerationContext(
        story_id=7,
        flow_position=1,
        approved_facts=(
            ApprovedFact(fact_id="event-7-title", field="title", value="Titlu"),
        ),
        editorial_plan={"intent_id": "editorial:7"},
        conversation_plan={"intent_id": "conversation:7"},
        voice_plan={
            "intent_id": "voice:7",
            "vocatives": {"maximum_per_story": 0},
            "profanity_ceiling": "clean",
        },
        word_budget_authority=STANDARD_STORY_WORD_BUDGET_V1,
        provisional_word_budget_plan=_provisional_story_word_budget_plan(150),
        runtime_budget=120,
        protected_targets=(),
        allowed_satire_targets=("systemic_failure",),
        forbidden_claims=(),
    )
    authored = authored_story_result(7, 1)
    fixed_words = len(
        " ".join(
            (
                *(block["text"] for block in authored["commentary_blocks"]),
                authored["ending"],
            )
        ).split()
    )
    authored["factual_summary"] = " ".join(("cuvant",) * (word_count - fixed_words))
    result = _bind_story_authority(
        StoryAuthoredContentResult.model_validate(authored), context
    )

    outcome = validate_story(result, context, EpisodeGenerationState())

    assert outcome.accepted is accepted
    assert ("word_budget_exceeded" in outcome.errors) is (not accepted)
    assert (f"word_budget_actual:{word_count}" in outcome.errors) is (not accepted)


def test_story_budget_does_not_depend_on_score_or_source_count():
    scout, _, generic, commentary, voice = voice_pipeline([{"event_id": 7}])
    base = scout.ranked_events[0]
    editorial = generic.blueprint.segments[0]
    conversation = commentary.blueprint.stories[0]
    voice_story = voice.plan.stories[0]
    low = _story_context(
        base.model_copy(update={"final_score": 0.0, "source_count": 1}),
        1,
        editorial,
        conversation,
        voice_story,
    )
    high_multi = _story_context(
        base.model_copy(update={"final_score": 100.0, "source_count": 12}),
        1,
        editorial,
        conversation,
        voice_story,
    )

    assert low.word_budget_authority == high_multi.word_budget_authority
    assert low.word_budget_authority == STANDARD_STORY_WORD_BUDGET_V1
    assert low.provisional_word_budget_plan == high_multi.provisional_word_budget_plan
    assert low.approved_facts == high_multi.approved_facts


def test_requires_review_story_stops_before_opening_and_closing():
    scout, flow, generic, commentary, voice = voice_pipeline([{"event_id": 1}])
    invalid = authored_story_result(1, 1)
    invalid["ending"] = " ".join(("prea-lung",) * 1_000)
    provider = ScriptedLanguageModelProvider([invalid, invalid, invalid])
    with pytest.raises(ControlledGenerationError, match="handoff-valid"):
        ControlledGenerator(provider, config=config()).generate(
            scout_input=scout,
            selection_profile=profile_from_pipeline(scout),
            episode_context=context_from_pipeline(scout),
            flow_result=flow,
            editorial_blueprint=generic.blueprint,
            commentary_blueprint=commentary.blueprint,
            voice_plan=voice.plan,
        )
    assert len(provider.prompts) == 3
    assert all(
        prompt.component_type is GenerationComponentType.STORY
        for prompt in provider.prompts
    )


def profile_from_pipeline(scout):
    from test_editor_selection import profile

    return profile(target=len(scout.ranked_events))


def context_from_pipeline(scout):
    from test_editor_selection import context

    return context(target=len(scout.ranked_events))
