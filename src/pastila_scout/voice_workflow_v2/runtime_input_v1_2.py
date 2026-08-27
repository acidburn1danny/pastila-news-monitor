"""Versioned, model-visible Voice task contract.

V1.2 keeps the immutable factual inputs required by Voice V1.1 but removes the
ambiguous article-continuation framing. It is provider-template independent.
"""

from __future__ import annotations

import hashlib
import json
import re
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

VOICE_RUNTIME_INPUT_SCHEMA_V1_2 = "PASTILAACIDA_VOICE_RUNTIME_INPUT_V1_2"
VOICE_ABSTAIN_TOKEN_V1_2 = "<VOICE_ABSTAIN>"

_SYSTEM_INSTRUCTION_V1_2 = """Rol unic: produci numai textul AcidCommentaryV2 pentru o știre deja redactată factual.

Rezumatul și autoritățile din mesajul următor sunt date de referință, nu începutul unui articol. Nu le rezuma, nu le continua, nu le reformula și nu le repeta ca introducere. FactualSummaryV2 rămâne neschimbat în altă componentă.

Scrie o reacție editorială satirică la cel mult un aspect deja susținut. Nu afirma și nu sugera motive, cauze, actori, mecanisme, reacții, consecințe, cronologii, entități, numere sau statuturi care nu sunt furnizate. Păstrează exact incertitudinea, acuzațiile și limitele cauzale.

Poți inventa numai într-o analogie, comparație, scenetă sau replică imaginară marcată fără echivoc ca nefactuală. Construcția inventată nu poate explica evenimentul real.

Dacă nu poți scrie un comentariu sigur fără să adaugi ori să modifici fapte, răspunde exact <VOICE_ABSTAIN>.

Ieșirea permisă: fie comentariul și nimic altceva, fie <VOICE_ABSTAIN>. Fără titlu, etichetă, rezumat factual, lead jurnalistic, JSON, explicații despre reguli ori concluzie generică. Încheie la poantă."""


