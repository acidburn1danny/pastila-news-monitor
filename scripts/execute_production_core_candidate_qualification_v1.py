"""Execute the frozen comparative matrix after its commit/audit authorization gate."""

from __future__ import annotations

import argparse
import atexit
import hashlib
import json
import os
import signal
import stat
import subprocess
from pathlib import Path, PureWindowsPath

if "PINNED_ENTRY_EXECUTOR_SHA256" not in globals():  # test/import support; main rejects direct execution
    from pastila_scout.production_core_candidate_qualification_v1 import (
        atomic_publish,
        build_blind_packet,
        build_execution_receipt,
        canonical_json_bytes,
        materialize_batches,
    )

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = ROOT / "docs" / "artifacts"
IDENTITY_HELPER = ROOT / "scripts" / "resolve_production_core_object_identity_v1.sh"


def _object(path: Path) -> dict[str, object]:
    value = json.loads(path.read_bytes())
    if not isinstance(value, dict):
        raise SystemExit(f"object expected: {path}")
    return value


def _wsl(path: Path) -> str:
    if path.is_symlink() or not path.exists():
        raise SystemExit("Windows-to-WSL path authority rejected")
    windows = PureWindowsPath(path.absolute())
    if not windows.drive or windows.root != "\\" or len(windows.drive) != 2:
        raise SystemExit("unsupported Windows-to-WSL path authority")
    drive = windows.drive[0]
    if not drive.isascii() or not drive.isalpha():
        raise SystemExit("unsupported Windows drive authority")
    relative = windows.relative_to(windows.anchor)
    if any(part in {"", ".", ".."} for part in relative.parts):
        raise SystemExit("invalid Windows-to-WSL path authority")
    return f"/mnt/{drive.lower()}/" + "/".join(relative.parts)


def _read_pinned_source(path: Path, expected_sha256: str) -> bytes:
    if path.is_symlink():
        raise SystemExit("production executable source symlink rejected")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    descriptor = os.open(path, flags)
    try:
        metadata = os.fstat(descriptor)
        if not stat.S_ISREG(metadata.st_mode):
            raise SystemExit("production executable source is not a regular file")
        with os.fdopen(descriptor, "rb", closefd=False) as handle:
            data = handle.read()
    finally:
        os.close(descriptor)
    if hashlib.sha256(data).hexdigest() != expected_sha256:
        raise SystemExit("production executable source byte mismatch")
    return data


def _wsl_object_identity(path: str, helper_bytes: bytes) -> str:
    completed = subprocess.run(
        [
            "wsl.exe", "-d", "Ubuntu-24.04", "--", "bash", "--noprofile",
            "--norc", "-s", "--", path,
        ],
        input=helper_bytes, check=True, capture_output=True,
    )
    return completed.stdout.decode("utf-8", errors="strict")


def _run_launcher(command: list[str], launcher_bytes: bytes) -> None:
    subprocess.run(command, input=launcher_bytes, check=True)


def _publish_case_evidence(
    *, receipt_path: Path, receipt: dict[str, object],
    exports: dict[str, Path], materialization: str, repetition: int,
    alias: str, stem: str, packet: dict[str, object],
) -> None:
    """Publish one case atomically; structural FAIL does not stop later cases."""

    atomic_publish(receipt_path, canonical_json_bytes(receipt))
    for export_root in exports.values():
        role_dir = (
            export_root / f"materialization-{materialization}"
            / f"repetition-{repetition}" / alias
        )
        role_dir.mkdir(parents=True, exist_ok=True)
        atomic_publish(role_dir / f"{stem}.blind.json", canonical_json_bytes(packet))


