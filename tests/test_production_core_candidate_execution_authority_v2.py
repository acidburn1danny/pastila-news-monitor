import copy
import hashlib
import json
import os
import runpy
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from pastila_scout.production_core_candidate_execution_authority_v2 import (
    ExecutionAuthorityError,
    build_attempt,
    build_terminal_failure,
    canonical,
    identity,
    materialize_batches,
    result_status,
    validate_attempt,
    validate_boundary_logs,
    validate_case_receipt,
    validate_completion,
    validate_observation,
    validate_preflight,
    validate_terminal_failure,
)

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"


def load(name):
    return json.loads((ART / name).read_bytes())


def authorities():
    return (
        load("production-core-comparative-qualification-generation-v2.json"),
        load("production-core-candidate-request-manifest-v2.json"),
        load("production-core-candidate-object-manifest-v2.json"),
        load("production-core-candidate-generation-qualification-v2.json"),
    )


def synthetic_secret():
    value = {
        "schema": "pastila-production-core-candidate-alias-secret",
        "schema_version": 1,
        "nonce_hex": "0" * 64,
        "aliases": {
            "CANDIDATE-A": "pastila-editor-core-v1.1-experimental",
            "CANDIDATE-B": "pastila-editor-core-v1.2-experimental",
        },
    }
    return value, hashlib.sha256(canonical(value)).hexdigest()


def synthetic_preflight():
    def materialization(label):
        expected = (
            ("rootfs", "file", "274e7d1519f05f41108413efb01d35680b88e0f4b13bb63fca9634be155980f4"),
            ("base_model", "flat-dir", "f5a9327e40390c7f0cf93962d75abbbc5ae8da1fac48e1274092ac52cf88bf39"),
            ("adapter_v1_1", "flat-dir", "0bc4bb1b83b5c1375c1e676844dea079831e7ad0b90db955fa89a2f7d65c3e47"),
            ("adapter_v1_2", "flat-dir", "22b5a7bde7194c66d895b9acab5791a8d8573df67f93704eab933666df7978a2"),
        )
        objects = [
            {
                "role": role,
                "kind": kind,
                "expected_content_identity": digest,
                "physical_identity": f"/objects/{label}/{index}|1:{index}",
                "content_identity": digest,
            }
            for index, (role, kind, digest) in enumerate(expected)
        ]
        value = {
            "schema": "pastila-production-core-observed-materialization-provenance-v2",
            "materialization": label,
            "objects": objects,
        }
        return {**value, "materialization_provenance_identity": identity(value)}

    mechanism = load("production-core-candidate-execution-authority-v2.json")
    core = {
        "schema": "pastila-production-core-comparative-execution-preflight-v2",
        "schema_version": 2,
        "execution_authority_identity": mechanism["execution_authority_identity"],
        "qualification_generation_identity": authorities()[0][
            "qualification_generation_identity"
        ],
        "request_manifest_identity": authorities()[1]["request_manifest_identity"],
        "candidate_object_manifest_identity": authorities()[2]["manifest_identity"],
        "qualification_identity": authorities()[3]["qualification_identity"],
        "source_sha256": mechanism["source_sha256"],
        "system_prompt_sha256": {
            "pastila-editor-core-v1.1-experimental": "9b25e239fc227252906fecab393a42a82eca4baa643ceed28177d3c5054e93fc",
            "pastila-editor-core-v1.2-experimental": "111bc2734343c67aab4e1a04003199b98d4955fe9579e445cd7b5d6805a9da17",
        },
        "unicode_authority_sha256": [
            "20aab5eca3842c7a27cc6756d74488a4a5f744c8dca2948ec1128f26a60d1f79",
            "0aef84034ee1789eb71021454fac384e83080b05922272d63cf297f4bf08150e",
            "4579c185bd45feac761de590d874aca71788e339b35179318a4c43412fd4f9e4",
        ],
        "alias_secret_commitment": "08ac67b1516e72080eacd49fd08dff6adbe1c0f80c2b0313bc24f4052955a27b",
        "alias_secret_sha256": "08ac67b1516e72080eacd49fd08dff6adbe1c0f80c2b0313bc24f4052955a27b",
        "observed_materializations": {
            "A": materialization("A"),
            "B": materialization("B"),
        },
        "batch_count": 12,
        "matrix_rows": 2400,
        "attempt_consumed": False,
        "candidate_execution_performed": False,
    }
    return {**core, "preflight_identity": identity(core)}


