from __future__ import annotations

import json
import runpy
import sqlite3
from pathlib import Path

import pytest

from pastila_scout.vnext_foundation_v1 import object_identity
from pastila_scout.vnext_product_orchestrator_v1 import ProductOrchestrator, ProductOrchestratorError
from pastila_scout.vnext_scout_production_v1 import ScoutError, build_source_packet
from pastila_scout.vnext_state_sqlite_v1 import MIGRATIONS, SCHEMA_VERSION, SQLiteStateStore, migration_identity

_HELPERS = runpy.run_path(str(Path(__file__).with_name("test_vnext_product_orchestrator_integrated_core_e2e_v1.py")))
SOURCES = _HELPERS["SOURCES"]
_persisted_factual_bundle = _HELPERS["_persisted_factual_bundle"]
bootstrap_store = _HELPERS["bootstrap_store"]
prepare = _HELPERS["prepare"]
transport = _HELPERS["transport"]


def _capture_group(store: SQLiteStateStore, workflow: str, captured_at: str = "2026-09-29T01:00:00Z"):
    orchestrator = ProductOrchestrator(store)
    orchestrator.create_workflow(workflow)
    groups, _ = orchestrator.capture_and_group(
        workflow_identity=workflow, source_set=SOURCES,
        transport=transport, captured_at=captured_at, maximum_workers=2,
    )
    return orchestrator, groups


def test_schema_v7_adds_only_workflow_event_authority(tmp_path: Path):
    store = bootstrap_store(tmp_path, writer_identity="writer")
    assert SCHEMA_VERSION == 7
    with store.read() as connection:
        assert connection.execute("PRAGMA user_version").fetchone()[0] == 7
        columns = {row["name"]: row["type"] for row in connection.execute("PRAGMA table_info(workflow_events)")}
        assert columns == {"workflow_identity": "TEXT", "event_identity": "TEXT", "grouping_identity": "TEXT", "position": "INTEGER"}
        row = connection.execute("SELECT migration_identity FROM schema_migrations WHERE version=7").fetchone()
        assert row["migration_identity"] == migration_identity(7)


def test_migration_7_preserves_existing_v6_rows(tmp_path: Path):
    root = tmp_path / "root"; root.mkdir(); database = root / "state.sqlite3"
    connection = sqlite3.connect(database)
    try:
        for version in range(1, 7):
            for statement in MIGRATIONS[version]:
                connection.execute(statement)
            connection.execute("INSERT INTO schema_migrations VALUES(?,?,?)", (version, migration_identity(version), "writer"))
            connection.execute("INSERT OR IGNORE INTO writer_owner VALUES(1,?)", ("writer",))
        connection.execute("PRAGMA user_version=6")
        connection.execute("INSERT INTO workflows VALUES(?,?,?,?)", ("preserved", "DISCOVERED", "state", b"{}"))
        connection.commit()
    finally:
        connection.close()
    store = SQLiteStateStore(root=root, database=Path("state.sqlite3"), writer_identity="writer")
    store.bootstrap()
    with store.read() as check:
        assert check.execute("SELECT workflow_identity FROM workflows").fetchone()[0] == "preserved"
        assert check.execute("SELECT COUNT(*) FROM workflow_events").fetchone()[0] == 0


def test_grouping_persists_exact_workflow_membership_and_transition(tmp_path: Path):
    store = bootstrap_store(tmp_path, writer_identity="writer")
    _, groups = _capture_group(store, "flow")
    with store.read() as connection:
        rows = connection.execute("SELECT event_identity,grouping_identity,position FROM workflow_events WHERE workflow_identity=? ORDER BY position", ("flow",)).fetchall()
        transition = connection.execute("SELECT output_identity,receipt_json FROM state_transitions WHERE workflow_identity=? AND previous_state='CAPTURED' AND resulting_state='GROUPED'", ("flow",)).fetchone()
    assert [row["event_identity"] for row in rows] == [group.event_identity for group in groups]
    assert [row["position"] for row in rows] == list(range(len(groups)))
    expected = object_identity([group.grouping_identity for group in groups])
    assert transition["output_identity"] == expected
    assert json.loads(transition["receipt_json"])["output_identity"] == expected


def test_cross_workflow_selection_is_rejected_before_transition(tmp_path: Path):
    store = bootstrap_store(tmp_path, writer_identity="writer")
    _, groups_a = _capture_group(store, "flow-a")
    _, groups_b = _capture_group(store, "flow-b", "2026-09-29T02:00:00Z")
    foreign = next(group.event_identity for group in groups_a if group.event_identity not in {item.event_identity for item in groups_b})
    with pytest.raises(ScoutError, match="not owned uniquely"):
        build_source_packet(store, workflow_identity="flow-b", event_identity=foreign, selection_actor="Daniel", selection_authorization_identity="a" * 64, observed_at="2026-09-29T01:01:00Z")
    assert store.load_workflow("flow-b")["state"] == "GROUPED"
    with store.read() as connection:
        assert connection.execute("SELECT COUNT(*) FROM state_transitions WHERE workflow_identity=? AND previous_state='GROUPED' AND resulting_state='SELECTED'", ("flow-b",)).fetchone()[0] == 0


