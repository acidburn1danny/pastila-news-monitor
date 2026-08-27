import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / ".semantic-admission-v2-ten-case-conformance-run-v4-evidence"
PLAN = ROOT / "docs/artifacts/semantic-admission-v2-run4-constrained-plan.json"


def test_run4_bundle_hashes_identity_and_upstream_bindings_rederive():
    manifest = json.loads((EVIDENCE / "manifest.json").read_text("utf-8"))
    plan = json.loads(PLAN.read_text("utf-8"))
    authority = json.loads(
        (EVIDENCE / "run4-execution-authority.json").read_text("utf-8")
    )
    run3 = json.loads(
        (
            ROOT
            / ".semantic-admission-v2-ten-case-conformance-run-v3-evidence/manifest.json"
        ).read_text("utf-8")
    )
    wsl = json.loads(
        (
            ROOT
            / ".semantic-admission-v2-run4-wsl-access-preflight-v1-evidence/manifest.json"
        ).read_text("utf-8")
    )
    tokenizer = json.loads(
        (
            ROOT
            / ".semantic-admission-v2-tokenizer-regex-impact-v1-evidence/manifest.json"
        ).read_text("utf-8")
    )
    hashes = []

    for artifact in manifest["artifacts"]:
        actual = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
        assert actual == artifact["sha256"]
        hashes.append(actual)

    assert (
        hashlib.sha256("\n".join(hashes).encode()).hexdigest()
        == manifest["canonical_identity"]
    )
    assert plan["source_run3_identity"] == run3["canonical_identity"]
    assert plan["wsl_preflight_identity"] == wsl["canonical_identity"]
    assert plan["tokenizer_impact_identity"] == tokenizer["canonical_identity"]
    assert authority["plan_identity"] == hashlib.sha256(PLAN.read_bytes()).hexdigest()


def test_run4_ledger_is_exactly_once_complete_and_quarantined():
    manifest = json.loads((EVIDENCE / "manifest.json").read_text("utf-8"))
    plan = json.loads(PLAN.read_text("utf-8"))
    authority = json.loads(
        (EVIDENCE / "run4-execution-authority.json").read_text("utf-8")
    )
    ledger = json.loads((EVIDENCE / "raw-call-ledger.json").read_text("utf-8"))
    results = json.loads((EVIDENCE / "raw-results.json").read_text("utf-8"))
    summary = json.loads((EVIDENCE / "evaluation-summary.json").read_text("utf-8"))
    calls = ledger["calls"]
    expected = [
        (case_id, gate_id)
        for case_id in plan["case_ids"]
        for gate_id in plan["gate_order_per_case"]
    ]

    assert ledger["maximum_provider_calls"] == len(calls) == 20
    assert [call["ordinal"] for call in calls] == list(range(1, 21))
    assert [(call["case_id"], call["gate_id"]) for call in calls] == expected
    assert len({(call["case_id"], call["gate_id"]) for call in calls}) == 20
    assert all(call["exception_type"] is None for call in calls)
    assert all(
        hashlib.sha256((call["raw_response"] or "").encode()).hexdigest()
        == call["raw_response_sha256"]
        for call in calls
    )
    assert results["evaluation_count"] == 10
    assert results["provider_call_count"] == 20
    assert summary["retry_count"] == 0
    assert summary["repair_count"] == 0
    assert summary["selection_count"] == 0
    assert manifest["outputs_quarantined"] is True
    assert manifest["current_runtime_admission_affected"] is False
    assert authority["inference_authorized"] is True
    assert authority["runtime_authority"] is False
    assert authority["training_authority"] is False
