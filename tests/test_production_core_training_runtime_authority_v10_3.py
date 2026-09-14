import hashlib
import json
import subprocess
from pathlib import Path

from pastila_scout.production_core_training_runtime_authority_v10_3 import build_authority

ROOT = Path(__file__).resolve().parents[1]
AUTHORITY = ROOT / "docs/artifacts/production-core-training-runtime-authority-v10-3.json"


def test_v10_3_authority_is_reproducible_bound_and_zero_attempts():
    value = json.loads(AUTHORITY.read_bytes())
    observation = value["observation"]
    assert build_authority(observation) == value
    assert hashlib.sha256((ROOT / "scripts/train_production_core_candidate_successor_v1.py").read_bytes()).hexdigest() == observation["trainer_sha256"]
    assert subprocess.check_output(["git", "rev-parse", f'{observation["source_commit"]}^{{tree}}'], text=True).strip() == observation["source_tree"]
    assert observation["schema_cardinality_repair"] == "SCHEMA_4_EXACTLY_480_ROWS"
    assert value["qualification_attempt_consumed"] is False
    assert value["candidate_execution_performed"] is False