def test_preflight_is_exact_and_has_no_filesystem_effect(tmp_path):
    before = tuple(tmp_path.iterdir())
    rows = validate_preflight(*authorities())
    assert len(rows) == 2400
    assert tuple(tmp_path.iterdir()) == before
    requests = {row["case_id"]: row for row in authorities()[1]["requests"]}
    assert all(
        row["candidate_visible_request"]
        == requests[row["case_id"]]["candidate_visible_request"]
        and row["candidate_visible_request_sha256"]
        == requests[row["case_id"]]["candidate_visible_request_sha256"]
        for row in rows
    )


@pytest.mark.parametrize("slot", range(4))
def test_every_stale_or_rebound_terminal_authority_fails(slot):
    values = [copy.deepcopy(value) for value in authorities()]
    identity_fields = (
        "qualification_generation_identity",
        "request_manifest_identity",
        "manifest_identity",
        "qualification_identity",
    )
    values[slot][identity_fields[slot]] = "0" * 64
    with pytest.raises(ExecutionAuthorityError):
        validate_preflight(*values)


def test_request_byte_substitution_fails_even_when_outer_identity_is_redrawn():
    generation, requests, candidates, qualification = authorities()
    requests["requests"][0]["candidate_visible_request"] += "x"
    core = dict(requests)
    core.pop("request_manifest_identity")
    requests["request_manifest_identity"] = identity(core)
    with pytest.raises(ExecutionAuthorityError):
        validate_preflight(generation, requests, candidates, qualification)


def test_batches_are_exact_schedule_snapshots_and_alias_substitution_fails():
    rows = validate_preflight(*authorities())
    secret, commitment = synthetic_secret()
    batches = materialize_batches(rows, secret, commitment)
    assert len(batches) == 12
    assert sum(len(batch["batch"]) for batch in batches) == 2400
    assert all(
        hashlib.sha256(row["prompt"].encode()).hexdigest() == row["prompt_sha256"]
        for batch in batches
        for row in batch["batch"]
    )
    changed = copy.deepcopy(secret)
    changed["aliases"]["CANDIDATE-A"] = changed["aliases"]["CANDIDATE-B"]
    with pytest.raises(ExecutionAuthorityError):
        materialize_batches(rows, changed, commitment)


def test_attempt_and_terminal_failure_are_closed_and_non_promotional():
    authority = load("production-core-candidate-execution-authority-v2.json")[
        "execution_authority_identity"
    ]
    attempt = build_attempt(authority, synthetic_preflight())
    validate_attempt(attempt, authority)
    evidence_schema = json.loads(
        (
            ROOT
            / "docs/schemas/production-core-candidate-execution-evidence-v2.schema.json"
        ).read_bytes()
    )
    Draft202012Validator(evidence_schema).validate(attempt["preflight"])
    Draft202012Validator(evidence_schema).validate(attempt)
    partial = [{"path": "attempt.json", "sha256": "b" * 64}]
    failure = build_terminal_failure(
        attempt, 17, "SYNTHETIC_FAILURE", partial_artifacts=partial
    )
    validate_terminal_failure(failure, attempt, partial)
    schema = json.loads(
        (
            ROOT
            / "docs/schemas/production-core-candidate-execution-evidence-v2.schema.json"
        ).read_bytes()
    )
    Draft202012Validator(schema).validate(failure)
    assert attempt["attempt_ordinal"] == 1
    assert attempt["retry_or_redraw_authorized"] is False
    assert failure["completed_rows"] == 17
    assert failure["retry_or_redraw_authorized"] is False
    assert failure["promotion_effect"] is False
    changed = copy.deepcopy(attempt)
    changed["attempt_ordinal"] = 2
    with pytest.raises(ExecutionAuthorityError):
        validate_attempt(changed, authority)


