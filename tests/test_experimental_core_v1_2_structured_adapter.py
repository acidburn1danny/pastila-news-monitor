import json

import pytest

from pastila_scout.editor.generation.models import (
    ClosingGenerationResult,
    GenerationComponentType,
    OpeningGenerationResult,
    TransitionGenerationResult,
)
from pastila_scout.editor.generation.prompt import (
    GenerationPrompt,
    PromptLayer,
    PromptSection,
)
from pastila_scout.experimental_core_v1_2_structured_adapter import (
    adapt_core_v1_2_factual_summary_v2_prose,
    adapt_core_v1_2_non_story_prose,
    adapt_core_v1_2_story_prose,
)


def test_v2_factual_adapter_preserves_complete_prose_byte_for_byte():
    prose = "Prima propoziție factuală. A doua propoziție factuală."

    result = adapt_core_v1_2_factual_summary_v2_prose(prose)

    assert result.text == prose


@pytest.mark.parametrize("invalid", ("", " text", "text "))
def test_v2_factual_adapter_fails_closed_on_unclean_transport_surface(invalid):
    with pytest.raises(ValueError, match="V2 factual prose"):
        adapt_core_v1_2_factual_summary_v2_prose(invalid)


def _prompt() -> GenerationPrompt:
    return GenerationPrompt(
        component_type=GenerationComponentType.STORY,
        sections=(
            PromptSection(
                layer=PromptLayer.APPROVED_FACTS,
                title="Approved facts",
                content=json.dumps(
                    [{"fact_id": "event-1922-title"}, {"fact_id": "event-1922-summary"}],
                    separators=(",", ":"),
                ),
            ),
        ),
        output_schema_name="StoryAuthoredContentResult",
        prompt_fingerprint="sha256:" + "0" * 64,
    )


def test_v1_2_prose_is_adapted_and_preserved_without_invented_text() -> None:
    prose = "Prima propoziție. A doua propoziție explică faptele. Final clar."
    result = adapt_core_v1_2_story_prose(prose, _prompt())

    surfaces = (
        result.factual_summary,
        result.commentary_blocks[0].text,
        result.ending,
    )
    assert " ".join(surfaces) == prose
    assert result.model_validate(result.model_dump(), strict=True) == result
    assert result.declared_fact_usage == (
        "event-1922-title",
        "event-1922-summary",
    )
    assert result.commentary_blocks[0].source_fact_ids == result.declared_fact_usage
    assert result.commentary_blocks[0].block_type == "story"
    assert result.ending_type == "completed"
    assert result.used_callbacks == result.used_humor_mechanisms == ()


def test_v1_2_mapping_is_deterministic() -> None:
    prose = "Un fapt. Încă un fapt. Încheiere."
    assert adapt_core_v1_2_story_prose(prose, _prompt()) == (
        adapt_core_v1_2_story_prose(prose, _prompt())
    )


def test_v1_2_mapping_fails_closed_without_authority_or_enough_prose() -> None:
    prompt = _prompt().model_copy(
        update={
            "sections": (
                PromptSection(
                    layer=PromptLayer.APPROVED_FACTS,
                    title="Approved facts",
                    content="[]",
                ),
            )
        }
    )
    with pytest.raises(ValueError, match="identity mapping"):
        adapt_core_v1_2_story_prose("Un text suficient de lung.", prompt)
    with pytest.raises(ValueError, match="without invention"):
        adapt_core_v1_2_story_prose("Prea scurt", _prompt())


def _component_prompt(component, context, schema) -> GenerationPrompt:
    return GenerationPrompt(
        component_type=component,
        sections=(
            PromptSection(
                layer=PromptLayer.COMPONENT_CONTEXT,
                title="Local context",
                content=json.dumps(context, separators=(",", ":")),
            ),
        ),
        output_schema_name=schema.__name__,
        prompt_fingerprint="sha256:" + "1" * 64,
    )


