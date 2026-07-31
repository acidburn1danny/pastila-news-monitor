"""Focused validation tests for the stable Module 2.2 philosophy."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from pastila_scout.editor.persona import (
    DEFAULT_EDITORIAL_PERSONA,
    EditorialPrinciple,
    PersonaValidationError,
    persona_fingerprint,
    render_persona,
    validate_persona,
)

REQUIRED_PRINCIPLES = {
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
REQUIRED_TENSIONS = {
    "clarity-versus-completeness",
    "satire-versus-seriousness",
    "speed-versus-context",
    "emotional-impact-versus-restraint",
    "retention-versus-sensationalism",
    "opinion-versus-factual-fairness",
    "consistency-versus-episode-judgment",
}


def _philosophy():
    assert DEFAULT_EDITORIAL_PERSONA.philosophy is not None
    return DEFAULT_EDITORIAL_PERSONA.philosophy


def _replace_principle(principle_id: str, **changes):
    philosophy = _philosophy()
    principles = tuple(
        item.model_copy(update=changes) if item.principle_id == principle_id else item
        for item in philosophy.principles
    )
    return DEFAULT_EDITORIAL_PERSONA.model_copy(
        update={"philosophy": philosophy.model_copy(update={"principles": principles})}
    )


def _replace_tension(tension_id: str, **changes):
    philosophy = _philosophy()
    tensions = tuple(
        item.model_copy(update=changes) if item.tension_id == tension_id else item
        for item in philosophy.tensions
    )
    return DEFAULT_EDITORIAL_PERSONA.model_copy(
        update={"philosophy": philosophy.model_copy(update={"tensions": tensions})}
    )


def test_canonical_philosophy_validates():
    assert validate_persona(DEFAULT_EDITORIAL_PERSONA) is DEFAULT_EDITORIAL_PERSONA


def test_philosophy_models_are_immutable():
    with pytest.raises(ValidationError):
        _philosophy().version = "2.0.0"  # type: ignore[misc]


def test_all_required_principles_exist():
    assert {
        item.principle_id for item in _philosophy().principles
    } == REQUIRED_PRINCIPLES


def test_all_required_tensions_exist():
    assert {item.tension_id for item in _philosophy().tensions} == REQUIRED_TENSIONS


def test_principle_identifiers_are_unique():
    ids = [item.principle_id for item in _philosophy().principles]
    assert len(ids) == len(set(ids))


def test_tension_identifiers_are_unique():
    ids = [item.tension_id for item in _philosophy().tensions]
    assert len(ids) == len(set(ids))


def test_invalid_philosophy_semantic_version_is_rejected():
    philosophy = _philosophy().model_copy(update={"version": "one"})
    persona = DEFAULT_EDITORIAL_PERSONA.model_copy(update={"philosophy": philosophy})
    with pytest.raises(PersonaValidationError, match="philosophy version"):
        validate_persona(persona)


def test_invalid_priority_is_rejected():
    data = _philosophy().principles[0].model_dump()
    data["priority"] = "urgent"
    with pytest.raises(ValidationError):
        EditorialPrinciple.model_validate(data)


def test_missing_truth_before_performance_is_rejected():
    philosophy = _philosophy()
    principles = tuple(
        item
        for item in philosophy.principles
        if item.principle_id != "truth-before-performance"
    )
    persona = DEFAULT_EDITORIAL_PERSONA.model_copy(
        update={"philosophy": philosophy.model_copy(update={"principles": principles})}
    )
    with pytest.raises(PersonaValidationError, match="truth-before-performance"):
        validate_persona(persona)


def test_permission_to_fabricate_is_rejected():
    with pytest.raises(PersonaValidationError, match="permits fabrication"):
        validate_persona(
            _replace_principle("truth-before-performance", permits_fabrication=True)
        )


def test_satire_overriding_factuality_is_rejected():
    with pytest.raises(PersonaValidationError, match="satire over factuality"):
        validate_persona(
            _replace_principle(
                "satire-must-reveal", permits_satire_over_factuality=True
            )
        )


def test_absolute_completeness_requirement_is_rejected():
    with pytest.raises(PersonaValidationError, match="absolute completeness"):
        validate_persona(
            _replace_principle(
                "clarity-before-completeness", requires_absolute_completeness=True
            )
        )


def test_deceptive_audience_retention_is_rejected():
    with pytest.raises(PersonaValidationError, match="deceptive retention"):
        validate_persona(
            _replace_principle(
                "attention-is-editorial-responsibility",
                permits_deceptive_retention=True,
            )
        )


def test_humor_targeting_victims_is_rejected():
    with pytest.raises(PersonaValidationError, match="targeting vulnerable people"):
        validate_persona(
            _replace_principle(
                "humor-serves-story", permits_targeting_vulnerable_people=True
            )
        )


def test_missing_serious_story_tonal_judgment_is_rejected():
    philosophy = _philosophy()
    principles = tuple(
        item
        for item in philosophy.principles
        if item.principle_id != "serious-story-tonal-judgment"
    )
    persona = DEFAULT_EDITORIAL_PERSONA.model_copy(
        update={"philosophy": philosophy.model_copy(update={"principles": principles})}
    )
    with pytest.raises(PersonaValidationError, match="serious-story-tonal-judgment"):
        validate_persona(persona)


def test_missing_editor_in_chief_final_standard_is_rejected():
    philosophy = _philosophy()
    principles = tuple(
        item
        for item in philosophy.principles
        if item.principle_id != "editor-in-chief-final-standard"
    )
    persona = DEFAULT_EDITORIAL_PERSONA.model_copy(
        update={"philosophy": philosophy.model_copy(update={"principles": principles})}
    )
    with pytest.raises(PersonaValidationError, match="editor-in-chief-final-standard"):
        validate_persona(persona)


def test_invalid_tension_override_authority_is_rejected():
    persona = _replace_tension(
        "clarity-versus-completeness", override_authority="nobody"
    )
    with pytest.raises(PersonaValidationError, match="invalid override authority"):
        validate_persona(persona)


def test_factual_accuracy_cannot_be_overridden():
    persona = _replace_tension(
        "clarity-versus-completeness", may_override_factual_accuracy=True
    )
    with pytest.raises(
        PersonaValidationError, match="may not override factual accuracy"
    ):
        validate_persona(persona)


def test_automatic_philosophy_mutation_is_rejected():
    philosophy = _philosophy().model_copy(
        update={"may_be_modified_by_editorial_memory": True}
    )
    persona = DEFAULT_EDITORIAL_PERSONA.model_copy(update={"philosophy": philosophy})
    with pytest.raises(PersonaValidationError, match="automatically modify philosophy"):
        validate_persona(persona)


def test_rendering_includes_editorial_philosophy():
    assert "\nEditorial Philosophy\n" in render_persona(DEFAULT_EDITORIAL_PERSONA)


def test_rendering_contains_every_canonical_principle():
    rendered = render_persona(DEFAULT_EDITORIAL_PERSONA)
    assert all(item.title in rendered for item in _philosophy().principles)


def test_rendering_contains_every_canonical_tension():
    rendered = render_persona(DEFAULT_EDITORIAL_PERSONA)
    assert all(item.tension_id in rendered for item in _philosophy().tensions)


def test_rendering_order_is_deterministic():
    philosophy = _philosophy()
    shuffled = philosophy.model_copy(
        update={
            "principles": tuple(reversed(philosophy.principles)),
            "tensions": tuple(reversed(philosophy.tensions)),
        }
    )
    persona = DEFAULT_EDITORIAL_PERSONA.model_copy(update={"philosophy": shuffled})
    assert render_persona(persona) == render_persona(DEFAULT_EDITORIAL_PERSONA)


def test_fingerprint_changes_when_principle_changes():
    persona = _replace_principle(
        "truth-before-performance", statement="Changed meaningful statement."
    )
    assert persona_fingerprint(persona) != persona_fingerprint(
        DEFAULT_EDITORIAL_PERSONA
    )


def test_fingerprint_changes_when_tension_changes():
    persona = _replace_tension(
        "clarity-versus-completeness", default_resolution="Changed resolution."
    )
    assert persona_fingerprint(persona) != persona_fingerprint(
        DEFAULT_EDITORIAL_PERSONA
    )


def test_unordered_collection_order_does_not_change_fingerprint():
    philosophy = _philosophy()
    principle = philosophy.principles[0]
    changed_principle = principle.model_copy(
        update={
            "required_behaviors": tuple(reversed(principle.required_behaviors)),
            "prohibited_behaviors": tuple(reversed(principle.prohibited_behaviors)),
        }
    )
    principles = (changed_principle, *philosophy.principles[1:])
    changed = philosophy.model_copy(update={"principles": tuple(reversed(principles))})
    persona = DEFAULT_EDITORIAL_PERSONA.model_copy(update={"philosophy": changed})
    assert persona_fingerprint(persona) == persona_fingerprint(
        DEFAULT_EDITORIAL_PERSONA
    )


def test_philosophy_has_no_detailed_generation_procedures():
    assert not _philosophy().contains_detailed_generation_instructions
    rendered = render_persona(DEFAULT_EDITORIAL_PERSONA).casefold()
    assert "joke construction" not in rendered
    assert "episode-generation procedure" not in rendered


def test_philosophy_package_introduces_no_forbidden_dependency():
    root = Path("src/pastila_scout/editor/persona")
    source = "\n".join(
        path.read_text(encoding="utf-8") for path in sorted(root.glob("*.py"))
    ).casefold()
    for forbidden in (
        "import httpx",
        "import openai",
        "pastila_scout.ai",
        "pastila_scout.database",
        "pastila_scout.cli",
        "pastila_scout.editor.generation",
        "controlled_revision_quality",
        "path.write_text",
    ):
        assert forbidden not in source
