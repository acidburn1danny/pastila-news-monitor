"""Contract, validation, rendering, and boundary tests for Module 2.1."""

from __future__ import annotations

from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest
from pydantic import ValidationError

from pastila_scout.editor.persona import (
    DEFAULT_EDITORIAL_PERSONA,
    PersonaValidationError,
    default_editorial_persona,
    persona_fingerprint,
    render_persona,
    validate_persona,
)
from pastila_scout.editor.persona.models import (
    AuthorityKind,
    BoundaryKind,
    RelationshipKind,
)


def test_canonical_default_persona_validates():
    assert validate_persona(DEFAULT_EDITORIAL_PERSONA) is DEFAULT_EDITORIAL_PERSONA
    assert default_editorial_persona() == DEFAULT_EDITORIAL_PERSONA


def test_persona_models_are_immutable():
    with pytest.raises((ValidationError, FrozenInstanceError)):
        DEFAULT_EDITORIAL_PERSONA.title = "Changed"  # type: ignore[misc]


def test_canonical_rendering_is_byte_deterministic():
    assert render_persona(DEFAULT_EDITORIAL_PERSONA).encode("utf-8") == render_persona(
        default_editorial_persona()
    ).encode("utf-8")


def test_fingerprint_is_deterministic():
    first = persona_fingerprint(DEFAULT_EDITORIAL_PERSONA)
    second = persona_fingerprint(default_editorial_persona())

    assert first == second
    assert len(first) == 64


def test_meaningful_change_alters_fingerprint():
    changed = DEFAULT_EDITORIAL_PERSONA.model_copy(update={"project": "Alt proiect"})

    assert persona_fingerprint(changed) != persona_fingerprint(
        DEFAULT_EDITORIAL_PERSONA
    )


def test_collection_order_does_not_alter_semantic_fingerprint():
    persona = DEFAULT_EDITORIAL_PERSONA
    changed = persona.model_copy(
        update={
            "responsibilities": tuple(reversed(persona.responsibilities)),
            "boundaries": tuple(reversed(persona.boundaries)),
            "identity": persona.identity.model_copy(
                update={"capabilities": tuple(reversed(persona.identity.capabilities))}
            ),
        }
    )

    assert persona_fingerprint(changed) == persona_fingerprint(persona)


def test_invalid_semantic_version_is_rejected():
    changed = DEFAULT_EDITORIAL_PERSONA.model_copy(update={"version": "version-one"})

    with pytest.raises(PersonaValidationError, match="semantic versioning"):
        validate_persona(changed)


def test_missing_editor_in_chief_authority_is_rejected():
    changed = DEFAULT_EDITORIAL_PERSONA.model_copy(
        update={
            "authority_hierarchy": tuple(
                item
                for item in DEFAULT_EDITORIAL_PERSONA.authority_hierarchy
                if item.authority != AuthorityKind.EDITOR_IN_CHIEF
            )
        }
    )

    with pytest.raises(PersonaValidationError, match="missing: Editor-in-Chief"):
        validate_persona(changed)


def test_editor_in_chief_not_ranked_first_is_rejected():
    levels = list(DEFAULT_EDITORIAL_PERSONA.authority_hierarchy)
    levels[0] = levels[0].model_copy(update={"rank": 2})
    levels[1] = levels[1].model_copy(update={"rank": 1})
    changed = DEFAULT_EDITORIAL_PERSONA.model_copy(
        update={"authority_hierarchy": tuple(levels)}
    )

    with pytest.raises(PersonaValidationError, match="highest authority"):
        validate_persona(changed)


def test_duplicate_authority_levels_are_rejected():
    levels = DEFAULT_EDITORIAL_PERSONA.authority_hierarchy
    changed = DEFAULT_EDITORIAL_PERSONA.model_copy(
        update={
            "authority_hierarchy": (*levels, levels[-1].model_copy(update={"rank": 7}))
        }
    )

    with pytest.raises(PersonaValidationError, match="duplicate authority levels"):
        validate_persona(changed)


def test_persona_claiming_final_authority_is_rejected():
    relationship = DEFAULT_EDITORIAL_PERSONA.editor_in_chief_relationship.model_copy(
        update={"scout_has_final_authority": True}
    )
    changed = DEFAULT_EDITORIAL_PERSONA.model_copy(
        update={"editor_in_chief_relationship": relationship}
    )

    with pytest.raises(PersonaValidationError, match="final editorial authority"):
        validate_persona(changed)


def test_automatic_mutation_by_editorial_memory_is_rejected():
    relationship = DEFAULT_EDITORIAL_PERSONA.editorial_memory_relationship.model_copy(
        update={"may_modify_base_persona": True}
    )
    changed = DEFAULT_EDITORIAL_PERSONA.model_copy(
        update={"editorial_memory_relationship": relationship}
    )

    with pytest.raises(PersonaValidationError, match="must not automatically modify"):
        validate_persona(changed)


def test_permission_to_fabricate_facts_is_rejected():
    boundaries = tuple(
        (
            boundary.model_copy(update={"prohibited": False})
            if boundary.kind == BoundaryKind.FACT_FABRICATION
            else boundary
        )
        for boundary in DEFAULT_EDITORIAL_PERSONA.boundaries
    )
    changed = DEFAULT_EDITORIAL_PERSONA.model_copy(update={"boundaries": boundaries})

    with pytest.raises(PersonaValidationError, match="fact_fabrication"):
        validate_persona(changed)


def test_required_boundaries_are_present():
    kinds = {item.kind for item in DEFAULT_EDITORIAL_PERSONA.boundaries}

    assert kinds == set(BoundaryKind)


def test_required_relationships_are_present_and_typed():
    persona = DEFAULT_EDITORIAL_PERSONA

    assert persona.editor_in_chief_relationship.kind == RelationshipKind.EDITOR_IN_CHIEF
    assert (
        persona.editorial_memory_relationship.kind == RelationshipKind.EDITORIAL_MEMORY
    )
    assert (
        persona.editorial_profile_relationship.kind
        == RelationshipKind.EDITORIAL_PROFILE
    )


def test_renderer_contains_every_required_section():
    rendered = render_persona(DEFAULT_EDITORIAL_PERSONA)

    for section in (
        "Identity",
        "Mission",
        "Authority",
        "Responsibilities",
        "Boundaries",
        "Relationship with Editor-in-Chief",
        "Relationship with Editorial Memory",
        "Relationship with Editorial Profile",
    ):
        assert f"\n{section}\n" in rendered
    assert "Pastila Acidă" in rendered


def test_renderer_excludes_later_module_style_instructions():
    rendered = render_persona(DEFAULT_EDITORIAL_PERSONA).casefold()

    for excluded in (
        "audience persona",
        "satire mechanics",
        "joke template",
        "episode generation procedure",
        "temperature",
    ):
        assert excluded not in rendered


def test_persona_package_has_no_forbidden_runtime_dependencies():
    root = Path("src/pastila_scout/editor/persona")
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(root.glob("*.py"))
    ).casefold()

    for forbidden_import in (
        "import httpx",
        "import openai",
        "pastila_scout.ai",
        "pastila_scout.cli",
        "pastila_scout.editor.generation",
        "pastila_scout.database",
        "path.write_text",
    ):
        assert forbidden_import not in source
