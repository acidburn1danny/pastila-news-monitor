"""Immutable editorial-knowledge lifecycle, history, and validation contracts."""

from __future__ import annotations

import hashlib
import json
import os
import tempfile
from collections import Counter
from enum import StrEnum
from pathlib import Path, PurePosixPath

from pydantic import BaseModel, ConfigDict, Field, model_validator

SCHEMA_NAME = "scout_editorial_knowledge_evolution"
SCHEMA_VERSION = "1.0.0"
CONTRACT_VERSION = 1


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class LifecycleState(StrEnum):
    PROPOSED = "PROPOSED"
    ACTIVE = "ACTIVE"
    REFINED = "REFINED"
    SUPPORTED = "SUPPORTED"
    SUPERSEDED = "SUPERSEDED"
    DEPRECATED = "DEPRECATED"
    INVALIDATED = "INVALIDATED"


class EvolutionTrigger(StrEnum):
    EVIDENCE_ADDED = "EVIDENCE_ADDED"
    EVIDENCE_REMOVED = "EVIDENCE_REMOVED"
    EXPERIMENT_CONFIRMED = "EXPERIMENT_CONFIRMED"
    EXPERIMENT_REFINED = "EXPERIMENT_REFINED"
    EXPERIMENT_CONTRADICTED = "EXPERIMENT_CONTRADICTED"
    CONFIDENCE_UPDATED = "CONFIDENCE_UPDATED"
    STATUS_TRANSITION = "STATUS_TRANSITION"
    RELATIONSHIP_ADDED = "RELATIONSHIP_ADDED"
    RELATIONSHIP_REMOVED = "RELATIONSHIP_REMOVED"


class EvolutionState(StrictModel):
    status: LifecycleState
    confidence: str
    entry_version: int = Field(ge=1)
    evolution_version: int = Field(ge=0)
    cumulative_evidence_count: int = Field(ge=0)


class EvolutionEvent(StrictModel):
    event_id: str = Field(pattern=r"^EVE-EK-[0-9]{3}-[0-9]{3}$")
    knowledge_id: str = Field(pattern=r"^EK-[0-9]{3}$")
    timestamp: str
    previous_state: EvolutionState
    new_state: EvolutionState
    trigger: EvolutionTrigger
    supporting_experiments: tuple[str, ...]
    supporting_manifests: tuple[str, ...]
    supporting_artifacts: tuple[str, ...]
    reason: str = Field(min_length=1)
    confidence_before: str
    confidence_after: str
    event_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def event_invariants(self) -> EvolutionEvent:
        if (
            self.new_state.evolution_version
            != self.previous_state.evolution_version + 1
        ):
            raise ValueError("evolution version mismatch")
        if (
            self.confidence_before != self.previous_state.confidence
            or self.confidence_after != self.new_state.confidence
        ):
            raise ValueError("confidence snapshot mismatch")
        if (
            self.confidence_before != self.confidence_after
            and not self.supporting_experiments
        ):
            raise ValueError("confidence change requires experiment evidence")
        if (
            self.trigger != EvolutionTrigger.STATUS_TRANSITION
            and not self.supporting_experiments
        ):
            raise ValueError("evolution event requires supporting experiment")
        return self


class EntryHistory(StrictModel):
    knowledge_id: str
    entry_version: int = Field(ge=1)
    evolution_schema_version: str
    events: tuple[EvolutionEvent, ...] = Field(min_length=1)
    current_state: EvolutionState
    confirmations: int = Field(ge=0)
    refinements: int = Field(ge=0)
    contradictions: int = Field(ge=0)
    supersessions: int = Field(ge=0)
    deprecations: int = Field(ge=0)
    history_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def history_invariants(self) -> EntryHistory:
        identifiers = [event.event_id for event in self.events]
        if len(identifiers) != len(set(identifiers)):
            raise ValueError("duplicate evolution event")
        if any(
            first.timestamp > second.timestamp
            for first, second in zip(self.events, self.events[1:])
        ):
            raise ValueError("broken timeline ordering")
        if any(event.knowledge_id != self.knowledge_id for event in self.events):
            raise ValueError("event knowledge ID mismatch")
        if any(
            first.new_state != second.previous_state
            for first, second in zip(self.events, self.events[1:])
        ):
            raise ValueError("history state discontinuity")
        if self.events[-1].new_state != self.current_state:
            raise ValueError("current state mismatch")
        return self


