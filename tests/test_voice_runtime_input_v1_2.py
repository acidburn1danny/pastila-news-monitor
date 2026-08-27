from __future__ import annotations

import pytest
from pydantic import ValidationError

from pastila_scout.voice_workflow_v2 import (
    VOICE_ABSTAIN_TOKEN_V1_2,
    VoiceOutputDispositionV1_2,
    VoiceRuntimeInputV1_2,
    render_voice_runtime_input_v1_2,
    validate_voice_output_boundary_v1_2,
)


def _runtime_input() -> VoiceRuntimeInputV1_2:
    return VoiceRuntimeInputV1_2(
        factual_summary="Fapt acceptat, cu statut încă incert.",
        event_authority=("Sursa confirmă faptul și păstrează incertitudinea.",),
        commentary_background_authority=("Instituția de fundal există.",),
        editorial_intent="Reacție satirică scurtă despre contrastul deja susținut.",
    )


def test_v1_2_rendering_separates_reference_data_from_output_contract() -> None:
    rendered = render_voice_runtime_input_v1_2(_runtime_input())

    assert tuple(message["role"] for message in rendered.messages) == (
        "system",
        "user",
    )
    system = rendered.messages[0]["content"]
    user = rendered.messages[1]["content"]
    assert "nu începutul unui articol" in system
    assert "Nu le rezuma, nu le continua" in system
    assert VOICE_ABSTAIN_TOKEN_V1_2 in system
    assert user.endswith("</output_contract>")
    assert "Comentează acid faptele acceptate fără să adaugi fapte" not in user
    assert "Fapt acceptat, cu statut încă incert." in user
    assert rendered.semantic_identity.startswith("sha256:")


def test_v1_2_rendering_is_deterministic_and_metadata_free() -> None:
    first = render_voice_runtime_input_v1_2(_runtime_input())
    second = render_voice_runtime_input_v1_2(_runtime_input())

    assert first == second
    visible = "\n".join(message["content"] for message in first.messages)
    assert "sha256:" not in visible
    assert "fact_id" not in visible
    assert "TRACE" not in visible


def test_v1_2_rejects_blank_authority_segments() -> None:
    with pytest.raises(ValidationError):
        VoiceRuntimeInputV1_2(
            factual_summary="Fapt.",
            event_authority=("",),
            editorial_intent="Comentariu sigur.",
        )


def test_v1_2_output_boundary_accepts_commentary_byte_exact() -> None:
    text = "Parcă realitatea și-a uitat parola."
    result = validate_voice_output_boundary_v1_2(
        text,
        factual_summary="Un sistem a fost trecut offline.",
    )

    assert result.disposition is VoiceOutputDispositionV1_2.COMMENTARY
    assert result.commentary_text == text


def test_v1_2_output_boundary_supports_fail_closed_abstention() -> None:
    result = validate_voice_output_boundary_v1_2(
        VOICE_ABSTAIN_TOKEN_V1_2,
        factual_summary="Fapt.",
    )

    assert result.disposition is VoiceOutputDispositionV1_2.ABSTAINED
    assert result.commentary_text is None


@pytest.mark.parametrize(
    ("output", "failure"),
    (
        ("", "voice_output_empty"),
        ("Comentariu acid: ceva", "voice_output_contains_wrapper"),
        ('{"commentary":"ceva"}', "voice_output_contains_wrapper"),
        (
            "<VOICE_ABSTAIN>\nExplicație suplimentară.",
            "voice_abstention_not_exact",
        ),
        ("**AcidCommentaryV2**\nText", "voice_output_contains_wrapper"),
        (
            "Un sistem a fost trecut offline. Altă frază.",
            "voice_output_repeats_factual_summary",
        ),
    ),
)
def test_v1_2_output_boundary_rejects_continuation_shapes(
    output: str,
    failure: str,
) -> None:
    result = validate_voice_output_boundary_v1_2(
        output,
        factual_summary="Un sistem a fost trecut offline.",
    )

    assert result.disposition is VoiceOutputDispositionV1_2.INVALID
    assert result.safe_failure_code == failure
