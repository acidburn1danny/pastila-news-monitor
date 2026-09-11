import copy
import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout.production_core_training_runtime_authority_v5 import (
    CONFIG_SHA256,
    CORPUS_SHA256,
    DEVELOPMENT_SHA256,
    LAUNCHER_SHA256,
    TRAINER_SHA256,
    build_authority,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "docs/artifacts/production-core-training-runtime-authority-v5.json"


def observation():
    return json.loads(ARTIFACT.read_bytes())["observation"]


def test_published_v5_authority_is_closed_and_zero_qualification():
    value = json.loads(ARTIFACT.read_bytes())
    assert build_authority(value["observation"]) == value
    assert value["full_training_started"] is False
    assert value["qualification_attempt_consumed"] is False
    assert value["candidate_execution_performed"] is False


def test_v5_file_bindings_match_independent_bytes():
    bindings = {
        ROOT / "docs/artifacts/production-core-v1.1-eos-remediation-corpus-v2.jsonl": CORPUS_SHA256,
        ROOT / "docs/artifacts/production-core-v1.1-eos-development-probes-v2.jsonl": DEVELOPMENT_SHA256,
        ROOT / "docs/artifacts/production-core-v1.1-json-successor-v2-training-config-v2.json": CONFIG_SHA256,
        ROOT / "scripts/run_production_core_candidate_successor_training_v1.sh": LAUNCHER_SHA256,
        ROOT / "scripts/train_production_core_candidate_successor_v1.py": TRAINER_SHA256,
    }
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
        (("config_sha256",), "0" * 64),
        (("trainer_sha256",), "0" * 64),
        (("authority_mounts_read_only",), False),
        (("host_path_fallback",), True),
        (("network_activity",), True),
        (("optimizer",), "TORCH_ADAMW"),
        (("smoke", "compile_load_triton"), False),
        (("smoke", "backward_4bit"), False),
        (("smoke", "optimizer_steps"), 0),
        (("smoke", "save_reload"), False),
        (("post_training_gate_required",), False),
        (("qualification_attempt_consumed",), True),
        (("promotion_effect",), True),
    ],
)
def test_v5_authority_rejects_substitution(path, bad):
    value = copy.deepcopy(observation())
    target = value
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = bad
    with pytest.raises(ValueError, match="observation mismatch"):
        build_authority(value)
