from __future__ import annotations

import json
from pathlib import Path

import pytest

from pastila_scout.vnext_editor_vertical_slice_v1 import (
    DECODING,
    GenerationEvidence,
)
from pastila_scout.vnext_foundation_v1 import BoundaryError, object_identity
from pastila_scout.vnext_product_orchestrator_v1 import (
    FactualReviewInstruction,
    PolicyInstruction,
    PolicyTerminalBundle,
    ProductOrchestrator,
    ProductOrchestratorError,
    bootstrap_store,
)
from pastila_scout.vnext_core_final_v1 import (
    CoreFinalError,
    load_exported_final,
    authorize_policy_session,
    build_policy_decision,
    enter_policy_review,
    persist_policy_decision,
)
from pastila_scout.vnext_workflow_v1 import TransitionRequest
from pastila_scout.vnext_r2_consolidation_binding_v1 import EXPECTED_LOCK_IDENTITY
from pastila_scout.vnext_scout_production_v1 import FetchResponse, SourceDefinition


class Backend:
    r2_lock_identity = EXPECTED_LOCK_IDENTITY

    def generate(self, messages, decoding):
        assert decoding == DECODING
        user = messages[1]["content"]
        marker = '"case_id":"'
        event = user.split(marker, 1)[1].split('"', 1)[0]
        raw = json.dumps(
            {"case_id": event, "text": "Guvernul a anuntat masura de 10 milioane de lei."},
            ensure_ascii=False,
            separators=(",", ":"),
        ).encode()
        return GenerationEvidence(
            rendered_prompt=json.dumps(messages, ensure_ascii=False),
            input_token_ids=(1, 2, 3),
            raw_output=raw,
            eos_token_id=2,
            pad_token_id=0,
            chat_template_sha256="1" * 64,
        )


def source(source_id, name, url):
    return SourceDefinition(source_id, name, url, ("politica",), 5)


SOURCES = (
    source("s1", "Sursa Unu", "https://one.example/feed"),
    source("s2", "Sursa Doi", "https://two.example/feed"),
)


def transport(definition, timeout):
    del timeout
    body = (
        "<rss><channel><item>"
        "<title>Guvernul anunta masura de 10 milioane de lei</title>"
        f"<link>https://{definition.source_id}.example/articol</link>"
        "<description>Guvernul a anuntat masura de 10 milioane de lei.</description>"
        "</item></channel></rss>"
    ).encode()
    return FetchResponse(body, definition.url, "application/rss+xml")


def prepare(tmp_path):
    store = bootstrap_store(tmp_path, writer_identity="writer")
    orchestrator = ProductOrchestrator(store)
    flow = "product-flow"
    orchestrator.create_workflow(flow)
    groups, failures = orchestrator.capture_and_group(
        workflow_identity=flow,
        sources_identity="2" * 64,
        sources=SOURCES,
        transport=transport,
        captured_at="2026-09-29T01:00:00Z",
        maximum_workers=2,
    )
    assert failures == ()
    assert len(groups) == 1
    editor = orchestrator.select_and_generate_editor_draft(
        workflow_identity=flow,
        selected_event_identity=groups[0].event_identity,
        backend=Backend(),
        source_packet_observed_at="2026-09-29T01:01:00Z",
        editor_observed_at="2026-09-29T01:02:00Z",
    )
    return store, orchestrator, editor


def factual_instruction(outcome="ACCEPT_DRAFT", fallback=()):
    return FactualReviewInstruction(
        actor="reviewer",
        outcome=outcome,
        authorization_identity=object_identity({"authority": "factual", "outcome": outcome}),
        reason_code="SOURCE_BOUND_REVIEW",
        fallback_span_ids=tuple(fallback),
    )


def policy_instruction(outcome="APPROVE_FINAL"):
    return PolicyInstruction(
        actor="publisher",
        outcome=outcome,
        authorization_identity=object_identity({"authority": "policy", "outcome": outcome}),
        reason_code="PUBLICATION_APPROVED",
    )


@pytest.mark.parametrize("outcome", ["ACCEPT_DRAFT", "APPROVE_SOURCE_FALLBACK"])
def test_integrated_core_reaches_bound_export(tmp_path, outcome):
    store, orchestrator, editor = prepare(tmp_path)
    fallback = (editor.packet["spans"][0]["span_id"],) if outcome == "APPROVE_SOURCE_FALLBACK" else ()
    factual = orchestrator.apply_factual_review(
        editor,
        instruction=factual_instruction(outcome, fallback),
        observed_at="2026-09-29T01:03:00Z",
    )
    exported = orchestrator.apply_policy_and_export(
        factual,
        instruction=policy_instruction(),
        policy_entry_observed_at="2026-09-29T01:04:00Z",
        policy_decision_observed_at="2026-09-29T01:05:00Z",
        final_observed_at="2026-09-29T01:06:00Z",
    )
    assert store.load_workflow(editor.workflow_identity)["state"] == "EXPORTED"
    assert exported.final["factual_input_identity"] == factual.artifact["artifact_identity"]
    assert (tmp_path / exported.receipt["export_ref"]).read_bytes()
    assert store.verify_integrity()["status"] == "PASS"


def test_user_event_selection_is_explicit_and_fail_closed(tmp_path):
    store = bootstrap_store(tmp_path, writer_identity="writer")
    orchestrator = ProductOrchestrator(store)
    orchestrator.create_workflow("flow")
    orchestrator.capture_and_group(
        workflow_identity="flow",
        sources_identity="2" * 64,
        sources=SOURCES,
        transport=transport,
        captured_at="2026-09-29T01:00:00Z",
    )
    with pytest.raises(Exception, match="unknown or empty event"):
        orchestrator.select_and_generate_editor_draft(
            workflow_identity="flow",
            selected_event_identity="event:missing",
            backend=Backend(),
            source_packet_observed_at="2026-09-29T01:01:00Z",
            editor_observed_at="2026-09-29T01:02:00Z",
        )
    assert store.load_workflow("flow")["state"] == "SOURCE_PACKET_INVALID"


