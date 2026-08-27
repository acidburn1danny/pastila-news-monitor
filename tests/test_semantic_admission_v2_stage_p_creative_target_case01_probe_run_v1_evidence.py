from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-creative-target-case01-probe-run-v1-evidence"
RUN_ID = "ddf4aae49ccffb0e591707e5e35530be65eb8f520b66a1840f08f53a10da401b"
LIFECYCLE = EVIDENCE / "durable-lifecycle" / RUN_ID
RAW_SHA256 = "5cf2c8a774f97cf561e9ddeb541a7300adbfa33a6c4b9d45f4f48587696aa8e0"


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text("utf-8"))


def test_complete_preserved_tree_has_exact_aggregate_identity() -> None:
    files = sorted(path for path in EVIDENCE.rglob("*") if path.is_file())
    entries = "".join(
        f"{path.relative_to(EVIDENCE).as_posix()}\0{hashlib.sha256(path.read_bytes()).hexdigest()}\n"
        for path in files
    ).encode()
    assert len(files) == 58
    assert sum(path.stat().st_size for path in files) == 62570
    assert hashlib.sha256(entries).hexdigest() == "1d8324b3908685909f8e1f744f43080eacde15f428c37e677c6e7a1296981721"


def test_binding_preserves_single_call_and_authority_boundaries() -> None:
    binding = _load(EVIDENCE / "identity-binding.json")
    assert binding["case_id"] == "HMCV1-SASC-01"
    assert binding["evaluator_binding_identity"] == "a6bba6cf229e5cf75352c2a0333b186841528e767e9a6638f7b7bef1e11e6ace"
    assert binding["request_candidate_identity"] == "79b27bb6d7e35dfa9153cafb724e82d5689973b49605a9ea09a4b6462f01d9cc"
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
    assert host[-1]["terminal_eos"] is True
    assert [event["sequence"] for event in runner] == list(range(1, 51))
    assert runner[0]["event"] == "RUNNER_STARTED"
    assert runner[-2]["event"] == "TERMINAL_EOS"
    assert runner[-2]["generated_tokens"] == 581
    assert runner[-2]["output_sha256"] == RAW_SHA256
    assert runner[-1]["event"] == "RESPONSE_PERSISTED"
    assert runner[-1]["terminal_eos"] is True
    assert runner[-1]["response_sha256"] == host[-1]["response_sha256"]


def test_raw_and_receipt_are_complete_and_hash_bound() -> None:
    raw = EVIDENCE / "stage-p-raw.bin"
    receipt = _load(EVIDENCE / "stage-p-phase-receipt-v2.json")
    assert len(raw.read_bytes()) == receipt["raw_bytes"] == 1706
    assert hashlib.sha256(raw.read_bytes()).hexdigest() == receipt["raw_sha256"] == RAW_SHA256
    assert receipt["provider_call_count"] == 1
    assert receipt["transport"] == receipt["raw_persistence"] == "SUCCESS"
    assert receipt["schema_validation"] == receipt["source_membership"] == "SUCCESS"
    assert receipt["reason_code"] == "STAGE_P_VALID"
    assert receipt["final_decision"] == "PASS_TO_NEXT_STAGE"
    assert receipt["eligibility"] == "QUARANTINED_EVALUATION_ONLY"
