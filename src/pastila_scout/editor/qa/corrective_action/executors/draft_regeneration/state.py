"""Immutable preparation lifecycle with content-free events."""

from typing import Any

from pydantic import model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.models import fingerprint

from .enums import (
    DraftRegenerationPreparationOutcome,
    DraftRegenerationPreparationPhase,
)

STATE_VERSION = "1"


class DraftRegenerationPreparationEvent(FrozenModel):
    from_phase: DraftRegenerationPreparationPhase | None
    to_phase: DraftRegenerationPreparationPhase
    revision: int
    event_code: str
    event_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values["event_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        expected = fingerprint(
            self.model_dump(exclude={"event_fingerprint"}, mode="python")
        )
        if self.event_fingerprint != expected:
            raise ValueError("preparation-event fingerprint is inconsistent")
        return self


class DraftRegenerationPreparationState(FrozenModel):
    state_version: str = STATE_VERSION
    phase: DraftRegenerationPreparationPhase
    revision: int
    executor_request_fingerprint: str
    regeneration_input_fingerprint: str | None = None
    regeneration_request_fingerprint: str | None = None
    controlled_generation_request_fingerprint: str | None = None
    precondition_evaluation_fingerprint: str | None = None
    preparation_outcome: DraftRegenerationPreparationOutcome | None = None
    diagnostic_code: str | None = None
    events: tuple[DraftRegenerationPreparationEvent, ...]
    state_fingerprint: str

    @classmethod
    def initial(cls, executor_request_fingerprint: str):
        event = DraftRegenerationPreparationEvent.build(
            from_phase=None,
            to_phase=DraftRegenerationPreparationPhase.RECEIVED,
            revision=0,
            event_code="preparation_received",
        )
        values = {
            "state_version": STATE_VERSION,
            "phase": DraftRegenerationPreparationPhase.RECEIVED,
            "revision": 0,
            "executor_request_fingerprint": executor_request_fingerprint,
            "regeneration_input_fingerprint": None,
            "regeneration_request_fingerprint": None,
            "controlled_generation_request_fingerprint": None,
            "precondition_evaluation_fingerprint": None,
            "preparation_outcome": None,
            "diagnostic_code": None,
            "events": (event,),
        }
        values["state_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    def transition(self, phase: DraftRegenerationPreparationPhase, **updates: Any):
        allowed = {
            DraftRegenerationPreparationPhase.RECEIVED: {
                DraftRegenerationPreparationPhase.VALIDATING_EXECUTOR_REQUEST
            },
            DraftRegenerationPreparationPhase.VALIDATING_EXECUTOR_REQUEST: {
                DraftRegenerationPreparationPhase.RESOLVING_INPUT,
                DraftRegenerationPreparationPhase.FAILED,
            },
            DraftRegenerationPreparationPhase.RESOLVING_INPUT: {
                DraftRegenerationPreparationPhase.BUILDING_REGENERATION_REQUEST,
                DraftRegenerationPreparationPhase.FAILED,
            },
            DraftRegenerationPreparationPhase.BUILDING_REGENERATION_REQUEST: {
                DraftRegenerationPreparationPhase.PROJECTING_GENERATION_REQUEST,
                DraftRegenerationPreparationPhase.FAILED,
            },
            DraftRegenerationPreparationPhase.PROJECTING_GENERATION_REQUEST: {
                DraftRegenerationPreparationPhase.EVALUATING_PRECONDITIONS,
                DraftRegenerationPreparationPhase.FAILED,
            },
            DraftRegenerationPreparationPhase.EVALUATING_PRECONDITIONS: {
                DraftRegenerationPreparationPhase.PREPARED,
                DraftRegenerationPreparationPhase.FAILED,
            },
            DraftRegenerationPreparationPhase.PREPARED: set(),
            DraftRegenerationPreparationPhase.FAILED: set(),
        }
        if phase not in allowed[self.phase]:
            raise ValueError("invalid preparation lifecycle transition")
        revision = self.revision + 1
        event = DraftRegenerationPreparationEvent.build(
            from_phase=self.phase,
            to_phase=phase,
            revision=revision,
            event_code=f"preparation_{phase.value}",
        )
        values = self.model_dump(exclude={"state_fingerprint"}, mode="python")
        values.update(
            updates, phase=phase, revision=revision, events=self.events + (event,)
        )
        values["state_fingerprint"] = fingerprint(values)
        return type(self).model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.state_version != STATE_VERSION or self.revision != len(self.events) - 1:
            raise ValueError("preparation state revision is inconsistent")
        expected = fingerprint(
            self.model_dump(exclude={"state_fingerprint"}, mode="python")
        )
        if self.state_fingerprint != expected:
            raise ValueError("preparation-state fingerprint is inconsistent")
        return self
