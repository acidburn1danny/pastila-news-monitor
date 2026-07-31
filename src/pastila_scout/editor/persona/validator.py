"""Semantic validation for editorial persona configuration."""

from __future__ import annotations

import re

from pastila_scout.editor.persona.models import (
    AuthorityKind,
    BoundaryKind,
    EditorialPersona,
    RelationshipKind,
)

_SEMVER = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?"
    r"(?:\+[0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*)?$"
)
_REQUIRED_BOUNDARIES = frozenset(BoundaryKind)
_REQUIRED_PRINCIPLES = frozenset(
    {
        "truth-before-performance",
        "clarity-before-completeness",
        "identify-editorial-core",
        "respect-the-audience",
        "spoken-language-first",
        "attention-is-editorial-responsibility",
        "satire-must-reveal",
        "humor-serves-story",
        "emotional-relevance",
        "explanation-must-earn-place",
        "editorial-selection",
        "pacing-is-meaning",
        "do-not-lecture",
        "responsible-criticism",
        "serious-story-tonal-judgment",
        "editor-in-chief-final-standard",
    }
)
_REQUIRED_TENSIONS = frozenset(
    {
        "clarity-versus-completeness",
        "satire-versus-seriousness",
        "speed-versus-context",
        "emotional-impact-versus-restraint",
        "retention-versus-sensationalism",
        "opinion-versus-factual-fairness",
        "consistency-versus-episode-judgment",
    }
)


class PersonaValidationError(ValueError):
    """Raised when a persona violates its fixed identity or authority contract."""


