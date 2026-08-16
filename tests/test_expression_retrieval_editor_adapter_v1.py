from __future__ import annotations

import ast
from pathlib import Path

import pytest

from pastila_scout.contracts.samples import (
    sample_episode_context,
    sample_scout_input,
    sample_selection_profile,
)
from pastila_scout.editor import SelectionEngine
from pastila_scout.editor.blueprint_builder import EditorialBlueprintBuilder
from pastila_scout.editor.commentary_builder import CommentaryBlueprintBuilder
from pastila_scout.editor.commentary_models import HumorSensitivity, ProtectedTarget
from pastila_scout.editor.engine import EditorialSelectionResult
from pastila_scout.editor.flow_optimizer import EpisodeFlowOptimizer
from pastila_scout.editor.generation.controlled_generator import _story_context
from pastila_scout.editor.generation.models import (
    GenerationComponentType,
    StoryGenerationResult,
)
from pastila_scout.editor.generation.prompt import PromptBuilder
from pastila_scout.editor.generation.state import EpisodeGenerationState
from pastila_scout.editor.voice_builder import VoiceModelBuilder
from pastila_scout.editor.voice_models import HumorIntensity, RoastEligibility
from pastila_scout.editor_operational_v1 import EditorOperationalCoordinatorV1
from pastila_scout.expression_retrieval_v1 import (
    ExpressionCatalogErrorV1,
    StoryVoicePaletteV1,
)
from pastila_scout.expression_retrieval_v1.editor_adapter import (
    build_editorial_retrieval_context_v1,
    build_story_voice_palette_for_editor_v1,
    serialize_story_voice_palette_v1,
)


@pytest.fixture(scope="module")
def editor_story_values():
    source = sample_scout_input()
    profile = sample_selection_profile()
    episode = sample_episode_context()
    preparation = EditorOperationalCoordinatorV1(SelectionEngine()).prepare(
        source, profile, episode
    )
    assert preparation.plan is not None
    selection = EditorialSelectionResult(
        preparation.plan.selection_output, preparation.plan.selection_trace
    )
    flow = EpisodeFlowOptimizer().optimize(source, profile, episode, selection)
    editorial = (
        EditorialBlueprintBuilder().build(source, profile, episode, flow).blueprint
    )
    commentary = (
        CommentaryBlueprintBuilder()
        .build(source, profile, episode, flow, editorial)
        .blueprint
    )
    voice = (
        VoiceModelBuilder()
        .build(source, profile, episode, flow, editorial, commentary)
        .plan
    )
    event_id = flow.output.episode_proposal.episode_flow[0].event_id
    return (
        next(item for item in source.ranked_events if item.event_id == event_id),
        next(item for item in editorial.segments if item.event_id == event_id),
        next(item for item in commentary.stories if item.event_id == event_id),
        next(item for item in voice.stories if item.event_id == event_id),
    )


def test_adapter_maps_reliable_editor_authority(editor_story_values) -> None:
    event, _, commentary, voice = editor_story_values
    context = build_editorial_retrieval_context_v1(
        event=event, episode_position=2, commentary=commentary, voice=voice
    )
    assert context.event_id == str(event.event_id)
    assert context.title == event.canonical_title
    assert context.summary == event.canonical_summary
    assert context.source_count == event.source_count
    assert context.source_ids == tuple(x.source_id for x in event.source_provenance)
    assert context.episode_position == 2
    assert context.political_context is ("Politica" in event.categories)
    assert context.international is ("Externe" in event.categories)
    assert context.entertainment is ("CanCan" in event.categories)
    assert context.protected_dimensions == tuple(
        x.value for x in voice.protected_dimensions
    )