def test_orchestrator_never_infers_factual_authority(tmp_path):
    _, orchestrator, editor = prepare(tmp_path)
    with pytest.raises(Exception):
        orchestrator.apply_factual_review(
            editor,
            instruction=factual_instruction("APPROVE_SOURCE_FALLBACK", ()),
            observed_at="2026-09-29T01:03:00Z",
        )


@pytest.mark.parametrize(("outcome", "state"), [("REJECT", "REJECTED"), ("REVISE", "REVISION_REQUIRED")])
def test_explicit_policy_terminal_routing(tmp_path, outcome, state):
    _, orchestrator, editor = prepare(tmp_path)
    factual = orchestrator.apply_factual_review(
        editor,
        instruction=factual_instruction(),
        observed_at="2026-09-29T01:03:00Z",
    )
    result = orchestrator.apply_policy_and_export(
        factual,
        instruction=policy_instruction(outcome),
        policy_entry_observed_at="2026-09-29T01:04:00Z",
        policy_decision_observed_at="2026-09-29T01:05:00Z",
        final_observed_at="2026-09-29T01:06:00Z",
    )
    assert isinstance(result, PolicyTerminalBundle)
    assert result.state == state
    assert orchestrator.store.load_workflow(editor.workflow_identity)["state"] == state


def test_cross_workflow_bundle_is_rejected(tmp_path):
    _, orchestrator, editor = prepare(tmp_path)
    other = bootstrap_store(tmp_path / "other", writer_identity="other")
    other.create_workflow("product-flow")
    with pytest.raises(Exception):
        ProductOrchestrator(other).apply_factual_review(
            editor,
            instruction=factual_instruction(),
            observed_at="2026-09-29T01:03:00Z",
        )


def test_export_replay_does_not_duplicate_terminal_transition(tmp_path):
    store, orchestrator, editor = prepare(tmp_path)
    factual = orchestrator.apply_factual_review(
        editor,
        instruction=factual_instruction(),
        observed_at="2026-09-29T01:03:00Z",
    )
    first = orchestrator.apply_policy_and_export(
        factual,
        instruction=policy_instruction(),
        policy_entry_observed_at="2026-09-29T01:04:00Z",
        policy_decision_observed_at="2026-09-29T01:05:00Z",
        final_observed_at="2026-09-29T01:06:00Z",
    )
    replay = orchestrator.apply_policy_and_export(
        factual,
        instruction=policy_instruction(),
        policy_entry_observed_at="2026-09-29T01:04:00Z",
        policy_decision_observed_at="2026-09-29T01:05:00Z",
        final_observed_at="2026-09-29T01:06:00Z",
    )
    assert replay.receipt == first.receipt
    with store.read() as connection:
        count = connection.execute(
            "SELECT COUNT(*) FROM state_transitions WHERE workflow_identity=? "
            "AND resulting_state='EXPORTED'",
            (editor.workflow_identity,),
        ).fetchone()[0]
    assert count == 1
    assert first.receipt["receipt_identity"]


def test_no_active_product_paths_are_written(tmp_path):
    _, orchestrator, _ = prepare(tmp_path)
    assert orchestrator.store.root == tmp_path.resolve()
    assert "/root/pastila-vnext/v1" not in str(orchestrator.store.root)


def test_restart_rehydrates_editor_review_bundle(tmp_path):
    _, _, editor = prepare(tmp_path)
    restarted = ProductOrchestrator(bootstrap_store(tmp_path, writer_identity="writer"))
    loaded = restarted.load_editor_review_bundle(editor.workflow_identity)
    assert loaded.packet == editor.packet
    assert loaded.invocation == editor.invocation
    assert loaded.draft == editor.draft


def test_restart_rehydrates_factual_result_and_completes_export(tmp_path):
    _, orchestrator, editor = prepare(tmp_path)
    factual = orchestrator.apply_factual_review(
        editor,
        instruction=factual_instruction(),
        observed_at="2026-09-29T01:03:00Z",
    )
    restarted = ProductOrchestrator(bootstrap_store(tmp_path, writer_identity="writer"))
    loaded = restarted.load_factual_result_bundle(editor.workflow_identity)
    assert loaded.artifact == factual.artifact
    exported = restarted.apply_policy_and_export(
        loaded,
        instruction=policy_instruction(),
        policy_entry_observed_at="2026-09-29T01:04:00Z",
        policy_decision_observed_at="2026-09-29T01:05:00Z",
        final_observed_at="2026-09-29T01:06:00Z",
    )
    assert exported.final["factual_input_identity"] == factual.artifact["artifact_identity"]


def test_restart_rejects_tampered_persisted_editor_draft(tmp_path):
    _, _, editor = prepare(tmp_path)
    path = tmp_path / "blobs" / "editor-drafts" / f"{editor.draft['draft_identity']}.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["text"] = "tampered"
    path.write_text(json.dumps(value), encoding="utf-8")
    restarted = ProductOrchestrator(bootstrap_store(tmp_path, writer_identity="writer"))
    with pytest.raises(Exception):
        restarted.load_editor_review_bundle(editor.workflow_identity)