class RelationshipEvolutionEvent(StrictModel):
    relationship_event_id: str
    timestamp: str
    action: str
    source_id: str
    target_id: str
    relationship_type: str
    supporting_artifact: str
    event_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")


class KnowledgeEvolutionHistory(StrictModel):
    schema_name: str
    schema_version: str
    contract_version: int
    generated_at: str
    source_knowledge_base_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    histories: tuple[EntryHistory, ...]
    relationship_history: tuple[RelationshipEvolutionEvent, ...]
    history_fingerprint: str = Field(pattern=r"^[0-9a-f]{64}$")
    provider_requests: int = 0
    network_calls: int = 0
    benchmark_executions: int = 0
    benchmark_replays: int = 0

    @model_validator(mode="after")
    def root_invariants(self) -> KnowledgeEvolutionHistory:
        if self.schema_name != SCHEMA_NAME or self.schema_version != SCHEMA_VERSION:
            raise ValueError("unsupported evolution schema")
        if self.contract_version != CONTRACT_VERSION:
            raise ValueError("unsupported evolution contract")
        ids = [item.knowledge_id for item in self.histories]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate entry history")
        relationship_ids = [
            item.relationship_event_id for item in self.relationship_history
        ]
        if len(relationship_ids) != len(set(relationship_ids)):
            raise ValueError("duplicate relationship evolution event")
        if any(
            (
                self.provider_requests,
                self.network_calls,
                self.benchmark_executions,
                self.benchmark_replays,
            )
        ):
            raise ValueError("evolution build must remain offline")
        return self


class EvolutionDiagnostics(StrictModel):
    valid: bool
    errors: tuple[str, ...]
    histories_validated: int
    events_validated: int
    relationships_validated: int
    artifacts_validated: int


def _hash(value: object) -> str:
    serialized = json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def event_fingerprint(event: EvolutionEvent | dict) -> str:
    payload = (
        event.model_dump(mode="json")
        if isinstance(event, EvolutionEvent)
        else json.loads(json.dumps(event))
    )
    payload.pop("event_fingerprint", None)
    return _hash(payload)


def history_fingerprint(history: EntryHistory | dict) -> str:
    payload = (
        history.model_dump(mode="json")
        if isinstance(history, EntryHistory)
        else json.loads(json.dumps(history))
    )
    payload.pop("history_fingerprint", None)
    return _hash(payload)


def relationship_event_fingerprint(event: RelationshipEvolutionEvent | dict) -> str:
    payload = (
        event.model_dump(mode="json")
        if isinstance(event, RelationshipEvolutionEvent)
        else json.loads(json.dumps(event))
    )
    payload.pop("event_fingerprint", None)
    return _hash(payload)


def evolution_history_fingerprint(history: KnowledgeEvolutionHistory | dict) -> str:
    payload = (
        history.model_dump(mode="json")
        if isinstance(history, KnowledgeEvolutionHistory)
        else json.loads(json.dumps(history))
    )
    payload.pop("history_fingerprint", None)
    payload.pop("generated_at", None)
    return _hash(payload)


