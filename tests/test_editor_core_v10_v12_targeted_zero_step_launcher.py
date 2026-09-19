import ast
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts/launch_editor_core_v10_v12_targeted_continuation_zero_step.py"


def module():
    spec = importlib.util.spec_from_file_location("targeted_zero_step", LAUNCHER)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(value)
    return value


def test_launcher_contains_no_training_or_model_execution_route():
    source = LAUNCHER.read_text("utf-8")
    tree = ast.parse(source)
    imports = {
        alias.name
        for node in ast.walk(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
        for alias in node.names
    }
    assert not imports.intersection({"torch", "transformers", "peft", "bitsandbytes"})
    assert "optimizer.step" not in source
    assert "from_pretrained" not in source
    assert "PASS_ZERO_STEP_ZERO_TRAINING" in source


def test_flat_manifest_is_name_size_and_content_bound(tmp_path):
    m = module()
    (tmp_path / "a").write_bytes(b"one")
    first = m.flat_manifest(tmp_path)
    (tmp_path / "a").write_bytes(b"two")
    assert m.flat_manifest(tmp_path) != first
    (tmp_path / "a").rename(tmp_path / "b")
    assert m.flat_manifest(tmp_path) != first


def test_output_snapshot_requires_empty_ext4(monkeypatch, tmp_path):
    m = module()
    monkeypatch.setattr(m.subprocess, "check_output", lambda *args, **kwargs: "ext4\n")
    assert m.output_snapshot(tmp_path) == (tmp_path.stat().st_dev, tmp_path.stat().st_ino)
    (tmp_path / "unexpected").write_text("x", encoding="utf-8")
    with pytest.raises(ValueError, match="not empty"):
        m.output_snapshot(tmp_path)


def test_output_snapshot_rejects_drvfs(monkeypatch, tmp_path):
    m = module()
    monkeypatch.setattr(m.subprocess, "check_output", lambda *args, **kwargs: "9p\n")
    with pytest.raises(ValueError, match="requires ext4"):
        m.output_snapshot(tmp_path)


def test_zero_step_rejects_model_drift_before_parent_or_runtime(monkeypatch, tmp_path):
    m = module()
    model = tmp_path / "model"
    adapter = tmp_path / "adapter"
    snapshot = tmp_path / "snapshot"
    output = tmp_path / "output"
    for path in (model, adapter, snapshot, output):
        path.mkdir()
    (model / "file").write_bytes(b"wrong")
    monkeypatch.setattr(m, "output_snapshot", lambda path: (1, 2))
    monkeypatch.setattr(m, "validate_public_inputs", lambda: ({}, {}, {}))
    with pytest.raises(ValueError, match="base model identity"):
        m.zero_step(model, adapter, tmp_path / "rootfs", snapshot, output)


def test_publication_state_and_dataset_boundary_close_without_training():
    m = module()
    manifest, config, result = m.validate_public_inputs()
    assert result["verdict"] == "PASS" and result["blockers"] == 0
    assert manifest["manifest_identity"] == "cbcf7a90ff55b56b5499ce4967a54118b3d99c57c105d7645fada6ad54392b8e"
    assert config["training_config_identity"] == "934bc1dcd02f2eb23e98e4ef371e2fd89eb9d7b921eb0554cec8e51cc561f975"
    assert config["training_performed"] is False and config["training_authorized"] is False


def test_parent_receipt_substitution_fails_closed(monkeypatch, tmp_path):
    m = module()
    monkeypatch.setattr(m, "flat_manifest", lambda path: m.PARENT_ADAPTER)
    (tmp_path / "adapter_config.json").write_text("{}", encoding="utf-8")
    receipt = {
        "candidate": "pastila-editor-core-v1.2-json-successor-v10",
        "final_checkpoint_identity": "0" * 64,
        "base_model_manifest_sha256": m.BASE_MODEL,
    }
    receipt["receipt_identity"] = m.hashlib.sha256(m.canonical(receipt)).hexdigest()
    (tmp_path / "training-receipt.json").write_text(m.json.dumps(receipt), encoding="utf-8")
    with pytest.raises(ValueError, match="checkpoint closure"):
        m.validate_parent(tmp_path)