def source_ready_after_backend_failure(tmp_path):
    store = bootstrap_store(tmp_path, writer_identity="writer")
    orchestrator = ProductOrchestrator(store)
    orchestrator.create_workflow("recovery-flow")
    groups, _ = orchestrator.capture_and_group(
        workflow_identity="recovery-flow",
        sources_identity="2" * 64,
        sources=SOURCES,
        transport=transport,
        captured_at="2026-09-29T04:00:00Z",
    )
    class FailingBackend(Backend):
        def generate(self, messages, decoding):
            raise RuntimeError("injected")
    with pytest.raises(RuntimeError, match="injected"):
        orchestrator.select_and_generate_editor_draft(
            workflow_identity="recovery-flow",
            selected_event_identity=groups[0].event_identity,
            backend=FailingBackend(),
            source_packet_observed_at="2026-09-29T04:01:00Z",
            editor_observed_at="2026-09-29T04:02:00Z",
        )
    assert store.load_workflow("recovery-flow")["state"] == "SOURCE_PACKET_READY"
    return store, orchestrator, groups[0].event_identity


def enter_editor_pending(store):
    semantic = object_identity({"editor": "pending-fault"})
    store.transition(TransitionRequest(
        "recovery-flow", "fault:editor-pending", "SOURCE_PACKET_READY", "EDITOR_PENDING",
        "EDITOR", "STARTED", object_identity({"packet": "input"}), None,
        f"attempt:{semantic}", f"idempotency:{semantic}", "2026-09-29T04:02:00Z",
        {"component": "fault-injection"},
    ))


def test_source_packet_ready_recovery_continues_editor(tmp_path):
    store, orchestrator, event = source_ready_after_backend_failure(tmp_path)
    bundle = orchestrator.select_and_generate_editor_draft(
        workflow_identity="recovery-flow",
        selected_event_identity=event,
        backend=Backend(),
        source_packet_observed_at="2026-09-29T04:01:00Z",
        editor_observed_at="2026-09-29T04:02:00Z",
    )
    assert bundle.packet["event_identity"] == event
    assert store.load_workflow("recovery-flow")["state"] == "FACTUAL_REVIEW_PENDING"


def test_editor_pending_requires_explicit_disposition(tmp_path):
    store, orchestrator, event = source_ready_after_backend_failure(tmp_path)
    enter_editor_pending(store)
    with pytest.raises(ProductOrchestratorError, match="explicit retry or failure disposition"):
        orchestrator.select_and_generate_editor_draft(
            workflow_identity="recovery-flow",
            selected_event_identity=event,
            backend=Backend(),
            source_packet_observed_at="2026-09-29T04:01:00Z",
            editor_observed_at="2026-09-29T04:02:00Z",
        )
    failure = orchestrator.record_editor_failure(
        workflow_identity="recovery-flow",
        failure_code="INFERENCE_INTERRUPTED",
        evidence_identity=object_identity({"failure": "injected"}),
        observed_at="2026-09-29T04:03:00Z",
    )
    assert failure.failure["eligible_for_voice"] is False
    assert store.load_workflow("recovery-flow")["state"] == "FACTUAL_REVIEW_PENDING"


def test_editor_pending_retry_requires_authority_and_recovers(tmp_path):
    store, orchestrator, _ = source_ready_after_backend_failure(tmp_path)
    enter_editor_pending(store)
    with pytest.raises(ProductOrchestratorError, match="authorization"):
        orchestrator.retry_editor_generation(
            workflow_identity="recovery-flow",
            backend=Backend(),
            retry_authorization_identity="short",
            editor_observed_at="2026-09-29T04:03:00Z",
        )
    bundle = orchestrator.retry_editor_generation(
        workflow_identity="recovery-flow",
        backend=Backend(),
        retry_authorization_identity=object_identity({"retry": "authorized"}),
        editor_observed_at="2026-09-29T04:03:00Z",
    )
    assert bundle.draft["eligible_for_voice"] is False
    with store.read() as connection:
        row = connection.execute(
            "SELECT input_identity FROM state_transitions WHERE workflow_identity=? "
            "AND previous_state='EDITOR_PENDING' AND resulting_state='EDITOR_DRAFT_READY'",
            ("recovery-flow",),
        ).fetchone()
    retry_path = tmp_path / "blobs" / "editor-retry-authorizations" / f"{row['input_identity']}.json"
    retry_receipt = json.loads(retry_path.read_text(encoding="utf-8"))
    assert retry_receipt["authorization_identity"] == object_identity({"retry": "authorized"})
    assert retry_receipt["receipt_identity"] == row["input_identity"]
    assert store.load_workflow("recovery-flow")["state"] == "FACTUAL_REVIEW_PENDING"


def persist_approved_policy(store, factual):
    enter_policy_review(
        store,
        workflow_identity=factual.workflow_identity,
        factual_output=factual.artifact,
        observed_at="2026-09-29T05:04:00Z",
    )
    instruction = policy_instruction()
    session = authorize_policy_session(
        store,
        workflow_identity=factual.workflow_identity,
        factual_output=factual.artifact,
        actor=instruction.actor,
        allowed_outcome=instruction.outcome,
        authorization_identity=instruction.authorization_identity,
    )
    decision = build_policy_decision(
        workflow_identity=factual.workflow_identity,
        factual_output=factual.artifact,
        session=session,
        outcome=instruction.outcome,
        actor=instruction.actor,
        reason_code=instruction.reason_code,
    )
    persist_policy_decision(
        store,
        workflow_identity=factual.workflow_identity,
        factual_output=factual.artifact,
        session=session,
        decision=decision,
        observed_at="2026-09-29T05:05:00Z",
    )


def test_approved_for_final_recovery_continues_without_new_authority(tmp_path):
    store, orchestrator, editor = prepare(tmp_path)
    factual = orchestrator.apply_factual_review(
        editor, instruction=factual_instruction(), observed_at="2026-09-29T05:03:00Z"
    )
    persist_approved_policy(store, factual)
    restarted = ProductOrchestrator(bootstrap_store(tmp_path, writer_identity="writer"))
    loaded = restarted.load_factual_result_bundle(editor.workflow_identity)
    result = restarted.apply_policy_and_export(
        loaded,
        instruction=policy_instruction(),
        policy_entry_observed_at="2026-09-29T05:04:00Z",
        policy_decision_observed_at="2026-09-29T05:05:00Z",
        final_observed_at="2026-09-29T05:06:00Z",
    )
    assert result.final["artifact_kind"] == "FINAL_OUTPUT"
    assert store.load_workflow(editor.workflow_identity)["state"] == "EXPORTED"


