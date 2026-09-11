"""Execute only the accepted Core V2 comparative generation."""

from __future__ import annotations

import argparse
import atexit
import ctypes
import hashlib
import json
import os
import signal
import shutil
import stat
import subprocess
from pathlib import Path, PureWindowsPath

if "PINNED_ENTRY_EXECUTOR_SHA256" not in globals():
    from pastila_scout.production_core_candidate_execution_authority_v3 import (
        GENERATION_IDENTITY,
        MATRIX_ROWS,
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
    from pastila_scout.production_core_semantic_authority_v2 import (
        SENTENCE_PROPERTY_SHA256,
        SENTENCE_TEST_SHA256,
        UAX29_SHA256,
        Unicode16SentenceAuthority,
        validate_response_v2,
    )
    from pastila_scout.production_core_checkpoint_resume_v6 import (
        build_receipt as build_checkpoint_receipt,
        validate_chain as validate_checkpoint_chain,
        write_receipt as write_checkpoint_receipt,
    )

    PINNED_UNICODE_AUTHORITY_SHA256 = (
        SENTENCE_PROPERTY_SHA256,
        SENTENCE_TEST_SHA256,
        UAX29_SHA256,
    )
ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"
HELPER = ROOT / "scripts" / "resolve_production_core_object_authority_v2.sh"
RUNNER = (
    ROOT
    / "src"
    / "pastila_scout"
    / "production_core_candidate_qualification_runner_v3.py"
)
LAUNCHER = ROOT / "scripts" / "run_production_core_candidate_qualification_v3.sh"
NAMES = (
    "production-core-successor-comparative-qualification-generation-v5.json",
    "production-core-candidate-request-manifest-v2.json",
    "production-core-successor-candidate-object-manifest-v5.json",
    "production-core-successor-candidate-generation-qualification-v5.json",
)
PROMPTS = {
    "pastila-editor-core-v1.1-json-successor-v2": ROOT
    / ".experimental-0-3-editor-core-v1-architecture-prompt-first-training-plan-v1-evidence"
    / "PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1.txt",
    "pastila-editor-core-v1.2-json-successor": ROOT
    / ".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence"
    / "PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt",
}
PROMPT_SHA256 = {
    "pastila-editor-core-v1.1-json-successor-v2": "9b25e239fc227252906fecab393a42a82eca4baa643ceed28177d3c5054e93fc",
    "pastila-editor-core-v1.2-json-successor": "111bc2734343c67aab4e1a04003199b98d4955fe9579e445cd7b5d6805a9da17",
}


def read(path):
    if path.is_symlink():
        raise SystemExit("symlink authority rejected")
    fd = os.open(
        path, os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    )
    try:
        if not stat.S_ISREG(os.fstat(fd).st_mode):
            raise SystemExit("regular file required")
        with os.fdopen(fd, "rb", closefd=False) as h:
            return h.read()
    finally:
        os.close(fd)


def obj(raw):
    value = json.loads(raw)
    if not isinstance(value, dict):
        raise SystemExit("object required")
    return value


def typed_supervisor_failure(result: Path, returncode: int) -> str:
    """Recover only a closed, durable supervisor classification."""
    path = result / "supervisor-failure.json"
    try:
        raw = read(path)
        value = obj(raw)
    except OSError, ValueError, json.JSONDecodeError, SystemExit:
        return "UNCAUGHT_AFTER_ATTEMPT_CONSUMPTION"
    expected_exit = {
        "INFERENCE_WALL_TIME_EXCEEDED": 124,
        "INVALID_HEARTBEAT_AUTHORITY": 125,
        "INVALID_FINAL_HEARTBEAT_AUTHORITY": 125,
    }
    if (
        raw != canonical(value)
        or tuple(value)
        != (
            "schema",
            "schema_version",
            "code",
            "ceiling_ns",
            "watchdog_exit_code",
            "last_sequence",
            "last_completed_count",
            "last_stage",
        )
        or value.get("schema") != "pastila-production-core-supervisor-failure"
        or value.get("schema_version") != 2
        or value.get("ceiling_ns") != 600_000_000_000
        or value.get("code") not in expected_exit
        or value.get("watchdog_exit_code") != expected_exit[value["code"]]
        or returncode != value["watchdog_exit_code"]
        or type(value.get("last_sequence")) is not int
        or not -1 <= value["last_sequence"] <= 201
        or type(value.get("last_completed_count")) is not int
        or not 0 <= value["last_completed_count"] <= 200
        or value.get("last_stage")
        not in ("INIT", "LOAD", "GENERATE", "CASE_COMPLETE", "BATCH_COMPLETE")
    ):
        return "UNCAUGHT_AFTER_ATTEMPT_CONSUMPTION"
    return str(value["code"])


def validate_inference_lifecycle(
    started_raw: bytes,
    completed_raw: bytes,
    *,
    sequence: int,
    row: dict[str, object],
    observation: dict[str, object],
) -> None:
    started, completed = obj(started_raw), obj(completed_raw)
    started_core, completed_core = dict(started), dict(completed)
    started_identity = started_core.pop("event_identity", None)
    completed_identity = completed_core.pop("event_identity", None)
    if (
        started_raw != canonical(started)
        or completed_raw != canonical(completed)
        or started_identity != identity(started_core)
        or completed_identity != identity(completed_core)
        or tuple(started)
        != (
            "schema",
            "schema_version",
            "phase",
            "sequence",
            "completed_count",
            "case_id",
            "request_identity",
            "input_tokens",
            "started_boottime_ns",
            "event_identity",
        )
        or tuple(completed)
        != (
            "schema",
            "schema_version",
            "phase",
            "sequence",
            "completed_count",
            "case_id",
            "request_identity",
            "started_event_identity",
            "generation_wall_ns",
            "output_tokens",
            "terminal_eos",
            "termination_reason",
            "event_identity",
        )
        or started.get("schema") != "pastila-production-core-inference-lifecycle-event"
        or completed.get("schema")
        != "pastila-production-core-inference-lifecycle-event"
        or started.get("schema_version") != 1
        or completed.get("schema_version") != 1
        or started.get("phase") != "STARTED"
        or completed.get("phase") != "COMPLETED"
        or started.get("sequence") != sequence
        or completed.get("sequence") != sequence
        or started.get("completed_count") != sequence - 1
        or completed.get("completed_count") != sequence
        or started.get("case_id") != row.get("case_id")
        or completed.get("case_id") != row.get("case_id")
        or started.get("request_identity") != row.get("request_identity")
        or completed.get("request_identity") != row.get("request_identity")
        or completed.get("started_event_identity") != started_identity
        or started.get("input_tokens") != observation.get("input_tokens")
        or completed.get("generation_wall_ns") != observation.get("generation_wall_ns")
        or completed.get("output_tokens") != observation.get("output_tokens")
        or completed.get("terminal_eos") != observation.get("terminal_eos")
        or completed.get("termination_reason")
        != observation.get("termination_reason")
        or type(started.get("started_boottime_ns")) is not int
        or started["started_boottime_ns"] < 0
    ):
        raise SystemExit("inference lifecycle evidence mismatch")


def atomic(path, data):
    if path.exists() or path.is_symlink():
        raise SystemExit("artifact collision")
    tmp = path.with_name("." + path.name + ".tmp")
    with tmp.open("xb") as h:
        h.write(data)
        h.flush()
        os.fsync(h.fileno())
    os.replace(tmp, path)


def reject_reparse_chain(path):
    current = Path(path).absolute()
    chain = [current, *current.parents]
    for component in chain:
        metadata = os.lstat(component)
        if stat.S_ISLNK(metadata.st_mode) or getattr(
            metadata, "st_file_attributes", 0
        ) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0):
            raise SystemExit("reparse path authority rejected")
    return current.resolve(strict=True)


