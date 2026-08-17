from __future__ import annotations

from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class DiffOperationV1(StrEnum):
    RETAINED = "RETAINED"
    LIGHT_EDIT = "LIGHT_EDIT"
    SUBSTANTIAL_EDIT = "SUBSTANTIAL_EDIT"
    DELETED = "DELETED"
    INSERTED = "INSERTED"
    MOVED = "MOVED"


class EditClassV1(StrEnum):
    FACT_CORRECTION = "FACT_CORRECTION"
    REMOVE_HALLUCINATION = "REMOVE_HALLUCINATION"
    STYLE_OR_VOICE = "STYLE_OR_VOICE"
    STRUCTURE = "STRUCTURE"
    EXPRESSION_OR_WORDING = "EXPRESSION_OR_WORDING"
    MECHANISM_OR_JOKE = "MECHANISM_OR_JOKE"
    REDUNDANCY = "REDUNDANCY"
    TRANSITION = "TRANSITION"
    UNKNOWN = "UNKNOWN"


class LearnabilityV1(StrEnum):
    STYLE_CANDIDATE = "STYLE_CANDIDATE"
    FACT_ONLY = "FACT_ONLY"
    ONE_OFF = "ONE_OFF"
    UNKNOWN = "UNKNOWN"


class EditorialMechanicV1(StrEnum):
    FACTUAL_SETUP = "FACTUAL_SETUP"
    ACID_ESCALATION = "ACID_ESCALATION"
    ANALOGY = "ANALOGY"
    EXPECTATION_INVERSION = "EXPECTATION_INVERSION"
    CALLBACK = "CALLBACK"
    RHETORICAL_QUESTION = "RHETORICAL_QUESTION"
    ABSURD_LOGICAL_EXTENSION = "ABSURD_LOGICAL_EXTENSION"
    SERIOUS_RESET = "SERIOUS_RESET"
    PUNCHLINE_ENDING = "PUNCHLINE_ENDING"
    PUNCHLINE_TRANSITION = "PUNCHLINE_TRANSITION"
    SEMANTIC_BRIDGE = "SEMANTIC_BRIDGE"
    CONTRAST_BRIDGE = "CONTRAST_BRIDGE"
    WORDPLAY_BRIDGE = "WORDPLAY_BRIDGE"


class SnapshotV1(FrozenModel):
    captured_at: str
    sha256: str = Field(pattern=r"^sha256:[0-9a-f]{64}$")
    text: str = Field(min_length=1)


class CaptureMetadataV1(FrozenModel):
    project_id: str = Field(min_length=1)
    event_id: int = Field(gt=0)
    component_id: str = Field(min_length=1)
    provider: str | None = None
    model: str | None = None
    prompt_identity: str | None = None
    policy_identity: str | None = None
    catalog_identity: str | None = None
    mechanism_identity: str | None = None
    mechanic_identities: tuple[EditorialMechanicV1, ...] = ()
    retrieved_tool_ids: tuple[str, ...] = ()
    generation_attempt: int | None = Field(default=None, gt=0)


class DiffUnitV1(FrozenModel):
    operation: DiffOperationV1
    generated_index: int | None = Field(default=None, ge=0)
    final_index: int | None = Field(default=None, ge=0)
    generated_text: str | None = None
    final_text: str | None = None
    severity: Literal["NONE", "MINOR", "MAJOR"]
    similarity: float = Field(ge=0, le=1)
    proposed_class: EditClassV1


class OwnerClassificationV1(FrozenModel):
    diff_index: int = Field(ge=0)
    edit_class: EditClassV1
    learnability: LearnabilityV1
    owner_confirmed: bool = True


class ExpressionEvidenceV1(FrozenModel):
    authority_id: str
    generated_surface: str
    outcome: Literal["RETAINED", "MODIFIED", "REMOVED"]


class DimensionV1(FrozenModel):
    value: float | None = Field(default=None, ge=0, le=1)
    available: bool
    reason: str


class UsabilityKpiV1(FrozenModel):
    schema_version: Literal[1] = 1
    score: float | None = Field(default=None, ge=0, le=100)
    completeness: float = Field(ge=0, le=1)
    confidence: Literal["LOW", "MEDIUM", "HIGH"]
    band: str | None
    dimensions: dict[str, DimensionV1]
    wholesale_replacement: bool
    critical_factual_issue: bool
    classification_coverage: float = Field(ge=0, le=1)


class EditorialObservationV1(FrozenModel):
    schema_version: Literal[1] = 1
    capture_id: str = Field(min_length=1)
    metadata: CaptureMetadataV1
    generated: SnapshotV1
    final: SnapshotV1 | None = None
    finalization_source: str | None = None
    diff: tuple[DiffUnitV1, ...] = ()
    classifications: tuple[OwnerClassificationV1, ...] = ()
    expression_evidence: tuple[ExpressionEvidenceV1, ...] = ()
    kpi: UsabilityKpiV1 | None = None