def test_final_ready_recovery_completes_atomic_export(tmp_path, monkeypatch):
    import pastila_scout.vnext_core_final_v1 as final_module
    store, orchestrator, editor = prepare(tmp_path)
    factual = orchestrator.apply_factual_review(
        editor, instruction=factual_instruction(), observed_at="2026-09-29T06:03:00Z"
    )
    original = final_module._transition
    def fail_export(store_arg, workflow, left, right, *args, **kwargs):
        if left == "FINAL_READY" and right == "EXPORTED":
            raise RuntimeError("injected export interruption")
        return original(store_arg, workflow, left, right, *args, **kwargs)
    monkeypatch.setattr(final_module, "_transition", fail_export)
    with pytest.raises(RuntimeError, match="injected export interruption"):
        orchestrator.apply_policy_and_export(
            factual,
            instruction=policy_instruction(),
            policy_entry_observed_at="2026-09-29T06:04:00Z",
            policy_decision_observed_at="2026-09-29T06:05:00Z",
            final_observed_at="2026-09-29T06:06:00Z",
        )
    assert store.load_workflow(editor.workflow_identity)["state"] == "FINAL_READY"
    monkeypatch.setattr(final_module, "_transition", original)
    restarted = ProductOrchestrator(bootstrap_store(tmp_path, writer_identity="writer"))
    result = restarted.apply_policy_and_export(
        restarted.load_factual_result_bundle(editor.workflow_identity),
        instruction=policy_instruction(),
        policy_entry_observed_at="2026-09-29T06:04:00Z",
        policy_decision_observed_at="2026-09-29T06:05:00Z",
        final_observed_at="2026-09-29T06:06:00Z",
    )
    assert result.receipt["final_identity"] == result.final["artifact_identity"]
    assert store.load_workflow(editor.workflow_identity)["state"] == "EXPORTED"


def test_factual_abstention_is_terminal_and_rehydratable(tmp_path):
    store, orchestrator, editor = prepare(tmp_path)
    factual = orchestrator.apply_factual_review(
        editor,
        instruction=factual_instruction("ABSTAIN"),
        observed_at="2026-09-29T07:03:00Z",
    )
    assert factual.terminal_state == "ABSTAINED"
    restarted = ProductOrchestrator(bootstrap_store(tmp_path, writer_identity="writer"))
    loaded = restarted.load_factual_result_bundle(editor.workflow_identity)
    assert loaded.terminal_state == "ABSTAINED"
    with pytest.raises(ProductOrchestratorError, match="terminal"):
        restarted.apply_policy_and_export(
            loaded,
            instruction=policy_instruction(),
            policy_entry_observed_at="2026-09-29T07:04:00Z",
            policy_decision_observed_at="2026-09-29T07:05:00Z",
            final_observed_at="2026-09-29T07:06:00Z",
        )
    assert store.load_workflow(editor.workflow_identity)["state"] == "ABSTAINED"


def authorized_retry(tmp_path):
    store, orchestrator, _ = source_ready_after_backend_failure(tmp_path)
    enter_editor_pending(store)
    orchestrator.retry_editor_generation(
        workflow_identity="recovery-flow",
        backend=Backend(),
        retry_authorization_identity=object_identity({"retry": "authorized"}),
        editor_observed_at="2026-09-29T09:00:00Z",
    )
    with store.read() as connection:
        retry_identity = connection.execute(
            "SELECT input_identity FROM state_transitions WHERE workflow_identity=? "
            "AND previous_state='EDITOR_PENDING' AND resulting_state='EDITOR_DRAFT_READY'",
            ("recovery-flow",),
        ).fetchone()[0]
    return store, orchestrator, retry_identity


def test_retry_receipt_absence_fails_closed_on_rehydration(tmp_path):
    _, orchestrator, retry_identity = authorized_retry(tmp_path)
    (tmp_path / "blobs" / "editor-retry-authorizations" / f"{retry_identity}.json").unlink()
    with pytest.raises(ProductOrchestratorError, match="retry authorization"):
        orchestrator.load_editor_review_bundle("recovery-flow")


def test_retry_receipt_tamper_fails_closed_on_rehydration(tmp_path):
    _, orchestrator, retry_identity = authorized_retry(tmp_path)
    path = tmp_path / "blobs" / "editor-retry-authorizations" / f"{retry_identity}.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["authorization_identity"] = "0" * 64
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ProductOrchestratorError, match="binding mismatch"):
        orchestrator.load_editor_review_bundle("recovery-flow")


def test_retry_receipt_cross_workflow_fails_closed(tmp_path):
    store, orchestrator, retry_identity = authorized_retry(tmp_path)
    path = tmp_path / "blobs" / "editor-retry-authorizations" / f"{retry_identity}.json"
    value = json.loads(path.read_text(encoding="utf-8"))
    value["workflow_identity"] = "other-flow"
    value.pop("receipt_identity")
    rebound = object_identity(value)
    value["receipt_identity"] = rebound
    rebound_path = path.with_name(f"{rebound}.json")
    rebound_path.write_text(json.dumps(value), encoding="utf-8")
    path.unlink()
    with store.write() as connection:
        connection.execute(
            "UPDATE state_transitions SET input_identity=? "
            "WHERE workflow_identity=? AND previous_state='EDITOR_PENDING' "
            "AND resulting_state='EDITOR_DRAFT_READY'",
            (rebound, "recovery-flow"),
        )
    with pytest.raises(ProductOrchestratorError, match="binding mismatch"):
        orchestrator.load_editor_review_bundle("recovery-flow")


