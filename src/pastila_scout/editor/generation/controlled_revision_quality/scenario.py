"""Storage-independent synthetic benchmark scenario contracts."""

from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

from pastila_scout.editor.generation.models import EpisodeDraft


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class BenchmarkMode(StrEnum):
    SYNTHETIC_FIXTURE = "SYNTHETIC_FIXTURE"
    FUTURE_PROVIDER = "FUTURE_PROVIDER"


class ScenarioCategory(StrEnum):
    MINIMAL_CLARITY = "MINIMAL_CLARITY"
    GRAMMAR_AND_FLOW = "GRAMMAR_AND_FLOW"
    SUBSTANTIAL_REWRITE = "SUBSTANTIAL_REWRITE"
    PROTECTED_STRUCTURE = "PROTECTED_STRUCTURE"
    SOURCE_AUTHORITY = "SOURCE_AUTHORITY"
    QUOTE_PRESERVATION = "QUOTE_PRESERVATION"
    NUMERIC_FACT_PRESERVATION = "NUMERIC_FACT_PRESERVATION"
    TEMPORAL_FACT_PRESERVATION = "TEMPORAL_FACT_PRESERVATION"
    MULTI_COMPONENT_REVISION = "MULTI_COMPONENT_REVISION"
    HIGH_CONSTRAINT_REVISION = "HIGH_CONSTRAINT_REVISION"
    NO_CHANGE_REQUIRED = "NO_CHANGE_REQUIRED"
    ADVERSARIAL_AMBIGUITY = "ADVERSARIAL_AMBIGUITY"


class FailureCategory(StrEnum):
    INVALID_JSON = "INVALID_JSON"
    DTO_REJECTION = "DTO_REJECTION"
    DUPLICATE_REFERENCE = "DUPLICATE_REFERENCE"
    REFERENCE_TYPE_MISMATCH = "REFERENCE_TYPE_MISMATCH"
    UNAUTHORIZED_REFERENCE = "UNAUTHORIZED_REFERENCE"
    MISSING_COMPONENT = "MISSING_COMPONENT"
    ORDER_VIOLATION = "ORDER_VIOLATION"
    RECONSTRUCTION_FAILURE = "RECONSTRUCTION_FAILURE"
    DOMAIN_VALIDATION_FAILURE = "DOMAIN_VALIDATION_FAILURE"
    EDITORIAL_UNDER_REVISION = "EDITORIAL_UNDER_REVISION"
    EDITORIAL_OVER_REVISION = "EDITORIAL_OVER_REVISION"
    MEANING_DRIFT = "MEANING_DRIFT"
    SOURCE_AUTHORITY_DRIFT = "SOURCE_AUTHORITY_DRIFT"
    QUOTE_MUTATION = "QUOTE_MUTATION"
    NUMERIC_FACT_MUTATION = "NUMERIC_FACT_MUTATION"
    TEMPORAL_FACT_MUTATION = "TEMPORAL_FACT_MUTATION"
    PROTECTED_STRUCTURE_MUTATION = "PROTECTED_STRUCTURE_MUTATION"
    INSTRUCTION_NOT_FOLLOWED = "INSTRUCTION_NOT_FOLLOWED"
    UNNECESSARY_REWRITE = "UNNECESSARY_REWRITE"
    VALID_BUT_NOT_IMPROVED = "VALID_BUT_NOT_IMPROVED"
    USABLE_REVISION = "USABLE_REVISION"


class CandidateRevision(FrozenModel):
    """Synthetic candidate plus bounded pipeline observations."""

    draft: EpisodeDraft | None
    json_valid: bool = True
    dto_valid: bool = True
    authorization_valid: bool = True
    reconstruction_valid: bool = True
    domain_valid: bool = True
    editorial_accepted: bool = True
    instruction_followed: bool = True
    improved: bool = True
    source_authority_preserved: bool = True
    structural_failure: FailureCategory | None = None


class BenchmarkAcceptanceSpecification(FrozenModel):
    """Provider-independent deterministic acceptance requirements."""

    minimum_length: int = Field(ge=1)
    maximum_length: int = Field(ge=1)
    required_preserved_quotations: tuple[str, ...] = ()
    required_preserved_numeric_facts: tuple[str, ...] = ()
    required_preserved_dates: tuple[str, ...] = ()
    required_protected_structures: tuple[str, ...] = ()
    allowed_editable_targets: tuple[str, ...] = Field(min_length=1)
    forbidden_edits: tuple[str, ...] = ()
    expected_no_op: bool = False
    expected_proportional_revision: bool = True

    @model_validator(mode="after")
    def validate_bounds(self):
        if self.maximum_length < self.minimum_length:
            raise ValueError("acceptance length bounds are reversed")
        if len(set(self.allowed_editable_targets)) != len(
            self.allowed_editable_targets
        ):
            raise ValueError("acceptance targets contain duplicates")
        return self


class SyntheticRevisionScenario(FrozenModel):
    """One property-based synthetic benchmark case; no expected prose."""

    scenario_key: str = Field(pattern=r"^SYN-[0-9]{2}$")
    category: ScenarioCategory
    source_draft: EpisodeDraft
    candidate: CandidateRevision
    authorized_components: tuple[str, ...]
    revision_instruction_class: str
    revision_instruction: str = Field(min_length=20, max_length=1000)
    acceptance_specification: BenchmarkAcceptanceSpecification
    protected_structures: tuple[str, ...] = ()
    protected_facts: tuple[str, ...] = ()
    protected_quotes: tuple[str, ...] = ()
    protected_numeric_values: tuple[str, ...] = ()
    protected_dates: tuple[str, ...] = ()
    expects_no_change: bool = False
    maximum_change_ratio: float = Field(default=0.45, ge=0, le=1)
    expected_usable: bool
    expected_failure_category: FailureCategory

    @model_validator(mode="after")
    def validate_structural_failure(self):
        allowed = {
            FailureCategory.DUPLICATE_REFERENCE,
            FailureCategory.REFERENCE_TYPE_MISMATCH,
            FailureCategory.MISSING_COMPONENT,
            FailureCategory.ORDER_VIOLATION,
        }
        if (
            self.candidate.structural_failure is not None
            and self.candidate.structural_failure not in allowed
        ):
            raise ValueError("candidate structural failure is not bounded")
        return self
