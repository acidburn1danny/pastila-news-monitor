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
    build_review_decision,
    persist_factual_result,
)
from pastila_scout.vnext_foundation_v1 import object_identity
from pastila_scout.vnext_state_sqlite_v1 import SCHEMA_VERSION, SQLiteStateStore
from pastila_scout.vnext_workflow_v1 import STATES, TRANSITIONS, TransitionRequest

EDITOR = Path("docs/artifacts/vnext-critical-path-authority-repair-editor-vertical-slice-v1-fixture.json")
SOURCE = Path("docs/artifacts/vnext-sourcepacket-production-binding-v1-fixture.json")
AUTHORITY = Path("docs/artifacts/vnext-active-product-workflow-state-contract-v3.json")
FIXTURE = Path("docs/artifacts/vnext-cross-component-authority-ownership-factual-repair-v1-fixture.json")


class Backend:
    r2_lock_identity = "53fafbc03f70c8c32357645a6a428260f1bdfbd104edbe1c4aa825e95c83a10f"
    def __init__(self, evidence): self.evidence = evidence
    def generate(self, messages, decoding): assert decoding == DECODING; return self.evidence


def inputs():
    editor = json.loads(EDITOR.read_text(encoding="utf-8")); packet = json.loads(SOURCE.read_text(encoding="utf-8"))["source_packet"]
    evidence = GenerationEvidence(editor["rendered_prompt"], tuple(editor["input_token_ids"]), editor["raw_output"].encode(), editor["eos_token_id"], editor["pad_token_id"], editor["chat_template_sha256"])
    invocation, draft = run_editor_vertical_slice(packet, Backend(evidence))
    failure = build_structural_failure(packet, failure_code="STRICT_JSON_INVALID", evidence_identity="a" * 64)
    return packet, invocation, draft, failure


def transition(flow, left, right, index):
    return TransitionRequest(flow, f"fixture:{index}", left, right, "fixture", "PASS", object_identity(index), object_identity(index + 1), f"attempt:{flow}:{index}", f"idem:{flow}:{index}")


def prepare(store, flow, *, failure=False):
    packet, invocation, draft, failed = inputs(); store.create_workflow(flow)
    for index, (left, right) in enumerate((("DISCOVERED", "CAPTURED"), ("CAPTURED", "GROUPED"), ("GROUPED", "SELECTED"), ("SELECTED", "SOURCE_PACKET_READY")), 1): store.transition(transition(flow, left, right, index))
    if failure: persist_structural_failure(store, workflow_identity=flow, packet=packet, failure=failed, observed_at="2026-09-29T00:00:00Z")
    else: persist_editor_draft(store, workflow_identity=flow, packet=packet, invocation=invocation, draft=draft, observed_at="2026-09-29T00:00:00Z")
    return packet, invocation, draft, failed


def decide(flow, outcome, *, failure=False):
    packet, invocation, draft, failed = inputs(); spans = [packet["spans"][0]["span_id"]] if outcome == "APPROVE_SOURCE_FALLBACK" else []
    kwargs = {"structural_failure": failed} if failure else {"draft": draft, "invocation_receipt": invocation}
    decision = build_review_decision(workflow_identity=flow, review_session_identity=object_identity({"session": flow}), packet=packet, outcome=outcome, actor="owner", reason_code="REVIEWED", fallback_span_ids=spans, **kwargs)
    receipt, artifact = adjudicate(workflow_identity=flow, packet=packet, decision=decision, **kwargs)
    return packet, invocation, draft, failed, decision, receipt, artifact


def test_workflow_authority_exactly_matches_executable_contract():
    value = json.loads(AUTHORITY.read_text(encoding="utf-8"))
    assert set(map(tuple, value["transitions"])) == set(TRANSITIONS)
    assert set(value["states"]) == set(STATES)
    assert ("STRUCTURAL_FAIL", "FACTUAL_REVIEW_PENDING") in TRANSITIONS
    assert ("STRUCTURAL_FAIL", "SOURCE_FALLBACK") not in TRANSITIONS


