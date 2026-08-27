from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-case01-execution-evidence-reconciliation-v1.json"
LEGACY = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-case01-execution-result-v1.json"
INITIAL = ROOT / ".semantic-admission-v2-stage-p-construction-obligation-case01-probe-v1-execution"
RETRY = ROOT / ".semantic-admission-v2-stage-p-construction-obligation-case01-probe-v1-retry-01"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tree(root: Path) -> tuple[int, str, list[dict[str, object]]]:
    leaf = next((root / "durable-lifecycle").iterdir())
    files = sorted(leaf.glob("*.json"), key=lambda path: path.name)
    lines = [f"{path.name}\t{_sha(path)}" for path in files]
    events = [json.loads(path.read_text("utf-8")) for path in files]
    return len(files), hashlib.sha256("\n".join(lines).encode()).hexdigest(), events


def test_reconciliation_identity_and_immutable_sources_are_exact():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    parts = [value["artifact_id"], value["legacy_result_identity"], value["legacy_result_artifact_sha256"],
             value["attempts"][0]["reproduced_tree_identity"], value["attempts"][1]["reproduced_tree_identity"],
             value["attempts"][0]["phase_receipt_sha256"], value["attempts"][1]["phase_receipt_sha256"],
             value["attempts"][1]["raw_sha256"], "ONE_PRE_RUN_LAUNCH_FAILURE", "ONE_OBSERVED_GENERATION",
             "HISTORICAL_RETRY_AUTHORITY_NOT_REPOSITORY_BOUND", "NO_RERUN", "NO_REPAIR", "NO_STAGE_C"]
    assert hashlib.sha256("\n".join(parts).encode()).hexdigest() == value["canonical_identity"]
    assert _sha(LEGACY) == value["legacy_result_artifact_sha256"]
    assert _sha(INITIAL / "stage-p-phase-receipt-v2.json") == value["attempts"][0]["phase_receipt_sha256"]
    assert _sha(RETRY / "stage-p-phase-receipt-v2.json") == value["attempts"][1]["phase_receipt_sha256"]
    assert _sha(RETRY / "stage-p-raw.bin") == value["attempts"][1]["raw_sha256"]


def test_complete_lifecycle_trees_reproduce_and_legacy_identity_does_not():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    initial_count, initial_tree, _ = _tree(INITIAL)
    retry_count, retry_tree, _ = _tree(RETRY)
    assert (initial_count, initial_tree) == (3, value["attempts"][0]["reproduced_tree_identity"])
    assert (retry_count, retry_tree) == (85, value["attempts"][1]["reproduced_tree_identity"])
    assert retry_tree != value["legacy_recorded_retry_tree_identity"]


def test_only_second_invocation_contains_generation_and_terminal_output():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    _, _, initial = _tree(INITIAL)
    _, _, retry = _tree(RETRY)
    assert not any(event.get("actor") == "runner" for event in initial)
    assert not any(event.get("event") == "GENERATION_STARTED" for event in initial)
    assert [event["sequence"] for event in retry if event.get("actor") == "runner"] == list(range(1, 82))
    assert [event["sequence"] for event in retry if event.get("actor") == "host"] == list(range(1, 5))
    assert sum(event.get("event") == "GENERATION_STARTED" for event in retry) == 1
    assert {"TERMINAL_EOS", "RESPONSE_PERSISTED", "HOST_RESPONSE_VALIDATED"}.issubset(
        {event.get("event") for event in retry})
    raw = json.loads((RETRY / "stage-p-raw.bin").read_text("utf-8"))
    assert list(raw) == ["stage_id", "construction_role_audit", "entries", "creative_target_audits",
                         "coverage_receipt", "coverage_decision"]
    assert value["call_reconciliation"]["observed_provider_generations"] == 1


def test_reconciliation_fails_closed_on_authority_and_grants_nothing():
    value = json.loads(ARTIFACT.read_text("utf-8"))
    assert value["call_reconciliation"]["historical_retry_authority"] == (
        "NOT_INDEPENDENTLY_BOUND_BY_REPOSITORY_AUTHORITY_RECEIPT")
    assert not any(value["authority"].values())
    assert value["attempts"][1]["source_membership"] == "FAIL"
    assert value["attempts"][1]["final_decision"] == "ABSTAIN_FAIL_CLOSED"