def test_execution_path_contains_no_adjudication_or_stale_contract_authority():
    paths = (
        ROOT / "scripts/execute_production_core_candidate_qualification_v2.py",
        ROOT / "scripts/launch_production_core_candidate_qualification_v2.py",
        ROOT / "scripts/run_production_core_candidate_qualification_v2.sh",
        ROOT / "src/pastila_scout/production_core_candidate_execution_authority_v2.py",
        ROOT / "src/pastila_scout/production_core_candidate_qualification_runner_v2.py",
    )
    forbidden = (
        "replacement_authority",
        "ordinal 8",
        "ordinal8",
        "production-core-qualification-corpus-v1.json",
        "production-core-qualification-assertions-v1.json",
        "production-core-qualification-rubric-v1.json",
        "production-core-candidate-qualification-mechanism-v1.json",
        "build_blind_packet",
        "adjudicator-a-export",
        "adjudicator-b-export",
    )
    combined = "\n".join(path.read_text("utf-8") for path in paths)
    assert not any(marker in combined for marker in forbidden)


def test_symlink_entry_inputs_are_rejected_before_attempt_construction():
    source = (
        ROOT / "scripts/execute_production_core_candidate_qualification_v2.py"
    ).read_text("utf-8")
    assert "reject_reparse_chain" in source
    assert source.index("reject_reparse_chain(x)") < source.index("build_attempt(")


def test_qualification_artifact_self_binds_sources_and_zero_execution():
    value = load("production-core-candidate-execution-authority-v2.json")
    core = dict(value)
    recorded = core.pop("execution_authority_identity")
    assert recorded == identity(core)
    for path, expected in value["source_sha256"].items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == expected
    assert value["candidate_execution_performed"] is False
    assert value["adjudication_performed"] is False
    assert value["promotion_effect"] is False


def test_execution_authority_schema_closes_nested_keys_and_constants():
    value = load("production-core-candidate-execution-authority-v2.json")
    schema = json.loads(
        (
            ROOT
            / "docs/schemas/production-core-candidate-execution-authority-v2.schema.json"
        ).read_bytes()
    )
    Draft202012Validator(schema).validate(value)
    for path in (("authority_identities", "extra"), ("source_sha256", "extra")):
        changed = copy.deepcopy(value)
        changed[path[0]][path[1]] = "0" * 64
        assert list(Draft202012Validator(schema).iter_errors(changed))


def test_invalid_output_is_preserved_as_case_failure_and_next_case_continues():
    calls = []

    def validator(raw, _case, _authority):
        calls.append(raw)
        if raw == b"invalid":
            raise ValueError("synthetic")

    assert (
        result_status(b"invalid", validator, {}, object(), "EXECUTION_ENVELOPE_PASS")
        == "FAIL_CLOSED_INVALID_OUTPUT"
    )
    assert (
        result_status(b"valid", validator, {}, object(), "EXECUTION_ENVELOPE_PASS")
        == "STRUCTURALLY_VALID_PENDING_ADJUDICATION"
    )
    assert calls == [b"invalid", b"valid"]
    assert (
        result_status(
            b"valid", validator, {}, object(), "EXECUTION_ENVELOPE_FAIL_CLOSED"
        )
        == "FAIL_CLOSED_INVALID_OUTPUT"
    )


