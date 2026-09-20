import ast
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "scripts/train_editor_core_v10_v12_targeted_continuation_r2.py"
ROUTE = ROOT / "scripts/run_editor_core_v10_v12_targeted_continuation_r2.sh"
SMOKE = ROOT / "scripts/smoke_editor_core_v10_v12_targeted_training_route_r2.py"
CONFIG = ROOT / "docs/artifacts/editor-core-v10-v12-targeted-continuation-r2-training-config.json"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(value)
    return value


def test_fixture_smoke_closes_without_ml_execution():
    result = load(SMOKE, "r2_route_smoke").run()
    assert result["status"] == "PASS_FIXTURE_ONLY_ZERO_TRAINING"
    assert result["model_loaded"] is result["optimizer_created"] is result["training_performed"] is False
    assert result["optimizer_steps"] == 0


def test_worker_plan_is_exactly_72_rows_9_steps_and_final_checkpoint():
    worker = load(WORKER, "targeted_r2_worker")
    result = worker.validate_config(json.loads(CONFIG.read_bytes()), worker.EXPECTED_CORPUS, 72)
    assert result["rows"] == 72 and result["optimizer_steps"] == 9
    assert result["checkpoint_steps"] == [9]


@pytest.mark.parametrize("mutation", ["rows", "optimizer", "holdout", "parent", "seed"])
def test_worker_rejects_material_contract_drift(mutation):
    worker = load(WORKER, "targeted_r2_worker_negative")
    config = json.loads(CONFIG.read_bytes())
    if mutation == "rows":
        with pytest.raises(ValueError, match="corpus closure"):
            worker.validate_config(config, worker.EXPECTED_CORPUS, 71)
        return
    key, value = {"optimizer": ("optimizer", "PAGED_ADAMW_8BIT"), "holdout": ("holdout_training_use", True), "parent": ("parent_checkpoint_identity", "0" * 64), "seed": ("seed", 314159)}[mutation]
    config[key] = value
    with pytest.raises(ValueError, match="identity mismatch|configuration mismatch"):
        worker.validate_config(config, worker.EXPECTED_CORPUS, 72)


def test_ml_imports_and_optimizer_are_execution_only():
    tree = ast.parse(WORKER.read_text("utf-8"))
    top_imports = {alias.name for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
    assert not top_imports.intersection({"torch", "transformers", "peft", "bitsandbytes"})
    source = WORKER.read_text("utf-8")
    assert source.count("optimizer.step()") == 1
    assert 'deregister_op_overrides(disable_op_symbols="bmm")' in source
    assert "EXPECTED_ROWS = 72" in source and "EXPECTED_STEPS = 9" in source


def test_bound_route_is_isolated_and_binds_r2_sources():
    source = ROUTE.read_text("utf-8")
    assert f"EXPECTED_WORKER={hashlib.sha256(WORKER.read_bytes()).hexdigest()}" in source
    zero_step = ROOT / "scripts/launch_editor_core_v10_v12_targeted_r2_zero_step.py"
    assert f"EXPECTED_ZERO_STEP={hashlib.sha256(zero_step.read_bytes()).hexdigest()}" in source
    assert "unshare --kill-child=KILL --mount --net --pid --ipc --uts --fork" in source
    assert "EDITOR_CORE_R2_TRAINING_OWNER_AUTHORIZED" in source
    assert "EXPECTED_CHECKPOINT=00ee968941f8cba8ea47534d441c272c7a3120f9076953aa552f67e302a0ceef" in source
    assert 'checkpoint_identity "$PARENT_CHECKPOINT/checkpoint.json"' in source
    assert "HF_HUB_OFFLINE=1" in source and "TRANSFORMERS_OFFLINE=1" in source
    assert "--execute-authorized" in source


def test_r1_worker_and_parent_cannot_substitute():
    source = ROUTE.read_text("utf-8")
    r1_worker = ROOT / "scripts/train_editor_core_v10_v12_targeted_continuation_v1.py"
    assert hashlib.sha256(r1_worker.read_bytes()).hexdigest() not in source
    assert "8c277a123fef81908f03bdaf31925b93c1a95a3c0969ef23088331427e64013f" not in source


def test_bound_route_refuses_unarmed_invocation_without_side_effects():
    result = subprocess.run(["bash", str(ROUTE)], capture_output=True)
    assert result.returncode == 2
