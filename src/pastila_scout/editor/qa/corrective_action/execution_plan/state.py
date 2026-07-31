"""Immutable lifecycle state for authoritative execution planning."""

from typing import Any

from pydantic import Field, model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.models import fingerprint

from .enums import (
    CorrectiveActionExecutionPlanDiagnosticCode,
    CorrectiveActionExecutionPlanningEventCode,
    CorrectiveActionExecutionPlanningLifecycle,
    CorrectiveActionExecutionPlanOutcome,
)

STATE_VERSION = "1"
EVENT_VERSION = "1"


class CorrectiveActionExecutionPlanningEvent(FrozenModel):
    """One deterministic accepted lifecycle transition."""

    event_version: str = EVENT_VERSION
    sequence: int = Field(ge=0)
    from_phase: CorrectiveActionExecutionPlanningLifecycle
    to_phase: CorrectiveActionExecutionPlanningLifecycle
    revision: int = Field(ge=1)
    code: CorrectiveActionExecutionPlanningEventCode
    request_fingerprint: str | None
    plan_fingerprint: str | None
    event_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionExecutionPlanningEvent:
        values.setdefault("event_version", EVENT_VERSION)
        values["event_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def identity_valid(self):
        if self.event_version != EVENT_VERSION:
            raise ValueError("unsupported planning event version")
        expected = fingerprint(
            self.model_dump(exclude={"event_fingerprint"}, mode="python")
        )
        if self.event_fingerprint != expected:
            raise ValueError("planning event fingerprint is inconsistent")
        return self


class CorrectiveActionExecutionPlanningState(FrozenModel):
    """Safe immutable planning state with revisioned event history."""

    state_version: str = STATE_VERSION
    phase: CorrectiveActionExecutionPlanningLifecycle
    revision: int = Field(ge=0)
    request_fingerprint: str | None
    policy_fingerprint: str | None
    decision_result_fingerprint: str | None
    plan_fingerprint: str | None = None
    operational_outcome: CorrectiveActionExecutionPlanOutcome | None = None
    diagnostic_code: CorrectiveActionExecutionPlanDiagnosticCode | None = None
    trace: tuple[CorrectiveActionExecutionPlanningEvent, ...] = ()
    state_fingerprint: str

    @classmethod
    def prepare(
        cls,
        *,
        request_fingerprint: str | None,
        policy_fingerprint: str | None,
        decision_result_fingerprint: str | None,
    ) -> CorrectiveActionExecutionPlanningState:
        values = {
            "state_version": STATE_VERSION,
            "phase": CorrectiveActionExecutionPlanningLifecycle.PREPARED,
            "revision": 0,
            "request_fingerprint": request_fingerprint,
            "policy_fingerprint": policy_fingerprint,
            "decision_result_fingerprint": decision_result_fingerprint,
            "plan_fingerprint": None,
            "operational_outcome": None,
            "diagnostic_code": None,
            "trace": (),
        }
        return cls(**values, state_fingerprint=fingerprint(values))

    @model_validator(mode="after")
    def invariants(self):
        if self.state_version != STATE_VERSION:
            raise ValueError("unsupported planning state version")
        if self.revision != len(self.trace):
            raise ValueError("planning state revision and trace are inconsistent")
        for sequence, event in enumerate(self.trace):
            if event.sequence != sequence or event.revision != sequence + 1:
                raise ValueError("planning event sequence is inconsistent")
        if self.trace and self.trace[-1].to_phase is not self.phase:
            raise ValueError("planning trace does not reach current phase")
        terminal = self.phase in {
            CorrectiveActionExecutionPlanningLifecycle.FINALIZED,
            CorrectiveActionExecutionPlanningLifecycle.FAILED,
        }
        if terminal != (self.operational_outcome is not None):
            raise ValueError("terminal state requires exactly one outcome")
        if (self.phase is CorrectiveActionExecutionPlanningLifecycle.FAILED) != (
            self.diagnostic_code is not None
        ):
            raise ValueError("failed state requires exactly one diagnostic code")
        expected = fingerprint(
            self.model_dump(exclude={"state_fingerprint"}, mode="python")
        )
        if self.state_fingerprint != expected:
            raise ValueError("planning state fingerprint is inconsistent")
        return self


_ALLOWED_TRANSITIONS = {
    CorrectiveActionExecutionPlanningLifecycle.PREPARED: {
        CorrectiveActionExecutionPlanningLifecycle.VALIDATING
    },
    CorrectiveActionExecutionPlanningLifecycle.VALIDATING: {
        CorrectiveActionExecutionPlanningLifecycle.PLANNING,
        CorrectiveActionExecutionPlanningLifecycle.FAILED,
    },
    CorrectiveActionExecutionPlanningLifecycle.PLANNING: {
        CorrectiveActionExecutionPlanningLifecycle.PLANNED,
        CorrectiveActionExecutionPlanningLifecycle.FAILED,
    },
    CorrectiveActionExecutionPlanningLifecycle.PLANNED: {
        CorrectiveActionExecutionPlanningLifecycle.FINALIZED
    },
    CorrectiveActionExecutionPlanningLifecycle.FINALIZED: set(),
    CorrectiveActionExecutionPlanningLifecycle.FAILED: set(),
}

_EVENT_FOR_TRANSITION = {
    (
        CorrectiveActionExecutionPlanningLifecycle.PREPARED,
        CorrectiveActionExecutionPlanningLifecycle.VALIDATING,
    ): CorrectiveActionExecutionPlanningEventCode.VALIDATION_STARTED,
    (
        CorrectiveActionExecutionPlanningLifecycle.VALIDATING,
        CorrectiveActionExecutionPlanningLifecycle.PLANNING,
    ): CorrectiveActionExecutionPlanningEventCode.PLANNING_STARTED,
    (
        CorrectiveActionExecutionPlanningLifecycle.PLANNING,
        CorrectiveActionExecutionPlanningLifecycle.PLANNED,
    ): CorrectiveActionExecutionPlanningEventCode.PLAN_CONSTRUCTED,
    (
        CorrectiveActionExecutionPlanningLifecycle.PLANNED,
        CorrectiveActionExecutionPlanningLifecycle.FINALIZED,
    ): CorrectiveActionExecutionPlanningEventCode.PLANNING_FINALIZED,
    (
        CorrectiveActionExecutionPlanningLifecycle.VALIDATING,
        CorrectiveActionExecutionPlanningLifecycle.FAILED,
    ): CorrectiveActionExecutionPlanningEventCode.PLANNING_FAILED,
    (
        CorrectiveActionExecutionPlanningLifecycle.PLANNING,
        CorrectiveActionExecutionPlanningLifecycle.FAILED,
    ): CorrectiveActionExecutionPlanningEventCode.PLANNING_FAILED,
}


def transition_planning_state(
    state: CorrectiveActionExecutionPlanningState,
    to_phase: CorrectiveActionExecutionPlanningLifecycle,
    *,
    plan_fingerprint: str | None = None,
    operational_outcome: CorrectiveActionExecutionPlanOutcome | None = None,
    diagnostic_code: CorrectiveActionExecutionPlanDiagnosticCode | None = None,
) -> CorrectiveActionExecutionPlanningState:
    """Return the next immutable state or reject the transition unchanged."""

    if to_phase not in _ALLOWED_TRANSITIONS[state.phase]:
        raise ValueError("invalid execution-planning lifecycle transition")
    revision = state.revision + 1
    effective_plan = plan_fingerprint or state.plan_fingerprint
    event = CorrectiveActionExecutionPlanningEvent.build(
        sequence=len(state.trace),
        from_phase=state.phase,
        to_phase=to_phase,
        revision=revision,
        code=_EVENT_FOR_TRANSITION[(state.phase, to_phase)],
        request_fingerprint=state.request_fingerprint,
        plan_fingerprint=effective_plan,
    )
    values = {
        "state_version": state.state_version,
        "phase": to_phase,
        "revision": revision,
        "request_fingerprint": state.request_fingerprint,
        "policy_fingerprint": state.policy_fingerprint,
        "decision_result_fingerprint": state.decision_result_fingerprint,
        "plan_fingerprint": effective_plan,
        "operational_outcome": operational_outcome,
        "diagnostic_code": diagnostic_code,
        "trace": (*state.trace, event),
    }
    return CorrectiveActionExecutionPlanningState(
        **values, state_fingerprint=fingerprint(values)
    )
