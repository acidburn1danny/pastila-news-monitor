"""Workflow-bound factual acceptance for EditorDraft or structural failure."""
from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from pathlib import Path

from .vnext_editor_vertical_slice_v1 import (
    validate_editor_draft,
    validate_structural_failure,
)
from .vnext_foundation_v1 import BoundaryError, atomic_json, object_identity
from .vnext_scout_production_v1 import validate_scout_packet
from .vnext_state_sqlite_v1 import SQLiteStateStore
from .vnext_workflow_v1 import TransitionRequest

OUTCOMES = {"ACCEPT_DRAFT", "APPROVE_SOURCE_FALLBACK", "ABSTAIN"}
RESULT_STATES = {"ACCEPT_DRAFT": "ACCEPTED_SETUP", "APPROVE_SOURCE_FALLBACK": "SOURCE_FALLBACK", "ABSTAIN": "ABSTAINED"}
_SHA256 = re.compile(r"[0-9a-f]{64}")


class FactualAcceptanceError(BoundaryError):
    pass


def _identity(value: Mapping[str, object], key: str) -> str:
    actual = value.get(key)
    if not isinstance(actual, str) or _SHA256.fullmatch(actual) is None or actual != object_identity({k: v for k, v in value.items() if k != key}):
        raise FactualAcceptanceError(f"{key} mismatch")
    return actual


def _review_input(*, packet: Mapping[str, object], draft: Mapping[str, object] | None,
                  invocation_receipt: Mapping[str, object] | None,
                  structural_failure: Mapping[str, object] | None) -> tuple[str, str]:
    if (draft is None) == (structural_failure is None):
        raise FactualAcceptanceError("exactly one factual review input is required")
    if draft is not None:
        if invocation_receipt is None:
            raise FactualAcceptanceError("EditorDraft requires its invocation receipt")
        validate_editor_draft(draft, source_packet=packet, invocation_receipt=invocation_receipt)
        return "EDITOR_DRAFT", str(draft["draft_identity"])
    if invocation_receipt is not None:
        raise FactualAcceptanceError("structural failure cannot use an invocation receipt")
    assert structural_failure is not None
    validate_structural_failure(structural_failure, packet=packet)
    return "STRUCTURAL_FAILURE", str(structural_failure["failure_identity"])


def build_review_decision(*, workflow_identity: str, review_session_identity: str,
                          packet: Mapping[str, object], outcome: str, actor: str,
                          reason_code: str, draft: Mapping[str, object] | None = None,
                          invocation_receipt: Mapping[str, object] | None = None,
                          structural_failure: Mapping[str, object] | None = None,
                          fallback_span_ids: Sequence[str] = ()) -> dict[str, object]:
    input_kind, input_identity = _review_input(packet=packet, draft=draft, invocation_receipt=invocation_receipt, structural_failure=structural_failure)
    if not workflow_identity or _SHA256.fullmatch(review_session_identity) is None:
        raise FactualAcceptanceError("workflow and review-session authority are required")
    if outcome not in OUTCOMES or (outcome == "ACCEPT_DRAFT" and input_kind != "EDITOR_DRAFT"):
        raise FactualAcceptanceError("outcome is incompatible with factual review input")
    if not actor.strip() or not reason_code.strip():
        raise FactualAcceptanceError("review actor and reason code are required")
    span_ids = tuple(fallback_span_ids)
    known = {str(span["span_id"]) for span in validate_scout_packet(packet)}
    if len(set(span_ids)) != len(span_ids) or any(value not in known for value in span_ids):
        raise FactualAcceptanceError("fallback span binding mismatch")
    if (outcome == "APPROVE_SOURCE_FALLBACK") != bool(span_ids):
        raise FactualAcceptanceError("approved source fallback requires explicit source spans")
    decision: dict[str, object] = {
        "schema": "vnext-factual-review-decision", "schema_version": 2,
        "decision_kind": "FACTUAL", "outcome": outcome,
        "workflow_identity": workflow_identity, "review_session_identity": review_session_identity,
        "actor": actor.strip(), "reason_code": reason_code.strip(),
        "source_packet_identity": packet["packet_identity"], "input_kind": input_kind,
        "input_identity": input_identity, "fallback_span_ids": list(span_ids),
        "authority_mode": "EXPLICIT_TRUSTED_REVIEW_SESSION",
    }
    decision["decision_identity"] = object_identity(decision)
    return decision


