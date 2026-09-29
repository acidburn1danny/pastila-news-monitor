from __future__ import annotations

import json
from pathlib import Path

import pytest

from pastila_scout.vnext_foundation_v1 import object_identity
from pastila_scout.vnext_product_orchestrator_v1 import (
    ProductOrchestrator,
    ProductOrchestratorError,
    bootstrap_store,
)
from pastila_scout.vnext_scout_production_v1 import (
    FetchResponse,
    SourceDefinition,
    source_set_from_definitions,
)
from pastila_scout.vnext_state_sqlite_v1 import SCHEMA_VERSION
from pastila_scout.vnext_workflow_v1 import STATES, TRANSITIONS

AUTHORITY = Path("docs/artifacts/vnext-active-product-workflow-state-contract-v4.json")


def _sources():
    return source_set_from_definitions((
        SourceDefinition("one", "One", "https://one.example/feed", ("news",), 5),
        SourceDefinition("two", "Two", "https://two.example/feed", ("news",), 5),
    ))


def _prepare(tmp_path: Path, mode: str):
    store = bootstrap_store(tmp_path, writer_identity="audit")
    orchestrator = ProductOrchestrator(store)
    orchestrator.create_workflow("flow")

    def transport(source: SourceDefinition, timeout: float) -> FetchResponse:
        del timeout
        if mode == "all_failed" or (mode == "mixed" and source.source_id == "two"):
            raise OSError("offline")
        return FetchResponse(
            b"<rss><channel></channel></rss>",
            source.url,
            "application/rss+xml",
        )

    groups, failures = orchestrator.capture_and_group(
        workflow_identity="flow",
        source_set=_sources(),
        transport=transport,
        captured_at="2026-09-29T01:00:00Z",
    )
    assert groups == ()
    return store, orchestrator, failures


def _batch_path(store):
    paths = list((store.root / "blobs/capture-batches").glob("*.json"))
    assert len(paths) == 1
    return paths[0]


def test_workflow_authority_v4_is_content_addressed_and_exact():
    authority = json.loads(AUTHORITY.read_text(encoding="utf-8"))
    assert authority["authority_identity"] == object_identity(
        {key: value for key, value in authority.items() if key != "authority_identity"}
    )
    assert authority["supersedes"] == "vnext-active-product-workflow-state-contract-v3"
    assert set(map(tuple, authority["transitions"])) == set(TRANSITIONS)
    assert set(authority["states"]) == set(STATES)
    assert authority["terminal_semantics"]["NO_ELIGIBLE_CONTENT"]["operational_outcome"] == "PASS"
    assert authority["terminal_semantics"]["CAPTURE_FAILED"]["operational_outcome"] == "FAIL"
    assert SCHEMA_VERSION == 7


def test_all_empty_is_neutral_terminal_and_rehydrates(tmp_path: Path):
    store, orchestrator, failures = _prepare(tmp_path, "all_empty")
    assert failures == ()
    workflow = store.load_workflow("flow")
    assert workflow["state"] == "NO_ELIGIBLE_CONTENT"
    assert workflow["receipts"][-1]["outcome"] == "PASS"
    batch = orchestrator.load_capture_terminal_result("flow")
    assert {item["outcome"] for item in batch["source_dispositions"]} == {
        "NO_ELIGIBLE_ENTRIES"
    }


def test_all_failure_is_failure_terminal_and_rehydrates(tmp_path: Path):
    store, orchestrator, failures = _prepare(tmp_path, "all_failed")
    assert len(failures) == 2
    workflow = store.load_workflow("flow")
    assert workflow["state"] == "CAPTURE_FAILED"
    assert workflow["receipts"][-1]["outcome"] == "FAIL"
    batch = orchestrator.load_capture_terminal_result("flow")
    assert {item["outcome"] for item in batch["source_dispositions"]} == {
        "CAPTURE_FAILED"
    }


def test_mixed_empty_and_failure_is_failure_terminal(tmp_path: Path):
    store, orchestrator, failures = _prepare(tmp_path, "mixed")
    assert len(failures) == 1
    assert store.load_workflow("flow")["state"] == "CAPTURE_FAILED"
    batch = orchestrator.load_capture_terminal_result("flow")
    assert [item["outcome"] for item in batch["source_dispositions"]] == [
        "NO_ELIGIBLE_ENTRIES",
        "CAPTURE_FAILED",
    ]


@pytest.mark.parametrize("mode", ("all_empty", "all_failed"))
@pytest.mark.parametrize("mutation", ("missing", "duplicate", "altered", "cross_workflow"))
def test_terminal_transition_faults_fail_closed(tmp_path: Path, mode: str, mutation: str):
    store, orchestrator, _ = _prepare(tmp_path, mode)
    resulting = store.load_workflow("flow")["state"]
    with store.write() as connection:
        if mutation == "missing":
            connection.execute(
                "DELETE FROM state_transitions WHERE workflow_identity=? "
                "AND previous_state='DISCOVERED' AND resulting_state=?",
                ("flow", resulting),
            )
        elif mutation == "duplicate":
            connection.execute(
                "INSERT INTO state_transitions("
                "workflow_identity,receipt_identity,operation_identity,previous_state,"
                "resulting_state,actor,outcome,input_identity,output_identity,"
                "attempt_identity,idempotency_identity,receipt_json"
                ") SELECT workflow_identity,?,operation_identity,previous_state,"
                "resulting_state,actor,outcome,input_identity,output_identity,"
                "attempt_identity,idempotency_identity,receipt_json "
                "FROM state_transitions WHERE workflow_identity=? "
                "AND previous_state='DISCOVERED' AND resulting_state=?",
                ("d" * 64, "flow", resulting),
            )
        elif mutation == "altered":
            connection.execute(
                "UPDATE state_transitions SET outcome=? WHERE workflow_identity=? "
                "AND previous_state='DISCOVERED' AND resulting_state=?",
                ("FAIL" if resulting == "NO_ELIGIBLE_CONTENT" else "PASS", "flow", resulting),
            )
        else:
            connection.execute(
                "INSERT INTO workflows SELECT ?,current_state,state_identity,state_json "
                "FROM workflows WHERE workflow_identity=?",
                ("other-flow", "flow"),
            )
            connection.execute(
                "UPDATE state_transitions SET workflow_identity=? "
                "WHERE workflow_identity=? AND previous_state='DISCOVERED' "
                "AND resulting_state=?",
                ("other-flow", "flow", resulting),
            )
    with pytest.raises(ProductOrchestratorError):
        orchestrator.load_capture_terminal_result("flow")


@pytest.mark.parametrize("mode", ("all_empty", "all_failed"))
def test_terminal_batch_loss_fails_closed(tmp_path: Path, mode: str):
    store, orchestrator, _ = _prepare(tmp_path, mode)
    _batch_path(store).unlink()
    with pytest.raises(ProductOrchestratorError):
        orchestrator.load_capture_terminal_result("flow")
