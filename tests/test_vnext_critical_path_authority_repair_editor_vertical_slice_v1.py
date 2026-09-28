from __future__ import annotations

import copy
import json
import sqlite3
from dataclasses import replace
from pathlib import Path

import pytest

from pastila_scout.vnext_editor_vertical_slice_v1 import (
    DECODING,
    EditorVerticalSliceError,
    GenerationEvidence,
    persist_editor_draft,
    run_editor_vertical_slice,
    validate_editor_draft,
)
from pastila_scout.vnext_foundation_v1 import object_identity
from pastila_scout.vnext_scout_production_v1 import ScoutError
from pastila_scout.vnext_state_sqlite_v1 import (
    MIGRATION_1,
    SQLiteStateStore,
    migration_identity,
)
from pastila_scout.vnext_workflow_v1 import (
    TransitionRequest,
    apply_transition,
    new_workflow,
)

FIXTURE = Path("docs/artifacts/vnext-critical-path-authority-repair-editor-vertical-slice-v1-fixture.json")
SOURCE = Path("docs/artifacts/vnext-sourcepacket-production-binding-v1-fixture.json")
CONTRACT = Path("docs/artifacts/vnext-critical-path-authority-repair-editor-vertical-slice-v1.json")


class Backend:
    r2_lock_identity = "53fafbc03f70c8c32357645a6a428260f1bdfbd104edbe1c4aa825e95c83a10f"
    def __init__(self, evidence: GenerationEvidence): self.evidence = evidence
    def generate(self, messages, decoding):
        assert [item["role"] for item in messages] == ["system", "user"]
        assert decoding == DECODING
        return self.evidence


def inputs():
    value = json.loads(FIXTURE.read_text(encoding="utf-8"))
    packet = json.loads(SOURCE.read_text(encoding="utf-8"))["source_packet"]
    evidence = GenerationEvidence(
        value["rendered_prompt"], tuple(value["input_token_ids"]), value["raw_output"].encode(),
        value["eos_token_id"], value["pad_token_id"], value["chat_template_sha256"],
    )
    return value, packet, evidence


def transition(flow: str, previous: str, resulting: str, index: int) -> TransitionRequest:
    return TransitionRequest(flow, f"fixture:{index}", previous, resulting, "fixture", "PASS", object_identity(index), object_identity(index + 1), f"attempt:{index}", f"idem:{index}")


def advance_to_source_packet(store: SQLiteStateStore, flow: str) -> None:
    store.create_workflow(flow)
    for index, (left, right) in enumerate((("DISCOVERED", "CAPTURED"), ("CAPTURED", "GROUPED"), ("GROUPED", "SELECTED"), ("SELECTED", "SOURCE_PACKET_READY")), 1):
        store.transition(transition(flow, left, right, index))


def test_complete_fixture_vertical_slice_and_exact_provenance():
    fixture, packet, evidence = inputs()
    receipt, draft = run_editor_vertical_slice(packet, Backend(evidence))
    validate_editor_draft(draft, source_packet=packet, invocation_receipt=receipt)
    assert draft["text"] == fixture["expected_text"]
    assert receipt["receipt_identity"] == fixture["expected_invocation_receipt_identity"]
    assert draft["draft_identity"] == fixture["expected_draft_identity"]
    assert receipt["source_packet_identity"] == packet["packet_identity"]
    for key in ("prompt_identity", "messages_identity", "rendered_prompt_sha256", "input_token_ids_identity", "chat_template_sha256", "decoding_identity", "runtime_identity", "raw_output_sha256"):
        assert isinstance(receipt[key], str) and len(receipt[key]) == 64
    assert draft["eligible_as_accepted_setup"] is False and draft["eligible_for_voice"] is False


@pytest.mark.parametrize("raw", [b"bad", b"{}", b'{"case_id":"wrong","text":"x"}', b'{"case_id":"event:arin","text":"x","eligible_for_voice":true}', b'{"case_id":"event:arin","case_id":"event:arin","text":"x"}'])
def test_structural_invalid_output_never_creates_editor_draft(raw: bytes):
    _, packet, evidence = inputs()
    with pytest.raises(EditorVerticalSliceError):
        run_editor_vertical_slice(packet, Backend(replace(evidence, raw_output=raw)))


def test_source_and_receipt_tampering_fail_closed():
    _, packet, evidence = inputs()
    changed = copy.deepcopy(packet); changed["spans"][0]["text"] += " inventat"
    with pytest.raises(ScoutError):
        run_editor_vertical_slice(changed, Backend(evidence))
    receipt, draft = run_editor_vertical_slice(packet, Backend(evidence))
    changed_receipt = copy.deepcopy(receipt); changed_receipt["prompt_identity"] = "0" * 64
    with pytest.raises(EditorVerticalSliceError):
        validate_editor_draft(draft, source_packet=packet, invocation_receipt=changed_receipt)


