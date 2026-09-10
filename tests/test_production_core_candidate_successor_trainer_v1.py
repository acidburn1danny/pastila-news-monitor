import ast
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TRAINER = ROOT / "scripts/train_production_core_candidate_successor_v1.py"
LAUNCHER = ROOT / "scripts/run_production_core_candidate_successor_training_v1.sh"


def load_module():
    spec = importlib.util.spec_from_file_location("successor_trainer", TRAINER)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(value)
    return value


def test_trainer_is_offline_single_pass_boundary():
    tree = ast.parse(TRAINER.read_text("utf-8"))
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not imports.intersection({"requests", "httpx", "urllib", "socket"})
    source = TRAINER.read_text("utf-8")
    assert "PeftModel.from_pretrained" in source
    assert "is_trainable=True" in source
    assert source.count("optimizer.step()") == 1
    assert 'qualification_attempt_consumed": False' in source
    assert '"adjudication_performed": False' in source
    assert '"base_model_manifest_sha256": model_sha' in source
    assert '"save_reload": True' in source


def test_flat_manifest_is_content_and_name_bound(tmp_path):
    module = load_module()
    (tmp_path / "a").write_bytes(b"one")
    before = module.flat_manifest(tmp_path)
    (tmp_path / "a").write_bytes(b"two")
    assert module.flat_manifest(tmp_path) != before


def test_token_ids_accepts_transformers_encoding_shape_and_rejects_coercion():
    module = load_module()
    encoding = type("Encoding", (), {"ids": [1, 2, 3]})()
    assert module.token_ids(encoding) == [1, 2, 3]
    assert module.token_ids([encoding]) == [1, 2, 3]
    assert module.token_ids({"input_ids": [encoding]}) == [1, 2, 3]


def test_launcher_requires_network_namespace_and_offline_environment():
    source = LAUNCHER.read_text("utf-8")
    assert "unshare --mount --net --pid --ipc --uts --fork" in source
    assert "HF_HUB_OFFLINE=1" in source
    assert "TRANSFORMERS_OFFLINE=1" in source
    assert "TRITON_LIBCUDA_PATH=/usr/lib/wsl/lib" in source
    assert "TRITON_CACHE_DIR=/tmp/triton-cache" in source
    assert "CC=/usr/bin/gcc" in source
    assert "PATH=/usr/bin:/bin" in source
    assert "/host/" not in source
    assert 'mount -o remount,bind,ro "$2"' in source
    assert "mount -o remount,bind,ro" in source
    assert "AUTHORITY_MOUNTS_READ_ONLY=1" in source
    assert "OUTPUT_MOUNT_WRITABLE=1" in source
    assert 'MODEL_SHA256="${13}"' in source