def test_boundary_and_observation_validators_reject_extra_negative_and_substitution():
    network = {
        "schema": "pastila-production-core-network-boundary-log",
        "schema_version": 1,
        "policy": "DENY_ALL_NEW_CHILD_NAMESPACE",
        "observed_interfaces": ["lo"],
        "observed_ipv4_route_rows": 0,
        "namespace_init_pid": 1,
        "network_namespace_differs_from_parent": True,
        "pid_namespace_differs_from_parent": True,
        "promotion_effect": False,
    }
    file_boundary = {
        "schema": "pastila-production-core-file-boundary-log",
        "schema_version": 1,
        "model_mount_read_only": True,
        "adapter_mount_read_only": True,
        "candidate_private_snapshots": True,
        "authority_inputs_from_open_descriptors": True,
        "private_rootfs_from_open_descriptor": True,
        "mountinfo_sha256": "a" * 64,
        "host_pid_namespace_reachable": False,
    }
    validate_boundary_logs(network, file_boundary)
    changed = dict(file_boundary)
    changed["extra"] = True
    with pytest.raises(ExecutionAuthorityError):
        validate_boundary_logs(network, changed)
    raw = b"x"
    expected = {
        key: "a" * 64
        for key in (
            "rootfs_sha256",
            "base_manifest_sha256",
            "adapter_manifest_sha256",
            "system_prompt_sha256",
            "batch_sha256",
            "runner_sha256",
        )
    }
    expected.update(
        qualification_generation_identity=authorities()[0][
            "qualification_generation_identity"
        ],
        candidate="candidate",
        case_id="case",
        request_identity="sha256:" + "b" * 64,
    )
    core = {
        "schema": "pastila-production-core-frozen-runner-observation",
        "schema_version": 2,
        "qualification_generation_identity": expected[
            "qualification_generation_identity"
        ],
        "candidate": expected["candidate"],
        "rootfs_sha256": expected["rootfs_sha256"],
        "base_manifest_sha256": expected["base_manifest_sha256"],
        "adapter_manifest_sha256": expected["adapter_manifest_sha256"],
        "system_prompt_sha256": expected["system_prompt_sha256"],
        "batch_sha256": expected["batch_sha256"],
        "runner_sha256": expected["runner_sha256"],
        "case_id": expected["case_id"],
        "request_identity": expected["request_identity"],
        "input_tokens": 1,
        "output_tokens": 1,
        "load_wall_ns": 1,
        "generation_wall_ns": 1,
        "peak_rss_bytes": 1,
        "raw_output_sha256": hashlib.sha256(raw).hexdigest(),
        "runtime_versions": {
            "bitsandbytes": "0.50.1",
            "peft": "0.20.0",
            "torch": "2.13.0+cu130",
            "transformers": "5.15.0",
        },
        "terminal_eos": True,
        "candidate_output_status": "EXECUTION_ENVELOPE_PASS",
    }
    observation = {**core, "observation_identity": identity(core)}
    assert validate_observation(observation, raw, expected) == "EXECUTION_ENVELOPE_PASS"
    for field, value in (
        ("peak_rss_bytes", -1),
        ("generation_wall_ns", -1),
        ("extra", 1),
    ):
        changed = dict(observation)
        changed[field] = value
        with pytest.raises(ExecutionAuthorityError):
            validate_observation(changed, raw, expected)
    no_eos_core = {
        **core,
        "terminal_eos": False,
        "candidate_output_status": "EXECUTION_ENVELOPE_FAIL_CLOSED",
    }
    no_eos = {**no_eos_core, "observation_identity": identity(no_eos_core)}
    assert (
        validate_observation(no_eos, raw, expected) == "EXECUTION_ENVELOPE_FAIL_CLOSED"
    )
    dishonest_core = {
        **no_eos_core,
        "candidate_output_status": "EXECUTION_ENVELOPE_PASS",
    }
    dishonest = {**dishonest_core, "observation_identity": identity(dishonest_core)}
    with pytest.raises(ExecutionAuthorityError):
        validate_observation(dishonest, raw, expected)