def next_state(previous: LifecycleState, trigger: EvolutionTrigger) -> LifecycleState:
    """Apply deterministic evidence-driven lifecycle rules."""

    transitions = {
        (
            LifecycleState.PROPOSED,
            EvolutionTrigger.STATUS_TRANSITION,
        ): LifecycleState.ACTIVE,
        (
            LifecycleState.ACTIVE,
            EvolutionTrigger.EXPERIMENT_CONFIRMED,
        ): LifecycleState.SUPPORTED,
        (
            LifecycleState.REFINED,
            EvolutionTrigger.EXPERIMENT_CONFIRMED,
        ): LifecycleState.SUPPORTED,
        (
            LifecycleState.ACTIVE,
            EvolutionTrigger.EXPERIMENT_REFINED,
        ): LifecycleState.REFINED,
        (
            LifecycleState.SUPPORTED,
            EvolutionTrigger.EXPERIMENT_REFINED,
        ): LifecycleState.REFINED,
        (
            LifecycleState.ACTIVE,
            EvolutionTrigger.EXPERIMENT_CONTRADICTED,
        ): LifecycleState.REFINED,
        (
            LifecycleState.SUPPORTED,
            EvolutionTrigger.EXPERIMENT_CONTRADICTED,
        ): LifecycleState.REFINED,
    }
    try:
        return transitions[(previous, trigger)]
    except KeyError as exc:
        raise ValueError(f"invalid lifecycle transition: {previous}/{trigger}") from exc


def validate_evolution_history(
    history: KnowledgeEvolutionHistory, repository_root: Path
) -> EvolutionDiagnostics:
    errors: list[str] = []
    artifacts = 0
    if evolution_history_fingerprint(history) != history.history_fingerprint:
        errors.append("evolution history fingerprint mismatch")
    for entry in history.histories:
        if history_fingerprint(entry) != entry.history_fingerprint:
            errors.append(f"entry history fingerprint mismatch: {entry.knowledge_id}")
        for event in entry.events:
            if event_fingerprint(event) != event.event_fingerprint:
                errors.append(f"event fingerprint mismatch: {event.event_id}")
            for value in (*event.supporting_manifests, *event.supporting_artifacts):
                pure = PurePosixPath(value)
                if pure.is_absolute() or ".." in pure.parts:
                    errors.append(f"unsafe evidence path: {value}")
                elif not repository_root.joinpath(*pure.parts).is_file():
                    errors.append(f"missing evolution evidence: {value}")
                else:
                    artifacts += 1
    for event in history.relationship_history:
        if relationship_event_fingerprint(event) != event.event_fingerprint:
            errors.append(
                f"relationship event fingerprint mismatch: {event.relationship_event_id}"
            )
        pure = PurePosixPath(event.supporting_artifact)
        if not repository_root.joinpath(*pure.parts).is_file():
            errors.append(f"missing relationship evidence: {event.supporting_artifact}")
        else:
            artifacts += 1
    return EvolutionDiagnostics(
        valid=not errors,
        errors=tuple(errors),
        histories_validated=len(history.histories),
        events_validated=sum(len(item.events) for item in history.histories),
        relationships_validated=len(history.relationship_history),
        artifacts_validated=artifacts,
    )


def serialize_history(path: Path, history: KnowledgeEvolutionHistory) -> None:
    payload = (
        json.dumps(
            history.model_dump(mode="json"),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except OSError:
        temporary.unlink(missing_ok=True)
        raise


def deserialize_history(path: Path) -> KnowledgeEvolutionHistory:
    return KnowledgeEvolutionHistory.model_validate_json(
        path.read_text(encoding="utf-8")
    )


def statistics(history: KnowledgeEvolutionHistory) -> dict:
    states = Counter(item.current_state.status.value for item in history.histories)
    return {
        "schema_version": 1,
        "knowledge_entries": len(history.histories),
        "evolution_events": sum(len(item.events) for item in history.histories),
        "relationship_events": len(history.relationship_history),
        "states": {state.value: states[state.value] for state in LifecycleState},
        "confirmation_statistics": {
            "confirmations": sum(item.confirmations for item in history.histories),
            "refinements": sum(item.refinements for item in history.histories),
            "contradictions": sum(item.contradictions for item in history.histories),
            "supersessions": sum(item.supersessions for item in history.histories),
            "deprecations": sum(item.deprecations for item in history.histories),
        },
    }
