from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-track-b-baseline-language-case01-probe-run-v1-evidence"
RUN_ID = "6860c28d5925b279c61193179e4c26dd8d0764e4b62fa59e23cf7e2261df21c0"
LIFECYCLE = EVIDENCE / "durable-lifecycle" / RUN_ID
RAW_SHA256 = "942d9392bc2844b23ae8d6174a40e3df0f98f38e13e57db3e3babb47d4baefc0"


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text("utf-8"))


def test_complete_preserved_tree_has_exact_aggregate_identity() -> None:
    files = sorted(path for path in EVIDENCE.rglob("*") if path.is_file())
    entries = "".join(
        f"{path.relative_to(EVIDENCE).as_posix()}\0{hashlib.sha256(path.read_bytes()).hexdigest()}\n"
        for path in files
    ).encode()
    assert len(files) == 44
    assert sum(path.stat().st_size for path in files) == 35119
    assert hashlib.sha256(entries).hexdigest() == "7de1644b84db1f7fcaf6707d0812cf20081b473cf3b3dbc419eee8c188586f9b"


def test_binding_preserves_single_call_and_authority_boundaries() -> None:
    binding = _load(EVIDENCE / "identity-binding.json")
    assert binding["case_id"] == "HMCV1-SASC-01"
    assert binding["evaluator_binding_identity"] == "3478e78e710c9bfb389fc6f4b34ac7b236ec749dc5a5d6b5d119e32aebe2c49e"
    assert binding["request_candidate_identity"] == "c6ab0e2f7721710af208c70ad96d31a412596b9ce69ee8f7f485caba5b620f08"
    assert binding["maximum_provider_calls"] == 1
    assert binding["retry_count"] == binding["repair_count"] == binding["selection_count"] == 0
    assert binding["stage_c_constructed"] is binding["stage_c_called"] is False


def test_lifecycle_is_complete_ordered_and_terminal() -> None:
    host = [_load(path) for path in sorted(LIFECYCLE.glob("host-*.json"))]
    runner = [_load(path) for path in sorted(LIFECYCLE.glob("runner-*.json"))]
    assert [event["sequence"] for event in host] == [1, 2, 3, 4]
    assert [event["event"] for event in host] == [
        "HOST_LAUNCH", "HOST_PROCESS_STARTED", "HOST_PROCESS_EXITED", "HOST_RESPONSE_VALIDATED"
    ]
    assert host[2]["returncode"] == 0 and host[2]["response_exists"] is True
    assert host[3]["terminal_eos"] is True
    assert [event["sequence"] for event in runner] == list(range(1, 37))
    assert runner[0]["event"] == "RUNNER_STARTED"
    assert runner[-2]["event"] == "TERMINAL_EOS"
    assert runner[-2]["generated_tokens"] == 353
    assert runner[-2]["output_sha256"] == RAW_SHA256
    assert runner[-1]["event"] == "RESPONSE_PERSISTED"
    assert runner[-1]["terminal_eos"] is True
    assert runner[-1]["response_sha256"] == host[-1]["response_sha256"]


def test_raw_and_receipt_are_complete_and_hash_bound() -> None:
    raw = EVIDENCE / "stage-p-raw.bin"
    receipt = _load(EVIDENCE / "stage-p-phase-receipt-v2.json")
    assert len(raw.read_bytes()) == receipt["raw_bytes"] == 1160
    assert hashlib.sha256(raw.read_bytes()).hexdigest() == receipt["raw_sha256"] == RAW_SHA256
    assert receipt["provider_call_count"] == 1
    assert receipt["transport"] == receipt["raw_persistence"] == "SUCCESS"
    assert receipt["schema_validation"] == receipt["source_membership"] == "SUCCESS"
    assert receipt["reason_code"] == "STAGE_P_VALID"
    assert receipt["final_decision"] == "PASS_TO_NEXT_STAGE"
    assert receipt["eligibility"] == "QUARANTINED_EVALUATION_ONLY"
