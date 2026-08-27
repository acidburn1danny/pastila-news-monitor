from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-role-case01-receipt-v1-1-run-v1-freeze.json"
RUN = ROOT / ".semantic-admission-v2-stage-p-construction-role-case01-receipt-v1-1-run-v1-evidence"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_freeze_identity_and_root_evidence_are_byte_exact():
    value = json.loads(ARTIFACT.read_text("utf-8")); evidence = value["immutable_evidence"]
    parts = [value["artifact_id"], value["source_probe_binding_identity"],
             evidence["phase_receipt_sha256"], evidence["typed_liveness_receipt_sha256"],
             evidence["durable_tree_identity"], value["repeated_semantic_failure"]["decoded_partial_sha256"],
             "RECEIPT_PROPAGATION_PROOF_PASS", "CONSTRUCTION_TO_LEDGER_RECONCILIATION_FAILURE_RECURRED",
             "NO_RERUN", "NO_REMEDIATION", "NO_STAGE_C"]
    assert hashlib.sha256("\n".join(parts).encode()).hexdigest() == value["canonical_identity"]
    for filename, key in (("stage-p-phase-receipt-v2.json", "phase_receipt_sha256"),
                          ("constraint-liveness-failure.json", "typed_liveness_receipt_sha256"),
                          ("identity-binding.json", "identity_binding_sha256"),
                          ("stage-p-request.json", "request_sha256")):
        assert hashlib.sha256((RUN / filename).read_bytes()).hexdigest() == evidence[key]


def test_only_receipt_propagation_proof_receives_authority():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    assert value["receipt_propagation_proof"]["result"] == "PASS"
    assert value["authority"]["receipt_propagation_proof"] is True
    assert not any(flag for key, flag in value["authority"].items() if key != "receipt_propagation_proof")
    assert value["execution_receipt"]["provider_call_count"] == 1
    assert value["execution_receipt"]["stage_c_calls"] == 0


def test_complete_durable_lifecycle_tree_reproduces_exactly():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    evidence = value["immutable_evidence"]
    durable = RUN / "durable-lifecycle" / evidence["durable_lifecycle_relative_path"]
    files = sorted(path for path in durable.glob("*.json") if path.is_file())
    lines = [f"{path.name}\t{_sha256(path)}" for path in files]
    assert len(files) == 75
    assert hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest() == evidence["durable_tree_identity"]
    assert _sha256(durable / "host-00004-host-constraint-liveness-failure-classified.json") == evidence["host_liveness_event_sha256"]
    assert _sha256(durable / "runner-00071-runner-exception.json") == evidence["runner_exception_sha256"]
