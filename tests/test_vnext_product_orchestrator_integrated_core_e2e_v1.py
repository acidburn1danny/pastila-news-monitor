from __future__ import annotations

import json
from pathlib import Path

import pytest

from pastila_scout.vnext_editor_vertical_slice_v1 import (
    DECODING,
    GenerationEvidence,
)
from pastila_scout.vnext_foundation_v1 import object_identity
from pastila_scout.vnext_product_orchestrator_v1 import (
    FactualReviewInstruction,
    PolicyInstruction,
    ProductOrchestrator,
    ProductOrchestratorError,
    bootstrap_store,
)
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


def test_orchestrator_never_infers_policy_authority(tmp_path):
    _, orchestrator, editor = prepare(tmp_path)
    factual = orchestrator.apply_factual_review(
        editor,
        instruction=factual_instruction(),
        observed_at="2026-09-29T01:03:00Z",
    )
    with pytest.raises(ProductOrchestratorError, match="explicit APPROVE_FINAL"):
        orchestrator.apply_policy_and_export(
            factual,
            instruction=policy_instruction("REJECT"),
            policy_entry_observed_at="2026-09-29T01:04:00Z",
            policy_decision_observed_at="2026-09-29T01:05:00Z",
            final_observed_at="2026-09-29T01:06:00Z",
        )
    assert orchestrator.store.load_workflow(editor.workflow_identity)["state"] == "ACCEPTED_SETUP"


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
    with pytest.raises(Exception):
        orchestrator.apply_policy_and_export(
            factual,
            instruction=policy_instruction(),
            policy_entry_observed_at="2026-09-29T01:04:00Z",
            policy_decision_observed_at="2026-09-29T01:05:00Z",
            final_observed_at="2026-09-29T01:06:00Z",
        )
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