def validate_review_decision(decision: Mapping[str, object], *, workflow_identity: str,
                             packet: Mapping[str, object], input_kind: str, input_identity: str) -> None:
    required = {"schema", "schema_version", "decision_kind", "outcome", "workflow_identity", "review_session_identity", "actor", "reason_code", "source_packet_identity", "input_kind", "input_identity", "fallback_span_ids", "authority_mode", "decision_identity"}
    if set(decision) != required or decision.get("schema") != "vnext-factual-review-decision" or decision.get("schema_version") != 2:
        raise FactualAcceptanceError("factual decision schema mismatch")
    if decision.get("decision_kind") != "FACTUAL" or decision.get("outcome") not in OUTCOMES:
        raise FactualAcceptanceError("factual decision kind/outcome mismatch")
    if decision.get("authority_mode") != "EXPLICIT_TRUSTED_REVIEW_SESSION" or _SHA256.fullmatch(str(decision.get("review_session_identity"))) is None:
        raise FactualAcceptanceError("trusted review-session authority missing")
    if decision.get("workflow_identity") != workflow_identity or decision.get("source_packet_identity") != packet.get("packet_identity") or decision.get("input_kind") != input_kind or decision.get("input_identity") != input_identity:
        raise FactualAcceptanceError("factual decision provenance mismatch")
    if input_kind == "STRUCTURAL_FAILURE" and decision.get("outcome") == "ACCEPT_DRAFT":
        raise FactualAcceptanceError("structural failure cannot be accepted")
    if not isinstance(decision.get("actor"), str) or not str(decision["actor"]).strip() or not isinstance(decision.get("reason_code"), str) or not str(decision["reason_code"]).strip():
        raise FactualAcceptanceError("review actor and reason code are required")
    spans = decision.get("fallback_span_ids")
    known = {str(span["span_id"]) for span in validate_scout_packet(packet)}
    if not isinstance(spans, list) or not all(isinstance(v, str) for v in spans) or len(set(spans)) != len(spans) or any(v not in known for v in spans):
        raise FactualAcceptanceError("fallback span binding mismatch")
    if (decision["outcome"] == "APPROVE_SOURCE_FALLBACK") != bool(spans):
        raise FactualAcceptanceError("fallback approval/span invariant failed")
    _identity(decision, "decision_identity")


def adjudicate(*, workflow_identity: str, packet: Mapping[str, object], decision: Mapping[str, object],
               draft: Mapping[str, object] | None = None, invocation_receipt: Mapping[str, object] | None = None,
               structural_failure: Mapping[str, object] | None = None) -> tuple[dict[str, object], dict[str, object]]:
    input_kind, input_identity = _review_input(packet=packet, draft=draft, invocation_receipt=invocation_receipt, structural_failure=structural_failure)
    validate_review_decision(decision, workflow_identity=workflow_identity, packet=packet, input_kind=input_kind, input_identity=input_identity)
    outcome = str(decision["outcome"]); kind = RESULT_STATES[outcome]
    if outcome == "ACCEPT_DRAFT":
        assert draft is not None; text: str | None = str(draft["text"])
    elif outcome == "APPROVE_SOURCE_FALLBACK":
        by_id = {str(s["span_id"]): str(s["text"]) for s in validate_scout_packet(packet)}
        text = " ".join(by_id[v] for v in decision["fallback_span_ids"])
    else:
        text = None
    artifact: dict[str, object] = {
        "schema": "vnext-factual-output", "schema_version": 2, "artifact_kind": kind,
        "workflow_identity": workflow_identity, "event_identity": packet["event_identity"],
        "source_packet_identity": packet["packet_identity"], "review_input_kind": input_kind,
        "review_input_identity": input_identity, "decision_identity": decision["decision_identity"],
        "text": text, "eligible_for_voice": kind != "ABSTAINED",
        "requires_explicit_approval": kind == "SOURCE_FALLBACK",
    }
    artifact["artifact_identity"] = object_identity(artifact)
    receipt: dict[str, object] = {
        "schema": "vnext-factual-acceptance-receipt", "schema_version": 2,
        "workflow_identity": workflow_identity, "decision_identity": decision["decision_identity"],
        "input_identity": input_identity, "output_identity": artifact["artifact_identity"], "resulting_state": kind,
    }
    receipt["receipt_identity"] = object_identity(receipt)
    validate_factual_output(artifact, workflow_identity=workflow_identity, packet=packet, decision=decision, receipt=receipt, draft=draft, invocation_receipt=invocation_receipt, structural_failure=structural_failure)
    return receipt, artifact


