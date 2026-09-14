import copy
import hashlib
import importlib.util
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
TRAINER = ROOT / "scripts/train_production_core_candidate_successor_v1.py"
LAUNCHER = ROOT / "scripts/run_production_core_candidate_successor_training_v1.sh"


def load_trainer():
    spec = importlib.util.spec_from_file_location("v10_trainer", TRAINER)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


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


def test_trainer_rejects_corpus_not_bound_by_config():
    trainer = load_trainer()
    trainer.validate_training_corpus_binding({"training_corpus_sha256": "a" * 64}, "a" * 64)
    with pytest.raises(SystemExit, match="corpus/config binding mismatch"):
        trainer.validate_training_corpus_binding(
            {"training_corpus_sha256": "a" * 64}, "b" * 64
        )


def test_progress_events_are_durable_chained_and_identity_ignores_timing(tmp_path, monkeypatch):
    trainer = load_trainer()
    times = iter((1_010_000_000, 9_010_000_000))
    monkeypatch.setattr(trainer.time, "monotonic_ns", lambda: next(times))
    first = trainer.progress_event(
        tmp_path,
        previous_identity=None,
        event_ordinal=1,
        event="MICROSTEP_STARTED",
        epoch=1,
        position=1,
        row_index=437,
        example_id="example-437",
        token_count=2855,
        optimizer_steps_completed=0,
        started_ns=10_000_000,
    )
    second = trainer.progress_event(
        tmp_path,
        previous_identity=first,
        event_ordinal=2,
        event="MICROSTEP_COMPLETED",
        epoch=1,
        position=1,
        row_index=437,
        example_id="example-437",
        token_count=2855,
        optimizer_steps_completed=0,
        started_ns=10_000_000,
    )
    events = [json.loads(line) for line in (tmp_path / "training-progress.jsonl").read_text().splitlines()]
    assert [event["event_identity"] for event in events] == [first, second]
    assert events[1]["previous_event_identity"] == first
    assert events[0]["observed_elapsed_ms"] != events[1]["observed_elapsed_ms"]
    for event in events:
        identity = event.pop("event_identity")
        event.pop("observed_elapsed_ms")
        assert hashlib.sha256(
            json.dumps(event, separators=(",", ":"), sort_keys=True).encode()
        ).hexdigest() == identity


def test_launcher_terminates_the_isolated_training_process_group():
    source = LAUNCHER.read_text(encoding="utf-8")
    assert '"$MODE" == CHECKPOINT_SMOKE' in source
    assert '"$MODE" == BATCH_SMOKE' in source
    assert "setsid unshare --kill-child=KILL" in source
    assert 'kill -TERM -- "-$child_pid"' in source
    assert 'kill -KILL -- "-$child_pid"' in source


def test_trainer_pins_existing_reentrant_gradient_checkpointing_semantics():
    source = TRAINER.read_text(encoding="utf-8")
    assert 'gradient_checkpointing_kwargs={"use_reentrant": True}' in source


def test_progress_chain_validator_rejects_tampering(tmp_path, monkeypatch):
    trainer = load_trainer()
    monkeypatch.setattr(trainer.time, "monotonic_ns", lambda: 2_000_000_000)
    identity = trainer.progress_event(
        tmp_path,
        previous_identity=None,
        event_ordinal=1,
        event="MICROSTEP_STARTED",
        epoch=1,
        position=1,
        row_index=0,
        example_id="example-1",
        token_count=2000,
        optimizer_steps_completed=0,
        started_ns=1_000_000_000,
    )
    count, final, _ = trainer.validate_progress(tmp_path / "training-progress.jsonl")
    assert (count, final) == (1, identity)
    path = tmp_path / "training-progress.jsonl"
    path.write_text(path.read_text().replace('"token_count":2000', '"token_count":2001'))
    with pytest.raises(SystemExit, match="progress chain mismatch"):
        trainer.validate_progress(path)


def test_checkpoint_discovery_validates_content_and_authority(tmp_path):
    trainer = load_trainer()
    checkpoint = tmp_path / "training-checkpoints" / "step-000001"
    adapter = checkpoint / "adapter"
    adapter.mkdir(parents=True)
    (adapter / "adapter.safetensors").write_bytes(b"adapter")
    state = checkpoint / "training-state.pt"
    state.write_bytes(b"state")
    authority = {
        "corpus_sha256": "1" * 64,
        "config_sha256": "2" * 64,
        "predecessor_sha256": "3" * 64,
        "model_sha256": "4" * 64,
        "rootfs_sha256": "5" * 64,
        "launcher_sha256": "6" * 64,
        "trainer_sha256": "7" * 64,
        "training_mode": "FULL",
    }
    core = {
        "schema": "pastila-production-core-training-checkpoint",
        "schema_version": 1,
        **authority,
        "optimizer": "PAGED_ADAMW_8BIT",
        "triton_compile_load": True,
        "position_completed": 8,
        "row_index": 10,
        "example_id": "example-10",
        "token_count": 2200,
        "optimizer_steps_completed": 1,
        "previous_checkpoint_identity": None,
        "adapter_manifest_sha256": trainer.recursive_manifest(adapter),
        "state_sha256": trainer.sha(state),
    }
    identity = hashlib.sha256(
        json.dumps(core, separators=(",", ":"), sort_keys=True).encode()
    ).hexdigest()
    (checkpoint / "checkpoint.json").write_text(
        json.dumps({**core, "checkpoint_identity": identity})
    )
    found = trainer.discover_checkpoint(tmp_path, authority)
    assert found and found["checkpoint_identity"] == identity
    (adapter / "adapter.safetensors").write_bytes(b"substituted")
    with pytest.raises(SystemExit, match="checkpoint content mismatch"):
        trainer.discover_checkpoint(tmp_path, authority)


def test_adapter_config_canonicalization_sorts_set_derived_modules(tmp_path):
    trainer = load_trainer()
    (tmp_path / "adapter_config.json").write_text(
        json.dumps({"target_modules": ["v_proj", "down_proj", "q_proj"]})
    )
    trainer.canonicalize_adapter_config(tmp_path)
    value = json.loads((tmp_path / "adapter_config.json").read_bytes())
    assert value["target_modules"] == ["down_proj", "q_proj", "v_proj"]
    assert (tmp_path / "adapter_config.json").read_text().endswith("\n")