@pytest.mark.parametrize(
    ("title", "category", "attribute"),
    [
        ("Primaria blocheaza un permis la ghiseu", "Social", "bureaucracy"),
        ("O numire acuzata de clientelism", "Politica", "patronage"),
        ("Un santier abandonat ramane neterminat", "Social", "unfinished_project"),
        ("Autoritatile combat fake news", "Diverse", "disinformation"),
        ("Scandalul unei vedete", "CanCan", "entertainment"),
        ("Alegeri si coalitii", "Politica", "political_context"),
        ("Summit international", "Externe", "international"),
    ],
)
def test_adapter_uses_closed_context_triggers(
    editor_story_values, title: str, category: str, attribute: str
) -> None:
    event, _, commentary, voice = editor_story_values
    changed = event.model_copy(
        update={
            "canonical_title": title,
            "canonical_summary": title,
            "categories": (category,),
        }
    )
    context = build_editorial_retrieval_context_v1(
        event=changed, episode_position=1, commentary=commentary, voice=voice
    )
    assert getattr(context, attribute) is True


def test_national_source_does_not_invent_region(editor_story_values) -> None:
    event, _, commentary, voice = editor_story_values
    context = build_editorial_retrieval_context_v1(
        event=event, episode_position=1, commentary=commentary, voice=voice
    )
    assert context.region is None


def test_explicit_ardeal_source_enables_regional_context(editor_story_values) -> None:
    event, _, commentary, voice = editor_story_values
    provenance = event.source_provenance[0].model_copy(
        update={"source_id": "monitorul_cluj", "source_name": "Monitorul de Cluj"}
    )
    changed = event.model_copy(update={"source_provenance": (provenance,)})
    context = build_editorial_retrieval_context_v1(
        event=changed, episode_position=1, commentary=commentary, voice=voice
    )
    assert context.region == "Ardeal"


def test_tragedy_and_victim_authority_suppresses_risky_palette(
    editor_story_values,
) -> None:
    event, _, commentary, voice = editor_story_values
    changed_event = event.model_copy(
        update={
            "canonical_title": "Victime dupa un accident tragic",
            "canonical_summary": "Autoritatile confirma victime si un deces.",
        }
    )
    changed_commentary = commentary.model_copy(
        update={
            "protected_targets": (ProtectedTarget.VICTIMS,),
            "empathy": commentary.empathy.model_copy(
                update={"humor_sensitivity": HumorSensitivity.PROHIBITED}
            ),
        }
    )
    changed_voice = voice.model_copy(
        update={
            "humor_intensity": HumorIntensity.NONE,
            "roast_eligibility": RoastEligibility.PROHIBITED,
        }
    )
    context = build_editorial_retrieval_context_v1(
        event=changed_event,
        episode_position=1,
        commentary=changed_commentary,
        voice=changed_voice,
    )
    palette = build_story_voice_palette_for_editor_v1(
        event=changed_event,
        episode_position=1,
        commentary=changed_commentary,
        voice=changed_voice,
    )
    assert context.victim_sensitive and context.tragedy_sensitive
    assert context.raw_eligible is False
    assert all(
        item.family not in {"roast", "raw"}
        for items in (palette.comedy_devices, palette.signature_devices)
        for item in items
    )


def test_low_comedy_ordinary_story_does_not_gain_context_flags(
    editor_story_values,
) -> None:
    event, _, commentary, voice = editor_story_values
    changed = event.model_copy(
        update={
            "canonical_title": "Programul bibliotecii se modifica luni",
            "canonical_summary": "Biblioteca publica un program nou.",
            "categories": ("Diverse",),
        }
    )
    changed_voice = voice.model_copy(
        update={
            "humor_intensity": HumorIntensity.NONE,
            "roast_eligibility": RoastEligibility.PROHIBITED,
        }
    )
    context = build_editorial_retrieval_context_v1(
        event=changed,
        episode_position=1,
        commentary=commentary,
        voice=changed_voice,
    )
    assert not any(
        (
            context.bureaucracy,
            context.patronage,
            context.unfinished_project,
            context.disinformation,
            context.entertainment,
            context.international,
            context.political_context,
        )
    )