def test_workflow_repairs_make_success_and_failure_routes_coherent():
    success = new_workflow("success")
    success["state"] = "EDITOR_PENDING"; success["state_identity"] = object_identity({key: value for key, value in success.items() if key != "state_identity"})
    success, _, _ = apply_transition(success, transition("success", "EDITOR_PENDING", "EDITOR_DRAFT_READY", 10))
    success, _, _ = apply_transition(success, transition("success", "EDITOR_DRAFT_READY", "FACTUAL_REVIEW_PENDING", 11))
    assert success["state"] == "FACTUAL_REVIEW_PENDING"
    failed = new_workflow("failed")
    failed["state"] = "EDITOR_PENDING"; failed["state_identity"] = object_identity({key: value for key, value in failed.items() if key != "state_identity"})
    failed, _, _ = apply_transition(failed, transition("failed", "EDITOR_PENDING", "STRUCTURAL_FAIL", 20))
    failed, _, _ = apply_transition(failed, transition("failed", "STRUCTURAL_FAIL", "FACTUAL_REVIEW_PENDING", 21))
    assert failed["state"] == "FACTUAL_REVIEW_PENDING"


def test_sqlite_v1_database_migrates_through_v3(tmp_path: Path):
    database = tmp_path / "state.db"
    connection = sqlite3.connect(database)
    for statement in MIGRATION_1: connection.execute(statement)
    connection.execute("INSERT INTO schema_migrations VALUES(1,?,?)", (migration_identity(1), "writer"))
    connection.execute("INSERT INTO writer_owner VALUES(1,'writer')")
    connection.execute("INSERT INTO workflows VALUES('flow','DISCOVERED','state-id',X'7B7D')")
    connection.execute("INSERT INTO workflow_artifacts VALUES('old-draft','flow','EDITOR_DRAFT','payload','blobs/old.json','schema-v1')")
    connection.execute("PRAGMA user_version=1"); connection.commit(); connection.close()
    store = SQLiteStateStore(root=tmp_path, database=Path("state.db"), writer_identity="writer")
    store.bootstrap()
    with store.read() as current:
        assert current.execute("PRAGMA user_version").fetchone()[0] == 6
        sql = current.execute("SELECT sql FROM sqlite_master WHERE name='workflow_artifacts'").fetchone()[0]
        assert all(kind in sql for kind in ("STRUCTURAL_FAILURE", "ACCEPTED_SETUP", "SOURCE_FALLBACK", "ABSTAINED"))
        assert "PRIMARYKEY(workflow_identity,artifact_identity)" in sql.replace(" ", "")
        assert current.execute("SELECT artifact_kind FROM workflow_artifacts WHERE artifact_identity='old-draft'").fetchone()[0] == "EDITOR_DRAFT"


def test_editor_draft_persists_atomically_and_stops_before_acceptance(tmp_path: Path):
    _, packet, evidence = inputs(); receipt, draft = run_editor_vertical_slice(packet, Backend(evidence))
    store = SQLiteStateStore(root=tmp_path, database=Path("state.db"), writer_identity="writer"); store.bootstrap(); advance_to_source_packet(store, "flow")
    persist_editor_draft(store, workflow_identity="flow", packet=packet, invocation=receipt, draft=draft, observed_at="2026-09-28T00:00:00Z")
    assert store.load_workflow("flow")["state"] == "FACTUAL_REVIEW_PENDING"
    with store.read() as connection:
        row = connection.execute("SELECT artifact_kind,payload_ref FROM workflow_artifacts").fetchone()
        assert tuple(row) == ("EDITOR_DRAFT", f"blobs/editor-drafts/{draft['draft_identity']}.json")
        assert connection.execute("SELECT COUNT(*) FROM decisions").fetchone()[0] == 0
    assert (tmp_path / "blobs/editor-invocations" / f"{receipt['receipt_identity']}.json").is_file()


def test_unverified_backend_and_output_binding_fail_closed():
    _, packet, evidence = inputs()
    backend = Backend(evidence); backend.r2_lock_identity = "0" * 64
    with pytest.raises(EditorVerticalSliceError, match="verified R2"):
        run_editor_vertical_slice(packet, backend)
    receipt, draft = run_editor_vertical_slice(packet, Backend(evidence))
    changed = copy.deepcopy(draft); changed["raw_output_sha256"] = "0" * 64
    changed["draft_identity"] = object_identity({key: value for key, value in changed.items() if key != "draft_identity"})
    with pytest.raises(EditorVerticalSliceError, match="output binding"):
        validate_editor_draft(changed, source_packet=packet, invocation_receipt=receipt)


def test_contract_is_isolated_and_non_eligible():
    value = json.loads(CONTRACT.read_text(encoding="utf-8"))
    assert object_identity({key: item for key, item in value.items() if key != "closure_identity"}) == value["closure_identity"]
    assert value["status"] == "ISOLATED_NOT_ACTIVE"
    assert value["repairs"]["source_packet"]["active_schema_count"] == 1
    assert value["editor"]["eligible_as_accepted_setup"] is False
    assert value["active_integration"] is False and value["product_lock_replaced"] is False
    assert value["legacy_dependency_count"] == 0
    fixture = json.loads(FIXTURE.read_text(encoding="utf-8"))
    assert object_identity({key: item for key, item in fixture.items() if key != "fixture_identity"}) == fixture["fixture_identity"]