def lock_directory(path):
    if os.name != "nt":
        return os.open(path, os.O_RDONLY)
    create = ctypes.windll.kernel32.CreateFileW
    create.argtypes = [
        ctypes.c_wchar_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
        ctypes.c_uint32,
        ctypes.c_uint32,
        ctypes.c_void_p,
    ]
    create.restype = ctypes.c_void_p
    handle = create(
        str(path), 0x80000000, 0x00000001 | 0x00000002, None, 3, 0x02000000, None
    )
    if handle == ctypes.c_void_p(-1).value:
        raise SystemExit("output directory lock failed")
    return handle


def close_directory(handle):
    if os.name == "nt":
        ctypes.windll.kernel32.CloseHandle(handle)
    else:
        os.close(handle)


def wsl(path):
    if path.is_symlink() or not path.exists():
        raise SystemExit("WSL path rejected")
    p = PureWindowsPath(path.absolute())
    rel = p.relative_to(p.anchor)
    if not p.drive or p.root != "\\" or any(x in {"", ".", ".."} for x in rel.parts):
        raise SystemExit("WSL path rejected")
    return f"/mnt/{p.drive[0].lower()}/" + "/".join(rel.parts)


def object_authority(path, kind, helper):
    value = obj(
        subprocess.run(
            [
                "wsl.exe",
                "-d",
                "Ubuntu-24.04",
                "--",
                "bash",
                "--noprofile",
                "--norc",
                "-s",
                "--",
                path,
                kind,
            ],
            input=helper,
            check=True,
            capture_output=True,
        ).stdout
    )
    if tuple(value) != ("physical_identity", "content_identity"):
        raise SystemExit("object authority response rejected")
    return value


