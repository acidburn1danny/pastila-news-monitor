import copy
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from pastila_scout.production_core_training_runtime_authority_v10_2 import build_authority

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
AUTHORITY = ART / "production-core-training-runtime-authority-v10-2.json"


def test_authority_is_reproducible_and_zero_qualification_attempts():
    value = json.loads(AUTHORITY.read_bytes())
    assert build_authority(value["observation"]) == value
    assert value["full_training_authorized"] is True
    assert value["qualification_attempt_consumed"] is False
    assert value["candidate_execution_performed"] is False


def test_authority_binds_current_source_config_and_freeze_bytes():
    observation = json.loads(AUTHORITY.read_bytes())["observation"]
    paths = {
        "trainer_sha256": ROOT / "scripts/train_production_core_candidate_successor_v1.py",
        "launcher_sha256": ROOT / "scripts/run_production_core_candidate_successor_training_v1.sh",
        "training_input_validator_sha256": ROOT / "scripts/validate_production_core_v10_training_inputs.py",
        "corpus_manifest_sha256": ART / "production-core-v10-corpus-and-training-config-manifest.json",
        "performance_freeze_sha256": ART / "production-core-v10-performance-bakeoff-freeze.json",
    }
    for field, path in paths.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == observation[field]
    for candidate, binding in observation["candidates"].items():
        path = ART / f"{candidate}-training-config-v10.json"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == binding["config_sha256"]
    assert subprocess.check_output(["git", "rev-parse", f'{observation["source_commit"]}^{{tree}}'], text=True).strip() == observation["source_tree"]


@pytest.mark.parametrize("field", ["source_commit", "trainer_sha256", "performance_freeze_identity", "training_execution_profile", "qualification_attempt_consumed"])
def test_authority_rejects_substitution(field):
    observation = json.loads(AUTHORITY.read_bytes())["observation"]
    bad = copy.deepcopy(observation)
    bad[field] = True if field == "qualification_attempt_consumed" else "WRONG"
    with pytest.raises(ValueError, match="observation mismatch"):
        build_authority(bad)