def test_v1_2_opening_prose_and_metadata_mapping() -> None:
    prompt = _component_prompt(
        GenerationComponentType.OPENING,
        {
            "opening_plan": {"opener_function": "fact_first", "event_id": 1922},
            "accepted_story_ids": [1922, 766],
        },
        OpeningGenerationResult,
    )
    result = adapt_core_v1_2_non_story_prose(
        "Deschidere neutră.", prompt, OpeningGenerationResult
    )
    assert result.text == "Deschidere neutră."
    assert result.referenced_story_ids == (1922, 766)
    assert result.opening_mechanism == "fact_first"
    assert result.declared_plan_references == ("fact_first",)


def test_v1_2_transition_prose_and_endpoint_mapping() -> None:
    prompt = _component_prompt(
        GenerationComponentType.TRANSITION,
        {
            "from_story_id": 1922,
            "to_story_id": 766,
            "transition_plan": {
                "public_transition_type": "continuation",
                "reason_code": "adjacent-events",
            },
        },
        TransitionGenerationResult,
    )
    result = adapt_core_v1_2_non_story_prose(
        "Urmează al doilea subiect.", prompt, TransitionGenerationResult
    )
    assert result.text == "Urmează al doilea subiect."
    assert (result.from_story_id, result.to_story_id) == (1922, 766)
    assert result.transition_type == "continuation"
    assert result.declared_plan_references == ("adjacent-events",)
    assert result.fact_references == ()


def test_v1_2_closing_prose_and_metadata_mapping() -> None:
    prompt = _component_prompt(
        GenerationComponentType.CLOSING,
        {"closing_plan": {"closing_mode": "reflection", "event_id": 1922}},
        ClosingGenerationResult,
    )
    result = adapt_core_v1_2_non_story_prose(
        "Încheiere neutră.", prompt, ClosingGenerationResult
    )
    assert result.text == "Încheiere neutră."
    assert result.closing_mechanism == "reflection"
    assert result.declared_plan_references == ("reflection",)
    assert result.callback_executions == ()


@pytest.mark.parametrize("surface", ("{}", "{ }", "[]", "null", "42", "false"))
def test_v1_2_closing_rejects_structurally_empty_or_non_prose_surface(
    surface: str,
) -> None:
    prompt = _component_prompt(
        GenerationComponentType.CLOSING,
        {"closing_plan": {"closing_mode": "reflection", "event_id": 1922}},
        ClosingGenerationResult,
    )

    with pytest.raises(ValueError, match="structurally empty or non-prose"):
        adapt_core_v1_2_non_story_prose(surface, prompt, ClosingGenerationResult)


@pytest.mark.parametrize(
    "surface",
    (
        "O dronă descoperită în",
        "Încheiere fără punct final",
    ),
)
def test_v1_2_closing_rejects_incomplete_prose_without_finite_endpoint(
    surface: str,
) -> None:
    prompt = _component_prompt(
        GenerationComponentType.CLOSING,
        {"closing_plan": {"closing_mode": "reflection", "event_id": 1866}},
        ClosingGenerationResult,
    )

    with pytest.raises(ValueError, match="no finite sentence endpoint"):
        adapt_core_v1_2_non_story_prose(surface, prompt, ClosingGenerationResult)


@pytest.mark.parametrize(
    "surface",
    (
        "Încheiere neutră!",
        "Rămâne întrebarea: «ce urmează?»",
        "Situația rămâne incertă…",
    ),
)
def test_v1_2_closing_accepts_supported_finite_endpoints(surface: str) -> None:
    prompt = _component_prompt(
        GenerationComponentType.CLOSING,
        {"closing_plan": {"closing_mode": "reflection", "event_id": 1866}},
        ClosingGenerationResult,
    )

    result = adapt_core_v1_2_non_story_prose(surface, prompt, ClosingGenerationResult)

    assert result.text == surface


def test_v1_2_non_story_mapping_fails_closed_for_missing_metadata() -> None:
    prompt = _component_prompt(
        GenerationComponentType.OPENING,
        {"opening_plan": {}, "accepted_story_ids": [1922]},
        OpeningGenerationResult,
    )
    with pytest.raises(ValueError, match="opener_function"):
        adapt_core_v1_2_non_story_prose("Deschidere.", prompt, OpeningGenerationResult)
