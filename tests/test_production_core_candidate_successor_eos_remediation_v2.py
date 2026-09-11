import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/materialize_production_core_candidate_successor_eos_remediation_v2.py"
ART = ROOT / "docs/artifacts"


def module():
    spec = importlib.util.spec_from_file_location("eos_remediation", SCRIPT)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(value)
    return value


def test_train_and_development_are_canonical_and_isolated():
    value = module()
    train = value.rows("rem5-train", 320, development=False)
    development = value.rows("rem5-dev", 48, development=True)
    value.assert_isolated(train, development)
    assert {row["split"] for row in train} == {"TRAIN"}
    assert {row["split"] for row in development} == {"DEVELOPMENT"}
    assert all(row["messages"][2]["content"].endswith("}") for row in train + development)


def test_materialization_is_reproducible_and_zero_execution(tmp_path):
    value = module()
    import sys
    prior = sys.argv
    try:
        sys.argv = [str(SCRIPT), "--output-dir", str(tmp_path)]
        assert value.main() == 0
    finally:
        sys.argv = prior
    names = (
        "production-core-v1.1-eos-remediation-corpus-v2.jsonl",
        "production-core-v1.1-eos-development-probes-v2.jsonl",
        "production-core-v1.1-eos-remediation-corpus-v2.json",
        "production-core-v1.1-json-successor-v2-training-config-v2.json",
    )
    for name in names:
        assert (tmp_path / name).read_bytes() == (ART / name).read_bytes()
    manifest = json.loads((tmp_path / names[2]).read_bytes())
    assert manifest["qualification_or_holdout_examples_used"] == 0
    assert manifest["consumed_attempt_outputs_used"] == 0
    assert manifest["candidate_execution_performed"] is False
    config = json.loads((tmp_path / names[3]).read_bytes())
    assert config["optimizer"] == "PAGED_ADAMW_8BIT"
    assert config["epochs"] == 1
    assert config["post_training_eligibility_gate"]["require_terminal_eos"] is True
