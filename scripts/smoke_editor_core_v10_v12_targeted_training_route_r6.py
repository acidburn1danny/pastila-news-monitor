"""Fixture-only smoke for the R6 targeted training worker and bound route."""
from __future__ import annotations
import ast
import hashlib
import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKER = ROOT / "scripts/train_editor_core_v10_v12_targeted_continuation_r6.py"
ROUTE = ROOT / "scripts/run_editor_core_v10_v12_targeted_continuation_r6.sh"
ZERO_STEP = ROOT / "scripts/launch_editor_core_v10_v12_targeted_r6_zero_step.py"
FIXTURE = ROOT / "tests/fixtures/editor_core_targeted_training_route_r6/training-config.json"


def run() -> dict[str, object]:
    spec = importlib.util.spec_from_file_location("targeted_r6_worker", WORKER)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    result = module.fixture_smoke(json.loads(FIXTURE.read_bytes()))
    worker_source, route_source = WORKER.read_text("utf-8"), ROUTE.read_text("utf-8")
    tree = ast.parse(worker_source)
    top_imports = {alias.name for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
    if top_imports & {"torch", "transformers", "peft", "bitsandbytes"}:
        raise ValueError("ML imports escaped execution-only function")
    required = ["unshare --kill-child=KILL --mount --net --pid --ipc --uts --fork", "TRAINING_EXECUTION_AUTHORIZED=1", "mount -o remount,bind,ro", "EXPECTED_SOURCE_COMMIT=6494e127b84c67ca7ed2d14ec2ba95cd2195b7e1", "EXPECTED_SOURCE_TREE=0f9cdd4d2e8362f036c4d640ea591e637aad39d4", 'GIT=(git -c "safe.directory=$REPOSITORY" -C "$REPOSITORY")', '"${GIT[@]}" merge-base --is-ancestor', "EXPECTED_ZERO_STEP=", "EXPECTED_WORKER=", "EXPECTED_CORPUS=", "--execute-authorized"]
    if any(value not in route_source for value in required):
        raise ValueError("bound route source closure mismatch")
    if "git config --global" in route_source:
        raise ValueError("route must not persist Git trust policy")
    core = {"schema": "pastila-editor-core-targeted-r6-training-route-fixture-smoke", "schema_version": 1, "status": "PASS_FIXTURE_ONLY_ZERO_TRAINING", "worker_smoke_identity": result["smoke_identity"], "worker_sha256": hashlib.sha256(WORKER.read_bytes()).hexdigest(), "route_sha256": hashlib.sha256(ROUTE.read_bytes()).hexdigest(), "zero_step_sha256": hashlib.sha256(ZERO_STEP.read_bytes()).hexdigest(), "model_loaded": False, "optimizer_created": False, "optimizer_steps": 0, "training_performed": False}
    return {**core, "smoke_identity": hashlib.sha256(json.dumps(core, sort_keys=True, separators=(",", ":")).encode()).hexdigest()}


if __name__ == "__main__":
    print(json.dumps(run(), sort_keys=True, separators=(",", ":")))
