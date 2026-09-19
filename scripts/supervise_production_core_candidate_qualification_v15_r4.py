"""Persistent fail-closed supervisor for one separately authorized R4 attempt."""

from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import materialize_production_core_v15_r4_execution_authority as issuer
import project_production_core_candidate_qualification_v15_r4 as projection
from pastila_scout import production_core_successor_contract_v15_r3 as contract

SCHEMA = "pastila-production-core-v15-r4-supervisor-state"


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def digest(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def atomic_state(path: Path, core: dict) -> None:
    raw = canonical({**core, "state_identity": digest(canonical(core))}) + b"\n"
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW, 0o600)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(raw); handle.flush(); os.fsync(handle.fileno())
        os.replace(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        temporary.unlink(missing_ok=True)


def read_state(path: Path, run_identity: str) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("R4 supervisor state substitution")
    value = json.loads(path.read_bytes())
    core = dict(value); claimed = core.pop("state_identity", None)
    if (claimed != digest(canonical(core)) or core.get("schema") != SCHEMA
            or core.get("run_identity") != run_identity
            or core.get("phase") not in {"STARTING", "ACTIVE", "COMPLETE", "TERMINAL_FAILURE"}
            or type(core.get("accepted_checkpoints")) is not int
            or not 0 <= core["accepted_checkpoints"] <= 12
            or core.get("completed_rows") != core["accepted_checkpoints"] * 200
            or type(core.get("sequence")) is not int or core["sequence"] < 0
            or core.get("qualification_evidence") is not False):
        raise ValueError("R4 supervisor state rejected")
    return core


def systemd_state(unit: str) -> dict[str, str]:
    result = subprocess.run([
        "systemctl", "show", unit,
        "--property=ActiveState,SubState,Result,MainPID,ExecMainStatus", "--no-pager",
    ], check=True, capture_output=True, text=True)
    state = dict(line.split("=", 1) for line in result.stdout.splitlines() if "=" in line)
    if set(state) != {"ActiveState", "SubState", "Result", "MainPID", "ExecMainStatus"}:
        raise ValueError("R4 supervisor systemd state incomplete")
    return state


def command(recovery: Path, private: Path, backup: Path, v13_terminal: Path,
            terminal: Path, rootfs: Path, snapshot: Path, unicode_root: Path,
            output: Path) -> list[str]:
    return [
        sys.executable, str(issuer.ROOT / "scripts/execute_production_core_candidate_qualification_v15_r4.py"),
        "--recovery", str(recovery), "--private", str(private), "--backup", str(backup),
        "--v13-terminal", str(v13_terminal), "--terminal", str(terminal),
        "--rootfs", str(rootfs), "--snapshot", str(snapshot),
        "--unicode-root", str(unicode_root), "--output", str(output), "--consume-attempt",
    ]


def evidence_state(output: Path, authority: dict) -> tuple[dict | None, int, str | None]:
    attempt_path = output / "attempt.json"
    attempt = json.loads(attempt_path.read_bytes()) if attempt_path.is_file() and not attempt_path.is_symlink() else None
    checkpoints = len(list(output.glob("checkpoint-??.json")))
    terminal = "TERMINAL_FAILURE" if (output / "terminal-failure.json").is_file() else None
    if (output / "completion.json").is_file():
        terminal = "COMPLETE"
    if attempt is not None and attempt.get("execution_authority_identity") != authority["authority_identity"]:
        raise ValueError("R4 supervisor attempt authority mismatch")
    return attempt, checkpoints, terminal


def seal_uncaught(output: Path, authority: dict) -> None:
    attempt, _, terminal = evidence_state(output, authority)
    if attempt is None or terminal is not None:
        return
    boundary = {"boundary_identity": authority["authority_identity"],
                "source_sha256": authority["source_sha256"]}
    namespace = projection.build_namespace(boundary)
    snapshots = {name: json.loads((issuer.ROOT / "docs/artifacts" / name).read_bytes())
                 for name in namespace["NAMES"]}
    rows = namespace["validate_preflight"](*(snapshots[name] for name in namespace["NAMES"]))
    completed = namespace["completed_receipt_count"](output, attempt, rows)
    contract.close_post_claim_failure(
        output, completed_rows=completed,
        failure_class="UNHANDLED_SUPERVISED_PROCESS_EXIT", failed_batch=None,
        build_failure=namespace["build_terminal_failure"],
        validate_failure=namespace["validate_terminal_failure"],
        atomic_no_replace=projection.r3.predecessor.atomic_no_replace,
        canonical=namespace["canonical"],
    )


def supervise(monitor: Path, recovery: Path, private: Path, backup: Path,
              v13_terminal: Path, terminal: Path, rootfs: Path, snapshot: Path,
              unicode_root: Path, output: Path, *, owner_authorized: bool,
              tick_seconds: float = 2.0) -> dict:
    if not owner_authorized:
        raise ValueError("separate owner authorization for R4 attempt required")
    if (monitor.is_symlink() or not monitor.is_dir() or monitor.stat().st_mode & 0o077
            or monitor.resolve().is_relative_to(output.resolve())
            or output.resolve().is_relative_to(monitor.resolve())):
        raise ValueError("R4 owner-only disjoint monitor required")
    authority = json.loads((issuer.OUTPUT / "authority.json").read_bytes())
    run_identity = digest(canonical({"authority": authority["authority_identity"],
                                    "output": str(output.resolve()), "command": command(
                                        recovery, private, backup, v13_terminal, terminal,
                                        rootfs, snapshot, unicode_root, output)}))
    unit = f"pf9-v15-r4-{run_identity[:16]}.service"
    lock_path = monitor / "supervisor.lock"
    if lock_path.is_symlink():
        raise ValueError("R4 supervisor lock substitution")
    with lock_path.open("a+b") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("parallel R4 supervisor rejected") from error
        state_path = monitor / "supervisor-state.json"
        if state_path.exists():
            state = read_state(state_path, run_identity)
        else:
            if any(output.iterdir()):
                raise ValueError("R4 output must be empty before supervisor start")
            if systemd_state(unit)["ActiveState"] in ("active", "activating"):
                raise ValueError("parallel R4 worker rejected")
            state = {"schema": SCHEMA, "run_identity": run_identity,
                     "authority_identity": authority["authority_identity"],
                     "qualification_evidence": False, "phase": "STARTING",
                     "unit": unit, "accepted_checkpoints": 0, "completed_rows": 0,
                     "sequence": 0, "adjudication": False, "promotion": False}
            atomic_state(state_path, state)
            subprocess.run([
                "systemd-run", "--unit", unit.removesuffix(".service"), "--collect",
                "--service-type=exec", "--property=KillMode=control-group",
                "--property=Restart=no", "--setenv=PYTHONDONTWRITEBYTECODE=1",
                "--setenv=PYTHONPATH=" + os.pathsep.join((str(issuer.ROOT / "src"), str(issuer.ROOT / "scripts"))),
                *command(recovery, private, backup, v13_terminal, terminal,
                         rootfs, snapshot, unicode_root, output),
            ], check=True, capture_output=True)
        if state["phase"] in ("COMPLETE", "TERMINAL_FAILURE"):
            return state
        stopped = False
        def stop(_number, _frame):
            nonlocal stopped; stopped = True
        old_term = signal.signal(signal.SIGTERM, stop); old_int = signal.signal(signal.SIGINT, stop)
        try:
            while True:
                status = systemd_state(unit)
                attempt, checkpoints, terminal_state = evidence_state(output, authority)
                if checkpoints < state["accepted_checkpoints"]:
                    raise ValueError("R4 accepted checkpoint regression")
                phase = "ACTIVE" if status["ActiveState"] in ("active", "activating") else state["phase"]
                if terminal_state is not None:
                    phase = terminal_state
                elif status["ActiveState"] not in ("active", "activating"):
                    seal_uncaught(output, authority)
                    phase = "TERMINAL_FAILURE"
                state = {**state, "phase": phase, "accepted_checkpoints": checkpoints,
                         "completed_rows": checkpoints * 200, "sequence": state["sequence"] + 1}
                atomic_state(state_path, state)
                atomic_state(monitor / "supervisor-heartbeat.json", {
                    **state, "schema": SCHEMA, "active_state": status["ActiveState"],
                    "main_pid": status["MainPID"], "attempt_present": attempt is not None,
                    "observed_unix_ns": time.time_ns(), "qualification_evidence": False,
                })
                if stopped and phase not in ("COMPLETE", "TERMINAL_FAILURE"):
                    subprocess.run(["systemctl", "kill", "--kill-who=all", "--signal=SIGTERM", unit], check=False)
                    subprocess.run(["systemctl", "stop", unit], check=False)
                    continue
                if phase in ("COMPLETE", "TERMINAL_FAILURE"):
                    return state
                time.sleep(tick_seconds)
        finally:
            signal.signal(signal.SIGTERM, old_term); signal.signal(signal.SIGINT, old_int)


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("monitor", "recovery", "private", "backup", "v13-terminal", "terminal",
                 "rootfs", "snapshot", "unicode-root", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--owner-authorized", action="store_true", required=True)
    args = parser.parse_args()
    state = supervise(args.monitor, args.recovery, args.private, args.backup,
                      args.v13_terminal, args.terminal, args.rootfs, args.snapshot,
                      args.unicode_root, args.output, owner_authorized=args.owner_authorized)
    print(json.dumps(state, sort_keys=True))
    return 0 if state["phase"] == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