def validate_persona(persona: EditorialPersona) -> EditorialPersona:
    """Validate stable persona invariants and return the unchanged persona."""

    errors: list[str] = []
    if not _SEMVER.fullmatch(persona.version):
        errors.append("version must be valid semantic versioning")

    philosophy = persona.philosophy
    if philosophy is None:
        errors.append("editorial philosophy is required")
    else:
        if not _SEMVER.fullmatch(philosophy.version):
            errors.append("philosophy version must be valid semantic versioning")
        principle_ids = [item.principle_id for item in philosophy.principles]
        if len(principle_ids) != len(set(principle_ids)):
            errors.append("editorial principle identifiers must be unique")
        missing_principles = _REQUIRED_PRINCIPLES.difference(principle_ids)
        if missing_principles:
            errors.append(
                "required editorial principles are missing: "
                + ", ".join(sorted(missing_principles))
            )
        principle_orders = [item.order for item in philosophy.principles]
        if len(principle_orders) != len(set(principle_orders)):
            errors.append("editorial principle order values must be unique")
        tension_ids = [item.tension_id for item in philosophy.tensions]
        if len(tension_ids) != len(set(tension_ids)):
            errors.append("editorial tension identifiers must be unique")
        missing_tensions = _REQUIRED_TENSIONS.difference(tension_ids)
        if missing_tensions:
            errors.append(
                "required editorial tensions are missing: "
                + ", ".join(sorted(missing_tensions))
            )
        tension_orders = [item.order for item in philosophy.tensions]
        if len(tension_orders) != len(set(tension_orders)):
            errors.append("editorial tension order values must be unique")
        for principle in philosophy.principles:
            if principle.permits_fabrication:
                errors.append(f"{principle.principle_id} permits fabrication")
            if principle.permits_factual_distortion:
                errors.append(f"{principle.principle_id} permits factual distortion")
            if principle.permits_satire_over_factuality:
                errors.append(f"{principle.principle_id} places satire over factuality")
            if principle.requires_absolute_completeness:
                errors.append(
                    f"{principle.principle_id} requires absolute completeness"
                )
            if principle.permits_deceptive_retention:
                errors.append(f"{principle.principle_id} permits deceptive retention")
            if principle.permits_targeting_vulnerable_people:
                errors.append(
                    f"{principle.principle_id} permits targeting vulnerable people"
                )
        for tension in philosophy.tensions:
            if not isinstance(tension.override_authority, AuthorityKind):
                errors.append(f"{tension.tension_id} has invalid override authority")
            if tension.may_override_factual_accuracy:
                errors.append(f"{tension.tension_id} may not override factual accuracy")
        if philosophy.may_be_modified_by_editorial_memory:
            errors.append("Editorial Memory must not automatically modify philosophy")
        if philosophy.may_be_modified_by_editorial_profile:
            errors.append("Editorial Profile must not automatically modify philosophy")
        if philosophy.contains_detailed_generation_instructions:
            errors.append(
                "philosophy must not contain detailed generation instructions"
            )
        if philosophy.contains_fictional_biography:
            errors.append("philosophy must not contain fictional biography")

    levels = persona.authority_hierarchy
    authorities = [level.authority for level in levels]
    if len(authorities) != len(set(authorities)):
        errors.append("authority hierarchy contains duplicate authority levels")
    missing = set(AuthorityKind).difference(authorities)
    if missing:
        errors.append(
            "authority hierarchy is incomplete; missing: "
            + ", ".join(sorted(item.value for item in missing))
        )
    ordered = sorted(levels, key=lambda item: item.rank)
    if ordered and ordered[0].authority != AuthorityKind.EDITOR_IN_CHIEF:
        errors.append("Editor-in-Chief must be the highest authority")
    if ordered and ordered[-1].authority != AuthorityKind.SCOUT_JUDGMENT:
        errors.append("Scout editorial judgment must be the lowest authority")
    ranks = [level.rank for level in levels]
    if len(ranks) != len(set(ranks)) or sorted(ranks) != list(range(1, len(ranks) + 1)):
        errors.append("authority ranks must be unique and contiguous")

    boundaries = {boundary.kind: boundary for boundary in persona.boundaries}
    if len(boundaries) != len(persona.boundaries):
        errors.append("persona boundaries contain duplicates")
    missing_boundaries = _REQUIRED_BOUNDARIES.difference(boundaries)
    if missing_boundaries:
        errors.append(
            "required persona boundaries are missing: "
            + ", ".join(sorted(item.value for item in missing_boundaries))
        )
    for required in (
        BoundaryKind.FINAL_AUTHORITY,
        BoundaryKind.PERSONA_MUTATION,
        BoundaryKind.FACT_FABRICATION,
        BoundaryKind.FACTUAL_DISTORTION,
    ):
        if required in boundaries and not boundaries[required].prohibited:
            errors.append(f"persona must prohibit {required.value}")

    relationships = (
        (
            persona.editor_in_chief_relationship,
            RelationshipKind.EDITOR_IN_CHIEF,
            "editor_in_chief_relationship",
        ),
        (
            persona.editorial_memory_relationship,
            RelationshipKind.EDITORIAL_MEMORY,
            "editorial_memory_relationship",
        ),
        (
            persona.editorial_profile_relationship,
            RelationshipKind.EDITORIAL_PROFILE,
            "editorial_profile_relationship",
        ),
    )
    for relationship, expected, field_name in relationships:
        if relationship.kind != expected:
            errors.append(f"{field_name} must use relationship kind {expected.value}")
    if not persona.editor_in_chief_relationship.may_override_scout:
        errors.append("Editor-in-Chief relationship must permit overriding Scout")
    if persona.editor_in_chief_relationship.scout_has_final_authority:
        errors.append("Persona must not claim final editorial authority")
    if persona.editorial_memory_relationship.may_modify_base_persona:
        errors.append("Editorial Memory must not automatically modify the base Persona")
    if persona.editorial_profile_relationship.may_modify_base_persona:
        errors.append("Editorial Profile must not modify the base Persona")
    if not (
        persona.editorial_profile_relationship.guidance_requires_established_profile_finding
    ):
        errors.append("Editorial Profile guidance must require established findings")
    if not persona.mission.factual_fidelity_required:
        errors.append("Persona mission must require factual fidelity")

    if errors:
        raise PersonaValidationError("; ".join(errors))
    return persona