def _publish_terminal_failure(
    output: Path, generation: str, attempt: dict[str, object], failure_class: str
) -> None:
    if (output / "terminal-failure.json").exists():
        return
    partial = sorted(
        ({"path": str(path.relative_to(output)).replace("\\", "/"), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in output.rglob("*") if path.is_file()),
        key=lambda row: row["path"],
    )
    failure_core = {
        "schema": "pastila-production-core-comparative-execution-terminal-failure",
        "schema_version": 1,
        "qualification_generation_identity": generation,
        "attempt_identity": attempt["attempt_identity"],
        "failure_class": failure_class,
        "partial_artifact_count": len(partial),
        "partial_artifact_root": hashlib.sha256(canonical_json_bytes(partial)).hexdigest(),
        "retry_or_redraw_authorized": False,
        "promotion_effect": False,
    }
    failure = {**failure_core, "failure_identity": hashlib.sha256(canonical_json_bytes(failure_core)).hexdigest()}
    atomic_publish(output / "terminal-failure.json", canonical_json_bytes(failure))


def _install_terminal_signal_handlers(
    output: Path, generation: str, attempt: dict[str, object]
) -> None:
    def terminate(signum: int, _frame: object) -> None:
        _publish_terminal_failure(
            output, generation, attempt,
            f"SIGNAL_{signum}_AFTER_ATTEMPT_CONSUMPTION",
        )
        raise SystemExit(128 + signum)

    signal.signal(signal.SIGINT, terminate)
    signal.signal(signal.SIGTERM, terminate)


def _recover_unclosed_attempt(output: Path, generation: str) -> bool:
    if not (output / "attempt.json").is_file() or (output / "completion.json").exists() or (output / "terminal-failure.json").exists():
        return False
    existing_attempt = _object(output / "attempt.json")
    existing_core = dict(existing_attempt)
    existing_identity = existing_core.pop("attempt_identity", None)
    if (
        existing_attempt.get("qualification_generation_identity") != generation
        or existing_identity != hashlib.sha256(canonical_json_bytes(existing_core)).hexdigest()
    ):
        raise SystemExit("orphaned attempt authority mismatch")
    _publish_terminal_failure(
        output, generation, existing_attempt,
        "RECOVERED_CONSUMED_ATTEMPT_WITHOUT_TERMINAL_RECORD",
    )
    return True


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--resolution", required=True, type=Path)
    parser.add_argument("--secret", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--adjudicator-a-export", required=True, type=Path)
    parser.add_argument("--adjudicator-b-export", required=True, type=Path)
    options = parser.parse_args()
    if any(path.is_symlink() for path in (options.resolution, options.secret, options.output, options.adjudicator_a_export, options.adjudicator_b_export)):
        raise SystemExit("symlink authority rejected")
    output = options.output.resolve(strict=True)
    authority_names = (
        "production-core-candidate-object-manifest-v1.json",
        "production-core-comparative-qualification-generation-v1.json",
        "production-core-candidate-qualification-mechanism-v1.json",
    )
    authority_bytes = {name: (ARTIFACTS / name).read_bytes() for name in authority_names}
    terminal_validator = globals().get("PINNED_TERMINAL_VALIDATOR")
    if not callable(terminal_validator):
        raise SystemExit("terminal validator was not supplied by pinned entry authority")
    terminal_validator(authority_bytes)
    plan = json.loads(authority_bytes[authority_names[1]])
    candidate_manifest = json.loads(authority_bytes[authority_names[0]])
    mechanism = json.loads(authority_bytes[authority_names[2]])
    source_sha256 = mechanism.get("source_sha256")
    if not isinstance(source_sha256, dict):
        raise SystemExit("production executable source authority absent")
    executor_name = "scripts/execute_production_core_candidate_qualification_v1.py"
    helper_name = "scripts/resolve_production_core_object_identity_v1.sh"
    launcher_name = "scripts/run_production_core_candidate_qualification_v1.sh"
    if globals().get("PINNED_ENTRY_EXECUTOR_SHA256") != source_sha256.get(executor_name):
        raise SystemExit("executor was not loaded by the pinned entry authority")
    helper_bytes = _read_pinned_source(IDENTITY_HELPER, str(source_sha256.get(helper_name)))
    launcher = ROOT / launcher_name
    launcher_bytes = _read_pinned_source(launcher, str(source_sha256.get(launcher_name)))
    generation = str(plan["qualification_generation_identity"])
    if any(output.iterdir()):
        if _recover_unclosed_attempt(output, generation):
            return 1
        raise SystemExit("qualification attempt is already terminal or output is unauthorized")

    resolution = _object(options.resolution.resolve(strict=True))
    secret = _object(options.secret.resolve(strict=True))
    if list(resolution) != ["schema", "schema_version", "materializations"]:
        raise SystemExit("resolution schema/order mismatch")
    materializations = resolution["materializations"]
    if (
        resolution["schema"] != "pastila-production-core-local-object-resolution"
        or resolution["schema_version"] != 1
        or not isinstance(materializations, dict)
        or list(materializations) != ["A", "B"]
    ):
        raise SystemExit("resolution authority invalid")
    exports = {
        "ADJUDICATOR_A": options.adjudicator_a_export.resolve(strict=True),
        "ADJUDICATOR_B": options.adjudicator_b_export.resolve(strict=True),
    }
    if len({output, *exports.values()}) != 3:
        raise SystemExit("qualification output roots must be distinct")
    corpus = _object(ARTIFACTS / "production-core-qualification-corpus-v1.json")
    assertions = _object(ARTIFACTS / "production-core-qualification-assertions-v1.json")
    rubric = _object(ARTIFACTS / "production-core-qualification-rubric-v1.json")
    assertion_by_case = {row["case_id"]: row for row in assertions["assertions"]}  # type: ignore[index]
    case_by_id = {row["case_id"]: row for row in corpus["cases"]}  # type: ignore[index]
    batches = materialize_batches(plan, candidate_manifest, corpus, secret)
    resolved_objects: set[str] = set()
    for materialization in ("A", "B"):
        local = materializations[materialization]  # type: ignore[index]
        if not isinstance(local, dict) or list(local) != ["rootfs_tar", "model", "adapters", "materialization_provenance_identity"]:
            raise SystemExit("materialization resolution mismatch")
        paths = [str(local["rootfs_tar"]), str(local["model"]), *map(str, local["adapters"].values())]  # type: ignore[union-attr]
        identities = {_wsl_object_identity(path, helper_bytes) for path in paths}
        if len(identities) != len(paths) or resolved_objects.intersection(identities):
            raise SystemExit("clean materializations are not physically distinct")
        resolved_objects.update(identities)
        proof = str(local["materialization_provenance_identity"])
        expected_proof = plan["clean_materialization_authority"][materialization]["provenance_identity"]  # type: ignore[index]
        if proof != expected_proof:
            raise SystemExit("materialization provenance is not distinct")
    runner = ROOT / "src" / "pastila_scout" / "production_core_candidate_qualification_runner_v1.py"
    if runner.is_symlink() or not runner.is_file():
        raise SystemExit("runner source authority rejected")
    prompts = {
        "pastila-editor-core-v1.1-experimental": ROOT / ".experimental-0-3-editor-core-v1-architecture-prompt-first-training-plan-v1-evidence" / "PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1.txt",
        "pastila-editor-core-v1.2-experimental": ROOT / ".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence" / "PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt",
    }
    if any(any(path.iterdir()) for path in exports.values()):
        raise SystemExit("adjudicator export roots must be empty")
    attempt_core = {
        "schema": "pastila-production-core-comparative-execution-attempt",
        "schema_version": 1,
        "qualification_generation_identity": generation,
        "alias_secret_commitment": plan["alias_secret_commitment"],
        "attempt_ordinal": plan["replacement_authority"]["replacement_attempt_ordinal"],
        "retry_or_redraw_authorized": False,
        "status": "CONSUMED_BEFORE_EXECUTION",
    }
    attempt = {**attempt_core, "attempt_identity": hashlib.sha256(canonical_json_bytes(attempt_core)).hexdigest()}
    atomic_publish(output / "attempt.json", canonical_json_bytes(attempt))

    def terminalize_unclosed_attempt() -> None:
        if (output / "completion.json").exists() or (output / "terminal-failure.json").exists():
            return
        _publish_terminal_failure(
            output, generation, attempt,
            "UNCAUGHT_OR_CANCELLED_AFTER_ATTEMPT_CONSUMPTION",
        )

    atexit.register(terminalize_unclosed_attempt)
    _install_terminal_signal_handlers(output, generation, attempt)
    inventory: list[dict[str, object]] = []
    for batch in batches:
        materialization = str(batch["materialization"])
        candidate = str(batch["candidate"])
        alias = str(batch["candidate_alias"])
        repetition = int(batch["repetition"])
        local = materializations[materialization]  # type: ignore[index]
        adapters = local["adapters"]
        if not isinstance(adapters, dict) or set(adapters) != set(prompts):
            raise SystemExit("adapter resolution closure mismatch")
        batch_dir = output / f"materialization-{materialization}" / f"repetition-{repetition}" / alias
        batch_dir.mkdir(parents=True, exist_ok=False)
        batch_path = batch_dir / "batch.json"
        atomic_publish(batch_path, canonical_json_bytes(batch["batch"]))
        result_dir = batch_dir / "results"
        result_dir.mkdir()
        command = [
            "wsl.exe", "-d", "Ubuntu-24.04", "-u", "root", "--", "bash",
            "--noprofile", "--norc", "-s", "--", str(local["rootfs_tar"]), str(local["model"]),
            str(adapters[candidate]), _wsl(prompts[candidate]), _wsl(batch_path),
            _wsl(result_dir), candidate, generation,
            str(batch["batch_sha256"]),
            str(candidate_manifest["system_prompts"][candidate]),
            str(mechanism["source_sha256"]["src/pastila_scout/production_core_candidate_qualification_runner_v1.py"]),
            _wsl(runner),
        ]
        try:
            _run_launcher(command, launcher_bytes)  # exactly one attempt; no retry path
        except (OSError, subprocess.CalledProcessError) as exc:
            partial = sorted(
                ({"path": str(path.relative_to(output)).replace("\\", "/"), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in output.rglob("*") if path.is_file()),
                key=lambda row: row["path"],
            )
            failure_core = {
                "schema": "pastila-production-core-comparative-execution-terminal-failure",
                "schema_version": 1,
                "qualification_generation_identity": generation,
                "attempt_identity": attempt["attempt_identity"],
                "failed_materialization": materialization,
                "failed_repetition": repetition,
                "failed_candidate_alias": alias,
                "failure_class": type(exc).__name__,
                "partial_artifact_count": len(partial),
                "partial_artifact_root": hashlib.sha256(canonical_json_bytes(partial)).hexdigest(),
                "retry_or_redraw_authorized": False,
                "promotion_effect": False,
            }
            failure = {**failure_core, "failure_identity": hashlib.sha256(canonical_json_bytes(failure_core)).hexdigest()}
            atomic_publish(output / "terminal-failure.json", canonical_json_bytes(failure))
            return 1
        network_hash = hashlib.sha256((result_dir / "network-boundary.json").read_bytes()).hexdigest()
        file_hash = hashlib.sha256((result_dir / "file-boundary.json").read_bytes()).hexdigest()
        network_log = _object(result_dir / "network-boundary.json")
        file_log = _object(result_dir / "file-boundary.json")
        if network_log != {
            "schema": "pastila-production-core-network-boundary-log",
            "schema_version": 1,
            "policy": "DENY_ALL_NEW_CHILD_NAMESPACE",
            "observed_interfaces": ["lo"],
            "observed_ipv4_route_rows": 0,
            "namespace_init_pid": 1,
            "network_namespace_differs_from_parent": True,
            "pid_namespace_differs_from_parent": True,
            "promotion_effect": False,
        }:
            raise SystemExit("measured network boundary mismatch")
        if (
            file_log.get("schema") != "pastila-production-core-file-boundary-log"
            or file_log.get("schema_version") != 1
            or file_log.get("model_mount_read_only") is not True
            or file_log.get("adapter_mount_read_only") is not True
            or file_log.get("candidate_private_snapshots") is not True
            or file_log.get("authority_inputs_from_open_descriptors") is not True
            or file_log.get("private_rootfs_from_open_descriptor") is not True
            or file_log.get("host_pid_namespace_reachable") is not False
            or len(str(file_log.get("mountinfo_sha256"))) != 64
        ):
            raise SystemExit("measured file boundary mismatch")
        for row in batch["batch"]:  # type: ignore[union-attr]
            stem = f"{row['case_id']}.{str(row['request_identity']).removeprefix('sha256:')}"
            raw_path = result_dir / f"{stem}.raw"
            observation = _object(result_dir / f"{stem}.observation.json")
            observation_bytes = (result_dir / f"{stem}.observation.json").read_bytes()
            observation_core = dict(observation)
            observation_identity = observation_core.pop("observation_identity", None)
            if (
                observation_bytes != canonical_json_bytes(observation)
                or observation_identity != hashlib.sha256(canonical_json_bytes(observation_core)).hexdigest()
                or observation.get("qualification_generation_identity") != generation
                or observation.get("candidate") != candidate
                or observation.get("case_id") != row["case_id"]
                or observation.get("request_identity") != row["request_identity"]
                or observation.get("rootfs_sha256") != candidate_manifest["rootfs_sha256"]
                or observation.get("adapter_manifest_sha256") != candidate_manifest["adapters"][candidate]["manifest_sha256"]  # type: ignore[index]
                or type(observation.get("terminal_eos")) is not bool
            ):
                raise SystemExit("runner observation authority mismatch")
            raw = raw_path.read_bytes()
            schedule_row = next(
                item for item in plan["schedule"]  # type: ignore[index]
                if item["materialization"] == materialization
                and item["repetition"] == repetition
                and item["candidate_alias"] == alias
                and item["case_id"] == row["case_id"]
            )
            receipt = build_execution_receipt(
                authority=plan, schedule_row=schedule_row, raw_output=raw,
                input_tokens=observation["input_tokens"], output_tokens=observation["output_tokens"],  # type: ignore[arg-type]
                load_plus_generation_wall_ns=observation["load_wall_ns"] + observation["generation_wall_ns"],  # type: ignore[operator]
                peak_rss_bytes=observation["peak_rss_bytes"],  # type: ignore[arg-type]
                network_log_sha256=network_hash, file_access_log_sha256=file_hash,
                observation_sha256=hashlib.sha256(observation_bytes).hexdigest(),
                observation_identity=observation["observation_identity"],  # type: ignore[arg-type]
                runner_sha256=observation["runner_sha256"],  # type: ignore[arg-type]
                prompt_sha256=observation["system_prompt_sha256"],  # type: ignore[arg-type]
                batch_sha256=observation["batch_sha256"],  # type: ignore[arg-type]
                candidate=candidate,
                terminal_eos=observation["terminal_eos"],  # type: ignore[arg-type]
            )
            receipt_path = batch_dir / f"{stem}.receipt.json"
            packet = build_blind_packet(
                authority=plan, case=case_by_id[row["case_id"]], alias=alias,
                raw_output=raw, assertion=assertion_by_case[row["case_id"]], rubric=rubric,
                execution_receipt_identity=receipt["receipt_identity"],
                terminal_eos=observation["terminal_eos"],  # type: ignore[arg-type]
            )
            _publish_case_evidence(
                receipt_path=receipt_path, receipt=receipt, exports=exports,
                materialization=materialization, repetition=repetition,
                alias=alias, stem=stem, packet=packet,
            )
    inventory = sorted(
        ({"path": str(path.relative_to(output)).replace("\\", "/"), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()} for path in output.rglob("*") if path.is_file()),
        key=lambda row: row["path"],
    )
    terminal_core = {
        "schema": "pastila-production-core-comparative-execution-completion",
        "schema_version": 1,
        "qualification_generation_identity": generation,
        "batch_count": 12,
        "case_execution_count": 2400,
        "private_artifact_count": len(inventory),
        "private_artifacts": inventory,
        "private_artifact_root": hashlib.sha256(canonical_json_bytes(inventory)).hexdigest(),
        "adjudicator_exports": {},
        "promotion_effect": False,
    }
    export_roots: dict[str, str] = {}
    for role, export_root in exports.items():
        exported = []
        for path in export_root.rglob("*.blind.json"):
            raw_packet = path.read_bytes()
            packet = json.loads(raw_packet)
            forbidden = (b"pastila-editor-core-v1.1-experimental", b"pastila-editor-core-v1.2-experimental", b'"candidate":', b'"observation')
            if (
                not isinstance(packet, dict)
                or packet.get("schema") != "pastila-production-core-blind-adjudication-packet"
                or packet.get("candidate_alias") not in {"CANDIDATE-A", "CANDIDATE-B"}
                or any(marker in raw_packet for marker in forbidden)
            ):
                raise SystemExit("blind export identity leakage or schema mismatch")
            exported.append({"path": str(path.relative_to(export_root)).replace("\\", "/"), "sha256": hashlib.sha256(raw_packet).hexdigest()})
        exported.sort(key=lambda row: row["path"])
        if len(exported) != 2400 or len({row["path"] for row in exported}) != 2400:
            raise SystemExit("blind export packet closure mismatch")
        packets_root = hashlib.sha256(canonical_json_bytes(exported)).hexdigest()
        export_roots[role] = packets_root
        custody_core = {
            "schema": "pastila-production-core-blind-export-custody-manifest",
            "schema_version": 1,
            "adjudicator_role": role,
            "qualification_generation_identity": generation,
            "packet_count": len(exported),
            "packets_root": packets_root,
            "candidate_mapping_present": False,
            "private_observations_present": False,
        }
        custody = {**custody_core, "custody_identity": hashlib.sha256(canonical_json_bytes(custody_core)).hexdigest()}
        atomic_publish(export_root / "custody.json", canonical_json_bytes(custody))
        terminal_core["adjudicator_exports"][role] = custody["custody_identity"]  # type: ignore[index]
    if len(set(export_roots.values())) != 1:
        raise SystemExit("adjudicator exports are not byte-equivalent")
    terminal = {**terminal_core, "completion_identity": hashlib.sha256(canonical_json_bytes(terminal_core)).hexdigest()}
    atomic_publish(output / "completion.json", canonical_json_bytes(terminal))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
