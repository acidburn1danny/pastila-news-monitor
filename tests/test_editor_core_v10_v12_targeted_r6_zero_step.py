import ast
import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts/launch_editor_core_v10_v12_targeted_r6_zero_step.py"


def module():
    spec = importlib.util.spec_from_file_location("targeted_r6_zero_step", LAUNCHER)
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


def test_publication_selection_and_r6_dataset_close():
    m = module()
    manifest, config, audit = m.validate_public_inputs()
    assert audit["verdict"] == "PASS" and audit["blockers"] == 0
    assert manifest["manifest_identity"] == "73102c19815fe1e908883cb84ea5957e2923044097411ea6c2580b929fba7369"
    assert config["training_config_identity"] == "93efdcfb28a94db22f72d800245970dfe47a76609a30afc7bb92bc6afda0ed2b"
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


def test_r4_rejection_tampering_fails_closed(monkeypatch):
    m = module()
    original = json.loads((m.ARTIFACTS / "editor-core-v10-v12-targeted-r4-semantic-result.json").read_bytes())
    original["development_parent_decision"] = "ACCEPT_R4"
    replacement = json.dumps(original, ensure_ascii=False).encode()
    real_read_bytes = Path.read_bytes

    def read_bytes(path):
        if path.name == "editor-core-v10-v12-targeted-r4-semantic-result.json":
            return replacement
        return real_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    with pytest.raises(ValueError, match="R4 rejection closure"):
        m.validate_public_inputs()


def test_published_r6_blob_drift_fails_closed(monkeypatch):
    m = module()
    real_read_bytes = Path.read_bytes

    def read_bytes(path):
        if path.name == "editor-core-v10-v12-targeted-continuation-r6-manifest.json":
            return b"{}"
        return real_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    with pytest.raises(ValueError, match="published blob/worktree mismatch"):
        m.validate_public_inputs()


def test_r5_rejection_tampering_fails_closed(monkeypatch):
    m = module()
    original = json.loads((m.ARTIFACTS / "editor-core-v10-v12-targeted-r5-semantic-result.json").read_bytes())
    original["selection"]["retained_parent"] = "R5_STEP_6"
    replacement = json.dumps(original).encode()
    real_read_bytes = Path.read_bytes

    def read_bytes(path):
        if path.name == "editor-core-v10-v12-targeted-r5-semantic-result.json":
            return replacement
        return real_read_bytes(path)

    monkeypatch.setattr(Path, "read_bytes", read_bytes)
    with pytest.raises(ValueError, match="R5 rejection closure"):
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


def test_receipt_identity_excludes_ephemeral_output_identity(monkeypatch, tmp_path):
    m = module()
    outputs = [tmp_path / "first", tmp_path / "second"]
    for output in outputs:
        output.mkdir()
    monkeypatch.setattr(m, "output_snapshot", lambda path: (7, 101 if path == outputs[0] else 202))
    monkeypatch.setattr(m, "validate_public_inputs", lambda: (
        {"manifest_identity": m.DATASET_MANIFEST},
        {"training_corpus_sha256": "corpus", "training_config_identity": m.TRAINING_CONFIG},
        {"new_rows": 18, "replay_rows": 18, "holdout_rows": 12},
    ))
    monkeypatch.setattr(m, "flat_manifest", lambda path: m.BASE_MODEL)
    monkeypatch.setattr(m, "validate_parent", lambda path: {"adapter_identity": m.PARENT_ADAPTER, "checkpoint_identity": m.PARENT_CHECKPOINT})
    monkeypatch.setattr(m, "load_script", lambda *args: type("Snapshot", (), {"manifest": staticmethod(lambda path: {"manifest_identity": m.SNAPSHOT})})())
    monkeypatch.setattr(m, "run_runtime_probe", lambda *args: {"rootfs_sha256": m.ROOTFS, "cuda_available": True, "versions": {}})
    receipts = [m.zero_step(tmp_path, tmp_path, tmp_path, tmp_path, output) for output in outputs]
    assert receipts[0]["receipt_identity"] == receipts[1]["receipt_identity"]
    assert receipts[0]["output_runtime_observation"] != receipts[1]["output_runtime_observation"]
    for receipt in receipts:
        stable = {key: value for key, value in receipt.items() if key not in {"receipt_identity", "output_runtime_observation"}}
        assert receipt["receipt_identity"] == hashlib.sha256(m.canonical(stable)).hexdigest()


def test_output_identity_change_during_probe_fails_closed(monkeypatch, tmp_path):
    m = module()
    calls = iter(((7, 101), (7, 202)))
    monkeypatch.setattr(m, "output_snapshot", lambda path: next(calls))
    monkeypatch.setattr(m, "validate_public_inputs", lambda: ({}, {}, {}))
    monkeypatch.setattr(m, "flat_manifest", lambda path: m.BASE_MODEL)
    monkeypatch.setattr(m, "validate_parent", lambda path: {})
    monkeypatch.setattr(m, "load_script", lambda *args: type("Snapshot", (), {"manifest": staticmethod(lambda path: {"manifest_identity": m.SNAPSHOT})})())
    monkeypatch.setattr(m, "run_runtime_probe", lambda *args: {})
    with pytest.raises(ValueError, match="output identity changed"):
        m.zero_step(tmp_path, tmp_path, tmp_path, tmp_path, tmp_path)
