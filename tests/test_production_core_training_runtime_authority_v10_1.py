import copy
import hashlib
import json
import subprocess
from pathlib import Path

import pytest

from pastila_scout.production_core_training_runtime_authority_v10_1 import build_authority

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
AUTHORITY = ART / "production-core-training-runtime-authority-v10-1.json"


def test_authority_is_reproducible_closed_and_authorizes_no_qualification():
    value = json.loads(AUTHORITY.read_bytes())
    assert build_authority(value["observation"]) == value
    assert value["full_training_authorized"] is True
    assert value["candidate_execution_performed"] is False
    assert value["qualification_attempt_consumed"] is False
    assert value["adjudication_performed"] is False
    assert value["promotion_effect"] is False


def test_source_and_checkpoint_audit_bindings_match_exact_bytes():
    observation = json.loads(AUTHORITY.read_bytes())["observation"]
    paths = {
        "launcher_sha256": ROOT / "scripts/run_production_core_candidate_successor_training_v1.sh",
        "trainer_sha256": ROOT / "scripts/train_production_core_candidate_successor_v1.py",
        "checkpoint_resume_audit_sha256": ART / "production-core-v10-training-checkpoint-resume-audit.json",
        "predecessor_training_authority_sha256": ART / "production-core-training-runtime-authority-v10.json",
    }
    for field, path in paths.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == observation[field]
    assert subprocess.check_output(["git", "rev-parse", f'{observation["source_commit"]}^{{tree}}'], text=True).strip() == observation["source_tree"]


@pytest.mark.parametrize(("path", "bad"), [
    (("source_commit",), "0" * 40),
    (("checkpoint_resume_audit_identity",), "0" * 64),
    (("checkpoint_semantics", "atomic_publish"), False),
    (("checkpoint_semantics", "accepted_optimizer_steps_recomputed"), True),
    (("smoke_lifecycle", "optimizer"), "TORCH_ADAMW"),
    (("host_path_fallback",), True),
    (("qualification_attempt_consumed",), True),
])
def test_authority_rejects_substitution(path, bad):
    value = json.loads(AUTHORITY.read_bytes())["observation"]
    value = copy.deepcopy(value)
    target = value
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = bad
    with pytest.raises(ValueError, match="observation mismatch"):
        build_authority(value)


def test_checkpoint_audit_identity_and_materializer_are_reproducible():
    value = json.loads((ART / "production-core-v10-training-checkpoint-resume-audit.json").read_bytes())
    identity = value.pop("audit_identity")
    assert hashlib.sha256(json.dumps(value, separators=(",", ":"), sort_keys=True).encode()).hexdigest() == identity
    result = subprocess.run(
        [str(ROOT / ".venv/Scripts/python.exe"), str(ROOT / "scripts/materialize_production_core_v10_training_checkpoint_audit.py")],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert result.stdout.strip() == identity
