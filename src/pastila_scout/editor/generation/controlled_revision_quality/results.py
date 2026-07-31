"""Immutable content-free quality benchmark results."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from .scenario import FailureCategory, ScenarioCategory


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class DimensionScores(FrozenModel):
    structural_validity: bool
    dto_validity: bool
    authorization_validity: bool
    reconstruction_validity: bool
    episode_draft_validity: bool
    editorial_acceptance: bool
    meaning_preservation: bool
    protected_structure_preservation: bool
    quote_preservation: bool
    numeric_fact_preservation: bool
    temporal_fact_preservation: bool
    source_authority_preservation: bool
    no_op_compliance: bool
    instruction_compliance: bool
    revision_proportionality: bool


class ScenarioEvaluation(FrozenModel):
    scenario_key: str
    category: ScenarioCategory
    dimensions: DimensionScores
    usable_revision: bool
    failure_category: FailureCategory
    consistency_passed: bool


class BenchmarkResult(FrozenModel):
    scenario_count: int
    category_count: int
    usable_revision_rate: float = Field(ge=0, le=1)
    structural_pass_rate: float = Field(ge=0, le=1)
    dto_pass_rate: float = Field(ge=0, le=1)
    authorization_pass_rate: float = Field(ge=0, le=1)
    reconstruction_pass_rate: float = Field(ge=0, le=1)
    episode_draft_pass_rate: float = Field(ge=0, le=1)
    editorial_pass_rate: float = Field(ge=0, le=1)
    meaning_preservation_rate: float = Field(ge=0, le=1)
    quote_preservation_rate: float = Field(ge=0, le=1)
    numeric_preservation_rate: float = Field(ge=0, le=1)
    temporal_preservation_rate: float = Field(ge=0, le=1)
    protected_structure_preservation_rate: float = Field(ge=0, le=1)
    instruction_compliance_rate: float = Field(ge=0, le=1)
    no_op_compliance_rate: float = Field(ge=0, le=1)
    failure_counts: tuple[tuple[FailureCategory, int], ...]
    category_scores: tuple[tuple[ScenarioCategory, float], ...]
    overall_score: float = Field(ge=0, le=100)
    evaluation_duration_ms: float = Field(ge=0)
    consistency_checks: tuple[str, ...]
