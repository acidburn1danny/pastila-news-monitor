from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-role-case01-failure-and-receipt-mismatch-review-v1.json"
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-construction-role-case01-failure-review-v1-evidence/preflight.json"
RUN = ROOT / ".semantic-admission-v2-stage-p-construction-role-case01-run-v1-evidence"


def test_canonical_identity_and_source_bytes_are_frozen():
    value = json.loads(ARTIFACT.read_text("utf-8")); source = value["source_evidence"]
    parts = [value["artifact_id"], value["source_binding_identity"], source["phase_receipt_sha256"],
             source["durable_tree_identity"], source["decoded_partial_sha256"],
             value["frozen_result"]["semantic_failure_class"],
             value["receipt_classification_mismatch"]["class"], "DESIGN_ONLY", "NO_RERUN",
             "NO_REMEDIATION", "NO_STAGE_C"]
    assert hashlib.sha256("\n".join(parts).encode()).hexdigest() == value["canonical_identity"]
    assert hashlib.sha256((RUN / "stage-p-phase-receipt-v2.json").read_bytes()).hexdigest() == source["phase_receipt_sha256"]
    assert hashlib.sha256((RUN / "identity-binding.json").read_bytes()).hexdigest() == source["identity_binding_sha256"]
    assert hashlib.sha256((RUN / "stage-p-request.json").read_bytes()).hexdigest() == source["request_sha256"]


def test_failure_classes_remain_separate_and_fail_closed():
    value = json.loads(ARTIFACT.read_text("utf-8")); frozen = value["frozen_result"]
    assert frozen["semantic_failure_class"] == "CONSTRUCTION_TO_LEDGER_RECONCILIATION_FAILURE"
    assert frozen["execution_failure_class"] == "CONSTRAINT_LIVENESS_FAILURE"
    assert frozen["outer_receipt_class"] == "STAGE_P_PROVIDER_OR_TRANSPORT_FAILURE"
    assert frozen["final_decision"] == "ABSTAIN_FAIL_CLOSED"
    assert value["semantic_failure_analysis"]["evidentiary_limit"].startswith("The 2911-byte content")


def test_analysis_is_design_only_and_denies_all_expansive_authority():
    value = json.loads(ARTIFACT.read_text("utf-8")); evidence = json.loads(EVIDENCE.read_text("utf-8"))
    assert not any(value["authority"].values())
    assert evidence["result"] == "DESIGN_COMPLETE" and not evidence["remediation_implemented"]
    assert evidence["model_calls"] == evidence["provider_calls"] == evidence["inference_calls"] == 0
    assert evidence["reruns"] == evidence["stage_c_calls"] == 0
