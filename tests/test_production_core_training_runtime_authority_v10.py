import copy
import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout.production_core_training_runtime_authority_v10 import (
    CANDIDATES,
    build_authority,
)

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs/artifacts"
AUTHORITY = ART / "production-core-training-runtime-authority-v10.json"


def observation():
    return json.loads(AUTHORITY.read_bytes())["observation"]


def test_published_authority_is_closed_and_zero_execution():
    value = json.loads(AUTHORITY.read_bytes())
    assert build_authority(value["observation"]) == value
    assert value["full_training_authorized"] is False
    assert value["full_training_started"] is False
    assert value["candidate_execution_performed"] is False
    assert value["qualification_attempt_consumed"] is False


def test_all_v10_bindings_match_bytes_and_identities():
    value = observation()
    paths = {
        "execution_contract_sha256": ROOT / "src/pastila_scout/production_core_execution_contract_v10.py",
        "corpus_manifest_sha256": ART / "production-core-v10-corpus-and-training-config-manifest.json",
        "token_audit_receipt_sha256": ART / "production-core-v10-token-length-audit-receipt.json",
        "token_materialization_evidence_sha256": ART / "production-core-v10-token-materialization-evidence.json",
        "training_input_validator_sha256": ROOT / "scripts/validate_production_core_v10_training_inputs.py",
        "launcher_sha256": ROOT / "scripts/run_production_core_candidate_successor_training_v1.sh",
        "trainer_sha256": ROOT / "scripts/train_production_core_candidate_successor_v1.py",
        "runtime_smoke_authority_sha256": ART / "production-core-training-runtime-authority-v9.json",
    }
    for field, path in paths.items():
        assert hashlib.sha256(path.read_bytes()).hexdigest() == value[field]
    runtime_smoke = json.loads((ART / "production-core-training-runtime-authority-v9.json").read_bytes())
    assert runtime_smoke["training_runtime_authority_identity"] == value["runtime_smoke_authority_identity"]
    for candidate, binding in CANDIDATES.items():
        for kind, field in (("train", "training_corpus_sha256"), ("shadow", "shadow_corpus_sha256")):
            path = ART / f"{candidate}-{kind}.jsonl"
            assert hashlib.sha256(path.read_bytes()).hexdigest() == binding[field]
        config_path = ART / f"{candidate}-training-config-v10.json"
        config = json.loads(config_path.read_bytes())
        assert hashlib.sha256(config_path.read_bytes()).hexdigest() == binding["config_sha256"]
        assert config["training_config_identity"] == binding["training_config_identity"]


@pytest.mark.parametrize(("path", "bad"), [
    (("source_commit",), "0" * 40),
    (("rootfs_materialization_sha256", "D"), "0" * 64),
    (("rootfs_byte_identical",), False),
    (("execution_contract_identity",), "0" * 64),
    (("training_input_validator_sha256",), "0" * 64),
    (("maximum_training_sequence_tokens",), 1924),
    (("training_input_validation",), "FAIL"),
    (("runtime_smoke_authority_identity",), "0" * 64),
    (("runtime_smoke_authority_sha256",), "0" * 64),
    (("smoke_lifecycle", "optimizer"), "TORCH_ADAMW"),
    (("smoke_lifecycle", "backward_4bit"), False),
    (("authority_mounts_read_only",), False),
    (("host_path_fallback",), True),
    (("network_activity",), True),
    (("qualification_attempt_consumed",), True),
    (("promotion_effect",), True),
])
def test_authority_rejects_substitution(path, bad):
    value = copy.deepcopy(observation())
    target = value
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = bad
    with pytest.raises(ValueError, match="observation mismatch"):
        build_authority(value)