def structural_failure_bundle(tmp_path):
    store, orchestrator, _ = source_ready_after_backend_failure(tmp_path)
    enter_editor_pending(store)
    failure = orchestrator.record_editor_failure(
        workflow_identity="recovery-flow",
        failure_code="INFERENCE_INTERRUPTED",
        evidence_identity=object_identity({"failure": "injected"}),
        observed_at="2026-09-29T10:00:00Z",
    )
    return store, orchestrator, failure


def test_structural_failure_routes_to_source_fallback_and_rehydrates(tmp_path):
    store, orchestrator, failure = structural_failure_bundle(tmp_path)
    span = failure.packet["spans"][0]["span_id"]
    factual = orchestrator.apply_factual_review(
        failure,
        instruction=factual_instruction("APPROVE_SOURCE_FALLBACK", (span,)),
        observed_at="2026-09-29T10:01:00Z",
    )
    assert factual.artifact["artifact_kind"] == "SOURCE_FALLBACK"
    assert factual.structural_failure == failure.failure
    restarted = ProductOrchestrator(bootstrap_store(tmp_path, writer_identity="writer"))
    loaded = restarted.load_factual_result_bundle("recovery-flow")
    assert loaded.artifact == factual.artifact
    assert loaded.structural_failure == failure.failure
    assert store.load_workflow("recovery-flow")["state"] == "SOURCE_FALLBACK"


def test_structural_failure_routes_to_abstention_and_rehydrates(tmp_path):
    store, orchestrator, failure = structural_failure_bundle(tmp_path)
    factual = orchestrator.apply_factual_review(
        failure,
        instruction=factual_instruction("ABSTAIN"),
        observed_at="2026-09-29T10:01:00Z",
    )
    assert factual.terminal_state == "ABSTAINED"
    restarted = ProductOrchestrator(bootstrap_store(tmp_path, writer_identity="writer"))
    loaded = restarted.load_factual_result_bundle("recovery-flow")
    assert loaded.terminal_state == "ABSTAINED"
    assert loaded.structural_failure == failure.failure
    assert store.load_workflow("recovery-flow")["state"] == "ABSTAINED"


def test_structural_failure_cannot_be_accepted_as_draft(tmp_path):
    _, orchestrator, failure = structural_failure_bundle(tmp_path)
    with pytest.raises(Exception, match="incompatible"):
        orchestrator.apply_factual_review(
            failure,
            instruction=factual_instruction("ACCEPT_DRAFT"),
            observed_at="2026-09-29T10:01:00Z",
        )


def _persisted_factual_bundle(tmp_path, *, structural, outcome="ABSTAIN"):
    if structural:
        store, orchestrator, review = structural_failure_bundle(tmp_path)
        workflow_identity = "recovery-flow"
    else:
        store, orchestrator, review = prepare(tmp_path)
        workflow_identity = "product-flow"
    factual = orchestrator.apply_factual_review(
        review,
        instruction=factual_instruction(outcome),
        observed_at="2026-09-29T11:00:00Z",
    )
    return store, orchestrator, factual, workflow_identity


def _fault_transition(store, orchestrator, workflow_identity, previous_state, resulting_state, mode):
    if mode == "missing":
        with store.write() as connection:
            connection.execute(
                "DELETE FROM state_transitions WHERE workflow_identity=? "
                "AND previous_state=? AND resulting_state=?",
                (workflow_identity, previous_state, resulting_state),
            )
    elif mode == "duplicate":
        with store.write() as connection:
            connection.execute(
                "INSERT INTO state_transitions("
                "workflow_identity,receipt_identity,operation_identity,previous_state,"
                "resulting_state,actor,outcome,input_identity,output_identity,"
                "attempt_identity,idempotency_identity,receipt_json"
                ") SELECT workflow_identity,?,operation_identity,previous_state,"
                "resulting_state,actor,outcome,input_identity,output_identity,"
                "attempt_identity,idempotency_identity,receipt_json "
                "FROM state_transitions WHERE workflow_identity=? "
                "AND previous_state=? AND resulting_state=?",
                ("e" * 64, workflow_identity, previous_state, resulting_state),
            )
    elif mode == "altered":
        with store.write() as connection:
            connection.execute(
                "UPDATE state_transitions SET output_identity=? WHERE workflow_identity=? "
                "AND previous_state=? AND resulting_state=?",
                ("d" * 64, workflow_identity, previous_state, resulting_state),
            )
    elif mode == "cross_workflow":
        orchestrator.create_workflow("foreign-flow")
        with store.write() as connection:
            connection.execute(
                "UPDATE state_transitions SET workflow_identity=? WHERE workflow_identity=? "
                "AND previous_state=? AND resulting_state=?",
                ("foreign-flow", workflow_identity, previous_state, resulting_state),
            )
    else:
        raise AssertionError(mode)


@pytest.mark.parametrize("mode", ("missing", "duplicate", "altered", "cross_workflow"))
def test_structural_failure_transition_lineage_fails_closed(tmp_path, mode):
    store, orchestrator, _ = structural_failure_bundle(tmp_path)
    _fault_transition(
        store, orchestrator, "recovery-flow",
        "EDITOR_PENDING", "STRUCTURAL_FAIL", mode,
    )
    with pytest.raises(ProductOrchestratorError, match="structural failure transition"):
        orchestrator.load_editor_failure_bundle("recovery-flow")


@pytest.mark.parametrize("mode", ("missing", "duplicate", "altered", "cross_workflow"))
def test_structural_failure_review_transition_lineage_fails_closed(tmp_path, mode):
    store, orchestrator, _ = structural_failure_bundle(tmp_path)
    _fault_transition(
        store, orchestrator, "recovery-flow",
        "STRUCTURAL_FAIL", "FACTUAL_REVIEW_PENDING", mode,
    )
    with pytest.raises(ProductOrchestratorError, match="structural failure review transition"):
        orchestrator.load_editor_failure_bundle("recovery-flow")


