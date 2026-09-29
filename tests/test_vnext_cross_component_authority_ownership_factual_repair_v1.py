from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from pastila_scout.vnext_editor_vertical_slice_v1 import (
    DECODING,
    GenerationEvidence,
    build_structural_failure,
    persist_editor_draft,
    persist_structural_failure,
    run_editor_vertical_slice,
)
from pastila_scout.vnext_factual_acceptance_v1 import (
    FactualAcceptanceError,
    adjudicate,
    authorize_review_session,
    build_review_decision,
    persist_factual_result,
)
from pastila_scout.vnext_foundation_v1 import atomic_json, object_identity
from pastila_scout.vnext_state_sqlite_v1 import SCHEMA_VERSION, SQLiteStateStore
from pastila_scout.vnext_workflow_v1 import STATES, TRANSITIONS, TransitionRequest

EDITOR = Path("docs/artifacts/vnext-critical-path-authority-repair-editor-vertical-slice-v1-fixture.json")
SOURCE = Path("docs/artifacts/vnext-sourcepacket-production-binding-v1-fixture.json")
AUTHORITY = Path("docs/artifacts/vnext-active-product-workflow-state-contract-v4.json")
FIXTURE = Path("docs/artifacts/vnext-cross-component-authority-ownership-factual-repair-v1-fixture.json")


def _canonical_packet(packet, workflow_identity="fixture-flow"):
    packet = dict(packet)
    receipt = {
        "schema": "vnext-source-selection-receipt",
        "schema_version": 1,
        "workflow_identity": workflow_identity,
        "event_identity": packet["event_identity"],
        "actor": "fixture-reviewer",
        "authorization_identity": "a" * 64,
        "transition_receipt_identity": "b" * 64,
    }
    receipt["receipt_identity"] = object_identity(receipt)
    packet["selection_authority"] = "EXPLICIT_USER_EVENT_ID"
    packet["selection_receipt"] = receipt
    packet["packet_identity"] = object_identity(
        {key: value for key, value in packet.items() if key != "packet_identity"}
    )
    return packet


class Backend:
    r2_lock_identity = "53fafbc03f70c8c32357645a6a428260f1bdfbd104edbe1c4aa825e95c83a10f"
    def __init__(self, evidence): self.evidence = evidence
    def generate(self, messages, decoding): assert decoding == DECODING; return self.evidence


def inputs():
    editor = json.loads(EDITOR.read_text(encoding="utf-8")); packet = _canonical_packet(json.loads(SOURCE.read_text(encoding="utf-8"))["source_packet"])
    evidence = GenerationEvidence(editor["rendered_prompt"], tuple(editor["input_token_ids"]), editor["raw_output"].encode(), editor["eos_token_id"], editor["pad_token_id"], editor["chat_template_sha256"])
    invocation, draft = run_editor_vertical_slice(packet, Backend(evidence))
    failure = build_structural_failure(packet, failure_code="STRICT_JSON_INVALID", evidence_identity="a" * 64)
    return packet, invocation, draft, failure


def transition(flow, left, right, index):
    return TransitionRequest(flow, f"fixture:{index}", left, right, "fixture", "PASS", object_identity(index), object_identity(index + 1), f"attempt:{flow}:{index}", f"idem:{flow}:{index}")


def prepare(store, flow, *, failure=False):
    packet, invocation, draft, failed = inputs(); store.create_workflow(flow)
    for index, (left, right) in enumerate((("DISCOVERED", "CAPTURED"), ("CAPTURED", "GROUPED"), ("GROUPED", "SELECTED")), 1): store.transition(transition(flow, left, right, index))
    store.transition(TransitionRequest(flow, "fixture:4", "SELECTED", "SOURCE_PACKET_READY", "fixture", "PASS", object_identity(4), packet["packet_identity"], f"attempt:{flow}:4", f"idem:{flow}:4"))
    relative = Path("blobs/source-packets") / f"{packet['packet_identity']}.json"
    if not (store.root / relative).exists():
        atomic_json(store.root / relative, packet, root=store.root, overwrite=False)
    with store.write() as connection:
        connection.execute("INSERT OR IGNORE INTO events VALUES(?,?)", (packet["event_identity"], "fixture-group"))
        connection.execute("INSERT OR IGNORE INTO source_packets VALUES(?,?,?,?)", (packet["packet_identity"], packet["event_identity"], packet["packet_identity"], relative.as_posix()))
    if failure: persist_structural_failure(store, workflow_identity=flow, packet=packet, failure=failed, observed_at="2026-09-29T00:00:00Z")
    else: persist_editor_draft(store, workflow_identity=flow, packet=packet, invocation=invocation, draft=draft, observed_at="2026-09-29T00:00:00Z")
    return packet, invocation, draft, failed


