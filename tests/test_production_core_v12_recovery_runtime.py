import hashlib
import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/materialize_production_core_v12_recovery_runtime.py"


def module():
    spec = importlib.util.spec_from_file_location("v12_recovery_runtime", SCRIPT)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(value)
    return value


def test_recovery_resolution_seal_and_projection_are_strict():
    value = module()
    core = {
        "schema": "pastila-production-core-v12-recovery-runtime-resolution",
        "schema_version": 1,
        "candidate_execution": 0,
        "successor_attempt_consumption": 0,
        "adjudication": False,
        "promotion": False,
    }
    sealed = {**core, "resolution_identity": hashlib.sha256(value.canonical(core)).hexdigest()}
    value.validate_recovery_resolution(sealed)
    broken = dict(sealed)
    broken["candidate_execution"] = 1
    with pytest.raises(ValueError, match="seal mismatch"):
        value.validate_recovery_resolution(broken)
    invalid_state = {**core, "candidate_execution": False}
    invalid_state["resolution_identity"] = hashlib.sha256(value.canonical({key: item for key, item in invalid_state.items() if key != "resolution_identity"})).hexdigest()
    with pytest.raises(ValueError, match="execution state mismatch"):
        value.validate_recovery_resolution(invalid_state)

    projection = {
        "schema": "pastila-production-core-local-object-resolution-v2",
        "schema_version": 2,
        "materializations": {
            label: {
                "rootfs_tar": "/mnt/c/replay/rootfs.tar",
                "model": f"/mnt/c/replay/models/{label}",
                "adapters": {
                    name: f"/mnt/c/replay/adapters/{label}/{name}"
                    for name in value.EXPECTED_ADAPTERS
                },
            }
            for label in ("A", "B")
        },
    }
    value.validate_projection(projection)
    broken_projection = dict(projection)
    broken_projection["schema"] = "pastila-production-core-local-object-resolution-v10"
    with pytest.raises(ValueError, match="schema mismatch"):
        value.validate_projection(broken_projection)


def test_flat_object_validator_rejects_wrong_identity_and_writable_file(tmp_path):
    value = module()
    root = tmp_path / "object"
    root.mkdir()
    payload = root / "payload.bin"
    payload.write_bytes(b"canonical")
    payload.chmod(0o444)
    root.chmod(0o555)
    expected = value.flat_identity(root)
    assert value.validate_flat_directory(root, expected) == expected
    with pytest.raises(ValueError, match="directory missing"):
        value.validate_flat_directory(tmp_path / "missing-model", expected)
    root.chmod(0o755)
    with pytest.raises(ValueError, match="directory is writable"):
        value.validate_flat_directory(root, expected)
    root.chmod(0o555)

    payload.chmod(0o644)
    payload.write_bytes(b"wrong")
    payload.chmod(0o444)
    with pytest.raises(ValueError, match="identity mismatch"):
        value.validate_flat_directory(root, expected)

    payload.chmod(0o644)
    payload.write_bytes(b"canonical")
    with pytest.raises(ValueError, match="not read-only"):
        value.validate_flat_directory(root, expected)


def test_flat_object_validator_rejects_symlink_substitution(tmp_path):
    value = module()
    root = tmp_path / "object"
    root.mkdir()
    target = tmp_path / "target.bin"
    target.write_bytes(b"canonical")
    try:
        (root / "payload.bin").symlink_to(target)
    except OSError:
        pytest.skip("symlink creation is unavailable on this Windows host")
    root.chmod(0o555)
    with pytest.raises(ValueError, match="not read-only"):
        value.validate_flat_directory(root, "0" * 64)