def test_case_receipt_and_completion_are_strictly_self_bound():
    authority = load("production-core-candidate-execution-authority-v2.json")[
        "execution_authority_identity"
    ]
    attempt = build_attempt(authority, synthetic_preflight())
    expected_row = validate_preflight(*authorities())[0]
    receipt_core = {
        "schema": "pastila-production-core-case-execution-receipt-v2",
        "schema_version": 2,
        "execution_authority_identity": authority,
        "attempt_identity": attempt["attempt_identity"],
        "qualification_generation_identity": authorities()[0][
            "qualification_generation_identity"
        ],
        "global_ordinal": 1,
        "materialization": expected_row["materialization"],
        "repetition": expected_row["repetition"],
        "candidate_alias": expected_row["candidate_alias"],
        "case_id": expected_row["case_id"],
        "request_identity": expected_row["request_identity"],
        "candidate_visible_request_sha256": expected_row[
            "candidate_visible_request_sha256"
        ],
        "raw_output_sha256": "d" * 64,
        "observation_identity": "e" * 64,
        "structural_status": "FAIL_CLOSED_INVALID_OUTPUT",
        "retry_or_redraw": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }
    receipt = {**receipt_core, "receipt_identity": identity(receipt_core)}
    assert validate_case_receipt(receipt, attempt, expected_row) == 1
    evidence_schema = json.loads(
        (
            ROOT
            / "docs/schemas/production-core-candidate-execution-evidence-v2.schema.json"
        ).read_bytes()
    )
    Draft202012Validator(evidence_schema).validate(receipt)
    rows = validate_preflight(*authorities())
    receipts = {}
    paths = {"attempt.json"}
    for row in rows:
        directory = (
            f"materialization-{row['materialization']}/"
            f"repetition-{row['repetition']}/{row['candidate_alias']}"
        )
        stem = f"{row['case_id']}.{row['request_identity'].removeprefix('sha256:')}"
        path = f"{directory}/{stem}.receipt.json"
        item_core = {
            **receipt_core,
            "global_ordinal": row["global_ordinal"],
            "materialization": row["materialization"],
            "repetition": row["repetition"],
            "candidate_alias": row["candidate_alias"],
            "case_id": row["case_id"],
            "request_identity": row["request_identity"],
            "candidate_visible_request_sha256": row[
                "candidate_visible_request_sha256"
            ],
        }
        receipts[path] = {**item_core, "receipt_identity": identity(item_core)}
        paths.update(
            {
                path,
                f"{directory}/results/{stem}.raw",
                f"{directory}/results/{stem}.observation.json",
                f"{directory}/batch.json",
                f"{directory}/system-prompt.txt",
                f"{directory}/results/heartbeat.json",
                f"{directory}/results/network-boundary.json",
                f"{directory}/results/file-boundary.json",
            }
        )
    inventory = [{"path": path, "sha256": "f" * 64} for path in sorted(paths)]
    completion_core = {
        "schema": "pastila-production-core-comparative-execution-completion-v2",
        "schema_version": 2,
        "attempt_identity": attempt["attempt_identity"],
        "execution_authority_identity": authority,
        "qualification_generation_identity": authorities()[0][
            "qualification_generation_identity"
        ],
        "completed_rows": 2400,
        "artifact_inventory": inventory,
        "artifact_root": identity(inventory),
        "retry_or_redraw": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }
    completion = {**completion_core, "completion_identity": identity(completion_core)}
    # Producer-declared receipts and inventory are insufficient: completion
    # validation accepts only the byte snapshots read back from the locked
    # artifact tree.
    with pytest.raises(ExecutionAuthorityError):
        validate_completion(completion, attempt, rows, {})
    Draft202012Validator(evidence_schema).validate(completion)
    changed = copy.deepcopy(completion)
    changed["artifact_inventory"][0]["path"] = "../escape"
    changed_core = dict(changed)
    changed_core.pop("completion_identity")
    changed["artifact_root"] = identity(changed["artifact_inventory"])
    changed_core = dict(changed)
    changed_core.pop("completion_identity")
    changed["completion_identity"] = identity(changed_core)
    with pytest.raises(ExecutionAuthorityError):
        validate_completion(changed, attempt, rows, {})


@pytest.mark.skipif(os.name != "nt", reason="qualification profile is Windows/WSL")
def test_output_directory_handle_blocks_post_snapshot_rename(tmp_path):
    namespace = runpy.run_path(
        str(ROOT / "scripts/execute_production_core_candidate_qualification_v2.py")
    )
    directory = tmp_path / "locked"
    directory.mkdir()
    handle = namespace["lock_directory"](directory)
    try:
        with pytest.raises(PermissionError):
            directory.rename(tmp_path / "substituted")
    finally:
        namespace["close_directory"](handle)
    directory.rename(tmp_path / "released")


@pytest.mark.skipif(shutil.which("wsl.exe") is None, reason="WSL profile unavailable")
def test_object_authority_helper_detects_post_snapshot_content_change(tmp_path):
    directory = tmp_path / "object"
    directory.mkdir()
    target = directory / "a.bin"
    target.write_bytes(b"first")
    linux = "/mnt/" + directory.drive[0].lower() + "/" + "/".join(directory.parts[1:])
    helper = (
        ROOT / "scripts/resolve_production_core_object_authority_v2.sh"
    ).read_bytes()
    command = [
        "wsl.exe",
        "-d",
        "Ubuntu-24.04",
        "--",
        "bash",
        "--noprofile",
        "--norc",
        "-s",
        "--",
        linux,
        "flat-dir",
    ]
    first = json.loads(
        subprocess.run(command, input=helper, check=True, capture_output=True).stdout
    )
    target.write_bytes(b"second")
    second = json.loads(
        subprocess.run(command, input=helper, check=True, capture_output=True).stdout
    )
    assert first["physical_identity"] == second["physical_identity"]
    assert first["content_identity"] != second["content_identity"]


