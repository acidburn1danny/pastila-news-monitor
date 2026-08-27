from __future__ import annotations

import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / ".semantic-admission-v2-stage-p-case01-v4-prompt-v2-probe-evidence"
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
    assert hashlib.sha256("\n".join(values).encode("utf-8")).hexdigest() == manifest["canonical_identity"]
    assert manifest["canonical_identity"] == "d6e0cb249b54ff188cf70995a7e7d848819ccc6eef3257a1bef1528005e17859"


def test_lifecycle_tree_reproduces_with_exact_tab_separator() -> None:
    manifest = json.loads(MANIFEST.read_text("utf-8"))
    durable = EVIDENCE / "durable-lifecycle"
    files = sorted(path for path in durable.rglob("*.json") if path.is_file())
    lines = [f"{path.relative_to(durable).as_posix()}\t{_sha(path)}" for path in files]
    tree = hashlib.sha256("\n".join(lines).encode("utf-8")).hexdigest()
    assert len(files) == manifest["durable_lifecycle"]["file_count"] == 46
    assert tree == manifest["durable_lifecycle"]["tree_identity"] == "c1fcd31d3b05b10a63435370c0c44f2ac9b09fb33022d77845ae1bdfae3c0fd2"


def test_raw_ledger_and_one_shot_receipts_are_consistent() -> None:
    raw = EVIDENCE / "stage-p-raw.bin"
    binding = json.loads((EVIDENCE / "identity-binding.json").read_text("utf-8"))
    phase = json.loads((EVIDENCE / "stage-p-phase-receipt-v2.json").read_text("utf-8"))
    analysis = json.loads((EVIDENCE / "validated-analysis.json").read_text("utf-8"))
    assert raw.stat().st_size == phase["raw_bytes"] == analysis["execution"]["raw_bytes"] == 1431
    assert _sha(raw) == phase["raw_sha256"] == analysis["execution"]["raw_sha256"]
    assert binding["maximum_provider_calls"] == phase["provider_call_count"] == analysis["execution"]["provider_call_count"] == 1
    assert binding["retry_count"] == binding["repair_count"] == binding["selection_count"] == 0


def test_historical_failure_and_authority_boundaries_remain_explicit() -> None:
    manifest = json.loads(MANIFEST.read_text("utf-8"))
    analysis = json.loads((EVIDENCE / "validated-analysis.json").read_text("utf-8"))
    assert analysis["evaluation"]["source_role_realization_result"] == "FAIL"
    assert analysis["evaluation"]["case01_acceptance_status"] == "NOT_DEMONSTRATED"
    assert analysis["boundaries"]["stage_c_constructed"] is analysis["boundaries"]["stage_c_called"] is False
    assert all(value is False for value in manifest["authority"].values())