@pytest.mark.parametrize(
    ("structural", "column", "value"),
    (
        (False, "input_identity", "a" * 64),
        (False, "outcome", "APPROVE_SOURCE_FALLBACK"),
        (False, "actor", "intruder"),
        (False, "receipt_identity", "b" * 64),
        (True, "input_identity", "a" * 64),
        (True, "outcome", "APPROVE_SOURCE_FALLBACK"),
        (True, "actor", "intruder"),
        (True, "receipt_identity", "b" * 64),
    ),
)
def test_factual_decision_row_drift_fails_closed(tmp_path, structural, column, value):
    store, orchestrator, factual, workflow_identity = _persisted_factual_bundle(
        tmp_path, structural=structural
    )
    with store.write() as connection:
        connection.execute(
            f"UPDATE decisions SET {column}=? WHERE decision_identity=?",
            (value, factual.decision["decision_identity"]),
        )
    with pytest.raises(BoundaryError):
        orchestrator.load_factual_result_bundle(workflow_identity)


@pytest.mark.parametrize("structural", (False, True))
@pytest.mark.parametrize("mode", ("missing", "duplicate", "altered", "cross_workflow"))
def test_factual_transition_lineage_fails_closed(tmp_path, structural, mode):
    store, orchestrator, factual, workflow_identity = _persisted_factual_bundle(
        tmp_path, structural=structural
    )
    _fault_transition(
        store, orchestrator, workflow_identity,
        "FACTUAL_REVIEW_PENDING", str(factual.artifact["artifact_kind"]), mode,
    )
    with pytest.raises(ProductOrchestratorError, match="factual result transition"):
        orchestrator.load_factual_result_bundle(workflow_identity)


@pytest.mark.parametrize("structural", (False, True))
@pytest.mark.parametrize(
    ("column", "value"),
    (("payload_identity", "c" * 64), ("schema_identity", "foreign-schema")),
)
def test_factual_artifact_row_drift_fails_closed(tmp_path, structural, column, value):
    store, orchestrator, factual, workflow_identity = _persisted_factual_bundle(
        tmp_path, structural=structural
    )
    with store.write() as connection:
        connection.execute(
            f"UPDATE workflow_artifacts SET {column}=? "
            "WHERE workflow_identity=? AND artifact_identity=?",
            (value, workflow_identity, factual.artifact["artifact_identity"]),
        )
    with pytest.raises(ProductOrchestratorError, match="factual artifact binding mismatch"):
        orchestrator.load_factual_result_bundle(workflow_identity)


@pytest.mark.parametrize("structural", (False, True))
def test_factual_transition_decision_receipt_provenance_fails_closed(tmp_path, structural):
    store, orchestrator, factual, workflow_identity = _persisted_factual_bundle(
        tmp_path, structural=structural
    )
    with store.write() as connection:
        row = connection.execute(
            "SELECT receipt_identity,receipt_json FROM state_transitions "
            "WHERE workflow_identity=? AND previous_state='FACTUAL_REVIEW_PENDING' "
            "AND resulting_state=?",
            (workflow_identity, factual.artifact["artifact_kind"]),
        ).fetchone()
        receipt = json.loads(row["receipt_json"])
        receipt["provenance"]["decision_receipt_identity"] = "f" * 64
        connection.execute(
            "UPDATE state_transitions SET receipt_json=? WHERE receipt_identity=?",
            (json.dumps(receipt, sort_keys=True, separators=(",", ":")), row["receipt_identity"]),
        )
    with pytest.raises(
        ProductOrchestratorError,
        match="factual result transition receipt provenance mismatch",
    ):
        orchestrator.load_factual_result_bundle(workflow_identity)


@pytest.mark.parametrize(
    ("column", "value"),
    (("payload_identity", "9" * 64), ("payload_ref", "blobs/source-packets/foreign.json")),
)
def test_source_packet_row_drift_fails_closed(tmp_path, column, value):
    store, orchestrator, editor = prepare(tmp_path)
    with store.write() as connection:
        connection.execute(
            f"UPDATE source_packets SET {column}=? WHERE packet_identity=?",
            (value, editor.packet["packet_identity"]),
        )
    with pytest.raises(BoundaryError):
        orchestrator.load_source_packet("product-flow")


@pytest.mark.parametrize("mode", ("missing", "duplicate", "altered", "cross_workflow"))
def test_source_packet_transition_lineage_fails_closed(tmp_path, mode):
    store, orchestrator, _ = prepare(tmp_path)
    _fault_transition(
        store, orchestrator, "product-flow",
        "SELECTED", "SOURCE_PACKET_READY", mode,
    )
    with pytest.raises(BoundaryError):
        orchestrator.load_source_packet("product-flow")


@pytest.mark.parametrize(
    ("column", "value"),
    (("payload_identity", "8" * 64), ("schema_identity", "foreign-schema")),
)
def test_editor_draft_artifact_row_drift_fails_closed(tmp_path, column, value):
    store, orchestrator, editor = prepare(tmp_path)
    with store.write() as connection:
        connection.execute(
            f"UPDATE workflow_artifacts SET {column}=? "
            "WHERE workflow_identity=? AND artifact_identity=?",
            (value, "product-flow", editor.draft["draft_identity"]),
        )
    with pytest.raises(ProductOrchestratorError, match="EditorDraft artifact binding mismatch"):
        orchestrator.load_editor_review_bundle("product-flow")


@pytest.mark.parametrize("mode", ("missing", "duplicate", "altered", "cross_workflow"))
def test_editor_draft_transition_lineage_fails_closed(tmp_path, mode):
    store, orchestrator, _ = prepare(tmp_path)
    _fault_transition(
        store, orchestrator, "product-flow",
        "EDITOR_PENDING", "EDITOR_DRAFT_READY", mode,
    )
    with pytest.raises(BoundaryError):
        orchestrator.load_editor_review_bundle("product-flow")