@pytest.mark.parametrize(("outcome", "kind"), (("ACCEPT_DRAFT", "ACCEPTED_SETUP"), ("APPROVE_SOURCE_FALLBACK", "SOURCE_FALLBACK"), ("ABSTAIN", "ABSTAINED")))
def test_draft_review_has_three_exclusive_bound_results(outcome, kind):
    *_, decision, receipt, artifact = decide("flow", outcome)
    assert artifact["artifact_kind"] == kind and artifact["workflow_identity"] == "flow"
    assert decision["authority_mode"] == "EXPLICIT_TRUSTED_REVIEW_SESSION"
    assert receipt["workflow_identity"] == "flow"


def test_structural_failure_uses_same_gate_and_cannot_be_accepted():
    *_, artifact = decide("failed", "APPROVE_SOURCE_FALLBACK", failure=True)
    assert artifact["artifact_kind"] == "SOURCE_FALLBACK" and artifact["review_input_kind"] == "STRUCTURAL_FAILURE"
    packet, _, _, failed = inputs()
    with pytest.raises(FactualAcceptanceError, match="incompatible"):
        build_review_decision(workflow_identity="failed", review_session_identity="a" * 64, packet=packet, outcome="ACCEPT_DRAFT", actor="owner", reason_code="bad", structural_failure=failed)


def test_workflow_bound_identity_and_cross_workflow_associations(tmp_path):
    store = SQLiteStateStore(root=tmp_path, database=Path("state.db"), writer_identity="writer"); store.bootstrap()
    assert SCHEMA_VERSION == 3
    for flow in ("flow-a", "flow-b"):
        prepare(store, flow); packet, invocation, draft, _, decision, receipt, artifact = decide(flow, "ACCEPT_DRAFT")
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
    packet, _, _, failed, decision, receipt, artifact = decide("failed", "APPROVE_SOURCE_FALLBACK", failure=True)
    persist_factual_result(store, workflow_identity="failed", packet=packet, structural_failure=failed, decision=decision, receipt=receipt, artifact=artifact, observed_at="2026-09-29T00:01:00Z")
    with store.read() as connection:
        assert connection.execute("SELECT artifact_kind FROM workflow_artifacts WHERE artifact_kind='STRUCTURAL_FAILURE'").fetchone()[0] == "STRUCTURAL_FAILURE"
        assert connection.execute("SELECT outcome FROM decisions").fetchone()[0] == "APPROVE_SOURCE_FALLBACK"


def test_wrong_workflow_or_tampering_fails_before_publication(tmp_path):
    store = SQLiteStateStore(root=tmp_path, database=Path("state.db"), writer_identity="writer"); store.bootstrap(); prepare(store, "flow")
    packet, invocation, draft, _, decision, receipt, artifact = decide("other", "ACCEPT_DRAFT")
    before = sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*.json"))
    with pytest.raises(FactualAcceptanceError, match="provenance|workflow"):
        persist_factual_result(store, workflow_identity="flow", packet=packet, draft=draft, invocation_receipt=invocation, decision=decision, receipt=receipt, artifact=artifact, observed_at="2026-09-29T00:01:00Z")
    assert sorted(path.relative_to(tmp_path) for path in tmp_path.rglob("*.json")) == before
    changed = copy.deepcopy(decision); changed["actor"] = "attacker"
    with pytest.raises(FactualAcceptanceError): adjudicate(workflow_identity="other", packet=packet, draft=draft, invocation_receipt=invocation, decision=changed)


def test_successor_fixture_is_utf8_and_content_addressed():
    value = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert object_identity({k: v for k, v in value.items() if k != "fixture_identity"}) == value["fixture_identity"]
    assert "ș" in value["romanian_text"] and "ț" in value["romanian_text"] and "?" not in value["romanian_text"]
