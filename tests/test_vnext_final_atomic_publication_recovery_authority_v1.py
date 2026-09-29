from __future__ import annotations

import json
import runpy
from pathlib import Path

import pytest

from pastila_scout.vnext_core_final_v1 import (
    CoreFinalError,
    assemble_and_export_final,
    authorize_policy_session,
    build_policy_decision,
    enter_policy_review,
    load_exported_final,
    persist_policy_decision,
)
from pastila_scout.vnext_foundation_v1 import object_identity

HELPERS = runpy.run_path("tests/test_vnext_core_workflow_authority_e2e_ownership_repair_v1.py")


def approved_store(tmp_path):
    store, flow, artifact = HELPERS["prepare_through_factual_acceptance"](tmp_path)
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
    return store, flow, artifact, decision


def test_failed_final_ready_transition_never_publishes_export(tmp_path):
    store, flow, artifact, decision = approved_store(tmp_path)
    original = store.transition

    def fail(*args, **kwargs):
        raise RuntimeError("INJECTED_FINAL_READY_FAILURE")

    store.transition = fail
    with pytest.raises(RuntimeError, match="FINAL_READY"):
        assemble_and_export_final(
            store, workflow_identity=flow, factual_output=artifact,
            decision=decision, observed_at="2026-09-29T00:04:00Z",
        )
    store.transition = original
    assert store.load_workflow(flow)["state"] == "APPROVED_FOR_FINAL"
    assert not list((tmp_path / "exports").glob("*.json"))
    assert not list((tmp_path / "receipts" / "final-exports").glob("*.json"))

    final, receipt = assemble_and_export_final(
        store, workflow_identity=flow, factual_output=artifact,
        decision=decision, observed_at="2026-09-29T00:04:00Z",
    )
    assert load_exported_final(
        store, workflow_identity=flow, final_identity=final["artifact_identity"]
    ) == (final, receipt)