@pytest.mark.parametrize("mode", ("missing", "duplicate", "altered", "cross_workflow"))
def test_editor_to_factual_transition_lineage_fails_closed(tmp_path, mode):
    store, orchestrator, _ = prepare(tmp_path)
    _fault_transition(
        store, orchestrator, "product-flow",
        "EDITOR_DRAFT_READY", "FACTUAL_REVIEW_PENDING", mode,
    )
    with pytest.raises(ProductOrchestratorError, match="EditorDraft factual review transition"):
        orchestrator.load_editor_review_bundle("product-flow")


@pytest.mark.parametrize(
    ("previous_state", "resulting_state", "loader"),
    (
        ("SELECTED", "SOURCE_PACKET_READY", "source"),
        ("EDITOR_PENDING", "EDITOR_DRAFT_READY", "editor"),
        ("EDITOR_DRAFT_READY", "FACTUAL_REVIEW_PENDING", "editor"),
    ),
)
def test_upstream_operational_receipt_drift_fails_closed(
    tmp_path, previous_state, resulting_state, loader
):
    store, orchestrator, _ = prepare(tmp_path)
    with store.write() as connection:
        row = connection.execute(
            "SELECT receipt_identity,receipt_json FROM state_transitions "
            "WHERE workflow_identity=? AND previous_state=? AND resulting_state=?",
            ("product-flow", previous_state, resulting_state),
        ).fetchone()
        receipt = json.loads(row["receipt_json"])
        receipt["actor"] = "INTRUDER"
        connection.execute(
            "UPDATE state_transitions SET receipt_json=? WHERE receipt_identity=?",
            (json.dumps(receipt, sort_keys=True, separators=(",", ":")), row["receipt_identity"]),
        )
    with pytest.raises(ProductOrchestratorError, match="transition receipt binding mismatch"):
        if loader == "source":
            orchestrator.load_source_packet("product-flow")
        else:
            orchestrator.load_editor_review_bundle("product-flow")


@pytest.mark.parametrize("mode", ("missing", "duplicate", "altered", "cross_workflow"))
def test_terminal_factual_rehydration_rejects_broken_editor_lineage(tmp_path, mode):
    store, orchestrator, editor = prepare(tmp_path)
    orchestrator.apply_factual_review(
        editor,
        instruction=factual_instruction("ABSTAIN"),
        observed_at="2026-09-29T12:00:00Z",
    )
    _fault_transition(
        store, orchestrator, "product-flow",
        "EDITOR_DRAFT_READY", "FACTUAL_REVIEW_PENDING", mode,
    )
    restarted = ProductOrchestrator(bootstrap_store(tmp_path, writer_identity="writer"))
    with pytest.raises(ProductOrchestratorError, match="EditorDraft factual review transition"):
        restarted.load_factual_result_bundle("product-flow")


def _persisted_policy_bundle(tmp_path, outcome):
    store, orchestrator, editor = prepare(tmp_path)
    factual = orchestrator.apply_factual_review(
        editor,
        instruction=factual_instruction(),
        observed_at="2026-09-29T20:00:00Z",
    )
    instruction = policy_instruction(outcome)
    if outcome == "APPROVE_FINAL":
        persist_approved_policy(store, factual)
    else:
        result = orchestrator.apply_policy_and_export(
            factual,
            instruction=instruction,
            policy_entry_observed_at="2026-09-29T20:01:00Z",
            policy_decision_observed_at="2026-09-29T20:02:00Z",
            final_observed_at="2026-09-29T20:03:00Z",
        )
        assert isinstance(result, PolicyTerminalBundle)
    restarted = ProductOrchestrator(bootstrap_store(tmp_path, writer_identity="writer"))
    loaded = restarted.load_factual_result_bundle(editor.workflow_identity)
    return store, restarted, loaded, instruction


def _recover_policy(orchestrator, factual, instruction):
    return orchestrator.apply_policy_and_export(
        factual,
        instruction=instruction,
        policy_entry_observed_at="2026-09-29T20:01:00Z",
        policy_decision_observed_at="2026-09-29T20:02:00Z",
        final_observed_at="2026-09-29T20:03:00Z",
    )


@pytest.mark.parametrize("outcome", ("APPROVE_FINAL", "REJECT", "REVISE"))
@pytest.mark.parametrize(
    ("column", "value"),
    (("input_identity", "a" * 64), ("receipt_identity", "b" * 64)),
)
def test_policy_decision_row_binding_fails_closed(tmp_path, outcome, column, value):
    store, orchestrator, factual, instruction = _persisted_policy_bundle(tmp_path, outcome)
    with store.write() as connection:
        connection.execute(
            f"UPDATE decisions SET {column}=? WHERE workflow_identity=? "
            "AND decision_kind='APPROVAL'",
            (value, factual.workflow_identity),
        )
    with pytest.raises(ProductOrchestratorError, match="policy decision row binding"):
        _recover_policy(orchestrator, factual, instruction)


@pytest.mark.parametrize("outcome", ("APPROVE_FINAL", "REJECT", "REVISE"))
@pytest.mark.parametrize(
    ("column", "value"),
    (
        ("request_identity", "a" * 64),
        ("issued_by", "intruder"),
        ("input_identity", "b" * 64),
        ("status", "OPEN"),
    ),
)
def test_policy_session_row_binding_fails_closed(tmp_path, outcome, column, value):
    store, orchestrator, factual, instruction = _persisted_policy_bundle(tmp_path, outcome)
    with store.write() as connection:
        connection.execute(
            f"UPDATE policy_sessions SET {column}=? WHERE workflow_identity=?",
            (value, factual.workflow_identity),
        )
    with pytest.raises(ProductOrchestratorError, match="policy-session row binding"):
        _recover_policy(orchestrator, factual, instruction)


