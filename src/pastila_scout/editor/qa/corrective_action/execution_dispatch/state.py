"""Immutable deterministic lifecycle for authoritative dispatch."""

from enum import StrEnum
from typing import Any

from pydantic import model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.models import fingerprint

STATE_VERSION = "1"
EVENT_VERSION = "1"


class CorrectiveActionExecutionDispatchPhase(StrEnum):
    PREPARED = "prepared"
    VALIDATING = "validating"
    EVALUATING_ELIGIBILITY = "evaluating_eligibility"
    RESOLVING = "resolving"
    BUILDING_EXECUTOR_REQUEST = "building_executor_request"
    INVOKING_EXECUTOR = "invoking_executor"
    VALIDATING_EXECUTOR_RESULT = "validating_executor_result"
    DISPATCHED = "dispatched"
    FINALIZED = "finalized"
    FAILED = "failed"


class CorrectiveActionExecutionDispatchEvent(FrozenModel):
    """One safe lifecycle transition with no content or timestamps."""

    event_version: str = EVENT_VERSION
    sequence: int
    from_phase: CorrectiveActionExecutionDispatchPhase
    to_phase: CorrectiveActionExecutionDispatchPhase
    revision: int
    request_fingerprint: str
    event_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionExecutionDispatchEvent:
        values.setdefault("event_version", EVENT_VERSION)
        values["event_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.event_version != EVENT_VERSION or self.sequence != self.revision:
            raise ValueError("invalid dispatch lifecycle event")
        expected = fingerprint(
            self.model_dump(exclude={"event_fingerprint"}, mode="python")
        )
        if self.event_fingerprint != expected:
            raise ValueError("dispatch lifecycle event fingerprint is inconsistent")
        return self


class CorrectiveActionExecutionDispatchState(FrozenModel):
    """Immutable lifecycle state; every transition returns a new instance."""

    state_version: str = STATE_VERSION
    phase: CorrectiveActionExecutionDispatchPhase
    revision: int
    request_fingerprint: str
    events: tuple[CorrectiveActionExecutionDispatchEvent, ...]
    state_fingerprint: str

    @classmethod
    def prepared(
        cls, request_fingerprint: str
    ) -> CorrectiveActionExecutionDispatchState:
        values = {
            "state_version": STATE_VERSION,
            "phase": CorrectiveActionExecutionDispatchPhase.PREPARED,
            "revision": 0,
            "request_fingerprint": request_fingerprint,
            "events": (),
        }
        return cls(**values, state_fingerprint=fingerprint(values))

    @model_validator(mode="after")
    def invariants(self):
        if self.state_version != STATE_VERSION:
            raise ValueError("unsupported dispatch state version")
        if self.revision != len(self.events):
            raise ValueError("dispatch state revision is inconsistent")
        expected = fingerprint(
            self.model_dump(exclude={"state_fingerprint"}, mode="python")
        )
        if self.state_fingerprint != expected:
            raise ValueError("dispatch state fingerprint is inconsistent")
        return self


_TRANSITIONS = {
    CorrectiveActionExecutionDispatchPhase.PREPARED: {
        CorrectiveActionExecutionDispatchPhase.VALIDATING,
    },
    CorrectiveActionExecutionDispatchPhase.VALIDATING: {
        CorrectiveActionExecutionDispatchPhase.EVALUATING_ELIGIBILITY,
        CorrectiveActionExecutionDispatchPhase.FAILED,
    },
    CorrectiveActionExecutionDispatchPhase.EVALUATING_ELIGIBILITY: {
        CorrectiveActionExecutionDispatchPhase.RESOLVING,
        CorrectiveActionExecutionDispatchPhase.FINALIZED,
        CorrectiveActionExecutionDispatchPhase.FAILED,
    },
    CorrectiveActionExecutionDispatchPhase.RESOLVING: {
        CorrectiveActionExecutionDispatchPhase.BUILDING_EXECUTOR_REQUEST,
        CorrectiveActionExecutionDispatchPhase.FAILED,
    },
    CorrectiveActionExecutionDispatchPhase.BUILDING_EXECUTOR_REQUEST: {
        CorrectiveActionExecutionDispatchPhase.INVOKING_EXECUTOR,
        CorrectiveActionExecutionDispatchPhase.FAILED,
    },
    CorrectiveActionExecutionDispatchPhase.INVOKING_EXECUTOR: {
        CorrectiveActionExecutionDispatchPhase.VALIDATING_EXECUTOR_RESULT,
        CorrectiveActionExecutionDispatchPhase.FAILED,
    },
    CorrectiveActionExecutionDispatchPhase.VALIDATING_EXECUTOR_RESULT: {
        CorrectiveActionExecutionDispatchPhase.DISPATCHED,
        CorrectiveActionExecutionDispatchPhase.FAILED,
    },
    CorrectiveActionExecutionDispatchPhase.DISPATCHED: {
        CorrectiveActionExecutionDispatchPhase.FINALIZED,
    },
}


def transition_dispatch_state(
    state: CorrectiveActionExecutionDispatchState,
    phase: CorrectiveActionExecutionDispatchPhase,
) -> CorrectiveActionExecutionDispatchState:
    """Apply the sole allowed transition graph without mutating prior state."""

    if phase not in _TRANSITIONS.get(state.phase, set()):
        raise ValueError("invalid dispatch lifecycle transition")
    revision = state.revision + 1
    event = CorrectiveActionExecutionDispatchEvent.build(
        sequence=revision,
        from_phase=state.phase,
        to_phase=phase,
        revision=revision,
        request_fingerprint=state.request_fingerprint,
    )
    values = {
        "state_version": STATE_VERSION,
        "phase": phase,
        "revision": revision,
        "request_fingerprint": state.request_fingerprint,
        "events": (*state.events, event),
    }
    return CorrectiveActionExecutionDispatchState(
        **values, state_fingerprint=fingerprint(values)
    )


def validate_dispatch_state(state: CorrectiveActionExecutionDispatchState) -> None:
    """Validate lifecycle state and its complete transition trace."""

    if not isinstance(state, CorrectiveActionExecutionDispatchState):
        raise TypeError("invalid dispatch state")
    cursor = CorrectiveActionExecutionDispatchState.prepared(state.request_fingerprint)
    for event in state.events:
        cursor = transition_dispatch_state(cursor, event.to_phase)
        if cursor.events[-1] != event:
            raise ValueError("dispatch lifecycle trace is inconsistent")
    if cursor != state:
        raise ValueError("dispatch state is inconsistent")
