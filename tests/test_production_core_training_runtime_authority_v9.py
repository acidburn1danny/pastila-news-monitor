import copy
import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout.production_core_training_runtime_authority_v9 import (
    CANDIDATES,
    CORPUS_SHA256,
    DEVELOPMENT_SHA256,
    LAUNCHER_SHA256,
    TRAINER_SHA256,
    build_authority,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/production-core-training-runtime-authority-v9.json"


def observation():
    return json.loads(ARTIFACT.read_bytes())["observation"]


def test_published_v9_authority_is_closed_and_zero_qualification():
    value = json.loads(ARTIFACT.read_bytes())
    assert build_authority(value["observation"]) == value
    assert value["full_training_started"] is False
    assert value["qualification_attempt_consumed"] is False
    assert value["candidate_execution_performed"] is False


def test_v9_file_bindings_match_independent_bytes():
    bindings = {
        ROOT / "docs/artifacts/production-core-v9-dual-structural-remediation-train.jsonl": CORPUS_SHA256,
        ROOT / "docs/artifacts/production-core-v9-dual-structural-remediation-development.jsonl": DEVELOPMENT_SHA256,
        ROOT / "scripts/run_production_core_candidate_successor_training_v1.sh": LAUNCHER_SHA256,
        ROOT / "scripts/train_production_core_candidate_successor_v1.py": TRAINER_SHA256,
    }
    for name, candidate in CANDIDATES.items():
        suffix = "v1.1" if "v1.1" in name else "v1.2"
        bindings[ROOT / f"docs/artifacts/pastila-editor-core-{suffix}-json-successor-v9-training-config-v3.json"] = candidate["config_sha256"]
    for path, expected in bindings.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == expected


@pytest.mark.parametrize(
    ("path", "bad"),
    [
        (("source_commit",), "0" * 40),
        (("rootfs_materialization_sha256", "D"), "0" * 64),
        (("rootfs_byte_identical",), False),
        (("corpus_sha256",), "0" * 64),
        (("development_probe_sha256",), "0" * 64),
        (("trainer_sha256",), "0" * 64),
        (("authority_mounts_read_only",), False),
        (("host_path_fallback",), True),
        (("network_activity",), True),
        (("optimizer",), "TORCH_ADAMW"),
        (("smoke_lifecycle", "compile_load_triton"), False),
        (("smoke_lifecycle", "backward_4bit"), False),
        (("smoke_lifecycle", "optimizer_steps_per_candidate"), 0),
        (("smoke_lifecycle", "save_reload"), False),
        (("post_training_gate_required",), False),
        (("qualification_attempt_consumed",), True),
        (("promotion_effect",), True),
    ],
)
def test_v9_authority_rejects_substitution(path, bad):
    value = copy.deepcopy(observation())
    target = value
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = bad
    with pytest.raises(ValueError, match="observation mismatch"):
        build_authority(value)
