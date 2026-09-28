"""Canonical VNext workflow state authority, isolated from product components."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from .vnext_foundation_v1 import (
    BoundaryError,
    atomic_json,
    object_identity,
    validate_schema,
)

SCHEMA_VERSION = 1
INITIAL_STATE = "DISCOVERED"
TERMINAL_FAILURES = frozenset({
    "CAPTURE_FAILED", "SOURCE_PACKET_INVALID", "EDITOR_FAILED",
    "FACTUAL_ACCEPTANCE_FAILED", "VOICE_UNAVAILABLE", "FINAL_ASSEMBLY_FAILED",
})
TRANSITIONS = frozenset({
    ("DISCOVERED", "CAPTURED"), ("DISCOVERED", "CAPTURE_FAILED"),
    ("CAPTURED", "GROUPED"), ("GROUPED", "SELECTED"),
    ("SELECTED", "SOURCE_PACKET_READY"), ("SELECTED", "SOURCE_PACKET_INVALID"),
    ("SOURCE_PACKET_READY", "EDITOR_PENDING"),
    ("EDITOR_PENDING", "EDITOR_DRAFT_READY"), ("EDITOR_PENDING", "EDITOR_FAILED"),
    ("EDITOR_DRAFT_READY", "STRUCTURAL_PASS"), ("EDITOR_DRAFT_READY", "STRUCTURAL_FAIL"),
    ("STRUCTURAL_PASS", "FACTUAL_REVIEW_PENDING"),
    ("FACTUAL_REVIEW_PENDING", "ACCEPTED_SETUP"),
    ("FACTUAL_REVIEW_PENDING", "SOURCE_FALLBACK"),
    ("FACTUAL_REVIEW_PENDING", "ABSTAINED"),
    ("FACTUAL_REVIEW_PENDING", "FACTUAL_ACCEPTANCE_FAILED"),
    ("ACCEPTED_SETUP", "VOICE_PENDING"), ("ACCEPTED_SETUP", "VOICE_DISABLED"),
    ("SOURCE_FALLBACK", "VOICE_PENDING"), ("SOURCE_FALLBACK", "VOICE_DISABLED"),
    ("VOICE_PENDING", "VOICE_DRAFT_READY"), ("VOICE_PENDING", "VOICE_UNAVAILABLE"),
    ("VOICE_DRAFT_READY", "POLICY_REVIEW_PENDING"),
    ("VOICE_DISABLED", "POLICY_REVIEW_PENDING"),
    ("POLICY_REVIEW_PENDING", "APPROVED_FOR_FINAL"),
    ("POLICY_REVIEW_PENDING", "REJECTED"),
    ("POLICY_REVIEW_PENDING", "REVISION_REQUIRED"),
    ("APPROVED_FOR_FINAL", "FINAL_READY"),
    ("APPROVED_FOR_FINAL", "FINAL_ASSEMBLY_FAILED"),
    ("FINAL_READY", "EXPORTED"),
})
STATES = frozenset(value for pair in TRANSITIONS for value in pair) | TERMINAL_FAILURES


class IllegalTransition(BoundaryError):
    pass


class ReplayConflict(BoundaryError):
    pass


@dataclass(frozen=True)
class TransitionRequest:
    workflow_id: str
    operation_id: str
    previous_state: str
    resulting_state: str
    actor: str
    outcome: str
    input_identity: str
    output_identity: str | None
    attempt_identity: str
    idempotency_identity: str
    observed_at: str | None = None
    provenance: Mapping[str, str] | None = None

    def semantic(self) -> dict[str, object]:
        return {
            "schema": "vnext-operational-receipt",
            "schema_version": SCHEMA_VERSION,
            "workflow_identity": self.workflow_id,
            "operation_identity": self.operation_id,
            "previous_state": self.previous_state,
            "resulting_state": self.resulting_state,
            "actor": self.actor,
            "outcome": self.outcome,
            "input_identity": self.input_identity,
            "output_identity": self.output_identity,
            "attempt_identity": self.attempt_identity,
            "idempotency_identity": self.idempotency_identity,
        }

    def receipt(self) -> dict[str, object]:
        value = self.semantic()
        value["receipt_identity"] = object_identity(value)
        if self.observed_at is not None:
            value["observed_at"] = self.observed_at
        if self.provenance is not None:
            value["provenance"] = dict(sorted(self.provenance.items()))
        return value


def new_workflow(workflow_id: str) -> dict[str, object]:
    if not workflow_id:
        raise BoundaryError("workflow identity required")
    value: dict[str, object] = {
        "schema": "vnext-workflow-state",
        "schema_version": SCHEMA_VERSION,
        "workflow_identity": workflow_id,
        "state": INITIAL_STATE,
        "receipts": [],
        "idempotency": {},
    }
    value["state_identity"] = object_identity(value)
    return value


def validate_workflow(value: Mapping[str, object]) -> None:
    validate_schema(value, "vnext-workflow-state")
    if value.get("state") not in STATES or not isinstance(value.get("workflow_identity"), str):
        raise BoundaryError("invalid workflow state")
    if not isinstance(value.get("receipts"), list) or not isinstance(value.get("idempotency"), Mapping):
        raise BoundaryError("invalid workflow history")
    expected = object_identity({key: item for key, item in value.items() if key != "state_identity"})
    if value.get("state_identity") != expected:
        raise BoundaryError("workflow identity mismatch")


def apply_transition(value: Mapping[str, object], request: TransitionRequest) -> tuple[dict[str, object], dict[str, object], bool]:
    validate_workflow(value)
    if request.workflow_id != value["workflow_identity"]:
        raise IllegalTransition("workflow mismatch")
    receipt = request.receipt()
    fingerprint = object_identity(request.semantic())
    idempotency = dict(value["idempotency"])
    existing = idempotency.get(request.idempotency_identity)
    if existing is not None:
        if existing != fingerprint:
            raise ReplayConflict(f"conflicting replay: {request.idempotency_identity}")
        prior = next(item for item in value["receipts"] if item["idempotency_identity"] == request.idempotency_identity)
        return dict(value), dict(prior), False
    if request.previous_state != value["state"]:
        raise IllegalTransition(f"expected state {value['state']}, got {request.previous_state}")
    if (request.previous_state, request.resulting_state) not in TRANSITIONS:
        raise IllegalTransition(f"illegal transition: {request.previous_state} -> {request.resulting_state}")
    receipts = [dict(item) for item in value["receipts"]]
    receipts.append(receipt)
    idempotency[request.idempotency_identity] = fingerprint
    updated: dict[str, object] = {
        "schema": "vnext-workflow-state",
        "schema_version": SCHEMA_VERSION,
        "workflow_identity": request.workflow_id,
        "state": request.resulting_state,
        "receipts": receipts,
        "idempotency": idempotency,
    }
    updated["state_identity"] = object_identity(updated)
    return updated, receipt, True


class WorkflowStore:
    """A fixture boundary store; the future product may persist the same document in SQLite."""

    def __init__(self, root: Path):
        self.root = root.resolve(strict=True)

    def path(self, workflow_id: str) -> Path:
        if not workflow_id or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in workflow_id):
            raise BoundaryError("unsafe workflow identity")
        return self.root / f"{workflow_id}.json"

    def create(self, workflow_id: str) -> dict[str, object]:
        value = new_workflow(workflow_id)
        atomic_json(self.path(workflow_id), value, root=self.root, overwrite=False)
        return value

    def load(self, workflow_id: str) -> dict[str, object]:
        import json

        value = json.loads(self.path(workflow_id).read_text(encoding="utf-8"))
        validate_workflow(value)
        return value

    def transition(self, request: TransitionRequest) -> tuple[dict[str, object], dict[str, object], bool]:
        current = self.load(request.workflow_id)
        updated, receipt, changed = apply_transition(current, request)
        if changed:
            atomic_json(self.path(request.workflow_id), updated, root=self.root, overwrite=True)
        return updated, receipt, changed
