import importlib.util
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/materialize_production_core_v9_dual_structural_remediation.py"
ART = ROOT / "docs/artifacts"


def module():
    spec = importlib.util.spec_from_file_location("v9_dual_remediation", SCRIPT)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(value)
    return value


def test_v9_targets_are_canonical_fence_free_and_holdout_isolated():
    value = module()
    train = value.rows("rem9-train", 480, development=False)
    development = value.rows("rem9-dev", 72, development=True)
    value.assert_isolated(train, development)
    for row in train + development:
        target = row["messages"][2]["content"]
        assert target[0] == "{" and target[-1] == "}"
        assert "```" not in target
        assert value.compact(json.loads(target)) == target


def test_v9_materialization_is_reproducible_and_zero_qualification(tmp_path):
    value = module()
    previous = sys.argv
    try:
        sys.argv = [str(SCRIPT), "--output-dir", str(tmp_path)]
        assert value.main() == 0
    finally:
        sys.argv = previous
    names = (
        "production-core-v9-dual-structural-remediation-train.jsonl",
        "production-core-v9-dual-structural-remediation-development.jsonl",
        "production-core-v9-dual-structural-remediation-corpus.json",
        "pastila-editor-core-v1.1-json-successor-v9-training-config-v3.json",
        "pastila-editor-core-v1.2-json-successor-v9-training-config-v3.json",
    )
    for name in names:
        assert (tmp_path / name).read_bytes() == (ART / name).read_bytes()
    manifest = json.loads((tmp_path / names[2]).read_bytes())
    assert manifest["qualification_or_holdout_examples_used"] == 0
    assert manifest["consumed_attempt_outputs_used"] == 0
    for name in names[3:]:
        config = json.loads((tmp_path / name).read_bytes())
        assert config["schema_version"] == 3
        assert config["optimizer"] == "PAGED_ADAMW_8BIT"
        assert config["candidate_execution_performed"] is False
        assert config["promotion_effect"] is False


def test_successor_trainer_has_fail_closed_v9_cardinality():
    source = (ROOT / "scripts/train_production_core_candidate_successor_v1.py").read_text()
    assert "expected_rows_by_schema = {1: 240, 2: 320, 3: 480}" in source
    assert 'raise SystemExit("training config schema version mismatch")' in source