def test_same_content_addressed_event_is_safely_reused_between_workflows(tmp_path: Path):
    store = bootstrap_store(tmp_path, writer_identity="writer")
    _, groups_a = _capture_group(store, "flow-a")
    _, groups_b = _capture_group(store, "flow-b")
    assert [item.event_identity for item in groups_a] == [item.event_identity for item in groups_b]
    with store.read() as connection:
        assert connection.execute("SELECT COUNT(*) FROM events").fetchone()[0] == len(groups_a)
        assert connection.execute("SELECT COUNT(*) FROM workflow_events").fetchone()[0] == 2 * len(groups_a)


@pytest.mark.parametrize("mode", ("absent", "altered", "cross_workflow"))
def test_workflow_event_membership_faults_fail_closed(tmp_path: Path, mode: str):
    store, orchestrator, editor = prepare(tmp_path); event = editor.packet["event_identity"]
    with store.write() as connection:
        if mode == "absent":
            connection.execute("DELETE FROM workflow_events WHERE workflow_identity=? AND event_identity=?", ("product-flow", event))
        elif mode == "altered":
            connection.execute("UPDATE workflow_events SET grouping_identity=? WHERE workflow_identity=? AND event_identity=?", ("f" * 64, "product-flow", event))
        else:
            connection.execute("INSERT INTO workflows SELECT ?,current_state,state_identity,state_json FROM workflows WHERE workflow_identity=?", ("other-flow", "product-flow"))
            connection.execute("UPDATE workflow_events SET workflow_identity=? WHERE workflow_identity=? AND event_identity=?", ("other-flow", "product-flow", event))
    with pytest.raises((ProductOrchestratorError, ScoutError)):
        orchestrator.load_editor_review_bundle("product-flow")


def test_duplicate_workflow_event_membership_is_database_rejected(tmp_path: Path):
    store, _, editor = prepare(tmp_path); event = editor.packet["event_identity"]
    with pytest.raises(sqlite3.IntegrityError):
        with store.write() as connection:
            row = connection.execute("SELECT grouping_identity,position FROM workflow_events WHERE workflow_identity=? AND event_identity=?", ("product-flow", event)).fetchone()
            connection.execute("INSERT INTO workflow_events VALUES(?,?,?,?)", ("product-flow", event, row["grouping_identity"], row["position"]))


@pytest.mark.parametrize("mode", ("absent", "duplicate", "altered", "cross_workflow"))
def test_grouping_transition_faults_fail_closed(tmp_path: Path, mode: str):
    store, orchestrator, _ = prepare(tmp_path)
    with store.write() as connection:
        if mode == "absent":
            connection.execute("DELETE FROM state_transitions WHERE workflow_identity=? AND previous_state='CAPTURED' AND resulting_state='GROUPED'", ("product-flow",))
        elif mode == "duplicate":
            connection.execute("INSERT INTO state_transitions(workflow_identity,receipt_identity,operation_identity,previous_state,resulting_state,actor,outcome,input_identity,output_identity,attempt_identity,idempotency_identity,receipt_json) SELECT workflow_identity,?,operation_identity,previous_state,resulting_state,actor,outcome,input_identity,output_identity,attempt_identity,idempotency_identity,receipt_json FROM state_transitions WHERE workflow_identity=? AND previous_state='CAPTURED' AND resulting_state='GROUPED'", ("e" * 64, "product-flow"))
        elif mode == "altered":
            connection.execute("UPDATE state_transitions SET output_identity=? WHERE workflow_identity=? AND previous_state='CAPTURED' AND resulting_state='GROUPED'", ("e" * 64, "product-flow"))
        else:
            connection.execute("INSERT INTO workflows SELECT ?,current_state,state_identity,state_json FROM workflows WHERE workflow_identity=?", ("other-flow", "product-flow"))
            connection.execute("UPDATE state_transitions SET workflow_identity=? WHERE workflow_identity=? AND previous_state='CAPTURED' AND resulting_state='GROUPED'", ("other-flow", "product-flow"))
    with pytest.raises((ProductOrchestratorError, ScoutError)):
        orchestrator.load_editor_review_bundle("product-flow")


def test_terminal_factual_rehydration_rejects_broken_grouping_lineage(tmp_path: Path):
    store, orchestrator, _, workflow = _persisted_factual_bundle(tmp_path, structural=False, outcome="ABSTAIN")
    with store.write() as connection:
        connection.execute("DELETE FROM workflow_events WHERE workflow_identity=?", (workflow,))
    with pytest.raises(ProductOrchestratorError):
        orchestrator.load_factual_result_bundle(workflow)
