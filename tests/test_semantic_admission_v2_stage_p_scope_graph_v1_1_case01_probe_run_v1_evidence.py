from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-scope-graph-v1-1-case01-probe-run-v1-evidence"
RUN_ID = "d76ffd3e97cd48fa3860beedf82175146021a03edd3406d182e018a7a9ca76c1"
LIFECYCLE = EVIDENCE / "durable-lifecycle" / RUN_ID

EXPECTED_HASHES = {
    f"durable-lifecycle/{RUN_ID}/host-00001-host-launch.json":
        "8f8264e093657e1b1f77eceb04f7645b2fd112c18bf34a1f78856e196ecaf7be",
    f"durable-lifecycle/{RUN_ID}/host-00002-host-process-started.json":
        "886f23f48912aea263a43196098faac9a63c86462df1a820de0e1d1b0aa9e2f9",
    f"durable-lifecycle/{RUN_ID}/host-00003-host-process-exited.json":
        "90e59fa8050dbce7035d0c47504e352e1b61ace1d77c87664efd11808f7e60c7",
    "identity-binding.json": "0c02b768ba81606ae66b9d0b086418fce62df9e7096e4ca5f690307b9e51a7f7",
    "stage-p-phase-receipt-v2.json": "774196cddc6028bc9c56fceeb1cd9c98d50e108193dae6f80a2c63539228cee2",
    "stage-p-request.json": "b6e0fd27797998d9b447e9cb938b3ceaa173ee008dd8965a43dd5bf39f5a710d",
}


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text("utf-8"))


def test_all_preserved_files_have_exact_frozen_hashes() -> None:
    actual = {
        path.relative_to(EVIDENCE).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
        for path in EVIDENCE.rglob("*")
        if path.is_file()
    }
    assert actual == EXPECTED_HASHES


def test_request_and_binding_match_the_approved_v1_1_boundary() -> None:
    launch = _load(LIFECYCLE / "host-00001-host-launch.json")
    binding = _load(EVIDENCE / "identity-binding.json")
    assert launch["request_id_sha256"] == RUN_ID
    # The launch binds the canonical in-memory request payload.  The separately
    # frozen file hash above also covers its storage newline.
    assert launch["request_sha256"] == "1a1db7c28fac30c0f6378dfa94a5ff1d755387c7f7c33d4e73f84fc295667a1a"
    assert launch["runner_sha256"] == "45161010431b5b8404c456d8044a79c616bc8a2b05019da2ad584ab563dfbfe0"
    assert binding["runner_binding_identity"] == "57891ab6d928cde37a7d388e2f97a3da87d130e8debc1ab29b90bec850dc288a"
    assert binding["request_candidate_identity"] == "2fee4188906353caed6effa393e877b523e4cede4a567702e06a7f9d9094ba5e"
    assert binding["retry_count"] == binding["repair_count"] == binding["selection_count"] == 0
    assert binding["stage_c_constructed"] is binding["stage_c_called"] is False


def test_host_failure_is_ordered_and_fail_closed_without_runner_evidence() -> None:
    events = [_load(path) for path in sorted(LIFECYCLE.glob("*.json"))]
    assert [event["sequence"] for event in events] == [1, 2, 3]
    assert [event["event"] for event in events] == [
        "HOST_LAUNCH", "HOST_PROCESS_STARTED", "HOST_PROCESS_EXITED"
    ]
    assert events[-1]["response_exists"] is False
    decoded_tail = str(events[-1]["stdout_tail"]).replace("\x00", "")
    assert "Wsl/Service/E_ACCESSDENIED" in decoded_tail
    assert not list(LIFECYCLE.glob("runner-*.json"))

    receipt = _load(EVIDENCE / "stage-p-phase-receipt-v2.json")
    assert receipt["provider_call_count"] == 1
    assert receipt["transport"] == "FAIL"
    assert receipt["raw_persistence"] == receipt["schema_validation"] == receipt["source_membership"] == "NOT_RUN"
    assert receipt["raw_bytes"] == 0 and receipt["raw_path"] is receipt["raw_sha256"] is None
    assert receipt["final_decision"] == "ABSTAIN_FAIL_CLOSED"
    assert receipt["eligibility"] == "QUARANTINED_EVALUATION_ONLY"
