"""Deterministic non-generative Satirical Voice renderers."""

from __future__ import annotations

from collections.abc import Iterable

from pastila_scout.editor.decision.models import EditorialDecisionPlan
from pastila_scout.editor.persona import DEFAULT_EDITORIAL_PERSONA, EditorialPersona
from pastila_scout.editor.voice.models import (
    SatiricalOpportunity,
    SatiricalRisk,
    SatiricalVoice,
    SatiricalVoiceCalibration,
)
from pastila_scout.editor.voice.validator import (
    validate_satirical_opportunity,
    validate_satirical_voice,
)


def _bullets(values: Iterable[str]) -> list[str]:
    return [f"- {value}" for value in sorted(values)]


def render_satirical_voice(voice: SatiricalVoice) -> str:
    validate_satirical_voice(voice)
    lines = [
        "[Satirical Voice]",
        "",
        "Voice Identity",
        f"Voice ID: {voice.voice_id}",
        f"Version: {voice.version}",
        f"Title: {voice.title}",
        f"Project: {voice.project}",
        f"Jurisdiction: {voice.jurisdiction}",
        "",
        "Purpose",
        voice.purpose,
        "",
        "Voice Characteristics",
        *_bullets(voice.characteristics),
        "",
        "Canonical Principles",
    ]
    for item in sorted(voice.principles, key=lambda x: x.order):
        lines.extend((f"{item.order}. {item.title}", item.statement))
    lines.extend(("", "Satirical Mechanisms"))
    for item in sorted(voice.mechanisms, key=lambda x: x.order):
        lines.extend(
            (
                f"{item.order}. {item.title} ({item.mechanism_id.value})",
                f"   Definition: {item.definition}",
                f"   Uses: {'; '.join(sorted(item.appropriate_uses))}",
                f"   Risks: {'; '.join(sorted(item.misuse_risks))}",
                f"   Factual prerequisites: {'; '.join(sorted(item.factual_prerequisites))}",
                f"   Tonal constraints: {'; '.join(sorted(item.tonal_constraints))}",
            )
        )
    dimensions = voice.calibration.dimensions
    lines.extend(
        (
            "",
            "Valid Targets",
            *_bullets(item.value for item in voice.calibration.valid_targets),
            "",
            "Protected and Sensitive Subjects",
            *_bullets(item.value for item in voice.calibration.protected_subjects),
            "",
            "Default Voice Dimensions",
            f"Sarcasm intensity: {dimensions.sarcasm_intensity.value}",
            f"Emotional temperature: {dimensions.emotional_temperature.value}",
            f"Conversational proximity: {dimensions.conversational_proximity.value}",
            f"Humor density: {dimensions.humor_density.value}",
            f"Tonal seriousness: {dimensions.tonal_seriousness.value}",
            "",
            "Fixed Boundaries",
            *_bullets(voice.fixed_boundaries),
            "",
            "Relationship with Editorial Profile",
            "Established profile guidance may tune dimensions but cannot alter fixed boundaries.",
            "",
            "Editor-in-Chief Authority",
            "The Editor-in-Chief may override contextual defaults, never factuality boundaries.",
        )
    )
    return "\n".join(lines) + "\n"


def render_calibration(calibration: SatiricalVoiceCalibration) -> str:
    dimensions = calibration.dimensions
    lines = [
        "[Satirical Voice Calibration]",
        f"Sarcasm: {dimensions.sarcasm_intensity.value}",
        f"Emotion: {dimensions.emotional_temperature.value}",
        f"Proximity: {dimensions.conversational_proximity.value}",
        f"Humor density: {dimensions.humor_density.value}",
        f"Seriousness: {dimensions.tonal_seriousness.value}",
        "Allowed mechanisms:",
        *_bullets(item.value for item in calibration.allowed_mechanisms),
        "Valid targets:",
        *_bullets(item.value for item in calibration.valid_targets),
        "Protected subjects:",
        *_bullets(item.value for item in calibration.protected_subjects),
    ]
    return "\n".join(lines) + "\n"


def render_opportunity(
    opportunity: SatiricalOpportunity,
    plan: EditorialDecisionPlan,
    voice: SatiricalVoice,
    risks: tuple[SatiricalRisk, ...] = (),
    persona: EditorialPersona = DEFAULT_EDITORIAL_PERSONA,
) -> str:
    validate_satirical_opportunity(opportunity, plan, voice, risks, persona)
    material = {item.material_id: item for item in plan.source_material}
    lines = [
        "[Satirical Opportunity Assessment]",
        "",
        "Opportunity Identity",
        opportunity.opportunity_id,
        "",
        "Evidence",
        *[
            f"- {item}: {material[item].content}"
            for item in sorted(opportunity.supported_material_ids)
        ],
        "",
        "Target",
        f"{opportunity.target_type.value}: {opportunity.target_description}",
        "",
        "Editorial Function",
        opportunity.intended_editorial_function,
        "",
        "Supported Mechanisms",
        *_bullets(item.value for item in opportunity.supported_mechanisms),
        "",
        "Tonal Limits",
        opportunity.tonal_limit.value,
        "",
        "Sensitivity",
        opportunity.sensitivity.value if opportunity.sensitivity else "None",
        "",
        "Risks",
        *_bullets(item.risk_type.value for item in risks),
        "",
        "Confidence",
        opportunity.confidence.value,
        "",
        "Editor-in-Chief Review",
        "Required" if opportunity.requires_editor_in_chief_review else "Not required",
    ]
    return "\n".join(lines) + "\n"
