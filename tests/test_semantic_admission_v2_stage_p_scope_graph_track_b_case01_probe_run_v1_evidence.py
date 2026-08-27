from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-scope-graph-track-b-case01-probe-run-v1-evidence"
RUN_ID = "6860c28d5925b279c61193179e4c26dd8d0764e4b62fa59e23cf7e2261df21c0"
LIFECYCLE = EVIDENCE / "durable-lifecycle" / RUN_ID


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text("utf-8"))


def test_complete_timeout_tree_has_exact_aggregate_identity() -> None:
    files = sorted(path for path in EVIDENCE.rglob("*") if path.is_file())
    entries = "".join(
        f"{path.relative_to(EVIDENCE).as_posix()}\0{hashlib.sha256(path.read_bytes()).hexdigest()}\n"
        for path in files
    ).encode()
    assert len(files) == 21
    assert sum(path.stat().st_size for path in files) == 7603
    assert hashlib.sha256(entries).hexdigest() == "ee3b6df5f15037f5faa3c79eccfcce80483906d580b6a684f498b37e5bd9db39"


def test_binding_and_lifecycle_are_exact_and_ordered() -> None:
    binding = _load(EVIDENCE / "identity-binding.json")
    assert binding["case_id"] == "HMCV1-SASC-01"
    assert binding["evaluator_binding_identity"] == "c94bcf9ffed5d33223d31d9b2d1014b0595b15422af86cfb3581c8022b85e4a7"
    assert binding["request_candidate_identity"] == "c6ab0e2f7721710af208c70ad96d31a412596b9ce69ee8f7f485caba5b620f08"
    assert binding["retry_count"] == binding["repair_count"] == binding["selection_count"] == 0
    assert binding["stage_c_constructed"] is binding["stage_c_called"] is False

    host = [_load(path) for path in sorted(LIFECYCLE.glob("host-*.json"))]
    runner = [_load(path) for path in sorted(LIFECYCLE.glob("runner-*.json"))]
    assert [event["sequence"] for event in host] == [1, 2, 3, 4]
    assert [event["event"] for event in host] == [
        "HOST_LAUNCH", "HOST_PROCESS_STARTED", "HOST_TIMEOUT", "HOST_TERMINATION_OBSERVED"
    ]
    assert host[-1]["termination"] == "TERMINATED" and host[-1]["returncode"] == 1
    assert [event["sequence"] for event in runner] == list(range(1, 15))
    assert runner[-1]["event"] == "GENERATION_HEARTBEAT"


def test_last_partial_heartbeat_and_fail_closed_receipt_are_preserved() -> None:
    heartbeat = _load(LIFECYCLE / "runner-00014-generation-heartbeat.json")
    assert heartbeat["generated_tokens"] == 31
    assert heartbeat["decoded_utf8_bytes"] == 93
    assert heartbeat["decoded_sha256"] == "0a09678b7cfbf69b33688fad9c122ff60909d9dde5dce031f5fa285853be6f90"
    assert heartbeat["partial_output"].endswith('"entry_type":"CONTAINED_CREATIVE')
    assert heartbeat["tracking_path"] == "INCREMENTAL" and heartbeat["tracker_rebuilds"] == 0

    receipt = _load(EVIDENCE / "stage-p-phase-receipt-v2.json")
    assert receipt["provider_call_count"] == 1 and receipt["transport"] == "FAIL"
    assert receipt["raw_persistence"] == receipt["schema_validation"] == receipt["source_membership"] == "NOT_RUN"
    assert receipt["raw_bytes"] == 0 and receipt["raw_path"] is receipt["raw_sha256"] is None
    assert receipt["final_decision"] == "ABSTAIN_FAIL_CLOSED"
    assert receipt["eligibility"] == "QUARANTINED_EVALUATION_ONLY"
