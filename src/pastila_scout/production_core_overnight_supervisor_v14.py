"""Persistent supervisor protocol for a future V14 qualification launcher.

This module can run only synthetic smoke tasks. A production command requires a
separately signed launcher boundary; no candidate path is reachable here.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
import os
import re
import signal
import subprocess
import sys
import time
from pathlib import Path

AUTHORITY = "27955b01b3254a08679b200a3f20d4c5d382f582834b98119f701f37cc86b5ec"
SCHEMA = "pastila-production-core-v14-supervisor-observation"
UNIT_PREFIX = "pf9-v14-smoke-"


def canonical(value: object) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":")).encode()


def sha(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def atomic(path: Path, value: dict) -> None:
    raw = canonical(value) + b"\n"
    temporary = path.with_name(f".{path.name}.{os.getpid()}.tmp")
    with temporary.open("xb") as handle:
        handle.write(raw)
        handle.flush()
        os.fsync(handle.fileno())
    os.replace(temporary, path)
    fd = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def write_state(path: Path, state: dict) -> None:
    atomic(path, {**state, "state_identity": sha(canonical(state))})


def systemd_state(unit: str) -> dict[str, str]:
    completed = subprocess.run(
        ["systemctl", "show", unit, "--property=ActiveState,SubState,Result,MainPID,ExecMainStatus",
         "--no-pager"], capture_output=True, text=True, check=True,
    )
    result = dict(line.split("=", 1) for line in completed.stdout.splitlines() if "=" in line)
    if set(result) != {"ActiveState", "SubState", "Result", "MainPID", "ExecMainStatus"}:
        raise ValueError("systemd status incomplete")
    return result


def unit_name(run_identity: str, ordinal: int) -> str:
    return f"{UNIT_PREFIX}{run_identity[:16]}-{ordinal:02d}.service"


def verify_smoke_plan(plan: dict) -> str:
    if (plan.get("schema") != "pastila-production-core-v14-supervisor-smoke-plan"
            or plan.get("authority_identity") != AUTHORITY
            or plan.get("candidate_execution") is not False
            or plan.get("attempt_consumption") is not False
            or not isinstance(plan.get("tasks"), list)
            or not 1 <= len(plan["tasks"]) <= 12):
        raise ValueError("smoke-only supervisor plan rejected")
    for ordinal, task in enumerate(plan["tasks"], 1):
        if (not isinstance(task, dict)
                or set(task) != {"ordinal", "rows", "delay_ms"}
                or type(task["ordinal"]) is not int or task["ordinal"] != ordinal
                or type(task["rows"]) is not int or task["rows"] != 200
                or type(task["delay_ms"]) is not int or not 100 <= task["delay_ms"] <= 5000):
            raise ValueError("task schedule mismatch")
    return sha(canonical(plan))


def read_state(path: Path, run_identity: str) -> dict:
    if path.is_symlink() or not path.is_file():
        raise ValueError("supervisor state path substitution")
    state = json.loads(path.read_bytes())
    core = dict(state)
    recorded = core.pop("state_identity", None)
    if (set(core) != {"schema", "authority_identity", "run_identity", "qualification_evidence",
                      "phase", "active_unit", "accepted_checkpoints", "completed_rows", "sequence"}
            or recorded != sha(canonical(core))
            or state.get("schema") != SCHEMA
            or state.get("authority_identity") != AUTHORITY
            or state.get("run_identity") != run_identity
            or state.get("qualification_evidence") is not False
            or state.get("phase") not in {"READY", "STARTING", "ACTIVE", "TERMINAL_FAILURE", "COMPLETE"}
            or (state.get("phase") in {"STARTING", "ACTIVE"}) != (state.get("active_unit") is not None)
            or type(state.get("accepted_checkpoints")) is not int
            or type(state.get("completed_rows")) is not int
            or type(state.get("sequence")) is not int
            or state["accepted_checkpoints"] < 0 or state["sequence"] < 0
            or state["completed_rows"] != state["accepted_checkpoints"] * 200):
        raise ValueError("supervisor state substitution")
    return core


def marker_valid(path: Path, run_identity: str, ordinal: int) -> bool:
    if path.is_symlink() or not path.is_file():
        return False
    try:
        marker = json.loads(path.read_bytes())
    except (OSError, ValueError):
        return False
    return marker == {
        "schema": "pastila-production-core-v14-synthetic-smoke-marker",
        "run_identity": run_identity,
        "ordinal": ordinal,
        "rows": 200,
        "qualification_evidence": False,
    }


def supervise(root: Path, plan: dict, *, tick_seconds: float = 0.2) -> dict:
    run_identity = verify_smoke_plan(plan)
    if root.is_symlink() or not root.is_dir() or root.stat().st_mode & 0o077:
        raise ValueError("owner-only native supervisor root required")
    lock = root / "supervisor.lock"
    if lock.is_symlink() or (root / "supervisor-heartbeat.json").is_symlink():
        raise ValueError("supervisor runtime path substitution")
    with lock.open("a+b") as handle:
        try:
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise ValueError("parallel supervisor rejected") from error
        state_path = root / "supervisor-state.json"
        if state_path.exists():
            state = read_state(state_path, run_identity)
        else:
            state = {
                "schema": SCHEMA,
                "authority_identity": AUTHORITY,
                "run_identity": run_identity,
                "qualification_evidence": False,
                "phase": "READY",
                "active_unit": None,
                "accepted_checkpoints": 0,
                "completed_rows": 0,
                "sequence": 0,
            }
            write_state(state_path, state)
        if state["accepted_checkpoints"] > len(plan["tasks"]):
            raise ValueError("accepted checkpoint count exceeds plan")
        if state["phase"] == "COMPLETE" and state["accepted_checkpoints"] != len(plan["tasks"]):
            raise ValueError("false completion state")
        if state["phase"] in ("TERMINAL_FAILURE", "COMPLETE"):
            atomic(root / "supervisor-heartbeat.json", {
                "schema": SCHEMA, "authority_identity": AUTHORITY,
                "run_identity": run_identity, "qualification_evidence": False,
                "phase": state["phase"], "active_unit": None, "active_state": "inactive",
                "completed_rows": state["completed_rows"],
                "accepted_checkpoints": state["accepted_checkpoints"],
                "observed_unix_ns": time.time_ns(), "sequence": state["sequence"],
            })
            return state
        active = state.get("active_unit")
        if active is not None and (not isinstance(active, str) or not re.fullmatch(r"pf9-v14-smoke-[a-f0-9]{16}-\d{2}\.service", active)):
            raise ValueError("active unit substitution")
        stopped = False

        def stop(_number, _frame):
            nonlocal stopped
            stopped = True

        previous_term = signal.signal(signal.SIGTERM, stop)
        previous_int = signal.signal(signal.SIGINT, stop)
        try:
            while state["accepted_checkpoints"] < len(plan["tasks"]):
                ordinal = state["accepted_checkpoints"] + 1
                expected_unit = unit_name(run_identity, ordinal)
                if active is None:
                    marker = root / f"smoke-checkpoint-{ordinal:02d}.json"
                    if marker.exists():
                        raise ValueError("unaccepted checkpoint collision")
                    if systemd_state(expected_unit)["ActiveState"] in ("active", "activating"):
                        raise ValueError("existing worker unit rejected")
                    active = expected_unit
                    state = {**state, "phase": "STARTING", "active_unit": active, "sequence": state["sequence"] + 1}
                    write_state(state_path, state)
                    try:
                        subprocess.run([
                            "systemd-run", "--unit", expected_unit.removesuffix(".service"), "--collect",
                            "--service-type=exec", "--property=KillMode=control-group",
                            "--property=Restart=no", sys.executable,
                            str(Path(__file__).resolve()), "--synthetic-worker", str(root), run_identity,
                            str(ordinal), str(plan["tasks"][ordinal - 1]["delay_ms"]),
                        ], check=True, capture_output=True)
                    except subprocess.CalledProcessError:
                        state = {**state, "phase": "TERMINAL_FAILURE", "active_unit": None,
                                 "sequence": state["sequence"] + 1}
                        write_state(state_path, state)
                        break
                elif active != expected_unit:
                    raise ValueError("checkpoint/unit ordinal mismatch")
                status = systemd_state(active)
                if state["phase"] == "STARTING":
                    if status["ActiveState"] not in ("active", "activating") and not marker_valid(
                            root / f"smoke-checkpoint-{ordinal:02d}.json", run_identity, ordinal):
                        state = {**state, "phase": "TERMINAL_FAILURE", "active_unit": None,
                                 "sequence": state["sequence"] + 1}
                        write_state(state_path, state)
                        break
                    state = {**state, "phase": "ACTIVE", "sequence": state["sequence"] + 1}
                    write_state(state_path, state)
                heartbeat = {
                    "schema": SCHEMA,
                    "authority_identity": AUTHORITY,
                    "run_identity": run_identity,
                    "qualification_evidence": False,
                    "phase": state["phase"],
                    "active_unit": active,
                    "active_state": status["ActiveState"],
                    "completed_rows": state["completed_rows"],
                    "accepted_checkpoints": state["accepted_checkpoints"],
                    "observed_unix_ns": time.time_ns(),
                    "sequence": state["sequence"],
                }
                atomic(root / "supervisor-heartbeat.json", heartbeat)
                if stopped:
                    subprocess.run(["systemctl", "kill", "--kill-who=all", "--signal=SIGTERM", active], check=False)
                    subprocess.run(["systemctl", "stop", active], check=False)
                    state = {**state, "phase": "TERMINAL_FAILURE", "active_unit": None, "sequence": state["sequence"] + 1}
                    write_state(state_path, state)
                    break
                if status["ActiveState"] in ("activating", "active"):
                    time.sleep(tick_seconds)
                    continue
                marker = root / f"smoke-checkpoint-{ordinal:02d}.json"
                if status["Result"] != "success" or status["ExecMainStatus"] != "0" or not marker_valid(marker, run_identity, ordinal):
                    state = {**state, "phase": "TERMINAL_FAILURE", "active_unit": None, "sequence": state["sequence"] + 1}
                    write_state(state_path, state)
                    break
                state = {**state, "phase": "READY", "active_unit": None,
                         "accepted_checkpoints": ordinal, "completed_rows": ordinal * 200,
                         "sequence": state["sequence"] + 1}
                write_state(state_path, state)
                active = None
            if state["accepted_checkpoints"] == len(plan["tasks"]):
                state = {**state, "phase": "COMPLETE", "active_unit": None,
                         "sequence": state["sequence"] + 1}
                write_state(state_path, state)
            atomic(root / "supervisor-heartbeat.json", {
                "schema": SCHEMA,
                "authority_identity": AUTHORITY,
                "run_identity": run_identity,
                "qualification_evidence": False,
                "phase": state["phase"],
                "active_unit": None,
                "active_state": "inactive",
                "completed_rows": state["completed_rows"],
                "accepted_checkpoints": state["accepted_checkpoints"],
                "observed_unix_ns": time.time_ns(),
                "sequence": state["sequence"],
            })
            return state
        finally:
            signal.signal(signal.SIGTERM, previous_term)
            signal.signal(signal.SIGINT, previous_int)


def synthetic_worker(root: Path, run_identity: str, ordinal: int, delay_ms: int) -> None:
    if (not re.fullmatch(r"[a-f0-9]{64}", run_identity)
            or not 1 <= ordinal <= 12 or not 100 <= delay_ms <= 5000):
        raise ValueError("synthetic worker input rejected")
    time.sleep(delay_ms / 1000)
    atomic(root / f"smoke-checkpoint-{ordinal:02d}.json", {
        "schema": "pastila-production-core-v14-synthetic-smoke-marker",
        "run_identity": run_identity,
        "ordinal": ordinal,
        "rows": 200,
        "qualification_evidence": False,
    })


def main() -> int:
    if len(sys.argv) == 6 and sys.argv[1] == "--synthetic-worker":
        synthetic_worker(Path(sys.argv[2]), sys.argv[3], int(sys.argv[4]), int(sys.argv[5]))
        return 0
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, required=True)
    parser.add_argument("--plan", type=Path, required=True)
    args = parser.parse_args()
    result = supervise(args.root, json.loads(args.plan.read_bytes()))
    print(json.dumps(result, sort_keys=True))
    return 0 if result["phase"] == "COMPLETE" else 1


if __name__ == "__main__":
    raise SystemExit(main())
