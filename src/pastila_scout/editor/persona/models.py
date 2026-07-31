"""Immutable contracts for Scout's stable editorial operating identity."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class FrozenModel(BaseModel):
    """Strict immutable base for persona configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)


class AuthorityKind(StrEnum):
    EDITOR_IN_CHIEF = "Editor-in-Chief"
    VALIDATED_EDITORIAL_POLICY = "Validated project editorial policy"
    BASE_PERSONA = "Base Editorial Persona"
    EDITORIAL_PROFILE = "Current Editorial Profile"
    EPISODE_INSTRUCTIONS = "Episode-specific instructions"
    SCOUT_JUDGMENT = "Scout editorial judgment"


class BoundaryKind(StrEnum):
    FINAL_AUTHORITY = "final_editorial_authority"
    PERSONA_MUTATION = "automatic_persona_mutation"
    FACT_FABRICATION = "fact_fabrication"
    FACTUAL_DISTORTION = "factual_distortion"
    VERDICT_DEBATE = "verdict_debate"
    FORCED_SATIRE = "forced_satire"


class RelationshipKind(StrEnum):
    EDITOR_IN_CHIEF = "editor_in_chief"
    EDITORIAL_MEMORY = "editorial_memory"
    EDITORIAL_PROFILE = "editorial_profile"


class EditorialPriority(StrEnum):
    FOUNDATIONAL = "foundational"
    HIGH = "high"
    CONTEXTUAL = "contextual"


class PersonaIdentity(FrozenModel):
    professional_role: str = Field(min_length=1)
    editorial_context: str = Field(min_length=1)
    capabilities: tuple[str, ...] = Field(min_length=1)
    excluded_identities: tuple[str, ...] = Field(min_length=1)


class PersonaMission(FrozenModel):
    statement: str = Field(min_length=1)
    objectives: tuple[str, ...] = Field(min_length=1)
    factual_fidelity_required: bool


class AuthorityLevel(FrozenModel):
    rank: int = Field(ge=1)
    authority: AuthorityKind
    description: str = Field(min_length=1)


class PersonaBoundary(FrozenModel):
    kind: BoundaryKind
    prohibited: bool
    statement: str = Field(min_length=1)


class PersonaRelationship(FrozenModel):
    kind: RelationshipKind
    statement: str = Field(min_length=1)
    may_override_scout: bool = False
    may_modify_base_persona: bool = False
    scout_has_final_authority: bool = False
    guidance_requires_established_profile_finding: bool = False


class EditorialPrinciple(FrozenModel):
    principle_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    order: int = Field(gt=0)
    title: str = Field(min_length=1)
    statement: str = Field(min_length=1)
    rationale: str = Field(min_length=1)
    required_behaviors: tuple[str, ...] = Field(min_length=1)
    prohibited_behaviors: tuple[str, ...] = Field(min_length=1)
    priority: EditorialPriority
    permits_fabrication: bool = False
    permits_factual_distortion: bool = False
    permits_satire_over_factuality: bool = False
    requires_absolute_completeness: bool = False
    permits_deceptive_retention: bool = False
    permits_targeting_vulnerable_people: bool = False


class EditorialTension(FrozenModel):
    tension_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    order: int = Field(gt=0)
    first_value: str = Field(min_length=1)
    second_value: str = Field(min_length=1)
    default_resolution: str = Field(min_length=1)
    hard_boundary: str = Field(min_length=1)
    override_authority: AuthorityKind
    may_override_factual_accuracy: bool = False


class EditorialPhilosophy(FrozenModel):
    philosophy_id: str = Field(pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    version: str
    principles: tuple[EditorialPrinciple, ...] = Field(min_length=1)
    tensions: tuple[EditorialTension, ...] = Field(min_length=1)
    may_be_modified_by_editorial_memory: bool = False
    may_be_modified_by_editorial_profile: bool = False
    contains_detailed_generation_instructions: bool = False
    contains_fictional_biography: bool = False


class EditorialPersona(FrozenModel):
    persona_id: str = Field(min_length=1, pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
    version: str
    title: str = Field(min_length=1)
    jurisdiction: str = Field(min_length=1)
    project: str = Field(min_length=1)
    identity: PersonaIdentity
    mission: PersonaMission
    philosophy: EditorialPhilosophy | None = None
    authority_hierarchy: tuple[AuthorityLevel, ...] = Field(min_length=1)
    responsibilities: tuple[str, ...] = Field(min_length=1)
    boundaries: tuple[PersonaBoundary, ...] = Field(min_length=1)
    editor_in_chief_relationship: PersonaRelationship
    editorial_memory_relationship: PersonaRelationship
    editorial_profile_relationship: PersonaRelationship