def decide(store, flow, outcome, *, failure=False):
    packet, invocation, draft, failed = inputs(); spans = [packet["spans"][0]["span_id"]] if outcome == "APPROVE_SOURCE_FALLBACK" else []
    kwargs = {"structural_failure": failed} if failure else {"draft": draft, "invocation_receipt": invocation}
    session = authorize_review_session(
        store, workflow_identity=flow, packet=packet, actor="owner", allowed_outcome=outcome,
        authorization_identity=object_identity({"owner-authorization": flow, "outcome": outcome}), **kwargs,
    )
    decision = build_review_decision(workflow_identity=flow, review_session=session, packet=packet, outcome=outcome, actor="owner", reason_code="REVIEWED", fallback_span_ids=spans, **kwargs)
    receipt, artifact = adjudicate(workflow_identity=flow, packet=packet, decision=decision, **kwargs)
    return packet, invocation, draft, failed, session, decision, receipt, artifact


def test_workflow_authority_exactly_matches_executable_contract():
    value = json.loads(AUTHORITY.read_text(encoding="utf-8"))
    assert set(map(tuple, value["transitions"])) == set(TRANSITIONS)
    assert set(value["states"]) == set(STATES)
    assert ("STRUCTURAL_FAIL", "FACTUAL_REVIEW_PENDING") in TRANSITIONS
    assert ("STRUCTURAL_FAIL", "SOURCE_FALLBACK") not in TRANSITIONS


@pytest.mark.parametrize(("outcome", "kind"), (("ACCEPT_DRAFT", "ACCEPTED_SETUP"), ("APPROVE_SOURCE_FALLBACK", "SOURCE_FALLBACK"), ("ABSTAIN", "ABSTAINED")))
def test_draft_review_has_three_exclusive_bound_results(tmp_path, outcome, kind):
    store = SQLiteStateStore(root=tmp_path, database=Path("state.db"), writer_identity="writer"); store.bootstrap(); prepare(store, "flow")
    *_, decision, receipt, artifact = decide(store, "flow", outcome)
    assert artifact["artifact_kind"] == kind and artifact["workflow_identity"] == "flow"
    assert decision["authority_mode"] == "PERSISTED_SINGLE_USE_REVIEW_SESSION"
    assert receipt["workflow_identity"] == "flow"


def test_structural_failure_uses_same_gate_and_cannot_be_accepted(tmp_path):
    store = SQLiteStateStore(root=tmp_path, database=Path("state.db"), writer_identity="writer"); store.bootstrap(); prepare(store, "failed", failure=True)
    *_, artifact = decide(store, "failed", "APPROVE_SOURCE_FALLBACK", failure=True)
    assert artifact["artifact_kind"] == "SOURCE_FALLBACK" and artifact["review_input_kind"] == "STRUCTURAL_FAILURE"
    packet, _, _, failed = inputs()
    with pytest.raises(FactualAcceptanceError, match="incompatible"):
        authorize_review_session(store, workflow_identity="failed", packet=packet, actor="owner", allowed_outcome="ACCEPT_DRAFT", authorization_identity="a" * 64, structural_failure=failed)


def test_workflow_bound_identity_and_cross_workflow_associations(tmp_path):
    store = SQLiteStateStore(root=tmp_path, database=Path("state.db"), writer_identity="writer"); store.bootstrap()
    assert SCHEMA_VERSION == 7
    for flow in ("flow-a", "flow-b"):
        prepare(store, flow); packet, invocation, draft, _, _, decision, receipt, artifact = decide(store, flow, "ACCEPT_DRAFT")
        persist_factual_result(store, workflow_identity=flow, packet=packet, draft=draft, invocation_receipt=invocation, decision=decision, receipt=receipt, artifact=artifact, observed_at="2026-09-29T00:01:00Z")
    with store.read() as connection:
        assert connection.execute("SELECT COUNT(*) FROM workflow_artifacts WHERE artifact_kind='EDITOR_DRAFT'").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM workflow_artifacts WHERE artifact_kind='ACCEPTED_SETUP'").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 2
        assert connection.execute("SELECT COUNT(DISTINCT decision_identity) FROM decisions").fetchone()[0] == 2


def test_structural_failure_persists_noneligible_then_reviewed_fallback(tmp_path):
    store = SQLiteStateStore(root=tmp_path, database=Path("state.db"), writer_identity="writer"); store.bootstrap()
    prepare(store, "failed", failure=True)
    assert store.load_workflow("failed")["state"] == "FACTUAL_REVIEW_PENDING"
    packet, _, _, failed, _, decision, receipt, artifact = decide(store, "failed", "APPROVE_SOURCE_FALLBACK", failure=True)
    persist_factual_result(store, workflow_identity="failed", packet=packet, structural_failure=failed, decision=decision, receipt=receipt, artifact=artifact, observed_at="2026-09-29T00:01:00Z")
    with store.read() as connection:
        assert connection.execute("SELECT artifact_kind FROM workflow_artifacts WHERE artifact_kind='STRUCTURAL_FAILURE'").fetchone()[0] == "STRUCTURAL_FAILURE"
        assert connection.execute("SELECT outcome FROM decisions").fetchone()[0] == "APPROVE_SOURCE_FALLBACK"