def test_entry_executes_terminal_hash_validation_before_help():
    completed = subprocess.run(
        [
            sys.executable,
            str(ROOT / "scripts/launch_production_core_candidate_qualification_v2.py"),
            "--help",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert "--unicode-authority-root" in completed.stdout


def test_recovery_terminalizes_exact_consumed_attempt_without_launch(
    tmp_path, monkeypatch
):
    mechanism = load("production-core-candidate-execution-authority-v2.json")
    output = tmp_path / "output"
    output.mkdir()
    attempt = build_attempt(
        mechanism["execution_authority_identity"], synthetic_preflight()
    )
    (output / "attempt.json").write_bytes(canonical(attempt))
    partial_dir = output / "partial"
    partial_dir.mkdir()
    (partial_dir / "raw.bin").write_bytes(b"terminal evidence")
    expected_row = validate_preflight(*authorities())[0]
    receipt_core = {
        "schema": "pastila-production-core-case-execution-receipt-v2",
        "schema_version": 2,
        "execution_authority_identity": mechanism["execution_authority_identity"],
        "attempt_identity": attempt["attempt_identity"],
        "qualification_generation_identity": authorities()[0][
            "qualification_generation_identity"
        ],
        "global_ordinal": 1,
        "materialization": expected_row["materialization"],
        "repetition": expected_row["repetition"],
        "candidate_alias": expected_row["candidate_alias"],
        "case_id": expected_row["case_id"],
        "request_identity": expected_row["request_identity"],
        "candidate_visible_request_sha256": expected_row[
            "candidate_visible_request_sha256"
        ],
        "raw_output_sha256": "d" * 64,
        "observation_identity": "e" * 64,
        "structural_status": "FAIL_CLOSED_INVALID_OUTPUT",
        "retry_or_redraw": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }
    receipt = {**receipt_core, "receipt_identity": identity(receipt_core)}
    (partial_dir / "one.receipt.json").write_bytes(canonical(receipt))
    placeholders = []
    for name in ("resolution.json", "secret.json"):
        path = tmp_path / name
        path.write_text("{}", encoding="utf-8")
        placeholders.append(path)
    unicode_root = tmp_path / "unicode"
    unicode_root.mkdir()
    namespace = runpy.run_path(
        str(ROOT / "scripts/execute_production_core_candidate_qualification_v2.py"),
        init_globals={
            "PINNED_ENTRY_EXECUTOR_SHA256": mechanism["source_sha256"][
                "scripts/execute_production_core_candidate_qualification_v2.py"
            ],
            "PINNED_EXECUTION_MECHANISM": mechanism,
            "PINNED_TERMINAL_VALIDATOR": lambda snapshots: None,
            "GENERATION_IDENTITY": authorities()[0][
                "qualification_generation_identity"
            ],
            "MATRIX_ROWS": 2400,
            "build_attempt": build_attempt,
            "build_terminal_failure": build_terminal_failure,
            "canonical": canonical,
            "identity": identity,
            "materialize_batches": materialize_batches,
            "result_status": result_status,
            "validate_attempt": validate_attempt,
            "validate_case_receipt": validate_case_receipt,
            "validate_terminal_failure": validate_terminal_failure,
            "validate_preflight": validate_preflight,
        },
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "executor",
            "--resolution",
            str(placeholders[0]),
            "--secret",
            str(placeholders[1]),
            "--unicode-authority-root",
            str(unicode_root),
            "--output",
            str(output),
        ],
    )
    assert namespace["main"]() == 1
    failure = json.loads((output / "terminal-failure.json").read_bytes())
    assert (
        failure["failure_class"] == "RECOVERED_CONSUMED_ATTEMPT_WITHOUT_TERMINAL_RECORD"
    )
    assert failure["attempt_identity"] == attempt["attempt_identity"]
    assert failure["partial_artifact_count"] == 3
    assert failure["completed_rows"] == 1
    assert failure["retry_or_redraw_authorized"] is False
