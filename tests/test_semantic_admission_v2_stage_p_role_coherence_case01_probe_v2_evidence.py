from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-role-coherence-case01-probe-v2-evidence"
MANIFEST = EVIDENCE / "manifest.json"


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_bound_artifacts_and_canonical_identity_reproduce_exactly() -> None:
    manifest = json.loads(MANIFEST.read_text("utf-8"))
    assert len(manifest["bindings"]) == 7
    assert all(_sha(ROOT / item["path"]) == item["sha256"] for item in manifest["bindings"])
    values = [manifest["source_binding_identity"]]
    values.extend(item["sha256"].lower() for item in manifest["bindings"])
    values.append(manifest["durable_lifecycle"]["tree_identity"])
    identity = hashlib.sha256("\n".join(values).encode("utf-8")).hexdigest()
    assert identity == manifest["canonical_identity"] == "bd1ee45ed047f8aababc88586f2ee5d5aa98243f9d9638d996f6abeae442da1f"


def test_lifecycle_tree_reproduces_with_exact_tab_separator() -> None:
    manifest = json.loads(MANIFEST.read_text("utf-8"))
    durable = EVIDENCE / "durable-lifecycle"
    files = sorted(path for path in durable.rglob("*.json") if path.is_file())
    lines = [f"{path.relative_to(durable).as_posix()}\t{_sha(path)}" for path in files]
    tree = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    assert len(files) == manifest["durable_lifecycle"]["file_count"] == 59
    assert tree == manifest["durable_lifecycle"]["tree_identity"] == "f47a20be47b77568452023ef26ac52a72f27db2796e6d20ad7869f06a9f487b5"


def test_raw_ledger_and_one_shot_receipts_are_consistent() -> None:
    raw = EVIDENCE / "stage-p-raw.bin"
    binding = json.loads((EVIDENCE / "identity-binding.json").read_text("utf-8"))
    phase = json.loads((EVIDENCE / "stage-p-phase-receipt-v2.json").read_text("utf-8"))
    analysis = json.loads((EVIDENCE / "validated-analysis.json").read_text("utf-8"))
    assert raw.stat().st_size == phase["raw_bytes"] == analysis["execution"]["raw_bytes"] == 2198
    assert _sha(raw) == phase["raw_sha256"] == analysis["execution"]["raw_sha256"]
    assert binding["maximum_provider_calls"] == phase["provider_call_count"] == analysis["execution"]["provider_calls"] == 1
    assert binding["retry_count"] == binding["repair_count"] == binding["selection_count"] == 0
    assert phase["transport"] == phase["raw_persistence"] == phase["schema_validation"] == phase["source_membership"] == "SUCCESS"


def test_semantic_failure_remains_quarantined_and_grants_no_authority() -> None:
    manifest = json.loads(MANIFEST.read_text("utf-8"))
    analysis = json.loads((EVIDENCE / "validated-analysis.json").read_text("utf-8"))
    assert analysis["semantic"]["case01_acceptance"] == "FAIL"
    assert analysis["semantic"]["failure_class"] == "CREATIVE_COMPONENT_LITERALIZATION_AND_DUPLICATE_SCOPE"
    assert analysis["semantic"]["real_world_commitments"] == 3
    assert analysis["semantic"]["contained_creative"] == 1
    assert analysis["boundaries"]["stage_c_called"] is False
    assert all(value is False for value in manifest["authority"].values())