def test_recovery_audit_rejects_missing_wrong_and_substituted_objects(tmp_path, monkeypatch):
    value = module()
    model = tmp_path / "models"
    model.mkdir()
    payload = model / "weight.bin"
    payload.write_bytes(b"valid")
    payload.chmod(0o444)
    expected = value.flat_identity(model)
    monkeypatch.setattr(value, "EXPECTED_BASE", expected)
    adapter_name = "test-adapter"
    monkeypatch.setattr(value, "TOKENIZER_FILES", {})
    rootfs = tmp_path / "rootfs.tar"
    rootfs.write_bytes(b"rootfs")
    rootfs.chmod(0o444)
    monkeypatch.setattr(value, "EXPECTED_ROOTFS", value.sha256_file(rootfs))
    tokenizers = {}
    materializations = {}
    for label in ("A", "B"):
        target = tmp_path / f"model-{label}"
        target.mkdir()
        item = target / "weight.bin"
        item.write_bytes(b"valid")
        item.chmod(0o444)
        target.chmod(0o555)
        tokenizer = tmp_path / f"tokenizer-{label}"
        tokenizer.mkdir()
        adapter = tmp_path / f"adapter-{label}"
        adapter.mkdir()
        adapter_file = adapter / "adapter.bin"
        adapter_file.write_bytes(b"adapter")
        adapter_file.chmod(0o444)
        adapter.chmod(0o555)
        monkeypatch.setattr(value, "EXPECTED_ADAPTERS", {adapter_name: value.flat_identity(adapter)})
        tokenizers[label] = value.wsl_path(tokenizer) if value.os.name == "nt" else str(tokenizer)
        materializations[label] = {"rootfs_tar": value.wsl_path(rootfs) if value.os.name == "nt" else str(rootfs), "model": value.wsl_path(target) if value.os.name == "nt" else str(target), "adapters": {adapter_name: value.wsl_path(adapter) if value.os.name == "nt" else str(adapter)}}
    if value.os.name != "nt":
        monkeypatch.setattr(value, "host_path", lambda path: Path(path))
        materializations = {label: {"rootfs_tar": "/mnt/c/rootfs.tar", "model": f"/mnt/c/model-{label}", "adapters": {adapter_name: f"/mnt/c/adapter-{label}"}} for label in ("A", "B")}
        tokenizers = {label: f"/mnt/c/tokenizer-{label}" for label in ("A", "B")}
        mapping = {"/mnt/c/rootfs.tar": rootfs, **{f"/mnt/c/model-{label}": tmp_path / f"model-{label}" for label in ("A", "B")}, **{f"/mnt/c/adapter-{label}": tmp_path / f"adapter-{label}" for label in ("A", "B")}, **{f"/mnt/c/tokenizer-{label}": tmp_path / f"tokenizer-{label}" for label in ("A", "B")}}
        monkeypatch.setattr(value, "host_path", lambda path: mapping[path])
    projection = {"schema": "pastila-production-core-local-object-resolution-v2", "schema_version": 2, "materializations": materializations}
    source_inputs = {"prompts": {name: {"sha256": digest, "source_path": path.relative_to(value.ROOT).as_posix()} for (name, path), digest in zip(value.PROMPTS.items(), value.EXPECTED_PROMPTS.values(), strict=True)}, "qualification_artifacts": {name: {"identity": identity, "source_path": f"docs/artifacts/{filename}"} for name, filename, identity in (("comparative_generation", "production-core-successor-comparative-qualification-generation-v10.json", value.EXPECTED_GENERATION), ("candidate_generation_qualification", "production-core-successor-candidate-generation-qualification-v10.json", value.EXPECTED_QUALIFICATION), ("candidate_object_manifest", "production-core-successor-candidate-object-manifest-v10.json", value.EXPECTED_CANDIDATE_MANIFEST))}}
    core = {"schema": "pastila-production-core-v12-recovery-runtime-resolution", "schema_version": 1, "runner_identity": value.EXPECTED_RUNNER, "source_recovery_manifest_identity": "8c064b062bd68a2c3f5cae839672a8d4e94b8ee49b8d3d3ed8f077ffc878439e", "base_model_content_identity": expected, "adapter_content_identities": value.EXPECTED_ADAPTERS, "tokenizer_content_identity": value.EXPECTED_TOKENIZER, "prompt_identities": value.EXPECTED_PROMPTS, "source_inputs": source_inputs, "materializations": materializations, "tokenizers": tokenizers, "candidate_execution": 0, "successor_attempt_consumption": 0, "adjudication": False, "promotion": False}

    def sealed():
        return {**core, "resolution_identity": hashlib.sha256(value.canonical(core)).hexdigest()}

    value.audit_recovery_resolution(sealed(), projection)
    payload = tmp_path / "model-A" / "weight.bin"
    payload.chmod(0o644)
    payload.unlink()
    with pytest.raises(ValueError, match="empty runtime object"):
        value.audit_recovery_resolution(sealed(), projection)
    payload.write_bytes(b"wrong")
    payload.chmod(0o444)
    with pytest.raises(ValueError, match="identity mismatch"):
        value.audit_recovery_resolution(sealed(), projection)
    payload.chmod(0o644)
    payload.write_bytes(b"valid")
    payload.chmod(0o444)
    adapter_file = tmp_path / "adapter-A" / "adapter.bin"
    adapter_file.chmod(0o644)
    adapter_file.unlink()
    with pytest.raises(ValueError, match="empty runtime object"):
        value.audit_recovery_resolution(sealed(), projection)
    adapter_file.write_bytes(b"wrong")
    adapter_file.chmod(0o444)
    with pytest.raises(ValueError, match="identity mismatch"):
        value.audit_recovery_resolution(sealed(), projection)
    adapter_file.chmod(0o644)
    adapter_file.write_bytes(b"adapter")
    adapter_file.chmod(0o444)
    payload.chmod(0o644)
    payload.write_bytes(b"valid")
    with pytest.raises(ValueError, match="not read-only"):
        value.audit_recovery_resolution(sealed(), projection)
    payload.chmod(0o444)
    changed = json.loads(json.dumps(projection))
    changed["materializations"]["A"]["model"] = changed["materializations"]["B"]["model"]
    with pytest.raises(ValueError, match="path substitution"):
        value.audit_recovery_resolution(sealed(), changed)
    shared = json.loads(json.dumps(projection))
    shared["materializations"]["B"]["model"] = shared["materializations"]["A"]["model"]
    shared_core = {**core, "materializations": shared["materializations"]}
    shared_recovery = {**shared_core, "resolution_identity": hashlib.sha256(value.canonical(shared_core)).hexdigest()}
    with pytest.raises(ValueError, match="overlap"):
        value.audit_recovery_resolution(shared_recovery, shared)
    stale = sealed()
    stale["resolution_identity"] = "0" * 64
    with pytest.raises(ValueError, match="seal mismatch"):
        value.audit_recovery_resolution(stale, projection)