class _FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class VoiceRuntimeInputV1_2(_FrozenModel):
    """Semantic Voice input; identities and governance remain outside rendering."""

    schema_name: Literal["PASTILAACIDA_VOICE_RUNTIME_INPUT_V1_2"] = (
        VOICE_RUNTIME_INPUT_SCHEMA_V1_2
    )
    factual_summary: str = Field(min_length=1)
    event_authority: tuple[str, ...] = Field(min_length=1)
    commentary_background_authority: tuple[str, ...] = ()
    editorial_intent: str = Field(min_length=1)
    neighboring_story_context: tuple[str, ...] = ()

    @field_validator("factual_summary", "editorial_intent")
    @classmethod
    def reject_blank_scalar(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Voice runtime input contains blank text")
        return value

    @field_validator(
        "event_authority",
        "commentary_background_authority",
        "neighboring_story_context",
    )
    @classmethod
    def reject_blank_segments(cls, value: tuple[str, ...]) -> tuple[str, ...]:
        if any(not segment.strip() for segment in value):
            raise ValueError("Voice runtime input contains a blank segment")
        return value


class VoiceRenderedMessagesV1_2(_FrozenModel):
    schema_name: Literal["PASTILAACIDA_VOICE_RENDERED_MESSAGES_V1_2"] = (
        "PASTILAACIDA_VOICE_RENDERED_MESSAGES_V1_2"
    )
    messages: tuple[dict[str, str], dict[str, str]]
    semantic_identity: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")


class VoiceOutputDispositionV1_2(StrEnum):
    COMMENTARY = "commentary"
    ABSTAINED = "abstained"
    INVALID = "invalid"


class VoiceOutputBoundaryResultV1_2(_FrozenModel):
    disposition: VoiceOutputDispositionV1_2
    commentary_text: str | None = None
    safe_failure_code: str | None = None


def _identity(value: VoiceRuntimeInputV1_2) -> str:
    payload = json.dumps(
        value.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return f"sha256:{hashlib.sha256(payload).hexdigest()}"


def _segments(title: str, values: tuple[str, ...]) -> str:
    if not values:
        return f"<{title} absent=\"true\" />"
    body = "\n".join(f"- {value}" for value in values)
    return f"<{title}>\n{body}\n</{title}>"


def render_voice_runtime_input_v1_2(
    value: VoiceRuntimeInputV1_2,
) -> VoiceRenderedMessagesV1_2:
    """Render references first and put the output contract at the recency edge."""

    user = "\n\n".join(
        (
            (
                "<accepted_factual_summary immutable=\"true\" "
                "reference_only=\"true\">\n"
                f"{value.factual_summary}\n"
                "</accepted_factual_summary>"
            ),
            _segments("event_authority", value.event_authority),
            _segments(
                "commentary_background_authority",
                value.commentary_background_authority,
            ),
            _segments("neighboring_story_context", value.neighboring_story_context),
            (
                "<editorial_intent>\n"
                f"{value.editorial_intent}\n"
                "</editorial_intent>"
            ),
            (
                "<output_contract>\n"
                "Produce numai AcidCommentaryV2. Nu începe prin a relata faptele. "
                "Nu repeta rezumatul. Alege comentariul sigur sau răspunde exact "
                f"{VOICE_ABSTAIN_TOKEN_V1_2}.\n"
                "</output_contract>"
            ),
        )
    )
    return VoiceRenderedMessagesV1_2(
        messages=(
            {"role": "system", "content": _SYSTEM_INSTRUCTION_V1_2},
            {"role": "user", "content": user},
        ),
        semantic_identity=_identity(value),
    )


def validate_voice_output_boundary_v1_2(
    output: str,
    *,
    factual_summary: str,
) -> VoiceOutputBoundaryResultV1_2:
    """Validate task shape only; factual validation remains a separate hard gate."""

    if output == VOICE_ABSTAIN_TOKEN_V1_2:
        return VoiceOutputBoundaryResultV1_2(
            disposition=VoiceOutputDispositionV1_2.ABSTAINED
        )
    if VOICE_ABSTAIN_TOKEN_V1_2 in output:
        return VoiceOutputBoundaryResultV1_2(
            disposition=VoiceOutputDispositionV1_2.INVALID,
            safe_failure_code="voice_abstention_not_exact",
        )
    if not output.strip():
        return VoiceOutputBoundaryResultV1_2(
            disposition=VoiceOutputDispositionV1_2.INVALID,
            safe_failure_code="voice_output_empty",
        )
    stripped = output.lstrip()
    wrapper_surface = stripped.lstrip("*# ").casefold()
    if stripped.startswith(("{", "[")) or wrapper_surface.startswith(
        ("comentariu acid:", "acidcommentaryv2")
    ):
        return VoiceOutputBoundaryResultV1_2(
            disposition=VoiceOutputDispositionV1_2.INVALID,
            safe_failure_code="voice_output_contains_wrapper",
        )
    normalize = lambda text: re.sub(r"\s+", " ", text).strip().casefold()
    summary = normalize(factual_summary)
    if summary and summary in normalize(output):
        return VoiceOutputBoundaryResultV1_2(
            disposition=VoiceOutputDispositionV1_2.INVALID,
            safe_failure_code="voice_output_repeats_factual_summary",
        )
    return VoiceOutputBoundaryResultV1_2(
        disposition=VoiceOutputDispositionV1_2.COMMENTARY,
        commentary_text=output,
    )


__all__ = [
    "VOICE_ABSTAIN_TOKEN_V1_2",
    "VOICE_RUNTIME_INPUT_SCHEMA_V1_2",
    "VoiceOutputBoundaryResultV1_2",
    "VoiceOutputDispositionV1_2",
    "VoiceRenderedMessagesV1_2",
    "VoiceRuntimeInputV1_2",
    "render_voice_runtime_input_v1_2",
    "validate_voice_output_boundary_v1_2",
]
