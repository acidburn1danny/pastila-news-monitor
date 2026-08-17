"""Permanent regressions for the M6C.4D.1 architectural corrections."""

import json
import os
import subprocess
import sys

import pytest
from pydantic import ValidationError
from test_controlled_generation import (
    authored_story_result,
    config,
    context_from_pipeline,
    profile_from_pipeline,
)
from test_voice_model import voice_pipeline

from pastila_scout.editor.generation import (
    ControlledGenerator,
    DraftAssembler,
    EpisodeGenerationState,
    PromptBuilder,
    ScriptedLanguageModelProvider,
)
from pastila_scout.editor.generation.models import (
    ApprovedFact,
    CommentaryBlockResult,
    DraftStory,
    EpisodeDraft,
    FrozenModel,
    GeneratedCallbackAnchor,
    GenerationComponentType,
    StoryGenerationContext,
    StoryGenerationResult,
    TransitionGenerationResult,
)
from pastila_scout.editor.generation.prompt import (
    PromptCanonicalizationError,
    canonicalize,
)


class SetModel(FrozenModel):
    values: frozenset[object]


def prompt_context(*, reverse: bool = False) -> StoryGenerationContext:
    facts = (
        ApprovedFact(fact_id="f1", field="title", value="Titlu"),
        ApprovedFact(fact_id="f2", field="summary", value="Rezumat"),
    )
    forbidden = ("invented_quote", "unverified_motive")
    if reverse:
        facts = tuple(reversed(facts))
        forbidden = tuple(reversed(forbidden))
    return StoryGenerationContext(
        story_id=1,
        flow_position=1,
        approved_facts=facts,
        editorial_plan={"z": 2, "a": 1} if reverse else {"a": 1, "z": 2},
        conversation_plan={"peer": True},
        voice_plan={"profanity_ceiling": "clean"},
        word_budget=100,
        runtime_budget=60,
        protected_targets=(),
        allowed_satire_targets=("systemic_failure",),
        forbidden_claims=forbidden,
    )


def build_prompt(context, *, episode=None, state=None):
    return PromptBuilder().build(
        component_type=GenerationComponentType.STORY,
        episode_context=episode or {"episode": "test"},
        component_context=context,
        state=state or EpisodeGenerationState(),
        output_schema=StoryGenerationResult,
    )


def test_canonical_prompt_ignores_nonsemantic_collection_order() -> None:
    anchors = (
        GeneratedCallbackAnchor(
            callback_id="b",
            source_story_id=2,
            anchor_summary="B",
            allowed_target_component_ids=("closing",),
        ),
        GeneratedCallbackAnchor(
            callback_id="a",
            source_story_id=1,
            anchor_summary="A",
            allowed_target_component_ids=("closing",),
        ),
    )
    state_a = EpisodeGenerationState(
        story_factual_summaries={2: "B", 1: "A"},
        registered_callback_anchors=anchors,
    )
    state_b = EpisodeGenerationState(
        story_factual_summaries={1: "A", 2: "B"},
        registered_callback_anchors=tuple(reversed(anchors)),
    )
    first = build_prompt(
        prompt_context(),
        episode={"nested": {"letters": {"b", "a"}}},
        state=state_a,
    )
    second = build_prompt(
        prompt_context(reverse=True),
        episode={"nested": {"letters": frozenset(("a", "b"))}},
        state=state_b,
    )

    assert first.text == second.text
    assert first.prompt_fingerprint == second.prompt_fingerprint


def test_canonicalizer_supports_nested_sets_and_rejects_opaque_or_nonfinite() -> None:
    left = canonicalize(SetModel(values=frozenset(("x", 2, False))))
    right = canonicalize(SetModel(values=frozenset((False, "x", 2))))
    assert left == right
    with pytest.raises(
        PromptCanonicalizationError, match="unsupported prompt value type"
    ):
        canonicalize(object())
    for value in (float("nan"), float("inf"), float("-inf")):
        with pytest.raises(PromptCanonicalizationError, match="non-finite"):
            canonicalize(value)


def test_prompt_fingerprint_is_identical_across_hash_seeds() -> None:
    code = """
import json
from pastila_scout.editor.generation.models import GenerationComponentType, StoryGenerationResult
from pastila_scout.editor.generation.prompt import PromptBuilder
from pastila_scout.editor.generation.state import EpisodeGenerationState
p = PromptBuilder().build(component_type=GenerationComponentType.STORY, episode_context={'unordered': {'alpha','beta','gamma','delta','epsilon'}}, component_context={}, state=EpisodeGenerationState(), output_schema=StoryGenerationResult)
print(json.dumps({'text': p.text, 'fingerprint': p.prompt_fingerprint}, ensure_ascii=False, sort_keys=True))
"""
    outputs = []
    for seed in range(8):
        environment = os.environ.copy()
        environment["PYTHONHASHSEED"] = str(seed)
        completed = subprocess.run(
            [sys.executable, "-c", code],
            check=True,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment,
        )
        outputs.append(completed.stdout.strip())
    assert len(set(outputs)) == 1


def test_state_is_deeply_immutable_and_defensively_normalized() -> None:
    source = {2: "B", 1: "A"}
    state = EpisodeGenerationState(story_factual_summaries=source)
    snapshot = state.model_dump(mode="json")
    source[1] = "changed"

    assert state.factual_summary(1) == "A"
    assert isinstance(state.story_factual_summaries, tuple)
    assert not any(
        isinstance(value, (dict, list, set)) for value in state.__dict__.values()
    )
    with pytest.raises(ValidationError):
        state.revision = 2
    with pytest.raises(TypeError):
        state.story_factual_summaries[0] = state.story_factual_summaries[0]
    with pytest.raises(ValidationError):
        state.story_factual_summaries[0].text = "changed"
    assert state.model_dump(mode="json") == snapshot


