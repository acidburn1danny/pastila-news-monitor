"""Immutable M6C.6B Part 1 architecture descriptor."""

from pydantic import model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.models import fingerprint

ARCHITECTURE_VERSION = "1"
MILESTONE_ID = "m6c6b.execution_dispatch"


class CorrectiveActionExecutionDispatchDescriptor(FrozenModel):
    """Describe ownership without constructing dispatch runtime components."""

    milestone_id: str = MILESTONE_ID
    milestone_version: str = ARCHITECTURE_VERSION
    authoritative_input: str = "CorrectiveActionExecutionPlanResult"
    authoritative_output: str = "CorrectiveActionExecutionDispatchResult"
    ownership: str = "dispatch_contracts_only"
    frozen_upstream: str = "M6C.6A"
    future_executor_boundary: str = "M6C.6C+"
    dispatch_cardinality: str = "exactly_one_compatible_executor"
    routing_statement: str = (
        "The dispatcher routes an authoritative plan. "
        "It does not reinterpret the plan."
    )
    execution_statement: str = (
        "The executor performs the corrective operation. "
        "The dispatcher does not implement capability-specific business logic."
    )
    part_one_executes_actions: bool = False
    descriptor_fingerprint: str

    @classmethod
    def build(cls) -> CorrectiveActionExecutionDispatchDescriptor:
        values = {
            "milestone_id": MILESTONE_ID,
            "milestone_version": ARCHITECTURE_VERSION,
            "authoritative_input": "CorrectiveActionExecutionPlanResult",
            "authoritative_output": "CorrectiveActionExecutionDispatchResult",
            "ownership": "dispatch_contracts_only",
            "frozen_upstream": "M6C.6A",
            "future_executor_boundary": "M6C.6C+",
            "dispatch_cardinality": "exactly_one_compatible_executor",
            "routing_statement": (
                "The dispatcher routes an authoritative plan. "
                "It does not reinterpret the plan."
            ),
            "execution_statement": (
                "The executor performs the corrective operation. "
                "The dispatcher does not implement capability-specific business logic."
            ),
            "part_one_executes_actions": False,
        }
        return cls(**values, descriptor_fingerprint=fingerprint(values))

    @model_validator(mode="after")
    def invariants(self):
        if (
            self.milestone_id != MILESTONE_ID
            or self.milestone_version != ARCHITECTURE_VERSION
            or self.part_one_executes_actions
        ):
            raise ValueError("unsupported execution-dispatch architecture")
        expected = fingerprint(
            self.model_dump(exclude={"descriptor_fingerprint"}, mode="python")
        )
        if self.descriptor_fingerprint != expected:
            raise ValueError("dispatch architecture fingerprint is inconsistent")
        return self