def test_wrong_workflow_or_tampering_fails_before_publication(tmp_path):
    store = SQLiteStateStore(root=tmp_path, database=Path("state.db"), writer_identity="writer"); store.bootstrap(); prepare(store, "flow")
    (tmp_path / "other").mkdir(); other = SQLiteStateStore(root=tmp_path / "other", database=Path("state.db"), writer_identity="writer"); other.bootstrap(); prepare(other, "other")
    packet, invocation, draft, _, _, decision, receipt, artifact = decide(other, "other", "ACCEPT_DRAFT")
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*.json"))
    with pytest.raises(FactualAcceptanceError, match="provenance|workflow"):
        persist_factual_result(store, workflow_identity="flow", packet=packet, draft=draft, invocation_receipt=invocation, decision=decision, receipt=receipt, artifact=artifact, observed_at="2026-09-29T00:01:00Z")
    assert sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*.json")) == before
    changed = copy.deepcopy(decision); changed["actor"] = "attacker"
    with pytest.raises(FactualAcceptanceError): adjudicate(workflow_identity="other", packet=packet, draft=draft, invocation_receipt=invocation, decision=changed)


def test_unregistered_or_replayed_review_session_is_rejected(tmp_path):
    store = SQLiteStateStore(root=tmp_path, database=Path("state.db"), writer_identity="writer"); store.bootstrap(); packet, invocation, draft, _ = prepare(store, "flow")
    fake = {
        "schema": "vnext-factual-review-session", "schema_version": 2, "request_identity": "b" * 64, "workflow_identity": "flow",
        "issued_by": "writer", "actor": "owner", "source_packet_identity": packet["packet_identity"], "input_kind": "EDITOR_DRAFT",
        "input_identity": draft["draft_identity"], "allowed_outcome": "ACCEPT_DRAFT",
        "authorization_identity": "a" * 64, "status": "OPEN",
    }
    fake["review_session_identity"] = object_identity(fake)
    decision = build_review_decision(workflow_identity="flow", review_session=fake, packet=packet, outcome="ACCEPT_DRAFT", actor="owner", reason_code="REVIEWED", draft=draft, invocation_receipt=invocation)
    receipt, artifact = adjudicate(workflow_identity="flow", packet=packet, decision=decision, draft=draft, invocation_receipt=invocation)
    with pytest.raises(FactualAcceptanceError, match="absent"):
        persist_factual_result(store, workflow_identity="flow", packet=packet, draft=draft, invocation_receipt=invocation, decision=decision, receipt=receipt, artifact=artifact, observed_at="2026-09-29T00:01:00Z")

    authorization = object_identity({"owner-authorization": "flow", "outcome": "ACCEPT_DRAFT"})
    first_session = authorize_review_session(store, workflow_identity="flow", packet=packet, actor="owner", allowed_outcome="ACCEPT_DRAFT", authorization_identity=authorization, draft=draft, invocation_receipt=invocation)
    replayed_session = authorize_review_session(store, workflow_identity="flow", packet=packet, actor="owner", allowed_outcome="ACCEPT_DRAFT", authorization_identity=authorization, draft=draft, invocation_receipt=invocation)
    assert replayed_session == first_session
    valid_decision = build_review_decision(workflow_identity="flow", review_session=first_session, packet=packet, outcome="ACCEPT_DRAFT", actor="owner", reason_code="REVIEWED", draft=draft, invocation_receipt=invocation)
    valid_receipt, valid_artifact = adjudicate(workflow_identity="flow", packet=packet, decision=valid_decision, draft=draft, invocation_receipt=invocation)
    persist_factual_result(store, workflow_identity="flow", packet=packet, draft=draft, invocation_receipt=invocation, decision=valid_decision, receipt=valid_receipt, artifact=valid_artifact, observed_at="2026-09-29T00:01:00Z")
    persist_factual_result(store, workflow_identity="flow", packet=packet, draft=draft, invocation_receipt=invocation, decision=valid_decision, receipt=valid_receipt, artifact=valid_artifact, observed_at="2026-09-29T00:01:00Z")
    with store.read() as connection:
        assert connection.execute("SELECT status FROM review_sessions").fetchone()[0] == "CONSUMED"


def test_successor_fixture_is_utf8_and_content_addressed():
    value = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert object_identity({k: v for k, v in value.items() if k != "fixture_identity"}) == value["fixture_identity"]
    assert "ș" in value["romanian_text"] and "ț" in value["romanian_text"] and "?" not in value["romanian_text"]
