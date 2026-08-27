import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / ".semantic-admission-v2-ten-case-conformance-run-v3-evidence"


def test_run3_execution_bundle_hashes_and_identity_rederive():
    manifest = json.loads((EVIDENCE / "manifest.json").read_text("utf-8"))
    hashes = []

    for artifact in manifest["main_artifacts"]:
        actual = hashlib.sha256((ROOT / artifact["path"]).read_bytes()).hexdigest()
        assert actual == artifact["sha256"]
        hashes.append(actual)
    hashes.append(manifest["diagnostic_trace_set_identity"])

    assert (
        hashlib.sha256("\n".join(hashes).encode()).hexdigest()
        == manifest["canonical_identity"]
    )


def test_run3_ledger_is_complete_fail_closed_and_non_authorizing():
    manifest = json.loads((EVIDENCE / "manifest.json").read_text("utf-8"))
    authority = json.loads(
        (EVIDENCE / "run3-execution-authority.json").read_text("utf-8")
    )
    ledger = json.loads((EVIDENCE / "raw-call-ledger.json").read_text("utf-8"))
    results = json.loads((EVIDENCE / "raw-results.json").read_text("utf-8"))

    assert ledger["maximum_provider_calls"] == 20
    assert [call["ordinal"] for call in ledger["calls"]] == list(range(1, 21))
    assert all(
        hashlib.sha256((call["raw_response"] or "").encode()).hexdigest()
        == call["raw_response_sha256"]
        for call in ledger["calls"]
    )
    assert results["evaluation_count"] == 10
    assert results["provider_call_count"] == 20
    assert manifest["model_inference_started_count"] == 0
    assert manifest["final_abstention_count"] == 10
    assert manifest["admission_count"] == 0
    assert authority["silent_retry"] is False
    assert authority["repair"] is False
    assert authority["selection"] is False
    assert manifest["runtime_authority"] is False
