from __future__ import annotations

import pytest
from test_controlled_generation import authored_story_result, context_from_pipeline, profile_from_pipeline
from test_voice_model import voice_pipeline

from pastila_scout.editor.generation import ControlledGenerationError, ControlledGenerator, CoreOnlyV2Generator, GenerationComponentType, ScriptedLanguageModelProvider
from pastila_scout.editor.generation.models import GenerationPolicy, LanguageGenerationConfig
from pastila_scout.editor.generation.semantic_draft_v2 import ControlledSemanticGenerationResultV2, PastilaEditorSemanticDraftV2, SemanticDraftModeV2
from pastila_scout.editor_core_identities_v1 import CORE_V1_2_MODEL_ID


def _config(model_identifier=CORE_V1_2_MODEL_ID):
    return LanguageGenerationConfig(provider="scripted", model_identifier=model_identifier)


def _inputs(count):
    scout, flow, generic, commentary, voice = voice_pipeline([{"event_id": index} for index in range(1, count + 1)])
    return {"scout_input": scout, "selection_profile": profile_from_pipeline(scout), "episode_context": context_from_pipeline(scout), "flow_result": flow, "editorial_blueprint": generic.blueprint, "commentary_blueprint": commentary.blueprint, "voice_plan": voice.plan}


def _commentary():
    return {"text": "Ce spectacol administrativ: absurdul pare să aibă program fix."}


def test_active_core_v1_2_projects_immutable_fact_and_calls_model_only_for_commentary():
    inputs = _inputs(1)
    event = inputs["scout_input"].ranked_events[0]
    provider = ScriptedLanguageModelProvider([_commentary()])
    result = ControlledGenerator(provider, config=_config()).generate(**inputs)

    assert type(result) is ControlledSemanticGenerationResultV2
    assert type(result.draft) is PastilaEditorSemanticDraftV2
    assert result.draft.mode is SemanticDraftModeV2.CORE_PLUS_VOICE
    assert provider.call_order == [GenerationComponentType.STORY]
    story = result.draft.stories[0]
    assert story.factual_summary.text == event.canonical_summary
    assert story.factual_summary.authoring_owner == "governed_scout_projection_v1"
    assert story.factual_summary.provider == "none"
    assert story.acid_commentary is not None
    assert story.acid_commentary.text == _commentary()["text"]
    assert story.acid_commentary.execution_provenance.backend_kind == "model"
    assert result.draft.intro is None
    assert result.draft.final_monologue is None
    assert result.draft.transitions == ()


def test_multiple_stories_make_one_commentary_call_each_and_no_transition_call():
    inputs = _inputs(2)
    provider = ScriptedLanguageModelProvider([_commentary(), _commentary()])
    result = CoreOnlyV2Generator(provider, config=_config()).generate(**inputs)

    assert provider.call_order == [GenerationComponentType.STORY, GenerationComponentType.STORY]
    assert result.draft.transitions == ()
    assert tuple(item.factual_summary.text for item in result.draft.stories) == tuple(item.canonical_summary for item in inputs["scout_input"].ranked_events)


@pytest.mark.parametrize("invalid", ("Autoritatea a confirmat 12 cazuri.", "Rezumatul confirmat descrie exact evenimentul principal.", "Potrivit sursei, situația a fost confirmată."))
def test_commentary_with_factual_claim_surface_or_paraphrase_fails_closed(invalid):
    inputs = _inputs(1)
    provider = ScriptedLanguageModelProvider([{"text": invalid}])
    policy = GenerationPolicy(max_attempts_per_component=1, minimal_safe_enabled=False)
    with pytest.raises(ControlledGenerationError, match="nonfactual commentary"):
        CoreOnlyV2Generator(provider, config=_config(), policy=policy).generate(**inputs)


def test_non_v1_2_controlled_generation_keeps_historical_v1_behavior():
    inputs = _inputs(1)
    event_id = inputs["commentary_blueprint"].flow_order[0]
    provider = ScriptedLanguageModelProvider([authored_story_result(event_id, 1), {"text": "Deschidere istorică.", "referenced_story_ids": [event_id], "opening_mechanism": "fact_first", "declared_plan_references": ["opening"]}, {"text": "Închidere istorică.", "closing_mechanism": "reflection", "declared_plan_references": ["closing"]}])
    result = ControlledGenerator(provider, config=_config("historical-v1-model")).generate(**inputs)
    assert provider.call_order == [GenerationComponentType.STORY, GenerationComponentType.OPENING, GenerationComponentType.CLOSING]
    assert result.draft.opening == "Deschidere istorică."
    assert result.draft.closing == "Închidere istorică."
