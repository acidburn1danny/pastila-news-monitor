import ast
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "scripts/train_editor_core_v10_v12_targeted_continuation_r3.py"
ROUTE = ROOT / "scripts/run_editor_core_v10_v12_targeted_continuation_r3.sh"
SMOKE = ROOT / "scripts/smoke_editor_core_v10_v12_targeted_training_route_r3.py"
CONFIG = ROOT / "docs/artifacts/editor-core-v10-v12-targeted-continuation-r3-training-config.json"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(value)
    return value


def test_fixture_smoke_closes_without_ml_execution():
    result = load(SMOKE, "r3_route_smoke").run()
    assert result["status"] == "PASS_FIXTURE_ONLY_ZERO_TRAINING"
    assert result["model_loaded"] is result["optimizer_created"] is result["training_performed"] is False
    assert result["optimizer_steps"] == 0


def test_worker_plan_is_exactly_48_rows_6_steps_and_final_checkpoint():
    worker = load(WORKER, "targeted_r3_worker")
    result = worker.validate_config(json.loads(CONFIG.read_bytes()), worker.EXPECTED_CORPUS, 48)
    assert result["rows"] == 48 and result["optimizer_steps"] == 6
    assert result["checkpoint_steps"] == [6]


@pytest.mark.parametrize("mutation", ["rows", "optimizer", "holdout", "parent", "seed"])
def test_worker_rejects_material_contract_drift(mutation):
    worker = load(WORKER, "targeted_r3_worker_negative")
    config = json.loads(CONFIG.read_bytes())
    if mutation == "rows":
        with pytest.raises(ValueError, match="corpus closure"):
            worker.validate_config(config, worker.EXPECTED_CORPUS, 47)
        return
    key, value = {"optimizer": ("optimizer", "PAGED_ADAMW_8BIT"), "holdout": ("r2_holdout_training_use", True), "parent": ("parent_checkpoint_identity", "0" * 64), "seed": ("seed", 271828)}[mutation]
    config[key] = value
    with pytest.raises(ValueError, match="identity mismatch|configuration mismatch"):
        worker.validate_config(config, worker.EXPECTED_CORPUS, 48)


def test_ml_imports_and_optimizer_are_execution_only():
    tree = ast.parse(WORKER.read_text("utf-8"))
    top_imports = {alias.name for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
    assert not top_imports.intersection({"torch", "transformers", "peft", "bitsandbytes"})
    source = WORKER.read_text("utf-8")
    assert source.count("optimizer.step()") == 1
    assert 'deregister_op_overrides(disable_op_symbols="bmm")' in source
    assert "EXPECTED_ROWS = 48" in source and "EXPECTED_STEPS = 6" in source


def test_bound_route_is_isolated_and_binds_r3_sources():
    source = ROUTE.read_text("utf-8")
    assert f"EXPECTED_WORKER={hashlib.sha256(WORKER.read_bytes()).hexdigest()}" in source
    zero_step = ROOT / "scripts/launch_editor_core_v10_v12_targeted_r3_zero_step.py"
    assert f"EXPECTED_ZERO_STEP={hashlib.sha256(zero_step.read_bytes()).hexdigest()}" in source
    assert "unshare --kill-child=KILL --mount --net --pid --ipc --uts --fork" in source
    assert "EDITOR_CORE_R3_TRAINING_OWNER_AUTHORIZED" in source
    assert "EXPECTED_SOURCE_COMMIT=283452937456a7136c6061d00a46ed93ca010317" in source
    assert "EXPECTED_SOURCE_TREE=fb241e53993b43ec2885a4b1904f94909bb9cbc7" in source
    assert 'merge-base --is-ancestor "$EXPECTED_SOURCE_COMMIT" HEAD' in source
    assert "EXPECTED_CHECKPOINT=96e10b85fe30c4be43c2cc1a0b906f04ea4c476cc8d422b4ad26e9758b85b2be" in source
    assert 'checkpoint_identity "$PARENT_CHECKPOINT/checkpoint.json"' in source
    assert "HF_HUB_OFFLINE=1" in source and "TRANSFORMERS_OFFLINE=1" in source
    assert "--execute-authorized" in source


def test_r2_worker_and_r1_parent_cannot_substitute():
    source = ROUTE.read_text("utf-8")
    r2_worker = ROOT / "scripts/train_editor_core_v10_v12_targeted_continuation_r2.py"
    assert hashlib.sha256(r2_worker.read_bytes()).hexdigest() not in source
    assert "8c277a123fef81908f03bdaf31925b93c1a95a3c0969ef23088331427e64013f" not in source


def test_bound_route_refuses_unarmed_invocation_without_side_effects():
    result = subprocess.run(["bash", str(ROUTE)], capture_output=True)
    assert result.returncode == 2
