"""Fail-closed systemd supervisor for a separately authorized V14 attempt.

Importing and testing this module never starts a candidate. ``run`` requires an
explicit owner authorization flag and a fresh executable pre-consumption audit.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

from pastila_scout import production_core_candidate_execution_authority_v14 as validator
from pastila_scout import production_core_checkpoint_resume_v6 as checkpoints
from pastila_scout import production_core_overnight_supervisor_v14 as protocol

ROOT = Path(__file__).resolve().parents[2]
ART = ROOT / "docs/artifacts"
AUTHORITY = protocol.AUTHORITY
SCHEMA = "pastila-production-core-v14-production-supervisor-observation"


def signed_launcher_identity() -> str:
    report = json.loads(subprocess.check_output([
        sys.executable, str(ROOT / "scripts/audit_production_core_v14_launcher_boundary.py")
    ], cwd=ROOT))
    if report.get("ed25519_verification") != "PASS" or report.get("source_closure") != "PASS":
        raise ValueError("launcher signature or source closure rejected")
    return str(report["boundary_identity"])


def load_json(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("qualification evidence path substitution")
    return json.loads(path.read_bytes())


def schedule(secret: Path) -> tuple[list[dict], tuple[dict, ...]]:
    names = (
        "production-core-successor-comparative-qualification-generation-v13.json",
        "production-core-candidate-request-manifest-v2.json",
        "production-core-successor-candidate-object-manifest-v10.json",
        "production-core-successor-candidate-generation-qualification-v13.json",
    )
    generation, requests, candidates, qualification = (load_json(ART / name) for name in names)
    rows = validator.validate_preflight(generation, requests, candidates, qualification)
    batches = validator.materialize_batches(rows, load_json(secret), generation["alias_secret_commitment"])
    return rows, batches


def accepted_progress(output: Path, attempt: dict, batches: tuple[dict, ...]) -> int:
    accepted, _ = checkpoints.validate_chain(
        output, attempt_identity=attempt["attempt_identity"],
        execution_authority_identity=AUTHORITY,
        generation_identity=validator.GENERATION_IDENTITY, batches=batches,
    )
    return accepted


def validate_terminal(output: Path, attempt: dict) -> dict | None:
    path = output / "terminal-failure.json"
    if not path.exists():
        return None
    failure = load_json(path)
    partial = sorted((
        {"path": p.relative_to(output).as_posix(), "sha256": protocol.sha(p.read_bytes())}
        for p in output.rglob("*") if p.is_file() and p != path
    ), key=lambda row: row["path"])
    validator.validate_terminal_failure(failure, attempt, partial)
    return failure


def validate_completion(output: Path, attempt: dict, rows: list[dict]) -> dict | None:
    path = output / "completion.json"
    if not path.exists():
        return None
    completion = load_json(path)
    snapshots = {
        p.relative_to(output).as_posix(): p.read_bytes()
        for p in output.rglob("*") if p.is_file() and p != path
    }
    validator.validate_completion(completion, attempt, rows, snapshots)
    return completion


def command(recovery: Path, private: Path, backup: Path, terminal: Path, unicode: Path, output: Path) -> list[str]:
    return [
        sys.executable, str(ROOT / "scripts/launch_production_core_candidate_qualification_v14.py"),
        "--recovery-root", str(recovery), "--private-root", str(private),
        "--backup-root", str(backup), "--terminal-root", str(terminal),
        "--unicode-root", str(unicode), "--output", str(output), "--consume-attempt",
    ]


def preflight_command(recovery: Path, private: Path, backup: Path, terminal: Path, unicode: Path, output: Path) -> list[str]:
    return [
        sys.executable, str(ROOT / "scripts/audit_production_core_v14_preconsumption_preflight.py"),
        "--recovery-root", str(recovery), "--private-root", str(private),
        "--backup-root", str(backup), "--terminal-root", str(terminal),
        "--unicode-root", str(unicode), "--output", str(output),
    ]


def terminal_observation(monitor: Path, run_id: str, reason: str, attempt: dict | None = None) -> None:
    protocol.atomic(monitor / "supervisor-terminal-observation.json", {
        "schema": "pastila-production-core-v14-supervisor-terminal-observation",
        "authority_identity": AUTHORITY,
        "run_identity": run_id,
        "reason": reason,
        "attempt_identity": attempt.get("attempt_identity") if attempt else None,
        "qualification_evidence": False,
        "adjudication": False,
        "promotion": False,
    })


def final_heartbeat(monitor: Path, run_id: str, launcher_boundary: str, state: dict) -> None:
    protocol.atomic(monitor / "supervisor-heartbeat.json", {
        "schema": SCHEMA,
        "authority_identity": AUTHORITY,
        "launcher_boundary_identity": launcher_boundary,
        "run_identity": run_id,
        "qualification_evidence": False,
        "phase": state["phase"],
        "active_state": "inactive",
        "main_pid": "0",
        "attempt_present": None,
        "accepted_checkpoints": state["accepted_checkpoints"],
        "completed_rows": state["completed_rows"],
        "observed_unix_ns": time.time_ns(),
    })


def run(monitor: Path, recovery: Path, private: Path, backup: Path, terminal: Path,
        unicode: Path, output: Path, *, owner_authorized: bool) -> dict:
    if not owner_authorized:
        raise ValueError("separate owner authorization required")
    if monitor.is_symlink() or not monitor.is_dir() or monitor.stat().st_mode & 0o077:
        raise ValueError("owner-only supervisor directory required")
    if monitor.resolve().is_relative_to(output.resolve()) or output.resolve().is_relative_to(monitor.resolve()):
        raise ValueError("supervisor observation overlaps qualification evidence")
    launcher_boundary = signed_launcher_identity()
    run_id = protocol.sha(protocol.canonical({
        "authority": AUTHORITY, "launcher_boundary": launcher_boundary,
        "output": str(output.resolve()), "terminal": str(terminal.resolve()),
    }))
    unit = f"pf9-v14-qualification-{run_id[:16]}.service"
    lock_path = monitor / "supervisor.lock"
    if lock_path.is_symlink():
        raise ValueError("supervisor lock substitution")
    import fcntl
    with lock_path.open("a+b") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("parallel qualification supervisor rejected") from error
        state_path = monitor / "supervisor-state.json"
        if state_path.exists():
            state = protocol.read_state(state_path, run_id)
        else:
            if any(output.iterdir()):
                raise ValueError("new attempt output is not empty")
            if protocol.systemd_state(unit)["ActiveState"] in ("active", "activating"):
                raise ValueError("parallel qualification worker rejected")
            receipt = json.loads(subprocess.check_output(
                preflight_command(recovery, private, backup, terminal, unicode, output), cwd=ROOT,
            ))
            if (receipt.get("verdict") != "PASS + 0 BLOCKERS"
                    or receipt.get("v14_authority_identity") != AUTHORITY
                    or receipt.get("launcher_boundary_identity") != launcher_boundary
                    or receipt.get("candidate_execution") != "0"
                    or receipt.get("successor_attempt_consumption") != "0"
                    or receipt.get("output") != "EMPTY_NATIVE_EXT4"):
                raise ValueError("final executable preflight rejected")
            state = {
                "schema": protocol.SCHEMA,
                "authority_identity": AUTHORITY,
                "run_identity": run_id,
                "qualification_evidence": False,
                "phase": "STARTING",
                "active_unit": unit,
                "accepted_checkpoints": 0,
                "completed_rows": 0,
                "sequence": 0,
            }
            protocol.write_state(state_path, state)
            try:
                subprocess.run([
                    "systemd-run", "--unit", unit.removesuffix(".service"), "--collect",
                    "--service-type=exec", "--property=KillMode=control-group",
                    "--property=Restart=no", "--setenv=PYTHONDONTWRITEBYTECODE=1",
                    "--setenv=PYTHONPATH=" + str(ROOT / "src"),
                    *command(recovery, private, backup, terminal, unicode, output),
                ], check=True, capture_output=True)
            except subprocess.CalledProcessError:
                state = {**state, "phase": "TERMINAL_FAILURE", "active_unit": None,
                         "sequence": state["sequence"] + 1}
                protocol.write_state(state_path, state)
                terminal_observation(monitor, run_id, "SYSTEMD_LAUNCH_REJECTED")
                final_heartbeat(monitor, run_id, launcher_boundary, state)
                return state
        if state["phase"] in ("COMPLETE", "TERMINAL_FAILURE"):
            final_heartbeat(monitor, run_id, launcher_boundary, state)
            return state
        if state["active_unit"] != unit or state["accepted_checkpoints"] > 12:
            raise ValueError("production supervisor state substitution")
        try:
            rows, batches = schedule(private / "candidate-alias-secret-v13.json")
        except Exception:
            subprocess.run(["systemctl", "kill", "--kill-who=all", "--signal=SIGTERM", unit], check=False)
            subprocess.run(["systemctl", "stop", unit], check=False)
            state = {**state, "phase": "TERMINAL_FAILURE", "active_unit": None,
                     "sequence": state["sequence"] + 1}
            protocol.write_state(state_path, state)
            terminal_observation(monitor, run_id, "SCHEDULE_CLOSURE_REJECTED")
            final_heartbeat(monitor, run_id, launcher_boundary, state)
            raise
        stopped = False

        def stop(_number, _frame):
            nonlocal stopped
            stopped = True

        old_term = signal.signal(signal.SIGTERM, stop)
        old_int = signal.signal(signal.SIGINT, stop)
        try:
            while True:
                status = protocol.systemd_state(unit)
                attempt_path = output / "attempt.json"
                attempt = load_json(attempt_path) if attempt_path.exists() else None
                if attempt is not None:
                    validator.validate_attempt(attempt, AUTHORITY)
                    accepted = accepted_progress(output, attempt, batches)
                    if accepted < state["accepted_checkpoints"]:
                        raise ValueError("accepted checkpoint regression")
                    if accepted > state["accepted_checkpoints"]:
                        state = {**state, "accepted_checkpoints": accepted,
                                 "completed_rows": accepted * 200,
                                 "sequence": state["sequence"] + 1}
                        protocol.write_state(state_path, state)
                protocol.atomic(monitor / "supervisor-heartbeat.json", {
                    "schema": SCHEMA, "authority_identity": AUTHORITY,
                    "launcher_boundary_identity": launcher_boundary,
                    "run_identity": run_id, "qualification_evidence": False,
                    "active_state": status["ActiveState"], "main_pid": status["MainPID"],
                    "attempt_present": attempt is not None,
                    "accepted_checkpoints": state["accepted_checkpoints"],
                    "completed_rows": state["completed_rows"],
                    "observed_unix_ns": time.time_ns(),
                })
                if stopped:
                    subprocess.run(["systemctl", "kill", "--kill-who=all", "--signal=SIGTERM", unit], check=False)
                    subprocess.run(["systemctl", "stop", unit], check=False)
                    state = {**state, "phase": "TERMINAL_FAILURE", "active_unit": None,
                             "sequence": state["sequence"] + 1}
                    protocol.write_state(state_path, state)
                    terminal_observation(monitor, run_id, "SUPERVISOR_SIGNAL", attempt)
                    return state
                if attempt is not None:
                    failure = validate_terminal(output, attempt)
                    if failure is not None:
                        state = {**state, "phase": "TERMINAL_FAILURE", "active_unit": None,
                                 "sequence": state["sequence"] + 1}
                        protocol.write_state(state_path, state)
                        terminal_observation(monitor, run_id, "QUALIFICATION_TERMINAL_FAILURE", attempt)
                        return state
                    completion = validate_completion(output, attempt, rows)
                    if (completion is not None and status["ActiveState"] == "inactive"
                            and status["Result"] == "success" and status["ExecMainStatus"] == "0"
                            and state["accepted_checkpoints"] == 12):
                        state = {**state, "phase": "COMPLETE", "active_unit": None,
                                 "sequence": state["sequence"] + 1}
                        protocol.write_state(state_path, state)
                        return state
                if status["ActiveState"] not in ("activating", "active"):
                    state = {**state, "phase": "TERMINAL_FAILURE", "active_unit": None,
                             "sequence": state["sequence"] + 1}
                    protocol.write_state(state_path, state)
                    terminal_observation(monitor, run_id, "WORKER_EXIT_WITHOUT_ACCEPTED_COMPLETION", attempt)
                    return state
                if state["phase"] == "STARTING":
                    state = {**state, "phase": "ACTIVE", "sequence": state["sequence"] + 1}
                    protocol.write_state(state_path, state)
                time.sleep(2)
        except Exception:
            subprocess.run(["systemctl", "kill", "--kill-who=all", "--signal=SIGTERM", unit], check=False)
            subprocess.run(["systemctl", "stop", unit], check=False)
            state = {**state, "phase": "TERMINAL_FAILURE", "active_unit": None,
                     "sequence": state["sequence"] + 1}
            protocol.write_state(state_path, state)
            terminal_observation(monitor, run_id, "SUPERVISOR_VALIDATION_ERROR")
            raise
        finally:
            signal.signal(signal.SIGTERM, old_term)
            signal.signal(signal.SIGINT, old_int)
            if state["phase"] in ("COMPLETE", "TERMINAL_FAILURE"):
                final_heartbeat(monitor, run_id, launcher_boundary, state)


def main() -> int:
    parser = argparse.ArgumentParser()
    for name in ("monitor", "recovery", "private", "backup", "terminal", "unicode", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    parser.add_argument("--owner-authorized", action="store_true")
    args = parser.parse_args()
    result = run(args.monitor, args.recovery, args.private, args.backup, args.terminal,
                 args.unicode, args.output, owner_authorized=args.owner_authorized)
    print(json.dumps(result, sort_keys=True))
    return 0 if result["phase"] == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