def test_callback_consumption_replaces_anchor_without_mutating_previous_state() -> None:
    anchor = GeneratedCallbackAnchor(
        callback_id="callback-1",
        source_story_id=1,
        anchor_summary="anchor",
        allowed_target_component_ids=("transition-01-02",),
    )
    state = EpisodeGenerationState(registered_callback_anchors=(anchor,))
    transition = TransitionGenerationResult(
        from_story_id=1,
        to_story_id=2,
        text="Tranziție.",
        transition_type="contrast",
        callback_usage=("callback-1",),
        declared_plan_references=("transition",),
    )
    next_state = state.accept_transition("transition-01-02", transition)

    assert next_state is not state
    assert state.revision == 0 and next_state.revision == 1
    assert anchor.current_uses == 0
    assert state.registered_callback_anchors[0].current_uses == 0
    assert next_state.registered_callback_anchors[0].current_uses == 1


def test_assembled_text_rejects_direct_deserialized_and_copy_divergence() -> None:
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
    story = DraftStory(
        story_id=1,
        factual_summary="Fapt.",
        commentary_blocks=(block,),
        ending="Final.",
    )
    draft = DraftAssembler().assemble(
        episode_id="episode",
        story_order=(1,),
        opening="Deschidere.",
        stories=(story,),
        transitions=(),
        closing="Închidere.",
        cta=None,
    )
    assert EpisodeDraft.model_validate_json(draft.model_dump_json()) == draft
    injected = draft.model_dump(mode="python") | {
        "assembled_text": "INJECTED-ASSEMBLED-TEXT"
    }
    with pytest.raises(ValidationError, match="assembled_text"):
        EpisodeDraft.model_validate(injected)
    with pytest.raises(ValidationError, match="assembled_text"):
        draft.model_copy(update={"assembled_text": "INJECTED-ASSEMBLED-TEXT"})
    changed = story.model_copy(update={"ending": "Final schimbat."})
    rebuilt = DraftAssembler().assemble(
        episode_id="episode",
        story_order=(1,),
        opening="Deschidere.",
        stories=(changed,),
        transitions=(),
        closing="Închidere.",
        cta=None,
    )
    assert rebuilt.assembled_text != draft.assembled_text


def test_static_cta_is_absent_from_all_provider_data_including_closing_retry() -> None:
    sentinel = "STATIC-CTA-SENTINEL-DO-NOT-SEND"
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
                "text": "Tranziție.",
                "transition_type": "contrast",
                "declared_plan_references": ["transition"],
            },
            {
                "text": "Deschidere.",
                "referenced_story_ids": list(order),
                "opening_mechanism": "fact_first",
                "declared_plan_references": ["opening"],
            },
            {
                "text": "Închidere invalidă.",
                "callback_executions": ["unknown-callback"],
                "closing_mechanism": "reflection",
                "declared_plan_references": ["closing"],
            },
            {
                "text": "Închidere validă.",
                "closing_mechanism": "reflection",
                "declared_plan_references": ["closing"],
            },
            {
                "bridge_text": "Bridge CTA.",
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
        static_cta_content=sentinel,
    )

    assert all(sentinel not in prompt.text for prompt in provider.prompts)
    assert all(
        sentinel not in json.dumps(schema.model_json_schema(), sort_keys=True)
        for schema in provider.schemas
    )
    assert sentinel not in result.final_state.model_dump_json()
    assert result.draft.cta.static_content == sentinel
    assert result.draft.assembled_text.count(sentinel) == 1
    assert result.draft.teleprompter_text.count(sentinel) == 1
    closing_prompts = [
        prompt
        for prompt in provider.prompts
        if prompt.component_type is GenerationComponentType.CLOSING
    ]
    assert len(closing_prompts) == 2
    assert all(sentinel not in prompt.text for prompt in closing_prompts)


def test_disabled_cta_does_not_inject_static_content() -> None:
    # One-story episodes deterministically omit CTA even when local static data exists.
    scout, flow, generic, commentary, voice = voice_pipeline([{"event_id": 1}])
    story_id = commentary.blueprint.flow_order[0]
    provider = ScriptedLanguageModelProvider(
        [
            authored_story_result(story_id, 1),
            {
                "text": "Deschidere.",
                "referenced_story_ids": [story_id],
                "opening_mechanism": "fact",
                "declared_plan_references": ["opening"],
            },
            {
                "text": "Închidere.",
                "closing_mechanism": "reflection",
                "declared_plan_references": ["closing"],
            },
        ]
    )
    result = ControlledGenerator(provider, config=config()).generate(
        scout_input=scout,
        selection_profile=profile_from_pipeline(scout),
        episode_context=context_from_pipeline(scout),
        flow_result=flow,
        editorial_blueprint=generic.blueprint,
        commentary_blueprint=commentary.blueprint,
        voice_plan=voice.plan,
        static_cta_content="STATIC-CTA-SENTINEL-DO-NOT-SEND",
    )
    assert result.draft.cta is None
    assert "STATIC-CTA-SENTINEL-DO-NOT-SEND" not in result.draft.assembled_text
