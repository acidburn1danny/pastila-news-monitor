"""Immutable resolved Pastila Acidă GenerationProfile fixture."""

from .canonical import semantic_fingerprint
from .models import GenerationProfile


def _build_reference_profile() -> GenerationProfile:
    values = {
        "generation_profile_id": "pastila-acida-baseline-generation-profile",
        "profile_version": "1.0.0",
        "profile_name_reference": "profile-name:pastila-acida-baseline",
        "profile_purpose_reference": "profile-purpose:spoken-satirical-editorial",
        "preset_identity": "satirical_commentary",
        "language": "ro",
        "spoken_language_mode": "conversational",
        "teleprompter_mode": "performance",
        "verbosity_profile": "moderate",
        "sentence_complexity": "low_to_medium",
        "sentence_length_target": "short",
        "paragraph_length_target": "short",
        "paragraph_density": "low",
        "delivery_pacing": "conversational",
        "delivery_speed_target": "moderate",
        "humor_density": "moderate",
        "sarcasm_density": "high",
        "irony_density": "high",
        "rhetorical_question_density": "moderate",
        "analogy_density": "moderate",
        "callback_density": "moderate",
        "transition_density": "moderate",
        "emotional_intensity": "moderate",
        "editorial_aggressiveness": "medium_high",
        "formality": "low",
        "colloquialism_level": "moderate",
        "vocabulary_accessibility": "general_public",
        "assumed_knowledge_level": "general",
        "claim_density": "high",
        "quotation_density": "low",
        "repetition_tolerance": "low",
        "preferred_opening_style": "conversational_hook",
        "preferred_closing_style": "reflective_punchline",
        "allowed_sentence_pattern_references": (
            "sentence-pattern:spoken-contrast",
            "sentence-pattern:short-rhetorical-question",
        ),
        "prohibited_sentence_pattern_references": (
            "sentence-pattern:bureaucratic-overload",
            "sentence-pattern:unsupported-accusation",
        ),
        "style_constraint_references": (
            "style-constraint:preserve-romanian-diacritics",
            "style-constraint:preserve-factual-qualifiers",
        ),
        "audience_model_reference": "audience-model:pastila-acida-general",
        "voice_reference": "editorial-voice:pastila-acida",
        "spoken_communication_reference": "spoken-communication:pastila-acida",
        "romanian_conversational_reference": "romanian-conversational:pastila-acida",
        "authority_references": ("editorial-authority:pastila-acida",),
        "profile_fingerprint": "0" * 64,
    }
    profile = GenerationProfile(**values)
    return profile.model_copy(
        update={"profile_fingerprint": semantic_fingerprint(profile)}
    )


PASTILA_ACIDA_GENERATION_PROFILE = _build_reference_profile()

__all__ = ("PASTILA_ACIDA_GENERATION_PROFILE",)
