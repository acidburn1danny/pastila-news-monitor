from __future__ import annotations

import json
import runpy
from pathlib import Path

import pytest

from pastila_scout.vnext_product_orchestrator_v1 import (
    ProductOrchestrator,
    ProductOrchestratorError,
)
_HELPERS = runpy.run_path(
    str(Path(__file__).with_name("test_vnext_product_orchestrator_integrated_core_e2e_v1.py"))
)
Backend = _HELPERS["Backend"]
SOURCES = _HELPERS["SOURCES"]
_persisted_factual_bundle = _HELPERS["_persisted_factual_bundle"]
prepare = _HELPERS["prepare"]
transport = _HELPERS["transport"]
bootstrap_store = _HELPERS["bootstrap_store"]


def _selection_blob(store, packet):
    receipt = packet["selection_receipt"]
    return store.root / "blobs/source-selections" / f"{receipt['receipt_identity']}.json"


def test_canonical_packet_carries_content_addressed_selection_authority(tmp_path: Path):
    store, orchestrator, editor = prepare(tmp_path)
    packet = editor.packet
    receipt = packet["selection_receipt"]
    assert packet["selection_authority"] == "EXPLICIT_USER_EVENT_ID"
    assert receipt["workflow_identity"] == "product-flow"
    assert receipt["event_identity"] == packet["event_identity"]
    assert receipt["actor"] == "Daniel"
    assert receipt["authorization_identity"] == "a" * 64
    assert _selection_blob(store, packet).is_file()
    assert orchestrator.load_source_packet("product-flow") == packet


@pytest.mark.parametrize(
    ("actor", "authorization"),
    (("", "a" * 64), ("Daniel", "not-a-content-identity")),
)
def test_selection_requires_explicit_actor_and_authorization(
    tmp_path: Path, actor: str, authorization: str
):
    store = bootstrap_store(tmp_path, writer_identity="writer")
    orchestrator = ProductOrchestrator(store)
    orchestrator.create_workflow("flow")
    groups, _ = orchestrator.capture_and_group(
        workflow_identity="flow",
        source_set=SOURCES,
        transport=transport,
        captured_at="2026-09-29T01:00:00Z",
        maximum_workers=2,
    )
    with pytest.raises(Exception):
        orchestrator.select_and_generate_editor_draft(
            workflow_identity="flow",
            selected_event_identity=groups[0].event_identity,
            selection_actor=actor,
            selection_authorization_identity=authorization,
            backend=Backend(),
            source_packet_observed_at="2026-09-29T01:01:00Z",
            editor_observed_at="2026-09-29T01:02:00Z",
        )
    assert store.load_workflow("flow")["state"] == "GROUPED"


@pytest.mark.parametrize("mode", ("absent", "duplicate", "altered", "cross_workflow"))
def test_selection_transition_lineage_fails_closed(tmp_path: Path, mode: str):
    store, orchestrator, editor = prepare(tmp_path)
    with store.write() as connection:
        if mode == "absent":
            connection.execute(
                "DELETE FROM state_transitions WHERE workflow_identity=? "
                "AND previous_state='GROUPED' AND resulting_state='SELECTED'",
                ("product-flow",),
            )
        elif mode == "duplicate":
            connection.execute(
                "INSERT INTO state_transitions("
                "workflow_identity,receipt_identity,operation_identity,previous_state,"
                "resulting_state,actor,outcome,input_identity,output_identity,"
                "attempt_identity,idempotency_identity,receipt_json"
                ") SELECT workflow_identity,?,operation_identity,previous_state,"
                "resulting_state,actor,outcome,input_identity,output_identity,"
                "attempt_identity,idempotency_identity,receipt_json "
                "FROM state_transitions WHERE workflow_identity=? "
                "AND previous_state='GROUPED' AND resulting_state='SELECTED'",
                ("f" * 64, "product-flow"),
            )
        elif mode == "altered":
            connection.execute(
                "UPDATE state_transitions SET actor='intruder' WHERE workflow_identity=? "
                "AND previous_state='GROUPED' AND resulting_state='SELECTED'",
                ("product-flow",),
            )
        else:
            connection.execute(
                "INSERT INTO workflows SELECT ?,current_state,state_identity,state_json "
                "FROM workflows WHERE workflow_identity=?",
                ("other-flow", "product-flow"),
            )
            connection.execute(
                "UPDATE state_transitions SET workflow_identity=? WHERE workflow_identity=? "
                "AND previous_state='GROUPED' AND resulting_state='SELECTED'",
                ("other-flow", "product-flow"),
            )
    with pytest.raises(ProductOrchestratorError):
        orchestrator.load_editor_review_bundle("product-flow")


@pytest.mark.parametrize("mode", ("absent", "altered"))
def test_selection_receipt_blob_fails_closed(tmp_path: Path, mode: str):
    store, orchestrator, editor = prepare(tmp_path)
    path = _selection_blob(store, editor.packet)
    if mode == "absent":
        path.unlink()
    else:
        value = json.loads(path.read_text(encoding="utf-8"))
        value["actor"] = "intruder"
        path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ProductOrchestratorError):
        orchestrator.load_editor_review_bundle("product-flow")


def test_terminal_factual_rehydration_rejects_broken_selection_lineage(tmp_path: Path):
    store, orchestrator, _, workflow = _persisted_factual_bundle(
        tmp_path, structural=False, outcome="ABSTAIN"
    )
    with store.write() as connection:
        connection.execute(
            "DELETE FROM state_transitions WHERE workflow_identity=? "
            "AND previous_state='GROUPED' AND resulting_state='SELECTED'",
            (workflow,),
        )
    with pytest.raises(ProductOrchestratorError):
        orchestrator.load_factual_result_bundle(workflow)
