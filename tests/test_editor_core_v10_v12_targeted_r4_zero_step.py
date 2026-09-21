import ast
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts/launch_editor_core_v10_v12_targeted_r4_zero_step.py"


def module():
    spec = importlib.util.spec_from_file_location("targeted_r4_zero_step", LAUNCHER)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(value)
    return value


def test_launcher_has_no_model_or_optimizer_route():
    source = LAUNCHER.read_text("utf-8")
    tree = ast.parse(source)
    imports = {alias.name for node in ast.walk(tree) if isinstance(node, (ast.Import, ast.ImportFrom)) for alias in node.names}
    assert not imports.intersection({"torch", "transformers", "peft", "bitsandbytes"})
    assert "optimizer.step" not in source
    assert "from_pretrained" not in source
    assert "PASS_ZERO_STEP_ZERO_TRAINING" in source


def test_publication_selection_and_r4_dataset_close():
    m = module()
    manifest, config, audit = m.validate_public_inputs()
    assert audit["verdict"] == "PASS" and audit["blockers"] == 0
    assert manifest["manifest_identity"] == "6ff7e14b7402c4ad676b897dfe5b9157f5cedf83a488eb5e6504748ff69af6ed"
    assert config["training_config_identity"] == "ff56af658234f6168aeb1c541600860ecda72172c7f663098da7b1751a8274a1"
    assert config["training_performed"] is False and config["training_authorized"] is False


def test_output_requires_empty_ext4(monkeypatch, tmp_path):
    m = module()
    monkeypatch.setattr(m.subprocess, "check_output", lambda *args, **kwargs: "ext4\n")
    assert m.output_snapshot(tmp_path) == (tmp_path.stat().st_dev, tmp_path.stat().st_ino)
    (tmp_path / "unexpected").write_text("x")
    with pytest.raises(ValueError, match="not empty"):
        m.output_snapshot(tmp_path)


def test_parent_checkpoint_substitution_fails(monkeypatch, tmp_path):
    m = module()
    adapter = tmp_path / "adapter"
    adapter.mkdir()
    (adapter / "adapter_config.json").write_text("{}")
    monkeypatch.setattr(m, "flat_manifest", lambda path: m.PARENT_ADAPTER)
    core = {"model_sha256": m.BASE_MODEL, "optimizer_steps": 9}
    receipt = {**core, "checkpoint_identity": "0" * 64}
    (tmp_path / "checkpoint.json").write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="identity derivation"):
        m.validate_parent(tmp_path)


def test_parent_step_count_substitution_fails(monkeypatch, tmp_path):
    m = module()
    adapter = tmp_path / "adapter"
    adapter.mkdir()
    (adapter / "adapter_config.json").write_text("{}")
    monkeypatch.setattr(m, "flat_manifest", lambda path: m.PARENT_ADAPTER)
    core = {"model_sha256": m.BASE_MODEL, "optimizer_steps": 8}
    receipt = {**core, "checkpoint_identity": hashlib.sha256(m.canonical(core)).hexdigest()}
    (tmp_path / "checkpoint.json").write_text(json.dumps(receipt))
    with pytest.raises(ValueError, match="closure mismatch"):
        m.validate_parent(tmp_path)


def test_published_tree_drift_fails_before_dataset_audit(monkeypatch):
    m = module()
    monkeypatch.setattr(m.subprocess, "check_output", lambda *args, **kwargs: "0" * 40 + "\n")
    with pytest.raises(ValueError, match="source tree mismatch"):
        m.validate_public_inputs()


@pytest.mark.parametrize("field", ["adapter", "checkpoint", "promotion", "release"])
def test_semantic_selection_substitution_fails(monkeypatch, field):
    m = module()
    original = json.loads((m.ARTIFACTS / "editor-core-v10-v12-targeted-r3-semantic-result.json").read_bytes())
    if field == "adapter":
        original["selection"]["retained_adapter_identity"] = "0" * 64
    elif field == "checkpoint":
        original["r2_parent"]["checkpoint_identity"] = "0" * 64
    else:
        original["selection"][field] = True
    core = {key: value for key, value in original.items() if key != "result_identity"}
    original["result_identity"] = hashlib.sha256(m.canonical(core)).hexdigest()
    replacement = json.dumps(original, ensure_ascii=False, separators=(",", ":")).encode()
    real_read_bytes = Path.read_bytes

    def read_bytes(path):
        if path.name == "editor-core-v10-v12-targeted-r3-semantic-result.json":
            return replacement
        return real_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    with pytest.raises(ValueError):
        m.validate_public_inputs()


def test_model_drift_stops_before_parent_and_runtime(monkeypatch, tmp_path):
    m = module()
    model, checkpoint, snapshot, output = (tmp_path / name for name in ("model", "checkpoint", "snapshot", "output"))
    for path in (model, checkpoint, snapshot, output):
        path.mkdir()
    (model / "wrong").write_bytes(b"wrong")
    monkeypatch.setattr(m, "output_snapshot", lambda path: (1, 2))
    monkeypatch.setattr(m, "validate_public_inputs", lambda: ({}, {}, {}))
    with pytest.raises(ValueError, match="base model identity"):
        m.zero_step(model, checkpoint, tmp_path / "rootfs", snapshot, output)
