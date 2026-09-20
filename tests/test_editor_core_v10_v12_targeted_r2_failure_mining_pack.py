import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "scripts/audit_editor_core_v10_v12_targeted_r2_failure_mining_pack.py"
ART = ROOT / "docs/artifacts"
PREFIX = "editor-core-v10-v12-targeted-continuation-r2"


def module():
    spec = importlib.util.spec_from_file_location("r2_audit", AUDIT)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(value)
    return value


def test_r2_pack_closes_without_training_or_contamination():
    result = module().audit()
    assert result["verdict"] == "PASS" and result["blockers"] == 0
    assert (result["new_rows"], result["replay_rows"], result["holdout_rows"]) == (36, 36, 18)
    assert result["exact_contamination_matches"] == 0
    assert result["prior_holdout_targets_reused"] is False
    assert result["r4_evidence_used"] is False
    assert result["maximum_training_sequence_tokens"] <= 3072
    assert result["training_performed"] is False


def test_holdout_has_no_assistant_messages():
    rows = [json.loads(line) for line in (ART / f"{PREFIX}-holdout-requests.jsonl").read_bytes().splitlines()]
    assert len(rows) == 18
    assert all([message["role"] for message in row["messages"]] == ["system", "user"] for row in rows)


def test_failure_classes_are_exactly_the_observed_three():
    manifest = json.loads((ART / f"{PREFIX}-manifest.json").read_bytes())
    assert set(manifest["failure_classes"]) == {"UNSUPPORTED_MATERIAL_CLAIMS", "EPISTEMIC_CALIBRATION", "TRANSITION_NO_NEW_FACTS"}
