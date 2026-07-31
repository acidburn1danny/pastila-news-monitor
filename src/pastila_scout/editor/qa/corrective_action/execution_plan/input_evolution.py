"""Version-2 planning lineage envelopes preserving legacy contracts exactly."""

from typing import Any

from pydantic import SerializeAsAny, model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.models import fingerprint

from .models import (
    CorrectiveActionExecutionPlan,
    CorrectiveActionExecutionPlanRequest,
    CorrectiveActionExecutionPlanResult,
)
from .planning_input import CorrectiveActionPlanningInput

EVOLUTION_VERSION = "2"


class CorrectiveActionExecutionPlanRequestV2(FrozenModel):
    """Version-2 request envelope retaining the bit-identical v1 request."""

    contract_version: str = EVOLUTION_VERSION
    legacy_request: CorrectiveActionExecutionPlanRequest
    planning_input: SerializeAsAny[CorrectiveActionPlanningInput]
    request_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("contract_version", EVOLUTION_VERSION)
        values["request_fingerprint"] = fingerprint(_request_identity(values))
        return cls.model_validate(values)

    @property
    def decision_result(self):
        return self.legacy_request.decision_result

    @property
    def planning_policy(self):
        return self.legacy_request.planning_policy

    @model_validator(mode="after")
    def invariants(self):
        if self.contract_version != EVOLUTION_VERSION:
            raise ValueError("unsupported version-2 planning request")
        decision = self.decision_result.decision
        if (
            decision is None
            or decision.action is not self.planning_input.corrective_action
        ):
            raise ValueError("planning input action does not match decision")
        if (
            self.planning_input.source_lineage_fingerprint
            != self.decision_result.result_fingerprint
        ):
            raise ValueError("planning input source lineage does not match decision")
        if (
            self.planning_input.authorization_policy_fingerprint
            != self.planning_policy.policy_fingerprint
        ):
            raise ValueError("planning input authorization policy is inconsistent")
        integration = self.decision_result.integration_result
        generation = integration.generation_result if integration else None
        authoritative_source = generation.draft if generation else None
        supplied_source = self.planning_input.authoritative_source_object
        if supplied_source is not None and supplied_source is not authoritative_source:
            raise ValueError("planning input does not preserve source identity")
        if self.request_fingerprint != fingerprint(
            _request_identity(self.model_dump(mode="python"))
        ):
            raise ValueError("version-2 planning-request fingerprint is inconsistent")
        return self


class CorrectiveActionExecutionPlanV2(FrozenModel):
    """Version-2 plan envelope preserving the exact v1 plan and typed input."""

    contract_version: str = EVOLUTION_VERSION
    request: CorrectiveActionExecutionPlanRequestV2
    legacy_plan: CorrectiveActionExecutionPlan
    planning_input: SerializeAsAny[CorrectiveActionPlanningInput]
    plan_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("contract_version", EVOLUTION_VERSION)
        values["plan_fingerprint"] = fingerprint(_plan_identity(values))
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.contract_version != EVOLUTION_VERSION:
            raise ValueError("unsupported version-2 execution plan")
        if self.planning_input is not self.request.planning_input:
            raise ValueError("execution plan does not preserve planning-input identity")
        if self.legacy_plan.decision_result is not self.request.decision_result:
            raise ValueError("execution plan does not preserve decision identity")
        if self.legacy_plan.source_action is not self.planning_input.corrective_action:
            raise ValueError("execution plan action and planning input differ")
        if (
            self.legacy_plan.required_capability
            is not self.planning_input.required_capability
        ):
            raise ValueError("execution plan capability and planning input differ")
        if self.plan_fingerprint != fingerprint(
            _plan_identity(self.model_dump(mode="python"))
        ):
            raise ValueError("version-2 plan fingerprint is inconsistent")
        return self


class CorrectiveActionExecutionPlanResultV2(FrozenModel):
    """Version-2 result envelope preserving exact plan and input identities."""

    contract_version: str = EVOLUTION_VERSION
    legacy_result: CorrectiveActionExecutionPlanResult
    plan: CorrectiveActionExecutionPlanV2
    result_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("contract_version", EVOLUTION_VERSION)
        values["result_fingerprint"] = fingerprint(_result_identity(values))
        return cls.model_validate(values)

    @property
    def planning_input(self):
        return self.plan.planning_input

    @model_validator(mode="after")
    def invariants(self):
        if self.contract_version != EVOLUTION_VERSION:
            raise ValueError("unsupported version-2 planning result")
        if self.legacy_result.plan is not self.plan.legacy_plan:
            raise ValueError("planning result does not preserve plan identity")
        if self.result_fingerprint != fingerprint(
            _result_identity(self.model_dump(mode="python"))
        ):
            raise ValueError("version-2 planning-result fingerprint is inconsistent")
        return self


def _request_identity(values):
    legacy = values["legacy_request"]
    planning_input = values["planning_input"]
    return {
        "contract_version": values["contract_version"],
        "legacy_request_fingerprint": _field(legacy, "request_fingerprint"),
        "planning_input_fingerprint": _field(planning_input, "input_fingerprint"),
    }


def _plan_identity(values):
    request = values["request"]
    legacy = values["legacy_plan"]
    planning_input = values["planning_input"]
    return {
        "contract_version": values["contract_version"],
        "request_fingerprint": _field(request, "request_fingerprint"),
        "legacy_plan_fingerprint": _field(legacy, "plan_fingerprint"),
        "planning_input_fingerprint": _field(planning_input, "input_fingerprint"),
    }


def _result_identity(values):
    legacy = values["legacy_result"]
    plan = values["plan"]
    return {
        "contract_version": values["contract_version"],
        "legacy_result_fingerprint": _field(legacy, "result_fingerprint"),
        "plan_fingerprint": _field(plan, "plan_fingerprint"),
        "planning_input_fingerprint": _field(
            plan, "planning_input", "input_fingerprint"
        ),
    }


def _field(value, name, nested=None):
    item = value[name] if isinstance(value, dict) else getattr(value, name)
    if nested is None:
        return item
    return item[nested] if isinstance(item, dict) else getattr(item, nested)
