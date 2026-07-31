"""Capability-neutral immutable planning-input metadata."""

from enum import StrEnum

from pydantic import model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.corrective_action import CorrectiveAction
from pastila_scout.editor.qa.models import fingerprint

from .enums import CorrectiveActionExecutionCapability

PLANNING_INPUT_VERSION = "1"


class CorrectiveActionPlanningInputType(StrEnum):
    DRAFT_REVISION = "draft_revision"


class CorrectiveActionPlanningInput(FrozenModel):
    """Closed capability-neutral identity shared with generic planning."""

    contract_version: str = PLANNING_INPUT_VERSION
    input_type: CorrectiveActionPlanningInputType
    corrective_action: CorrectiveAction
    required_capability: CorrectiveActionExecutionCapability
    source_lineage_fingerprint: str
    authorization_policy_fingerprint: str
    input_fingerprint: str

    @property
    def authoritative_source_object(self):
        """Return an exact upstream source object when the capability has one."""

        return None

    @model_validator(mode="after")
    def generic_identity_valid(self):
        if self.contract_version != PLANNING_INPUT_VERSION:
            raise ValueError("unsupported corrective-action planning-input version")
        expected = fingerprint(
            self.model_dump(exclude={"input_fingerprint"}, mode="python")
        )
        if self.input_fingerprint != expected:
            raise ValueError("planning-input fingerprint is inconsistent")
        return self