@pytest.mark.parametrize(
    ("outcome", "target"),
    (
        ("APPROVE_FINAL", "APPROVED_FOR_FINAL"),
        ("REJECT", "REJECTED"),
        ("REVISE", "REVISION_REQUIRED"),
    ),
)
@pytest.mark.parametrize("mode", ("missing", "duplicate", "altered", "cross_workflow"))
def test_policy_transition_lineage_fails_closed(tmp_path, outcome, target, mode):
    store, orchestrator, factual, instruction = _persisted_policy_bundle(tmp_path, outcome)
    _fault_transition(
        store, orchestrator, factual.workflow_identity,
        "POLICY_REVIEW_PENDING", target, mode,
    )
    with pytest.raises(ProductOrchestratorError, match="policy decision transition"):
        _recover_policy(orchestrator, factual, instruction)


@pytest.mark.parametrize("outcome", ("APPROVE_FINAL", "REJECT", "REVISE"))
def test_policy_transition_operational_receipt_fails_closed(tmp_path, outcome):
    target = {
        "APPROVE_FINAL": "APPROVED_FOR_FINAL",
        "REJECT": "REJECTED",
        "REVISE": "REVISION_REQUIRED",
    }[outcome]
    store, orchestrator, factual, instruction = _persisted_policy_bundle(tmp_path, outcome)
    with store.write() as connection:
        row = connection.execute(
            "SELECT receipt_json FROM state_transitions WHERE workflow_identity=? "
            "AND previous_state='POLICY_REVIEW_PENDING' AND resulting_state=?",
            (factual.workflow_identity, target),
        ).fetchone()
        receipt = json.loads(row["receipt_json"])
        receipt["actor"] = "intruder"
        connection.execute(
            "UPDATE state_transitions SET receipt_json=? WHERE workflow_identity=? "
            "AND previous_state='POLICY_REVIEW_PENDING' AND resulting_state=?",
            (json.dumps(receipt), factual.workflow_identity, target),
        )
    with pytest.raises(ProductOrchestratorError, match="transition receipt binding"):
        _recover_policy(orchestrator, factual, instruction)


def _exported_bundle(tmp_path):
    store, orchestrator, editor = prepare(tmp_path)
    factual = orchestrator.apply_factual_review(
        editor,
        instruction=factual_instruction(),
        observed_at="2026-09-29T21:00:00Z",
    )
    exported = orchestrator.apply_policy_and_export(
        factual,
        instruction=policy_instruction(),
        policy_entry_observed_at="2026-09-29T21:01:00Z",
        policy_decision_observed_at="2026-09-29T21:02:00Z",
        final_observed_at="2026-09-29T21:03:00Z",
    )
    return store, orchestrator, exported, editor.workflow_identity


@pytest.mark.parametrize(
    ("column", "value"),
    (
        ("payload_identity", "a" * 64),
        ("payload_ref", "blobs/final-outputs/foreign.json"),
        ("schema_identity", "foreign-schema"),
    ),
)
def test_final_artifact_row_binding_fails_closed(tmp_path, column, value):
    store, _, exported, workflow_identity = _exported_bundle(tmp_path)
    with store.write() as connection:
        connection.execute(
            f"UPDATE workflow_artifacts SET {column}=? WHERE workflow_identity=? "
            "AND artifact_kind='FINAL_OUTPUT'",
            (value, workflow_identity),
        )
    with pytest.raises(CoreFinalError, match="artifact-row binding"):
        load_exported_final(
            store,
            workflow_identity=workflow_identity,
            final_identity=str(exported.final["artifact_identity"]),
        )


@pytest.mark.parametrize(
    ("previous_state", "resulting_state", "label"),
    (
        ("APPROVED_FOR_FINAL", "FINAL_READY", "FINAL assembly"),
        ("FINAL_READY", "EXPORTED", "FINAL export"),
    ),
)
@pytest.mark.parametrize("mode", ("missing", "duplicate", "altered", "cross_workflow"))
def test_final_transition_lineage_fails_closed(
    tmp_path, previous_state, resulting_state, label, mode,
):
    store, orchestrator, exported, workflow_identity = _exported_bundle(tmp_path)
    _fault_transition(
        store, orchestrator, workflow_identity, previous_state, resulting_state, mode,
    )
    with pytest.raises(CoreFinalError, match=label):
        load_exported_final(
            store,
            workflow_identity=workflow_identity,
            final_identity=str(exported.final["artifact_identity"]),
        )


@pytest.mark.parametrize(
    ("previous_state", "resulting_state", "label"),
    (
        ("APPROVED_FOR_FINAL", "FINAL_READY", "FINAL assembly"),
        ("FINAL_READY", "EXPORTED", "FINAL export"),
    ),
)
def test_final_transition_operational_receipt_fails_closed(
    tmp_path, previous_state, resulting_state, label,
):
    store, _, exported, workflow_identity = _exported_bundle(tmp_path)
    with store.write() as connection:
        row = connection.execute(
            "SELECT receipt_json FROM state_transitions WHERE workflow_identity=? "
            "AND previous_state=? AND resulting_state=?",
            (workflow_identity, previous_state, resulting_state),
        ).fetchone()
        receipt = json.loads(row["receipt_json"])
        receipt["outcome"] = "ALTERED"
        connection.execute(
            "UPDATE state_transitions SET receipt_json=? WHERE workflow_identity=? "
            "AND previous_state=? AND resulting_state=?",
            (json.dumps(receipt), workflow_identity, previous_state, resulting_state),
        )
    with pytest.raises(CoreFinalError, match=f"{label} transition receipt binding"):
        load_exported_final(
            store,
            workflow_identity=workflow_identity,
            final_identity=str(exported.final["artifact_identity"]),
        )
