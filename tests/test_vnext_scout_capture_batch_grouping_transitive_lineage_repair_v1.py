from __future__ import annotations

import json
import runpy
import sqlite3
from pathlib import Path

import pytest

from pastila_scout.vnext_foundation_v1 import canonical_json, object_identity
from pastila_scout.vnext_product_orchestrator_v1 import ProductOrchestratorError

_HELPERS = runpy.run_path(
    str(Path(__file__).with_name("test_vnext_product_orchestrator_integrated_core_e2e_v1.py"))
)
_persisted_factual_bundle = _HELPERS["_persisted_factual_bundle"]
prepare = _HELPERS["prepare"]


def _batch_path(store):
    paths = list((store.root / "blobs/capture-batches").glob("*.json"))
    assert len(paths) == 1
    return paths[0]


def _capture_identity(store):
    with store.read() as connection:
        return connection.execute(
            "SELECT capture_identity FROM captures ORDER BY capture_identity"
        ).fetchone()[0]


def _rewrite_transition_input_consistently(store, previous, resulting, value):
    with store.write() as connection:
        row = connection.execute(
            "SELECT sequence,receipt_json FROM state_transitions "
            "WHERE workflow_identity=? AND previous_state=? AND resulting_state=?",
            ("product-flow", previous, resulting),
        ).fetchone()
        receipt = json.loads(row["receipt_json"])
        receipt["input_identity"] = value
        semantic = {
            key: receipt[key]
            for key in (
                "schema", "schema_version", "workflow_identity",
                "operation_identity", "previous_state", "resulting_state",
                "actor", "outcome", "input_identity", "output_identity",
                "attempt_identity", "idempotency_identity",
            )
        }
        receipt["receipt_identity"] = object_identity(semantic)
        connection.execute(
            "UPDATE state_transitions SET input_identity=?,receipt_identity=?,"
            "receipt_json=? WHERE sequence=?",
            (value, receipt["receipt_identity"], canonical_json(receipt), row["sequence"]),
        )


def test_valid_capture_to_grouping_lineage_rehydrates(tmp_path: Path):
    _, orchestrator, editor = prepare(tmp_path)
    assert orchestrator.load_editor_review_bundle("product-flow").packet == editor.packet


@pytest.mark.parametrize("mode", ("absent", "altered"))
def test_capture_batch_artifact_fails_closed(tmp_path: Path, mode: str):
    store, orchestrator, _ = prepare(tmp_path)
    path = _batch_path(store)
    if mode == "absent":
        path.unlink()
    else:
        value = json.loads(path.read_text(encoding="utf-8"))
        value["sources_identity"] = "f" * 64
        path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ProductOrchestratorError):
        orchestrator.load_editor_review_bundle("product-flow")


@pytest.mark.parametrize("mode", ("absent", "duplicate", "altered", "cross_workflow"))
def test_capture_transition_faults_fail_closed(tmp_path: Path, mode: str):
    store, orchestrator, _ = prepare(tmp_path)
    with store.write() as connection:
        if mode == "absent":
            connection.execute(
                "DELETE FROM state_transitions WHERE workflow_identity=? "
                "AND previous_state='DISCOVERED' AND resulting_state='CAPTURED'",
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
                "AND previous_state='DISCOVERED' AND resulting_state='CAPTURED'",
                ("d" * 64, "product-flow"),
            )
        elif mode == "altered":
            connection.execute(
                "UPDATE state_transitions SET output_identity=? "
                "WHERE workflow_identity=? AND previous_state='DISCOVERED' "
                "AND resulting_state='CAPTURED'",
                ("d" * 64, "product-flow"),
            )
        else:
            connection.execute(
                "INSERT INTO workflows SELECT ?,current_state,state_identity,state_json "
                "FROM workflows WHERE workflow_identity=?",
                ("other-flow", "product-flow"),
            )
            connection.execute(
                "UPDATE state_transitions SET workflow_identity=? "
                "WHERE workflow_identity=? AND previous_state='DISCOVERED' "
                "AND resulting_state='CAPTURED'",
                ("other-flow", "product-flow"),
            )
    with pytest.raises(ProductOrchestratorError):
        orchestrator.load_editor_review_bundle("product-flow")


def test_grouping_input_consistent_rewrite_fails_canonical_history(tmp_path: Path):
    store, orchestrator, _ = prepare(tmp_path)
    _rewrite_transition_input_consistently(
        store, "CAPTURED", "GROUPED", "f" * 64
    )
    with pytest.raises(ProductOrchestratorError):
        orchestrator.load_editor_review_bundle("product-flow")


@pytest.mark.parametrize("mode", ("row", "blob_absent", "blob_altered"))
def test_capture_payload_binding_faults_fail_closed(tmp_path: Path, mode: str):
    store, orchestrator, _ = prepare(tmp_path)
    capture = _capture_identity(store)
    if mode == "row":
        with store.write() as connection:
            connection.execute(
                "UPDATE captures SET payload_ref=? WHERE capture_identity=?",
                ("blobs/captures/wrong.json", capture),
            )
    else:
        path = store.root / "blobs/captures" / f"{capture}.json"
        if mode == "blob_absent":
            path.unlink()
        else:
            value = json.loads(path.read_text(encoding="utf-8"))
            value["source_text"] = "altered"
            path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ProductOrchestratorError):
        orchestrator.load_editor_review_bundle("product-flow")


def test_grouping_must_consume_exact_capture_batch(tmp_path: Path):
    store, orchestrator, _ = prepare(tmp_path)
    with store.write() as connection:
        row = connection.execute(
            "SELECT event_identity,capture_identity FROM event_sources "
            "ORDER BY capture_identity LIMIT 1"
        ).fetchone()
        connection.execute(
            "DELETE FROM event_sources WHERE event_identity=? AND capture_identity=?",
            tuple(row),
        )
    with pytest.raises(ProductOrchestratorError):
        orchestrator.load_editor_review_bundle("product-flow")


@pytest.mark.parametrize("table", ("attempts", "idempotency"))
def test_capture_operational_receipt_relations_fail_closed(tmp_path: Path, table: str):
    store, orchestrator, _ = prepare(tmp_path)
    with store.write() as connection:
        row = connection.execute(
            "SELECT attempt_identity,idempotency_identity FROM state_transitions "
            "WHERE workflow_identity=? AND previous_state='DISCOVERED' "
            "AND resulting_state='CAPTURED'",
            ("product-flow",),
        ).fetchone()
        if table == "attempts":
            connection.execute(
                "UPDATE attempts SET outcome='FAIL' WHERE attempt_identity=?",
                (row["attempt_identity"],),
            )
        else:
            connection.execute(
                "UPDATE idempotency SET request_identity=? "
                "WHERE workflow_identity=? AND idempotency_identity=?",
                ("e" * 64, "product-flow", row["idempotency_identity"]),
            )
    with pytest.raises(ProductOrchestratorError):
        orchestrator.load_editor_review_bundle("product-flow")


@pytest.mark.parametrize("terminal", (False, True))
def test_downstream_and_terminal_recovery_require_capture_lineage(
    tmp_path: Path, terminal: bool
):
    if terminal:
        store, orchestrator, _, workflow = _persisted_factual_bundle(
            tmp_path, structural=False, outcome="ABSTAIN"
        )
        loader = lambda: orchestrator.load_factual_result_bundle(workflow)
    else:
        store, orchestrator, _ = prepare(tmp_path)
        loader = lambda: orchestrator.load_editor_review_bundle("product-flow")
    _batch_path(store).unlink()
    with pytest.raises(ProductOrchestratorError):
        loader()
