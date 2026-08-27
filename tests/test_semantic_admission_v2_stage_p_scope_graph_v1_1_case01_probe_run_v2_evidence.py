from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-scope-graph-v1-1-case01-probe-run-v2-evidence"
RUN_ID = "d76ffd3e97cd48fa3860beedf82175146021a03edd3406d182e018a7a9ca76c1"
LIFECYCLE = EVIDENCE / "durable-lifecycle" / RUN_ID


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text("utf-8"))


def test_complete_preserved_tree_has_exact_aggregate_identity() -> None:
    files = sorted(path for path in EVIDENCE.rglob("*") if path.is_file())
    entries = "".join(
        f"{path.relative_to(EVIDENCE).as_posix()}\0{hashlib.sha256(path.read_bytes()).hexdigest()}\n"
        for path in files
    ).encode()
    assert len(files) == 39
    assert sum(path.stat().st_size for path in files) == 28268
    assert hashlib.sha256(entries).hexdigest() == "862b18e41cf7ec306738914641da3b39cc5b736be70a35543829aceadeddcca0"


def test_binding_and_lifecycle_are_complete_and_ordered() -> None:
    binding = _load(EVIDENCE / "identity-binding.json")
    assert binding["case_id"] == "HMCV1-SASC-01"
    assert binding["runner_binding_identity"] == "57891ab6d928cde37a7d388e2f97a3da87d130e8debc1ab29b90bec850dc288a"
    assert binding["request_candidate_identity"] == "2fee4188906353caed6effa393e877b523e4cede4a567702e06a7f9d9094ba5e"
    assert binding["retry_count"] == binding["repair_count"] == binding["selection_count"] == 0
    assert binding["stage_c_constructed"] is binding["stage_c_called"] is False

    host = [_load(path) for path in sorted(LIFECYCLE.glob("host-*.json"))]
    runner = [_load(path) for path in sorted(LIFECYCLE.glob("runner-*.json"))]
    assert [event["sequence"] for event in host] == [1, 2, 3]
    assert [event["sequence"] for event in runner] == list(range(1, 34))
    assert runner[0]["event"] == "RUNNER_STARTED"
    assert runner[-1]["event"] == "RUNNER_EXCEPTION"
    assert runner[-1]["exception_type"] == "ValueError"
    assert runner[-1]["exception_message"] == "EMPTY_ALLOWED_TOKEN_SET"
    assert host[-1]["event"] == "HOST_PROCESS_EXITED"
    assert host[-1]["returncode"] == 1 and host[-1]["response_exists"] is False
    assert "EMPTY_ALLOWED_TOKEN_SET" in str(host[-1]["stderr_tail"])


def test_failure_receipt_preserves_single_call_and_fail_closed_boundary() -> None:
    receipt = _load(EVIDENCE / "stage-p-phase-receipt-v2.json")
    assert receipt["provider_call_count"] == 1
    assert receipt["transport"] == "FAIL"
    assert receipt["raw_persistence"] == receipt["schema_validation"] == receipt["source_membership"] == "NOT_RUN"
    assert receipt["raw_bytes"] == 0 and receipt["raw_path"] is receipt["raw_sha256"] is None
    assert receipt["final_decision"] == "ABSTAIN_FAIL_CLOSED"
    assert receipt["eligibility"] == "QUARANTINED_EVALUATION_ONLY"
