"""Adversarial checks for the sealed, zero-attempt V13 authority."""
import json
import shutil
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import audit_production_core_successor_execution_authority_v13 as auditor  # noqa: E402
import materialize_production_core_successor_execution_authority_v13 as authority  # noqa: E402


def copied_authority(tmp_path):
    target = tmp_path / "authority"
    shutil.copytree(authority.OUTPUT, target)
    return target


def audit_static(target):
    return auditor.audit(target, Path("/unused"), Path("/unused"), Path("/unused"), recompute=False)


def test_issued_authority_has_new_generation_and_zero_attempts():
    observed = audit_static(authority.OUTPUT)
    assert observed["ed25519_verification"] == "PASS"
    value = json.loads((authority.OUTPUT / "authority.json").read_bytes())
    assert value["alias_secret_commitment"] != authority.generation_v13.HISTORICAL
    assert value["recovery_resolution_identity"] == authority.RESOLUTION
    assert value["v12_runtime_authority_identity"] == "6df414df46d2c76196a74b7e19baeb5c2cf39123cfdec48c7b859cb46e998d8f"
    assert value["candidate_execution"] == value["successor_attempt_consumption"] == 0
    assert value["adjudication"] is value["promotion"] is False


def test_failed_windows_recovery_substitution_rejected(tmp_path):
    target = copied_authority(tmp_path)
    path = target / "authority.json"
    value = json.loads(path.read_bytes())
    value["recovery_resolution_identity"] = "89e328339d6627f3f3cc5231b816353a4b580da391431feab4174029eb34779a"
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="seal mismatch"):
        audit_static(target)


def test_historical_secret_commitment_substitution_rejected(tmp_path):
    target = copied_authority(tmp_path)
    path = target / "authority.json"
    value = json.loads(path.read_bytes())
    value["alias_secret_commitment"] = authority.generation_v13.HISTORICAL
    path.write_text(json.dumps(value), encoding="utf-8")
    with pytest.raises(ValueError, match="seal mismatch"):
        audit_static(target)


def test_binding_and_signature_tampering_rejected(tmp_path):
    target = copied_authority(tmp_path)
    path = target / "binding.json"
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="binding mismatch"):
        audit_static(target)
    target = copied_authority(tmp_path / "other")
    path = target / "binding.sig"
    raw = bytearray(path.read_bytes())
    raw[0] ^= 1
    path.write_bytes(raw)
    with pytest.raises(Exception):
        audit_static(target)


def test_source_tree_drift_rejected(monkeypatch):
    monkeypatch.setattr(authority, "TREE", "0" * 40)
    with pytest.raises(ValueError, match="source tree mismatch"):
        authority.source_closure()
