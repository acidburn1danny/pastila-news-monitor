from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path

import pytest

from pastila_scout import vnext_r2_consolidation_binding_v1 as binding
from pastila_scout.vnext_foundation_v1 import object_identity

CLOSURE = Path("docs/artifacts/vnext-r2-byte-identical-consolidation-binding-closure-v1.json")


def required_identities() -> dict[str, str]:
    return {
        "adapter_flat_identity": "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02",
        "base_model_flat_identity": "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39",
        "checkpoint_identity": "96e10b85fe30c4be43c2cc1a0b906f04ea4c476cc8d422b4ad26e9758b85b2be",
        "tokenizer_flat_identity": "026c7803af845d166451a8845defbc359cfda96d2d33c56d9648dcc8c117d1b2",
        "tokenizer_json_sha256": "d5f6046775b112f0e2d456ee9dba450684ab964fe5c4e231599bdc6773028135",
    }


def synthetic_closure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "r2"; (root / "objects").mkdir(parents=True)
    payload = b"frozen-r2-fixture"
    (root / "objects/payload.bin").write_bytes(payload)
    lock = {
        "component": "R2_STEP_9_REFERENCE_REALIZER", "file_count": 1,
        "files": [{"path": "objects/payload.bin", "sha256": hashlib.sha256(payload).hexdigest(), "size": len(payload)}],
        "forbidden_dependencies": ["LEGACY_REPOSITORY"], "identities": required_identities(),
        "layout": {"adapter": "objects/adapter", "base_model": "objects/base-model", "dependency_preflight": "tooling/preflight.py", "tokenizer": "objects/tokenizer"},
        "runtime": {"adapter_loader": "PeftModel", "fix_mistral_regex": True, "loader": "AutoModelForImageTextToText", "local_files_only": True},
        "schema": "editor-vnext-r2-reference-dependency-lock", "schema_version": 1,
        "status": "MATERIALIZED_SELF_CONTAINED", "total_bytes": len(payload),
    }
    lock["lock_identity"] = object_identity(lock)
    raw = json.dumps(lock, ensure_ascii=False, indent=2, sort_keys=True).encode() + b"\n"
    (root / "dependency-lock.json").write_bytes(raw)
    monkeypatch.setattr(binding, "EXPECTED_LOCK_IDENTITY", lock["lock_identity"])
    monkeypatch.setattr(binding, "EXPECTED_LOCK_SHA256", hashlib.sha256(raw).hexdigest())
    monkeypatch.setattr(binding, "EXPECTED_FILE_COUNT", 1)
    monkeypatch.setattr(binding, "EXPECTED_TOTAL_BYTES", len(payload))
    return root


def test_published_binding_and_closure_identities_reproduce():
    closure = json.loads(CLOSURE.read_text(encoding="utf-8"))
    assert object_identity({key: value for key, value in closure.items() if key != "closure_identity"}) == closure["closure_identity"]
    assert closure["closure_identity"] == "98db9cb3a276b6684fd3f2013a359b55703b8073d7745a9461a40ba4168adbf6"
    manifest = binding.binding_manifest({"lock_identity": binding.EXPECTED_LOCK_IDENTITY})
    assert manifest == closure["binding"]
    assert manifest["binding_identity"] == "0084f051f7aac5e90f2209e1796d5dbf7a26bb3fbb14fbf0a9e06b5b0818810f"


def test_synthetic_byte_exact_closure_passes(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = synthetic_closure(tmp_path, monkeypatch)
    assert binding.verify_closure(root) == {"status": "PASS_BYTE_IDENTICAL", "lock_identity": binding.EXPECTED_LOCK_IDENTITY, "files": 1, "bytes": 17}


def test_byte_drift_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = synthetic_closure(tmp_path, monkeypatch)
    (root / "objects/payload.bin").write_bytes(b"frozen-r2-fixturf")
    with pytest.raises(binding.R2BindingError, match="identity mismatch"):
        binding.verify_closure(root)


def test_extra_file_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = synthetic_closure(tmp_path, monkeypatch); (root / "extra").write_text("x")
    with pytest.raises(binding.R2BindingError, match="inventory mismatch"):
        binding.verify_closure(root)


def test_symlink_and_hardlink_aliases_fail_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    root = synthetic_closure(tmp_path, monkeypatch)
    alias = root / "alias"
    try:
        alias.symlink_to(root / "objects/payload.bin")
    except OSError:
        pytest.skip("symlink unavailable")
    with pytest.raises(binding.R2BindingError, match="symlink"):
        binding.verify_closure(root)
    alias.unlink(); os.link(root / "objects/payload.bin", alias)
    with pytest.raises(binding.R2BindingError, match="independent regular file"):
        binding.verify_closure(root)


def test_platform_or_lock_substitution_fails_closed():
    with pytest.raises(binding.R2BindingError):
        binding.binding_manifest({"lock_identity": "0" * 64})
    with pytest.raises(binding.R2BindingError):
        binding.binding_manifest({"lock_identity": binding.EXPECTED_LOCK_IDENTITY}, platform_tree_identity="0" * 64)


def test_closure_preserves_product_boundaries():
    value = json.loads(CLOSURE.read_text(encoding="utf-8"))
    assert value["status"] == "ISOLATED_NOT_ACTIVE"
    assert value["binding"]["relocation_authorized"] is False
    assert value["product_root_modified"] is False and value["product_lock_modified"] is False
    assert value["validation"]["model_loaded"] is False and value["validation"]["inference_performed"] is False
    assert value["legacy_dependency_count"] == 0
    assert value["stop_all_candidates"] is True and value["voice"] == "DISABLED_UNTIL_PROMOTION"