def test_failed_exported_transition_remains_ineligible_and_recovers(tmp_path):
    store, flow, artifact, decision = approved_store(tmp_path)
    original = store.transition
    calls = 0

    def fail_second(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise RuntimeError("INJECTED_EXPORTED_FAILURE")
        return original(*args, **kwargs)

    store.transition = fail_second
    with pytest.raises(RuntimeError, match="EXPORTED"):
        assemble_and_export_final(
            store, workflow_identity=flow, factual_output=artifact,
            decision=decision, observed_at="2026-09-29T00:04:00Z",
        )
    store.transition = original
    assert store.load_workflow(flow)["state"] == "FINAL_READY"
    assert len(list((tmp_path / "exports").glob("*.json"))) == 1
    assert len(list((tmp_path / "receipts" / "final-exports").glob("*.json"))) == 1
    final_identity = next((tmp_path / "exports").glob("*.json")).stem
    with pytest.raises(CoreFinalError, match="not export-eligible"):
        load_exported_final(
            store, workflow_identity=flow, final_identity=final_identity
        )

    final, receipt = assemble_and_export_final(
        store, workflow_identity=flow, factual_output=artifact,
        decision=decision, observed_at="2026-09-29T00:04:00Z",
    )
    assert store.load_workflow(flow)["state"] == "EXPORTED"
    assert load_exported_final(
        store, workflow_identity=flow, final_identity=final["artifact_identity"]
    ) == (final, receipt)


def test_export_tampering_fails_eligibility_loader(tmp_path):
    store, flow, artifact, decision = approved_store(tmp_path)
    final, receipt = assemble_and_export_final(
        store, workflow_identity=flow, factual_output=artifact,
        decision=decision, observed_at="2026-09-29T00:04:00Z",
    )
    (tmp_path / receipt["export_ref"]).write_text('{"tampered":true}\n', encoding="utf-8")
    with pytest.raises(CoreFinalError, match="bytes mismatch"):
        load_exported_final(
            store, workflow_identity=flow, final_identity=final["artifact_identity"]
        )


def test_authority_semantics_claim_isolated_product_orchestrator():
    manifest = json.loads(
        Path("docs/artifacts/vnext-active-authority-audit-manifest-v1.json").read_text(encoding="utf-8")
    )
    invariants = manifest["invariants"]
    assert invariants["post_acceptance_policy_final_implemented"] is True
    assert invariants["policy_final_merged"] is True
    assert invariants["product_orchestrator_implemented"] is True



def exported_store(tmp_path):
    store, flow, artifact, decision = approved_store(tmp_path)
    final, receipt = assemble_and_export_final(
        store, workflow_identity=flow, factual_output=artifact,
        decision=decision, observed_at="2026-09-29T00:04:00Z",
    )
    return store, flow, final, receipt


def replace_receipt(tmp_path, final_identity, receipt):
    path = tmp_path / "receipts" / "final-exports" / f"{final_identity}.json"
    path.write_text(
        json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def test_self_consistent_receipt_rebinding_is_rejected(tmp_path):
    store, flow, final, receipt = exported_store(tmp_path)
    original = tmp_path / receipt["export_ref"]
    rebound_path = tmp_path / "exports" / "rebound.json"
    rebound_path.write_bytes(original.read_bytes())
    rebound = dict(receipt)
    rebound["export_ref"] = "exports/rebound.json"
    rebound.pop("receipt_identity")
    rebound["receipt_identity"] = object_identity(rebound)
    replace_receipt(tmp_path, final["artifact_identity"], rebound)
    with pytest.raises(CoreFinalError, match="transition binding mismatch"):
        load_exported_final(
            store, workflow_identity=flow, final_identity=final["artifact_identity"]
        )


def test_cross_workflow_receipt_is_rejected(tmp_path):
    store, flow, final, receipt = exported_store(tmp_path)
    rebound = dict(receipt)
    rebound["workflow_identity"] = "other-workflow"
    rebound.pop("receipt_identity")
    rebound["receipt_identity"] = object_identity(rebound)
    replace_receipt(tmp_path, final["artifact_identity"], rebound)
    with pytest.raises(CoreFinalError, match="provenance mismatch"):
        load_exported_final(
            store, workflow_identity=flow, final_identity=final["artifact_identity"]
        )


def test_missing_export_transition_binding_is_rejected(tmp_path):
    store, flow, final, _ = exported_store(tmp_path)
    with store.write() as connection:
        connection.execute(
            "UPDATE state_transitions SET output_identity=NULL "
            "WHERE workflow_identity=? AND resulting_state='EXPORTED'",
            (flow,),
        )
    with pytest.raises(CoreFinalError, match="transition binding mismatch"):
        load_exported_final(
            store, workflow_identity=flow, final_identity=final["artifact_identity"]
        )


def test_duplicate_export_transition_binding_is_rejected(tmp_path):
    store, flow, final, receipt = exported_store(tmp_path)
    attempt = "attempt:duplicate-export"
    with store.write() as connection:
        connection.execute(
            "INSERT INTO attempts VALUES(?,?,?,?)",
            (attempt, flow, "audit:duplicate-export", "PASS"),
        )
        connection.execute(
            "INSERT INTO state_transitions("
            "workflow_identity,receipt_identity,operation_identity,previous_state,"
            "resulting_state,actor,outcome,input_identity,output_identity,"
            "attempt_identity,idempotency_identity,receipt_json"
            ") VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                flow, object_identity({"duplicate": flow}), "audit:duplicate-export",
                "FINAL_READY", "EXPORTED", "audit", "PASS",
                final["artifact_identity"], receipt["receipt_identity"],
                attempt, "idempotency:duplicate-export", b"{}",
            ),
        )
    with pytest.raises(CoreFinalError, match="transition binding mismatch"):
        load_exported_final(
            store, workflow_identity=flow, final_identity=final["artifact_identity"]
        )