def validate_factual_output(artifact: Mapping[str, object], *, workflow_identity: str,
                            packet: Mapping[str, object], decision: Mapping[str, object], receipt: Mapping[str, object],
                            draft: Mapping[str, object] | None = None, invocation_receipt: Mapping[str, object] | None = None,
                            structural_failure: Mapping[str, object] | None = None) -> None:
    input_kind, input_identity = _review_input(packet=packet, draft=draft, invocation_receipt=invocation_receipt, structural_failure=structural_failure)
    validate_review_decision(decision, workflow_identity=workflow_identity, packet=packet, input_kind=input_kind, input_identity=input_identity)
    kind = RESULT_STATES[str(decision["outcome"])]
    if artifact.get("schema") != "vnext-factual-output" or artifact.get("schema_version") != 2 or artifact.get("artifact_kind") != kind or artifact.get("workflow_identity") != workflow_identity:
        raise FactualAcceptanceError("factual output schema/workflow mismatch")
    if artifact.get("source_packet_identity") != packet.get("packet_identity") or artifact.get("review_input_kind") != input_kind or artifact.get("review_input_identity") != input_identity or artifact.get("decision_identity") != decision.get("decision_identity"):
        raise FactualAcceptanceError("factual output provenance mismatch")
    expected = None
    if kind == "ACCEPTED_SETUP":
        assert draft is not None; expected = draft["text"]
    elif kind == "SOURCE_FALLBACK":
        by_id = {str(s["span_id"]): str(s["text"]) for s in validate_scout_packet(packet)}
        expected = " ".join(by_id[v] for v in decision["fallback_span_ids"])
    if artifact.get("text") != expected or artifact.get("eligible_for_voice") is not (kind != "ABSTAINED") or artifact.get("requires_explicit_approval") is not (kind == "SOURCE_FALLBACK"):
        raise FactualAcceptanceError("factual output text/eligibility mismatch")
    _identity(artifact, "artifact_identity")
    if receipt.get("schema") != "vnext-factual-acceptance-receipt" or receipt.get("schema_version") != 2 or receipt.get("workflow_identity") != workflow_identity or receipt.get("decision_identity") != decision.get("decision_identity") or receipt.get("input_identity") != input_identity or receipt.get("output_identity") != artifact.get("artifact_identity") or receipt.get("resulting_state") != kind:
        raise FactualAcceptanceError("acceptance receipt binding mismatch")
    _identity(receipt, "receipt_identity")


def persist_factual_result(store: SQLiteStateStore, *, workflow_identity: str, packet: Mapping[str, object],
                           decision: Mapping[str, object], receipt: Mapping[str, object], artifact: Mapping[str, object],
                           observed_at: str, draft: Mapping[str, object] | None = None,
                           invocation_receipt: Mapping[str, object] | None = None,
                           structural_failure: Mapping[str, object] | None = None) -> None:
    validate_factual_output(artifact, workflow_identity=workflow_identity, packet=packet, decision=decision, receipt=receipt, draft=draft, invocation_receipt=invocation_receipt, structural_failure=structural_failure)
    if store.load_workflow(workflow_identity)["state"] != "FACTUAL_REVIEW_PENDING":
        raise FactualAcceptanceError("workflow is not ready for factual review")
    kind = str(artifact["artifact_kind"])
    paths = ((Path("blobs/factual-outputs") / f"{artifact['artifact_identity']}.json", artifact), (Path("blobs/factual-decisions") / f"{decision['decision_identity']}.json", decision), (Path("blobs/factual-receipts") / f"{receipt['receipt_identity']}.json", receipt))
    for relative, value in paths:
        path = store.root / relative
        if path.exists():
            if json.loads(path.read_text(encoding="utf-8")) != value:
                raise FactualAcceptanceError(f"immutable factual evidence conflict: {relative}")
        else:
            atomic_json(path, dict(value), root=store.root, overwrite=False)
    def persist_rows(connection: object) -> None:
        connection.execute("INSERT INTO workflow_artifacts VALUES(?,?,?,?,?,?)", (artifact["artifact_identity"], workflow_identity, kind, artifact["artifact_identity"], paths[0][0].as_posix(), "vnext-factual-output-v2"))
        connection.execute("INSERT INTO decisions VALUES(?,?,?,?,?,?,?)", (decision["decision_identity"], workflow_identity, "FACTUAL", decision["outcome"], decision["actor"], decision["input_identity"], receipt["receipt_identity"]))
    operation = object_identity({"workflow": workflow_identity, "decision": decision["decision_identity"], "output": artifact["artifact_identity"]})
    store.transition(TransitionRequest(workflow_identity, "factual:adjudicate", "FACTUAL_REVIEW_PENDING", kind, "FACTUAL_REVIEW", str(decision["outcome"]), str(decision["input_identity"]), str(artifact["artifact_identity"]), f"attempt:{operation}", f"idempotency:{operation}", observed_at, {"component": "VNext Cross-Component Authority, Artifact Ownership & Factual Acceptance Repair v1", "decision_receipt_identity": str(receipt["receipt_identity"])}), before_commit=persist_rows)
