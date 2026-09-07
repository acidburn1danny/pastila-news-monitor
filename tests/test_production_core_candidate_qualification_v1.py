from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from pastila_scout.production_core_candidate_qualification_authority_v1 import (
    validate_terminal_candidate_qualification_authority,
)
from pastila_scout.production_core_candidate_qualification_v1 import (
    ALIASES,
    QualificationAuthorityError,
    atomic_publish,
    build_blind_packet,
    build_candidate_prompt,
    build_execution_receipt,
    canonical_json_bytes,
    deterministic_schedule,
    materialize_batches,
    validate_candidate_output,
    validate_secret_mapping,
)

ROOT = Path(__file__).resolve().parents[1]


def execution_module():
    path = ROOT / "scripts/execute_production_core_candidate_qualification_v1.py"
    spec = importlib.util.spec_from_file_location("pcq_execution_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def entry_module():
    path = ROOT / "scripts/launch_production_core_candidate_qualification_v1.py"
    spec = importlib.util.spec_from_file_location("pcq_entry_test", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def secret() -> dict[str, object]:
    return {
        "schema": "pastila-production-core-candidate-alias-secret",
        "schema_version": 1,
        "nonce_hex": "42" * 32,
        "aliases": {
            "CANDIDATE-A": "pastila-editor-core-v1.2-experimental",
            "CANDIDATE-B": "pastila-editor-core-v1.1-experimental",
        },
    }


def commitment(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def corpus() -> dict[str, object]:
    return json.loads((ROOT / "docs/artifacts/production-core-qualification-corpus-v1.json").read_bytes())


def response(case: dict[str, object]) -> dict[str, object]:
    return {
        "schema": "pastila-core-v2-structured-qualification-response",
        "schema_version": 1,
        "case_id": case["case_id"],
        "request_identity": case["request_identity"],
        "output_type": case["output_type"],
        "outcome": "ABSTAIN",
        "text": None,
        "claim_bindings": [],
        "abstention_code": "INSUFFICIENT_AUTHORITY",
    }


def test_exact_matrix_is_secret_deterministic_and_balanced() -> None:
    value = secret()
    ids = [row["case_id"] for row in corpus()["cases"]]
    first = deterministic_schedule(ids, value, commitment(value))
    assert first == deterministic_schedule(ids, value, commitment(value))
    assert len(first) == 2400
    assert {row["candidate_alias"] for row in first} == set(ALIASES)
    assert all(sum(row["candidate_alias"] == alias for row in first) == 1200 for alias in ALIASES)
    assert [row["global_ordinal"] for row in first] == list(range(1, 2401))
    for materialization in ("A", "B"):
        for repetition in (1, 2, 3):
            for alias in ALIASES:
                batch = [row for row in first if row["materialization"] == materialization and row["repetition"] == repetition and row["candidate_alias"] == alias]
                assert len(batch) == 200
                assert [row["batch_ordinal"] for row in batch] == list(range(1, 201))
    rebound = json.loads(json.dumps(value)); rebound["nonce_hex"] = "43" * 32
    with pytest.raises(QualificationAuthorityError):
        deterministic_schedule(ids, rebound, commitment(value))


def test_alias_mapping_is_exact_closed_and_not_derivable_from_schedule() -> None:
    value = secret(); digest = commitment(value)
    assert set(validate_secret_mapping(value, digest)) == set(ALIASES)
    ids = [row["case_id"] for row in corpus()["cases"]]
    encoded = canonical_json_bytes(deterministic_schedule(ids, value, digest))
    assert b"pastila-editor-core" not in encoded
    for mutation in (
        {**value, "extra": False},
        {**value, "aliases": {"CANDIDATE-A": "pastila-editor-core-v1.1-experimental", "CANDIDATE-B": "pastila-editor-core-v1.1-experimental"}},
    ):
        with pytest.raises(QualificationAuthorityError):
            validate_secret_mapping(mutation, commitment(mutation))


def test_public_plan_derives_exact_twelve_batches_and_rejects_rebinding() -> None:
    value = secret()
    plan = json.loads((ROOT / "docs/artifacts/production-core-comparative-qualification-generation-v1.json").read_bytes())
    manifest = json.loads((ROOT / "docs/artifacts/production-core-candidate-object-manifest-v1.json").read_bytes())
    frozen_corpus = corpus()
    # The committed plan uses an undisclosed secret. Build an equivalent synthetic plan
    # around this test-only key to exercise complete validation without learning it.
    core = dict(plan); core.pop("qualification_generation_identity")
    core["alias_secret_commitment"] = commitment(value)
    core["schedule"] = deterministic_schedule(
        [row["case_id"] for row in frozen_corpus["cases"]], value, commitment(value)
    )
    synthetic = {**core, "qualification_generation_identity": commitment(core)}
    batches = materialize_batches(synthetic, manifest, frozen_corpus, value)
    assert len(batches) == 12 and all(len(row["batch"]) == 200 for row in batches)
    rebound = json.loads(json.dumps(synthetic)); rebound["schedule"][0]["case_id"] = "pcq-fac-002"
    rebound_core = dict(rebound); rebound_core.pop("qualification_generation_identity")
    rebound["qualification_generation_identity"] = commitment(rebound_core)
    with pytest.raises(QualificationAuthorityError):
        materialize_batches(rebound, manifest, frozen_corpus, value)


def test_common_prompt_uses_only_frozen_case_authority() -> None:
    case = corpus()["cases"][0]
    prompt = build_candidate_prompt(case)
    assert case["case_id"] in prompt and case["request_identity"] in prompt
    assert "CANDIDATE-A" not in prompt and "experimental" not in prompt
    changed = dict(case); changed["ignored"] = "candidate-specific"
    assert build_candidate_prompt(changed) == prompt


def test_raw_output_requires_exact_canonical_bytes_and_bindings() -> None:
    case = corpus()["cases"][0]
    raw = canonical_json_bytes(response(case))
    parsed, canonical = validate_candidate_output(raw, case)
    assert canonical == raw and parsed["case_id"] == case["case_id"]
    for invalid in (raw + b"\n", b" " + raw, raw + b" trailing", b"\xef\xbb\xbf" + raw):
        with pytest.raises(QualificationAuthorityError):
            validate_candidate_output(invalid, case)
    rebound = response(case); rebound["case_id"] = "pcq-fac-002"
    with pytest.raises(QualificationAuthorityError):
        validate_candidate_output(canonical_json_bytes(rebound), case)


def test_resource_receipt_fails_closed_without_retry_or_promotion() -> None:
    authority = {"qualification_generation_identity": "a" * 64}
    row = {"materialization": "A", "repetition": 1, "ordinal": 1, "candidate_alias": "CANDIDATE-A", "case_id": "pcq-fac-001"}
    kwargs = {
        "authority": authority,
        "schedule_row": row,
        "raw_output": b"{}",
        "output_tokens": 2,
        "input_tokens": 10,
        "load_plus_generation_wall_ns": 20,
        "peak_rss_bytes": 30,
        "network_log_sha256": "b" * 64,
        "file_access_log_sha256": "c" * 64,
        "observation_sha256": "d" * 64,
        "observation_identity": "e" * 64,
        "runner_sha256": "f" * 64,
        "prompt_sha256": "1" * 64,
        "batch_sha256": "2" * 64,
        "candidate": "pastila-editor-core-v1.1-experimental",
    }
    receipt = build_execution_receipt(**kwargs)
    assert receipt["promotion_effect"] is False
    for key, bad in (("output_tokens", 6269), ("input_tokens", 1925), ("load_plus_generation_wall_ns", 600_000_000_001), ("peak_rss_bytes", 16_106_127_361)):
        changed = {**kwargs, key: bad}
        with pytest.raises(QualificationAuthorityError):
            build_execution_receipt(**changed)


def test_blind_packet_contains_alias_not_candidate_identity() -> None:
    case = corpus()["cases"][0]
    raw = canonical_json_bytes(response(case))
    packet = build_blind_packet(authority={"qualification_generation_identity": "a" * 64}, case=case, alias="CANDIDATE-A", raw_output=raw, assertion={"assertion_id": "x"}, rubric={})
    encoded = canonical_json_bytes(packet)
    assert packet["candidate_alias"] == "CANDIDATE-A"
    assert b"experimental_core" not in encoded and b"v1.1" not in encoded and b"v1.2" not in encoded


def test_atomic_publication_rejects_collision(tmp_path: Path) -> None:
    target = tmp_path / "receipt.json"
    atomic_publish(target, b"one")
    assert target.read_bytes() == b"one"
    with pytest.raises(QualificationAuthorityError):
        atomic_publish(target, b"two")


def test_launcher_has_one_network_namespace_and_frozen_boundary() -> None:
    launcher = (ROOT / "scripts/run_production_core_candidate_qualification_v1.sh").read_text("utf-8")
    runner = (ROOT / "src/pastila_scout/production_core_candidate_qualification_runner_v1.py").read_text("utf-8")
    assert launcher.count("unshare --mount --net --pid --ipc --uts --fork") == 1
    assert "curl " not in launcher and "wget " not in launcher
    assert "env -i" in launcher and "mount -o remount,bind,ro" in launcher
    assert "fix_mistral_regex=True" in runner
    assert "do_sample=False" in runner and "max_new_tokens=MAX_OUTPUT" in runner
    assert "requests" not in runner and "httpx" not in runner and "socket" not in runner
    orchestrator = (ROOT / "scripts/execute_production_core_candidate_qualification_v1.py").read_text("utf-8")
    assert "materialize_batches(" in orchestrator
    assert orchestrator.count("_run_launcher(command, launcher_bytes)") == 1
    assert "tenacity" not in orchestrator and "while attempt" not in orchestrator


def test_isolation_boundary_executes_with_no_network_or_host_pid_namespace() -> None:
    fixture = ROOT / "tests/fixtures/production_core_candidate_qualification_isolation_v1.sh"
    wsl_path = "/mnt/c/pf9/tests/fixtures/production_core_candidate_qualification_isolation_v1.sh"
    assert fixture.is_file()
    subprocess.run(
        ["wsl.exe", "-d", "Ubuntu-24.04", "-u", "root", "--", "bash", wsl_path],
        check=True,
        timeout=10,
    )


def test_watchdog_and_open_descriptor_snapshot_negative_paths_execute() -> None:
    subprocess.run(
        ["wsl.exe", "-d", "Ubuntu-24.04", "--", "bash", "/mnt/c/pf9/tests/fixtures/production_core_candidate_qualification_watchdog_v1.sh"],
        check=True,
        timeout=5,
    )


def test_consumed_attempt_recovery_is_terminal_and_never_retries(tmp_path: Path) -> None:
    module = execution_module()
    generation = "a" * 64
    core = {
        "schema": "pastila-production-core-comparative-execution-attempt",
        "schema_version": 1,
        "qualification_generation_identity": generation,
        "alias_secret_commitment": "b" * 64,
        "attempt_ordinal": 1,
        "retry_or_redraw_authorized": False,
        "status": "CONSUMED_BEFORE_EXECUTION",
    }
    attempt = {**core, "attempt_identity": hashlib.sha256(canonical_json_bytes(core)).hexdigest()}
    (tmp_path / "attempt.json").write_bytes(canonical_json_bytes(attempt))
    assert module._recover_unclosed_attempt(tmp_path, generation) is True
    failure = json.loads((tmp_path / "terminal-failure.json").read_bytes())
    assert failure["failure_class"] == "RECOVERED_CONSUMED_ATTEMPT_WITHOUT_TERMINAL_RECORD"
    assert failure["retry_or_redraw_authorized"] is False


def test_production_cli_recovers_before_mutable_authority_resolution(tmp_path: Path) -> None:
    plan = json.loads(
        (ROOT / "docs/artifacts/production-core-comparative-qualification-generation-v1.json").read_bytes()
    )
    generation = plan["qualification_generation_identity"]
    output = tmp_path / "output"
    output.mkdir()
    core = {
        "schema": "pastila-production-core-comparative-execution-attempt",
        "schema_version": 1,
        "qualification_generation_identity": generation,
        "alias_secret_commitment": plan["alias_secret_commitment"],
        "attempt_ordinal": 1,
        "retry_or_redraw_authorized": False,
        "status": "CONSUMED_BEFORE_EXECUTION",
    }
    attempt = {**core, "attempt_identity": hashlib.sha256(canonical_json_bytes(core)).hexdigest()}
    (output / "attempt.json").write_bytes(canonical_json_bytes(attempt))
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/launch_production_core_candidate_qualification_v1.py"),
            "--resolution", str(tmp_path / "missing-resolution.json"),
            "--secret", str(tmp_path / "missing-secret.json"),
            "--output", str(output),
            "--adjudicator-a-export", str(tmp_path / "missing-a"),
            "--adjudicator-b-export", str(tmp_path / "missing-b"),
        ],
        cwd=ROOT,
        check=False,
    )
    assert completed.returncode == 1
    failure = json.loads((output / "terminal-failure.json").read_bytes())
    assert failure["failure_class"] == "RECOVERED_CONSUMED_ATTEMPT_WITHOUT_TERMINAL_RECORD"


def test_windows_to_wsl_object_identity_argument_transport_is_executable() -> None:
    module = execution_module()
    target = ROOT / "docs/artifacts/production-core-candidate-object-manifest-v1.json"
    wsl_target = module._wsl(target)
    helper = ROOT / "scripts/resolve_production_core_object_identity_v1.sh"
    identity = module._wsl_object_identity(wsl_target, helper.read_bytes())
    assert identity.startswith(f"{wsl_target}|")
    device_inode = identity.rstrip().rsplit("|", 1)[1]
    device, inode = device_inode.split(":", 1)
    assert device.isdigit() and inode.isdigit()


def test_verified_helper_and_launcher_bytes_cannot_be_reopened_or_substituted(tmp_path: Path) -> None:
    module = execution_module()
    helper = tmp_path / "helper.sh"
    helper.write_bytes(b"verified-helper")
    helper_bytes = module._read_pinned_source(
        helper, hashlib.sha256(b"verified-helper").hexdigest()
    )
    helper.write_bytes(b"substituted-helper")
    with patch.object(module.subprocess, "run") as called:
        called.return_value.stdout = b"/object|1:2\n"
        assert module._wsl_object_identity("/object", helper_bytes) == "/object|1:2\n"
        assert called.call_args.kwargs["input"] == b"verified-helper"

    launcher = tmp_path / "launcher.sh"
    launcher.write_bytes(b"verified-launcher")
    launcher_bytes = module._read_pinned_source(
        launcher, hashlib.sha256(b"verified-launcher").hexdigest()
    )
    launcher.write_bytes(b"substituted-launcher")
    with patch.object(module.subprocess, "run") as called:
        module._run_launcher(["wsl.exe"], launcher_bytes)
        assert called.call_args.kwargs["input"] == b"verified-launcher"


def test_pinned_source_reader_rejects_substitution(tmp_path: Path) -> None:
    module = execution_module()
    source = tmp_path / "source.sh"
    source.write_bytes(b"substituted")
    with pytest.raises(SystemExit, match="byte mismatch"):
        module._read_pinned_source(source, hashlib.sha256(b"expected").hexdigest())


def test_pinned_entry_rejects_executor_substitution_before_execution(tmp_path: Path) -> None:
    module = entry_module()
    executor = tmp_path / "executor.py"
    executor.write_bytes(b"substituted")
    module.EXECUTOR = executor
    module.EXPECTED_EXECUTOR_SHA256 = hashlib.sha256(b"expected").hexdigest()
    with pytest.raises(SystemExit, match="Python authority byte mismatch"):
        module._read_pinned(executor, module.EXPECTED_EXECUTOR_SHA256)


def test_executor_rejects_direct_unpinned_entry() -> None:
    source = (ROOT / "scripts/execute_production_core_candidate_qualification_v1.py").read_text("utf-8")
    assert 'globals().get("PINNED_ENTRY_EXECUTOR_SHA256")' in source


def test_pinned_core_ignores_ambient_envelope_module_substitution() -> None:
    module = entry_module()
    fake = type(sys)("pastila_scout.production_core_technical_output_envelope_v1")
    fake.canonical_response_bytes = lambda _value: b"forged"
    sys.modules[fake.__name__] = fake
    loaded = module._load_core()
    valid = {
        "schema": "pastila-core-v2-structured-qualification-response",
        "schema_version": 1,
        "case_id": "case-1",
        "request_identity": "sha256:" + "0" * 64,
        "output_type": "FACTUAL",
        "outcome": "ABSTAIN",
        "text": None,
        "claim_bindings": [],
        "abstention_code": "INSUFFICIENT_AUTHORITY",
    }
    assert loaded.canonical_response_bytes(valid) != b"forged"


def test_sigterm_after_attempt_consumption_publishes_terminal_failure() -> None:
    subprocess.run(
        ["wsl.exe", "-d", "Ubuntu-24.04", "--", "bash", "/mnt/c/pf9/tests/fixtures/production_core_candidate_qualification_terminal_v1.sh"],
        check=True,
        timeout=5,
    )


def test_generated_public_authority_has_no_secret_or_execution_claim() -> None:
    plan = json.loads((ROOT / "docs/artifacts/production-core-comparative-qualification-generation-v1.json").read_bytes())
    qualification = json.loads((ROOT / "docs/artifacts/production-core-candidate-qualification-mechanism-v1.json").read_bytes())
    assert plan["matrix"] == {"materializations": 2, "repetitions": 3, "cases": 200, "candidates": 2, "rows": 2400}
    assert plan["alias_mapping_public"] is False
    assert "aliases" not in plan and plan["candidate_execution_performed"] is False
    assert qualification["synthetic_only"] is True
    assert qualification["candidate_models_loaded_or_executed"] is False
    assert plan["clean_materialization_authority"] == {
        "A": {"accepted_calibration_receipts": ["bcd03f8f63d278b80fabea4db24e55a5b7f65007a185cfcfea1398c20e78b069", "aeb3fd538b2c00c6b2acaa10ac94d912b6497140f6ead7c6f79d1c3ad01ed887"], "provenance_identity": "21782e3b5ed3a1643fcf376c1010e23a09f18986351a83115668908c5cf88cfc"},
        "B": {"accepted_calibration_receipts": ["30a3b8581ecc9c0cdfefbee66764959126023528d8d1bb95bd77bf781c4bcd4d", "46570ab41f247d782f1d7ac9c24ee0ae5332d56e28b5f18001b70f253f12995f"], "provenance_identity": "240a920deaae1127ab380b05238cd152dd63b9c36b60d6c9f21219e5be373f75"},
    }


def test_terminal_authority_rejects_fully_rebound_generation() -> None:
    names = (
        "production-core-candidate-object-manifest-v1.json",
        "production-core-comparative-qualification-generation-v1.json",
        "production-core-candidate-qualification-mechanism-v1.json",
    )
    artifacts = {name: (ROOT / "docs/artifacts" / name).read_bytes() for name in names}
    assert validate_terminal_candidate_qualification_authority(artifacts) == json.loads(artifacts[names[1]])["qualification_generation_identity"]
    rebound = dict(artifacts)
    changed = json.loads(rebound[names[1]])
    changed["alias_secret_commitment"] = "0" * 64
    core = dict(changed); core.pop("qualification_generation_identity")
    changed["qualification_generation_identity"] = commitment(core)
    rebound[names[1]] = json.dumps(changed, ensure_ascii=False, indent=2).encode() + b"\n"
    with pytest.raises(ValueError):
        validate_terminal_candidate_qualification_authority(rebound)
