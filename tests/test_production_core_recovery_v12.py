import copy
import importlib.util
from pathlib import Path

import pytest

from pastila_scout.production_core_recovery_v12 import validate, verify_external_objects

ROOT = Path(__file__).resolve().parents[1]
MATERIALIZER = ROOT / "scripts/materialize_production_core_recovery_manifest_v12.py"


def materializer():
    spec = importlib.util.spec_from_file_location("recovery_materializer", MATERIALIZER)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(value)
    return value


def test_recovery_manifest_is_reproducible_and_strict():
    value = materializer().build()
    validate(value)
    assert value["status"] == "PENDING_SECURE_PRIVATE_KEY_BACKUP"
    assert value["remaining_blockers"] == [
        "V8.1_ED25519_PRIVATE_KEY_HAS_NO_VERIFIED_OFF_SYSTEM_ENCRYPTED_BACKUP"
    ]
    assert value["execution_state"]["candidate_execution"] == 0
    assert value["execution_state"]["successor_attempt_consumption"] == 0
    broken = copy.deepcopy(value)
    broken["v12"]["runner_identity"] = "0" * 64
    with pytest.raises(ValueError, match="seal mismatch"):
        validate(broken)


def test_external_verifier_rejects_missing_objects(tmp_path):
    value = materializer().build()
    with pytest.raises(ValueError, match="missing external object"):
        verify_external_objects(value, tmp_path)
