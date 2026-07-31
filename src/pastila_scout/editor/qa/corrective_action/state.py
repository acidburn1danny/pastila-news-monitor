"""Private immutable revisioned M6C.5F decision runtime state."""

from pydantic import Field, model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.corrective_action.models import (
    CorrectiveActionDecisionLifecycle,
    CorrectiveActionDecisionTraceEvent,
)
from pastila_scout.editor.qa.models import fingerprint


class DecisionRuntimeState(FrozenModel):
    lifecycle: CorrectiveActionDecisionLifecycle
    revision: int = Field(ge=0)
    trace: tuple[CorrectiveActionDecisionTraceEvent, ...]
    state_fingerprint: str

    @classmethod
    def prepared(cls):
        values = {
            "lifecycle": CorrectiveActionDecisionLifecycle.PREPARED,
            "revision": 0,
            "trace": (),
        }
        return cls(**values, state_fingerprint=fingerprint(values))

    def advance(self, lifecycle, event_type, phase, code=None):
        allowed = {
            CorrectiveActionDecisionLifecycle.PREPARED: {
                CorrectiveActionDecisionLifecycle.VALIDATING
            },
            CorrectiveActionDecisionLifecycle.VALIDATING: {
                CorrectiveActionDecisionLifecycle.VALIDATING,
                CorrectiveActionDecisionLifecycle.DECIDING,
                CorrectiveActionDecisionLifecycle.FAILED,
            },
            CorrectiveActionDecisionLifecycle.DECIDING: {
                CorrectiveActionDecisionLifecycle.DECIDING,
                CorrectiveActionDecisionLifecycle.DECIDED,
                CorrectiveActionDecisionLifecycle.FAILED,
            },
            CorrectiveActionDecisionLifecycle.DECIDED: {
                CorrectiveActionDecisionLifecycle.DECIDED,
                CorrectiveActionDecisionLifecycle.FINALIZED,
                CorrectiveActionDecisionLifecycle.FAILED,
            },
            CorrectiveActionDecisionLifecycle.FINALIZED: set(),
            CorrectiveActionDecisionLifecycle.FAILED: set(),
        }
        if lifecycle not in allowed[self.lifecycle]:
            raise ValueError("invalid corrective-action lifecycle transition")
        event = CorrectiveActionDecisionTraceEvent.build(
            sequence=len(self.trace),
            event_type=event_type,
            phase=phase,
            code=code,
        )
        values = {
            "lifecycle": lifecycle,
            "revision": self.revision + 1,
            "trace": (*self.trace, event),
        }
        return type(self)(**values, state_fingerprint=fingerprint(values))

    @model_validator(mode="after")
    def invariants(self):
        expected = fingerprint(
            self.model_dump(exclude={"state_fingerprint"}, mode="python")
        )
        if self.state_fingerprint != expected:
            raise ValueError("runtime state fingerprint is inconsistent")
        if self.revision != len(self.trace):
            raise ValueError("runtime state revision is inconsistent")
        if tuple(item.sequence for item in self.trace) != tuple(range(len(self.trace))):
            raise ValueError("runtime trace sequence is inconsistent")
        return self