def test_expected_catalog_failure_is_empty_and_sanitized(
    editor_story_values, caplog: pytest.LogCaptureFixture
) -> None:
    event, _, commentary, voice = editor_story_values

    def broken_loader():
        raise ExpressionCatalogErrorV1("private catalog detail")

    palette = build_story_voice_palette_for_editor_v1(
        event=event,
        episode_position=1,
        commentary=commentary,
        voice=voice,
        catalog_loader=broken_loader,
    )
    assert palette == StoryVoicePaletteV1.empty(str(event.event_id))
    assert "expression_palette_unavailable:catalog" in caplog.text
    assert "private catalog detail" not in caplog.text


def test_expected_retrieval_failure_is_empty(
    editor_story_values, monkeypatch: pytest.MonkeyPatch
) -> None:
    event, _, commentary, voice = editor_story_values
    monkeypatch.setattr(
        "pastila_scout.expression_retrieval_v1.editor_adapter.retrieve_story_voice_palette_v1",
        lambda **_: (_ for _ in ()).throw(ValueError("invalid retrieval context")),
    )
    palette = build_story_voice_palette_for_editor_v1(
        event=event, episode_position=1, commentary=commentary, voice=voice
    )
    assert palette.total_count == 0


def test_palette_is_deterministic_bounded_and_compact(editor_story_values) -> None:
    event, _, commentary, voice = editor_story_values
    first = build_story_voice_palette_for_editor_v1(
        event=event, episode_position=1, commentary=commentary, voice=voice
    )
    second = build_story_voice_palette_for_editor_v1(
        event=event, episode_position=1, commentary=commentary, voice=voice
    )
    serialized = serialize_story_voice_palette_v1(first)
    assert first == second
    assert first.total_count <= 5
    assert serialized["usage_instruction"] == {
        "optional": True,
        "may_use_none": True,
        "never_force": True,
        "maximum_comedy_tools": 1,
        "never_chain_tools": True,
        "use_each_offered_tool_at_most_once": True,
        "integrate_naturally_without_introduction_or_quotation": True,
        "controlled_terms_are_optional_contextual_vocabulary": True,
        "unresolved_placeholders_forbidden": True,
        "skip_template_if_it_cannot_be_filled_naturally": True,
        "preserve_facts": True,
        "do_not_invent_attribution": True,
        "do_not_target_victims_or_tragedy": True,
        "respect_voice_plan_limits": True,
    }
    assert "reason" not in repr(serialized)
    assert len(repr(serialized)) < 2500


def test_story_task_contains_palette_and_prompt_fingerprint_covers_it(
    editor_story_values,
) -> None:
    event, editorial, commentary, voice = editor_story_values
    context = _story_context(event, 1, editorial, commentary, voice)
    assert context.optional_editorial_toolkit["usage_instruction"]["optional"] is True
    prompt = PromptBuilder().build(
        component_type=GenerationComponentType.STORY,
        episode_context={"episode": "test"},
        component_context=context,
        state=EpisodeGenerationState(),
        output_schema=StoryGenerationResult,
    )
    changed = context.model_copy(update={"optional_editorial_toolkit": {}})
    changed_prompt = PromptBuilder().build(
        component_type=GenerationComponentType.STORY,
        episode_context={"episode": "test"},
        component_context=changed,
        state=EpisodeGenerationState(),
        output_schema=StoryGenerationResult,
    )
    assert prompt.prompt_fingerprint != changed_prompt.prompt_fingerprint
    assert "optional_editorial_toolkit" in prompt.text


def test_provider_adapter_does_not_import_retrieval_package() -> None:
    root = Path(__file__).parents[1] / "src" / "pastila_scout"
    for path in (root / "editor_generation_provider_adapter_v1").glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports = (
            node.module
            for node in ast.walk(tree)
            if isinstance(node, ast.ImportFrom) and node.module
        )
        assert not any("expression_retrieval_v1" in name for name in imports)