def completed_receipt_count(output: Path, attempt: dict, rows: tuple) -> int:
    ordinals = []
    for path in output.rglob("*.receipt.json"):
        receipt = obj(read(path))
        if read(path) != canonical(receipt):
            raise SystemExit("noncanonical recovered receipt")
        ordinal = receipt.get("global_ordinal")
        if type(ordinal) is not int or not 1 <= ordinal <= len(rows):
            raise SystemExit("recovered receipt ordinal mismatch")
        ordinals.append(validate_case_receipt(receipt, attempt, rows[ordinal - 1]))
    ordered = sorted(ordinals)
    if ordered != list(range(1, len(ordered) + 1)):
        raise SystemExit("recovered receipt sequence mismatch")
    return len(ordered)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--resolution", type=Path, required=True)
    p.add_argument("--secret", type=Path, required=True)
    p.add_argument("--unicode-authority-root", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--preflight-only", action="store_true")
    o = p.parse_args()
    resolution_path, secret_path, unicode_root, output = (
        reject_reparse_chain(x)
        for x in (o.resolution, o.secret, o.unicode_authority_root, o.output)
    )
    directory_locks = [lock_directory(output)]

    def release_locks():
        while directory_locks:
            close_directory(directory_locks.pop())

    atexit.register(release_locks)
    snapshots = {n: read(ART / n) for n in NAMES}
    validator = globals().get("PINNED_TERMINAL_VALIDATOR")
    if not callable(validator):
        raise SystemExit("pinned validator absent")
    validator(snapshots)
    generation, requests, candidates, qualification = (obj(snapshots[n]) for n in NAMES)
    rows = validate_preflight(generation, requests, candidates, qualification)
    existing = list(output.iterdir())
    recovered_attempt = None
    if existing:
        names = {path.name for path in existing}
        if (
            "attempt.json" in names
            and "completion.json" not in names
            and "terminal-failure.json" not in names
        ):
            mechanism = globals().get("PINNED_EXECUTION_MECHANISM")
            attempt = obj(read(output / "attempt.json"))
            if not isinstance(mechanism, dict):
                raise SystemExit("mechanism absent")
            validate_attempt(attempt, str(mechanism["execution_authority_identity"]))
            recovered_attempt = attempt
        raise SystemExit("output must be empty or one recoverable attempt")
    secret = obj(read(secret_path))
    batches = materialize_batches(
        rows, secret, str(generation["alias_secret_commitment"])
    )
    unicode_authority = Unicode16SentenceAuthority.load(unicode_root)
    mechanism = globals().get("PINNED_EXECUTION_MECHANISM")
    if not isinstance(mechanism, dict):
        raise SystemExit("mechanism absent")
    sources = mechanism.get("source_sha256")
    if not isinstance(sources, dict) or globals().get(
        "PINNED_ENTRY_EXECUTOR_SHA256"
    ) != sources.get("scripts/execute_production_core_candidate_qualification_v3.py"):
        raise SystemExit("entry binding mismatch")
    source_bytes = {
        str(x.relative_to(ROOT)).replace("\\", "/"): read(x)
        for x in (HELPER, LAUNCHER, RUNNER)
    }
    if any(
        hashlib.sha256(raw).hexdigest() != sources.get(name)
        for name, raw in source_bytes.items()
    ):
        raise SystemExit("source authority mismatch")
    resolution = obj(read(resolution_path))
    mats = resolution.get("materializations")
    if (
        tuple(resolution) != ("schema", "schema_version", "materializations")
        or resolution.get("schema")
        != "pastila-production-core-local-object-resolution-v2"
        or resolution.get("schema_version") != 2
        or not isinstance(mats, dict)
        or tuple(mats) != ("A", "B")
    ):
        raise SystemExit("resolution rejected")
    helper = source_bytes[str(HELPER.relative_to(ROOT)).replace("\\", "/")]
    seen = set()
    provenance = set()
    observed_materializations = {}
    prompt_snapshots = {name: read(path) for name, path in PROMPTS.items()}
    if any(
        hashlib.sha256(prompt_snapshots[name]).hexdigest() != PROMPT_SHA256[name]
        for name in PROMPTS
    ):
        raise SystemExit("system prompt authority mismatch")
    for label in ("A", "B"):
        local = mats[label]
        adapters = local.get("adapters") if isinstance(local, dict) else None
        if (
            not isinstance(local, dict)
            or tuple(local) != ("rootfs_tar", "model", "adapters")
            or not isinstance(adapters, dict)
            or tuple(adapters) != tuple(PROMPTS)
        ):
            raise SystemExit("adapter resolution rejected")
        checks = [
            ("rootfs", str(local["rootfs_tar"]), "file", globals()["PINNED_ROOTFS_SHA256"]),
            (
                "base_model",
                str(local["model"]),
                "flat-dir",
                candidates["base_model_manifest_sha256"],
            ),
            *(
                (
                    role,
                    str(adapters[k]),
                    "flat-dir",
                    candidates["adapter_manifest_sha256"][k],
                )
                for role, k in zip(
                    ("adapter_v1_1", "adapter_v1_2"), PROMPTS, strict=True
                )
            ),
        ]
        ids = []
        observed_objects = []
        for role, path, kind, expected in checks:
            observed = object_authority(path, kind, helper)
            if observed["content_identity"] != expected:
                raise SystemExit(f"content-addressed object mismatch: {label}/{role}")
            ids.append(observed["physical_identity"])
            observed_objects.append(
                {
                    "role": role,
                    "kind": kind,
                    "expected_content_identity": expected,
                    **observed,
                }
            )
        if len(set(ids)) != len(ids) or seen.intersection(ids):
            raise SystemExit("materialization independence mismatch")
        seen.update(ids)
        provenance_core = {
            "schema": "pastila-production-core-observed-materialization-provenance-v2",
            "materialization": label,
            "objects": observed_objects,
        }
        proof = identity(provenance_core)
        if proof in provenance:
            raise SystemExit("materialization provenance mismatch")
        provenance.add(proof)
        observed_materializations[label] = {
            **provenance_core,
            "materialization_provenance_identity": proof,
        }
    pre = {
        "schema": "pastila-production-core-comparative-execution-preflight-v2",
        "schema_version": 2,
        "execution_authority_identity": mechanism["execution_authority_identity"],
        "qualification_generation_identity": GENERATION_IDENTITY,
        "request_manifest_identity": requests["request_manifest_identity"],
        "candidate_object_manifest_identity": candidates["manifest_identity"],
        "qualification_identity": qualification["qualification_identity"],
        "source_sha256": dict(sources),
        "system_prompt_sha256": dict(PROMPT_SHA256),
        "unicode_authority_sha256": list(globals()["PINNED_UNICODE_AUTHORITY_SHA256"]),
        "alias_secret_commitment": generation["alias_secret_commitment"],
        "alias_secret_sha256": hashlib.sha256(canonical(secret)).hexdigest(),
        "observed_materializations": observed_materializations,
        "batch_count": len(batches),
        "matrix_rows": MATRIX_ROWS,
        "attempt_consumed": False,
        "candidate_execution_performed": False,
    }
    pre = {**pre, "preflight_identity": identity(pre)}
    if o.preflight_only:
        print(json.dumps(pre, separators=(",", ":")))
        release_locks()
        return 0
    attempt = recovered_attempt or build_attempt(str(mechanism["execution_authority_identity"]), pre)
    if recovered_attempt is None:
        atomic(output / "attempt.json", canonical(attempt))
    elif attempt.get("preflight") != pre or attempt.get("preflight_identity") != pre.get("preflight_identity"):
        raise SystemExit("resume preflight substitution")
    accepted_checkpoints, previous_checkpoint = validate_checkpoint_chain(
        output,
        attempt_identity=str(attempt["attempt_identity"]),
        execution_authority_identity=str(mechanism["execution_authority_identity"]),
        generation_identity=GENERATION_IDENTITY,
        batches=batches,
    )
    completed = accepted_checkpoints * 200
    current_batch = None

    def terminal(code):
        if not (output / "terminal-failure.json").exists():
            partial = sorted(
                (
                    {
                        "path": str(x.relative_to(output)).replace("\\", "/"),
                        "sha256": hashlib.sha256(read(x)).hexdigest(),
                    }
                    for x in output.rglob("*")
                    if x.is_file()
                ),
                key=lambda x: x["path"],
            )
            coordinates = (
                None
                if current_batch is None
                else {
                    key: current_batch[key]
                    for key in ("materialization", "repetition", "candidate_alias")
                }
            )
            failure = build_terminal_failure(
                attempt,
                completed_receipt_count(output, attempt, rows),
                code,
                failed_batch=coordinates,
                partial_artifacts=partial,
            )
            validate_terminal_failure(failure, attempt, partial)
            atomic(output / "terminal-failure.json", canonical(failure))

    def interrupted(number, _frame):
        raise SystemExit(128 + number)

    signal.signal(signal.SIGINT, interrupted)
    signal.signal(signal.SIGTERM, interrupted)
    for checkpoint_ordinal, batch in enumerate(batches, 1):
        if checkpoint_ordinal <= accepted_checkpoints:
            continue
        current_batch = batch
        label = str(batch["materialization"])
        local = mats[label]
        candidate = str(batch["candidate"])
        directory = (
            output
            / f"materialization-{label}"
            / f"repetition-{batch['repetition']}"
            / str(batch["candidate_alias"])
        )
        directory.parent.mkdir(parents=True, exist_ok=True)
        staging = output / f".checkpoint-{checkpoint_ordinal:02d}.in-progress"
        if staging.exists():
            if staging.is_symlink() or not staging.is_dir():
                terminal("CHECKPOINT_STAGING_PATH_REJECTED")
                raise SystemExit("checkpoint staging path rejected")
            shutil.rmtree(staging)
        staging.mkdir()
        directory_locks.append(lock_directory(staging))
        batch_path = staging / "batch.json"
        atomic(batch_path, canonical(batch["batch"]))
        prompt_snapshot = staging / "system-prompt.txt"
        atomic(prompt_snapshot, prompt_snapshots[candidate])
        result = staging / "results"
        result.mkdir()
        directory_locks.append(lock_directory(result))
        prompt = prompt_snapshot
        command = [
            "wsl.exe",
            "-d",
            "Ubuntu-24.04",
            "-u",
            "root",
            "--",
            "bash",
            "--noprofile",
            "--norc",
            "-s",
            "--",
            str(local["rootfs_tar"]),
            str(local["model"]),
            str(local["adapters"][candidate]),
            wsl(prompt),
            wsl(batch_path),
            wsl(result),
            candidate,
            GENERATION_IDENTITY,
            str(batch["batch_sha256"]),
            PROMPT_SHA256[candidate],
            hashlib.sha256(
                source_bytes[str(RUNNER.relative_to(ROOT)).replace("\\", "/")]
            ).hexdigest(),
            wsl(RUNNER),
        ]
        try:
            subprocess.run(
                command,
                input=source_bytes[str(LAUNCHER.relative_to(ROOT)).replace("\\", "/")],
                check=True,
            )
        except subprocess.CalledProcessError as exc:
            terminal(typed_supervisor_failure(result, exc.returncode))
            raise SystemExit(exc.returncode) from exc
        network = obj(read(result / "network-boundary.json"))
        file_boundary = obj(read(result / "file-boundary.json"))
        validate_boundary_logs(network, file_boundary)
        expected_names = {
            "heartbeat.json",
            "network-boundary.json",
            "file-boundary.json",
        }
        for index, row in enumerate(batch["batch"], 1):
            stem = f"{row['case_id']}.{str(row['request_identity']).removeprefix('sha256:')}"
            raw_path = result / f"{stem}.raw"
            observation_path = result / f"{stem}.observation.json"
            expected_names.update({raw_path.name, observation_path.name})
            expected_names.update(
                {
                    f"inference-{index:03d}-started.json",
                    f"inference-{index:03d}-completed.json",
                }
            )
            raw = read(raw_path)
            observation = obj(read(observation_path))
            validate_inference_lifecycle(
                read(result / f"inference-{index:03d}-started.json"),
                read(result / f"inference-{index:03d}-completed.json"),
                sequence=index,
                row=row,
                observation=observation,
            )
            observation_core = dict(observation)
            observed_identity = observation_core.pop("observation_identity", None)
            expected = {
                "qualification_generation_identity": GENERATION_IDENTITY,
                "candidate": candidate,
                "rootfs_sha256": globals()["PINNED_ROOTFS_SHA256"],
                "base_manifest_sha256": candidates["base_model_manifest_sha256"],
                "adapter_manifest_sha256": candidates["adapter_manifest_sha256"][
                    candidate
                ],
                "system_prompt_sha256": hashlib.sha256(read(prompt)).hexdigest(),
                "batch_sha256": batch["batch_sha256"],
                "runner_sha256": hashlib.sha256(
                    source_bytes[str(RUNNER.relative_to(ROOT)).replace("\\", "/")]
                ).hexdigest(),
                "case_id": row["case_id"],
                "request_identity": row["request_identity"],
            }
            if read(observation_path) != canonical(observation):
                raise SystemExit("noncanonical observation")
            candidate_output_status = validate_observation(observation, raw, expected)
            case = next(
                item
                for item in requests["requests"]
                if item["case_id"] == row["case_id"]
            )
            structural = result_status(
                raw,
                validate_response_v2,
                case,
                unicode_authority,
                candidate_output_status,
            )
            receipt_core = {
                "schema": "pastila-production-core-case-execution-receipt-v2",
                "schema_version": 2,
                "execution_authority_identity": mechanism[
                    "execution_authority_identity"
                ],
                "attempt_identity": attempt["attempt_identity"],
                "qualification_generation_identity": GENERATION_IDENTITY,
                "global_ordinal": completed + index,
                "materialization": label,
                "repetition": batch["repetition"],
                "candidate_alias": batch["candidate_alias"],
                "case_id": row["case_id"],
                "request_identity": row["request_identity"],
                "candidate_visible_request_sha256": row["prompt_sha256"],
                "raw_output_sha256": hashlib.sha256(raw).hexdigest(),
                "observation_identity": observed_identity,
                "structural_status": structural,
                "retry_or_redraw": False,
                "adjudication_performed": False,
                "promotion_effect": False,
            }
            receipt = {**receipt_core, "receipt_identity": identity(receipt_core)}
            validate_case_receipt(
                receipt, attempt, rows[int(receipt["global_ordinal"]) - 1]
            )
            atomic(staging / f"{stem}.receipt.json", canonical(receipt))
        if {path.name for path in result.iterdir() if path.is_file()} != expected_names:
            raise SystemExit("result closure mismatch")
        close_directory(directory_locks.pop())
        close_directory(directory_locks.pop())
        if directory.exists():
            terminal("CHECKPOINT_DESTINATION_ALREADY_EXISTS")
            raise SystemExit("checkpoint destination already exists")
        os.replace(staging, directory)
        checkpoint = build_checkpoint_receipt(
            attempt_identity=str(attempt["attempt_identity"]),
            execution_authority_identity=str(mechanism["execution_authority_identity"]),
            generation_identity=GENERATION_IDENTITY,
            checkpoint_ordinal=checkpoint_ordinal,
            previous_checkpoint_identity=previous_checkpoint,
            batch=batch,
            directory=directory,
            directory_binding=str(directory.relative_to(output)).replace("\\", "/"),
        )
        write_checkpoint_receipt(output / f"checkpoint-{checkpoint_ordinal:02d}.json", checkpoint)
        previous_checkpoint = str(checkpoint["checkpoint_identity"])
        completed += 200
    current_batch = None
    artifact_snapshots = {
        str(path.relative_to(output)).replace("\\", "/"): read(path)
        for path in output.rglob("*")
        if path.is_file()
    }
    inventory = [
        {"path": path, "sha256": hashlib.sha256(data).hexdigest()}
        for path, data in sorted(artifact_snapshots.items())
    ]
    core = {
        "schema": "pastila-production-core-comparative-execution-completion-v2",
        "schema_version": 2,
        "attempt_identity": attempt["attempt_identity"],
        "execution_authority_identity": mechanism["execution_authority_identity"],
        "qualification_generation_identity": GENERATION_IDENTITY,
        "completed_rows": completed,
        "artifact_inventory": inventory,
        "artifact_root": identity(inventory),
        "retry_or_redraw": False,
        "adjudication_performed": False,
        "promotion_effect": False,
    }
    completion = {**core, "completion_identity": identity(core)}
    validate_completion(completion, attempt, rows, artifact_snapshots)
    atomic(output / "completion.json", canonical(completion))
    release_locks()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
