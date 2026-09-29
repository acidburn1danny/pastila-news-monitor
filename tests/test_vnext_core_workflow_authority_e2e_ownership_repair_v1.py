from __future__ import annotations

import json
from pathlib import Path

import pytest

from pastila_scout.vnext_core_final_v1 import (
    CoreFinalError,
    assemble_and_export_final,
    authorize_policy_session,
    build_policy_decision,
    enter_policy_review,
    persist_policy_decision,
)
from pastila_scout.vnext_editor_vertical_slice_v1 import (
    DECODING,
    GenerationEvidence,
    persist_editor_draft,
    run_editor_vertical_slice,
)
from pastila_scout.vnext_factual_acceptance_v1 import (
    adjudicate,
    authorize_review_session,
    build_review_decision,
    persist_factual_result,
)
from pastila_scout.vnext_foundation_v1 import atomic_json, object_identity
from pastila_scout.vnext_state_sqlite_v1 import SQLiteStateStore
from pastila_scout.vnext_workflow_v1 import TransitionRequest

EDITOR = Path("docs/artifacts/vnext-critical-path-authority-repair-editor-vertical-slice-v1-fixture.json")
SOURCE = Path("docs/artifacts/vnext-sourcepacket-production-binding-v1-fixture.json")


class Backend:
    r2_lock_identity = "53fafbc03f70c8c32357645a6a428260f1bdfbd104edbe1c4aa825e95c83a10f"

    def __init__(self, evidence: GenerationEvidence):
        self.evidence = evidence

    def generate(self, messages, decoding):
        assert decoding == DECODING
        return self.evidence


def transition(store, flow, left, right, index, output=None):
    semantic = {"flow": flow, "left": left, "right": right, "index": index}
    identity = object_identity(semantic)
    store.transition(
        TransitionRequest(
            flow, f"e2e:{index}", left, right, "fixture", "PASS",
            object_identity(index), output or object_identity(index + 1),
            f"attempt:{identity}", f"idempotency:{identity}",
        )
    )


def prepare_through_factual_acceptance(tmp_path, *, outcome="ACCEPT_DRAFT"):
    editor = json.loads(EDITOR.read_text(encoding="utf-8"))
    packet = json.loads(SOURCE.read_text(encoding="utf-8"))["source_packet"]
    evidence = GenerationEvidence(
        editor["rendered_prompt"], tuple(editor["input_token_ids"]),
        editor["raw_output"].encode(), editor["eos_token_id"],
        editor["pad_token_id"], editor["chat_template_sha256"],
    )
    invocation, draft = run_editor_vertical_slice(packet, Backend(evidence))
    store = SQLiteStateStore(root=tmp_path, database=Path("state.db"), writer_identity="writer")
    store.bootstrap()
    flow = "e2e-flow"
    store.create_workflow(flow)
    for index, (left, right) in enumerate(
        (("DISCOVERED", "CAPTURED"), ("CAPTURED", "GROUPED"), ("GROUPED", "SELECTED")), 1
    ):
        transition(store, flow, left, right, index)
    transition(store, flow, "SELECTED", "SOURCE_PACKET_READY", 4, packet["packet_identity"])
    relative = Path("blobs/source-packets") / f"{packet['packet_identity']}.json"
    atomic_json(tmp_path / relative, packet, root=tmp_path, overwrite=False)
    with store.write() as connection:
        connection.execute("INSERT INTO events VALUES(?,?)", (packet["event_identity"], "e2e-group"))
        connection.execute(
            "INSERT INTO source_packets VALUES(?,?,?,?)",
            (packet["packet_identity"], packet["event_identity"], packet["packet_identity"], relative.as_posix()),
        )
    persist_editor_draft(
        store, workflow_identity=flow, packet=packet, invocation=invocation,
        draft=draft, observed_at="2026-09-29T00:00:00Z",
    )
    spans = [packet["spans"][0]["span_id"]] if outcome == "APPROVE_SOURCE_FALLBACK" else []
    review = authorize_review_session(
        store, workflow_identity=flow, packet=packet, actor="owner",
        allowed_outcome=outcome,
        authorization_identity=object_identity({"factual-authority": flow, "outcome": outcome}),
        draft=draft, invocation_receipt=invocation,
    )
    decision = build_review_decision(
        workflow_identity=flow, review_session=review, packet=packet,
        outcome=outcome, actor="owner", reason_code="REVIEWED",
        draft=draft, invocation_receipt=invocation, fallback_span_ids=spans,
    )
    receipt, artifact = adjudicate(
        workflow_identity=flow, packet=packet, decision=decision,
        draft=draft, invocation_receipt=invocation,
    )
    persist_factual_result(
        store, workflow_identity=flow, packet=packet, decision=decision,
        receipt=receipt, artifact=artifact, draft=draft,
        invocation_receipt=invocation, observed_at="2026-09-29T00:01:00Z",
    )
    return store, flow, artifact


def approve_and_export(store, flow, artifact):
    enter_policy_review(
        store, workflow_identity=flow, factual_output=artifact,
        observed_at="2026-09-29T00:02:00Z",
    )
    session = authorize_policy_session(
        store, workflow_identity=flow, factual_output=artifact, actor="owner",
        allowed_outcome="APPROVE_FINAL",
        authorization_identity=object_identity({"policy-authority": flow}),
    )
    decision = build_policy_decision(
        workflow_identity=flow, factual_output=artifact, session=session,
        outcome="APPROVE_FINAL", actor="owner", reason_code="APPROVED",
    )
    persist_policy_decision(
        store, workflow_identity=flow, factual_output=artifact,
        session=session, decision=decision, observed_at="2026-09-29T00:03:00Z",
    )
    return assemble_and_export_final(
        store, workflow_identity=flow, factual_output=artifact,
        decision=decision, observed_at="2026-09-29T00:04:00Z",
    )


@pytest.mark.parametrize("outcome", ["ACCEPT_DRAFT", "APPROVE_SOURCE_FALLBACK"])
def test_real_components_reach_deterministic_final(tmp_path, outcome):
    store, flow, artifact = prepare_through_factual_acceptance(tmp_path, outcome=outcome)
    final, receipt = approve_and_export(store, flow, artifact)
    assert final["text"] == artifact["text"]
    assert final["factual_input_identity"] == artifact["artifact_identity"]
    assert store.load_workflow(flow)["state"] == "EXPORTED"
    assert (tmp_path / receipt["export_ref"]).exists()


def test_fabricated_registered_artifact_without_factual_evidence_is_rejected(tmp_path):
    store, flow, artifact = prepare_through_factual_acceptance(tmp_path)
    with store.write() as connection:
        connection.execute("DELETE FROM decisions WHERE decision_identity=?", (artifact["decision_identity"],))
    with pytest.raises(CoreFinalError, match="provenance"):
        enter_policy_review(
            store, workflow_identity=flow, factual_output=artifact,
            observed_at="2026-09-29T00:02:00Z",
        )


def test_missing_factual_receipt_is_rejected(tmp_path):
    store, flow, artifact = prepare_through_factual_acceptance(tmp_path)
    with store.read() as connection:
        receipt_identity = connection.execute(
            "SELECT receipt_identity FROM decisions WHERE decision_identity=?",
            (artifact["decision_identity"],),
        ).fetchone()[0]
    (tmp_path / "blobs" / "factual-receipts" / f"{receipt_identity}.json").unlink()
    with pytest.raises(CoreFinalError, match="factual receipt"):
        enter_policy_review(
            store, workflow_identity=flow, factual_output=artifact,
            observed_at="2026-09-29T00:02:00Z",
        )
