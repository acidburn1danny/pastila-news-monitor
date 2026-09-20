import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts/audit_editor_core_v10_v12_targeted_r3_failure_mining_pack.py"
ART = ROOT / "docs/artifacts"
PREFIX = "editor-core-v10-v12-targeted-continuation-r3"


def module():
    spec = importlib.util.spec_from_file_location("r3_audit", AUDIT); value = importlib.util.module_from_spec(spec)
    assert spec.loader is not None; spec.loader.exec_module(value); return value


def test_r3_pack_closes_without_training_or_contamination():
    result = module().audit()
    assert result["verdict"] == "PASS" and result["blockers"] == 0
    assert (result["new_rows"], result["replay_rows"], result["holdout_rows"]) == (24, 24, 12)
    assert result["exact_contamination_matches"] == 0
    assert result["replay_provenance"] == {"v10_v1_2": 8, "targeted_r1": 8, "targeted_r2": 8}
    assert result["r2_holdout_training_use"] is result["r2_holdout_targets_reused"] is False
    assert result["maximum_training_sequence_tokens"] <= 3072 and result["training_performed"] is False


def test_r3_scope_and_holdout_separation():
    manifest = json.loads((ART / f"{PREFIX}-manifest.json").read_bytes())
    assert manifest["failure_classes"] == ["EPISTEMIC_CALIBRATION"]
    assert len(manifest["source_diagnostic_case_ids"]) == 6
    rows = [json.loads(line) for line in (ART / f"{PREFIX}-holdout-requests.jsonl").read_bytes().splitlines()]
    assert len(rows) == 12 and all([m["role"] for m in row["messages"]] == ["system", "user"] for row in rows)


def test_r3_targets_preserve_three_epistemic_components():
    rows = [json.loads(line) for line in (ART / f"{PREFIX}-new-train.jsonl").read_bytes().splitlines()]
    for row in rows:
        target = json.loads(row["messages"][2]["content"])
        assert len(target["claim_bindings"]) == 3
        assert [item["claim_index"] for item in target["claim_bindings"]] == [1, 2, 3]
