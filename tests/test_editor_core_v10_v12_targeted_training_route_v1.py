import ast
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "scripts/train_editor_core_v10_v12_targeted_continuation_v1.py"
ROUTE = ROOT / "scripts/run_editor_core_v10_v12_targeted_continuation_v1.sh"
SMOKE = ROOT / "scripts/smoke_editor_core_v10_v12_targeted_training_route_v1.py"
CONFIG = ROOT / "docs/artifacts/editor-core-v10-v12-targeted-continuation-v1-training-config.json"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(value)
    return value


def test_fixture_smoke_closes_without_ml_execution():
    result = load(SMOKE, "route_smoke").run()
    assert result["status"] == "PASS_FIXTURE_ONLY_ZERO_TRAINING"
    assert result["model_loaded"] is False
    assert result["optimizer_created"] is False
    assert result["optimizer_steps"] == 0
    assert result["training_performed"] is False


def test_worker_plan_is_exactly_128_rows_16_steps_and_two_checkpoints():
    worker = load(WORKER, "targeted_worker")
    config = json.loads(CONFIG.read_bytes())
    result = worker.validate_config(config, worker.EXPECTED_CORPUS, 128)
    assert result["rows"] == 128
    assert result["optimizer_steps"] == 16
    assert result["checkpoint_steps"] == [8, 16]


@pytest.mark.parametrize("mutation", ["rows", "optimizer", "holdout"])
def test_worker_rejects_material_contract_drift(mutation):
    worker = load(WORKER, "targeted_worker_negative")
    config = json.loads(CONFIG.read_bytes())
    if mutation == "rows":
        with pytest.raises(ValueError, match="corpus closure"):
            worker.validate_config(config, worker.EXPECTED_CORPUS, 127)
        return
    if mutation == "optimizer":
        config["optimizer"] = "PAGED_ADAMW_8BIT"
    else:
        config["holdout_training_use"] = True
    with pytest.raises(ValueError, match="identity mismatch|configuration mismatch"):
        worker.validate_config(config, worker.EXPECTED_CORPUS, 128)


def test_ml_imports_and_optimizer_are_execution_only():
    tree = ast.parse(WORKER.read_text("utf-8"))
    top_imports = {alias.name for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
    assert not top_imports.intersection({"torch", "transformers", "peft", "bitsandbytes"})
    source = WORKER.read_text("utf-8")
    assert source.count("optimizer.step()") == 1
    assert "def fixture_smoke(config:" in source
    assert "PAGED_ADAMW_8BIT_NEW_STATE" in source


def test_bound_route_is_isolated_and_byte_binds_worker():
    source = ROUTE.read_text("utf-8")
    worker_sha = hashlib.sha256(WORKER.read_bytes()).hexdigest()
    assert f"EXPECTED_WORKER={worker_sha}" in source
    assert "unshare --kill-child=KILL --mount --net --pid --ipc --uts --fork" in source
    assert "EDITOR_CORE_TRAINING_OWNER_AUTHORIZED" in source
    assert "TRAINING_EXECUTION_AUTHORIZED=1" in source
    assert "HF_HUB_OFFLINE=1" in source and "TRANSFORMERS_OFFLINE=1" in source
    assert "--execute-authorized" in source


def test_bound_route_refuses_unarmed_invocation_without_side_effects():
    result = subprocess.run(["bash", str(ROUTE)], capture_output=True)
    assert result.returncode == 2
