from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-role-coherence-case01-probe-v1-evidence"
MANIFEST = EVIDENCE / "manifest.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_bound_artifacts_and_canonical_identity_reproduce_exactly() -> None:
    manifest = json.loads(MANIFEST.read_text("utf-8"))
    assert len(manifest["bindings"]) == 6
    assert all(_sha(ROOT / item["path"]) == item["sha256"] for item in manifest["bindings"])
    values = [manifest["source_binding_identity"]]
    values.extend(item["sha256"].lower() for item in manifest["bindings"])
    values.append(manifest["durable_lifecycle"]["tree_identity"])
    identity = hashlib.sha256("\n".join(values).encode("utf-8")).hexdigest()
    assert identity == manifest["canonical_identity"] == "7357722352c676770d6b1c36d64a13b93e6e078e8046cb8ff05d57fc67d3b188"


def test_lifecycle_tree_reproduces_with_exact_tab_separator() -> None:
    manifest = json.loads(MANIFEST.read_text("utf-8"))
    durable = EVIDENCE / "durable-lifecycle"
    files = sorted(path for path in durable.rglob("*.json") if path.is_file())
    lines = [f"{path.relative_to(durable).as_posix()}\t{_sha(path)}" for path in files]
    tree = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    assert len(files) == manifest["durable_lifecycle"]["file_count"] == 25
    assert tree == manifest["durable_lifecycle"]["tree_identity"] == "94286847c70948d36074fcafb1e539cb4cf65bcfb54466af0f8c21b3a99a982a"


def test_failed_probe_receipts_are_one_shot_and_fail_closed() -> None:
    manifest = json.loads(MANIFEST.read_text("utf-8"))
    binding = json.loads((EVIDENCE / "identity-binding.json").read_text("utf-8"))
    phase = json.loads((EVIDENCE / "stage-p-phase-receipt-v2.json").read_text("utf-8"))
    analysis = json.loads((EVIDENCE / "validated-analysis.json").read_text("utf-8"))
    assert binding["maximum_provider_calls"] == manifest["result"]["provider_call_count"] == 1
    assert binding["retry_count"] == binding["repair_count"] == binding["selection_count"] == 0
    assert phase["final_decision"] == "ABSTAIN_FAIL_CLOSED"
    assert analysis["durable_evidence"]["runner_exception"] == "EMPTY_ALLOWED_TOKEN_SET"
    assert manifest["result"]["raw_response"] == "NOT_PRODUCED"


def test_failure_remains_quarantined_and_grants_no_authority() -> None:
    manifest = json.loads(MANIFEST.read_text("utf-8"))
    analysis = json.loads((EVIDENCE / "validated-analysis.json").read_text("utf-8"))
    assert manifest["result"]["case01_acceptance"] == "NOT_DEMONSTRATED"
    assert analysis["failure_analysis"]["failure_class"] == "ROLE_COHERENCE_LATE_DEAD_END"
    assert manifest["result"]["stage_c_constructed"] is manifest["result"]["stage_c_called"] is False
    assert all(value is False for value in manifest["authority"].values())
