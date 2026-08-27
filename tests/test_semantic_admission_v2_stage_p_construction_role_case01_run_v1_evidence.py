from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-construction-role-case01-run-v1-evidence"
RUN_ID = "3cb718e4eff5a83053075290cdbfba7cfdea44464a5368cf71f4326ac5a26b51"
LIFECYCLE = EVIDENCE / "durable-lifecycle" / RUN_ID


def _load(path: Path) -> dict[str, object]:
    return json.loads(path.read_text("utf-8"))


def test_complete_preserved_tree_has_exact_aggregate_identity() -> None:
    files = sorted(path for path in EVIDENCE.rglob("*") if path.is_file())
    entries = "".join(
        f"{path.relative_to(EVIDENCE).as_posix()}\0{hashlib.sha256(path.read_bytes()).hexdigest()}\n"
        for path in files
    ).encode()
    assert len(files) == 78
    assert sum(path.stat().st_size for path in files) == 129562
    assert hashlib.sha256(entries).hexdigest() == "3ffab88551f45afc2d749f38f1dc98c79c7a91a22a408ed827231466a77200b1"


def test_lifecycle_preserves_classified_constraint_liveness() -> None:
    host = [_load(path) for path in sorted(LIFECYCLE.glob("host-*.json"))]
    runner = [_load(path) for path in sorted(LIFECYCLE.glob("runner-*.json"))]
    assert [event["sequence"] for event in host] == [1, 2, 3, 4]
    assert host[-1]["event"] == "HOST_CONSTRAINT_LIVENESS_FAILURE_CLASSIFIED"
    assert host[-1]["code"] == "CONSTRAINT_LIVENESS_FAILURE"
    assert host[-1]["decoded_utf8_bytes"] == 2911
    assert [event["sequence"] for event in runner] == list(range(1, 72))
    assert runner[-1]["event"] == "RUNNER_EXCEPTION"
    assert runner[-1]["exception_type"] == "StagePConstraintLivenessErrorV1"


def test_outer_receipt_is_single_call_fail_closed_and_nonterminal() -> None:
    receipt = _load(EVIDENCE / "stage-p-phase-receipt-v2.json")
    assert receipt["provider_call_count"] == 1
    assert receipt["transport"] == "FAIL"
    assert receipt["raw_persistence"] == receipt["schema_validation"] == receipt["source_membership"] == "NOT_RUN"
    assert receipt["raw_bytes"] == 0 and receipt["raw_path"] is receipt["raw_sha256"] is None
    assert receipt["final_decision"] == "ABSTAIN_FAIL_CLOSED"
    assert receipt["eligibility"] == "QUARANTINED_EVALUATION_ONLY"
