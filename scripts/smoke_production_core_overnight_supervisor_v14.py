"""No-candidate lifecycle smoke for the V14 systemd-backed supervisor."""
from __future__ import annotations

import json
import signal
import subprocess
import sys
import tempfile
import time
from pathlib import Path

from pastila_scout import production_core_overnight_supervisor_v14 as supervisor


def main() -> int:
    plan = {
        "schema": "pastila-production-core-v14-supervisor-smoke-plan",
        "authority_identity": supervisor.AUTHORITY,
        "candidate_execution": False,
        "attempt_consumption": False,
        "tasks": [{"ordinal": ordinal, "rows": 200, "delay_ms": 500} for ordinal in range(1, 4)],
    }
    with tempfile.TemporaryDirectory(prefix="pf9-v14-supervisor-smoke-") as temporary:
        root = Path(temporary)
        root.chmod(0o700)
        result = supervisor.supervise(root, plan)
        if (result["phase"] != "COMPLETE" or result["accepted_checkpoints"] != 3
                or result["completed_rows"] != 600 or result["active_unit"] is not None):
            raise ValueError("synthetic lifecycle incomplete")
        if supervisor.supervise(root, plan) != result:
            raise ValueError("completed state restart changed progress")
        heartbeat = json.loads((root / "supervisor-heartbeat.json").read_bytes())
        if heartbeat["qualification_evidence"] is not False or heartbeat["phase"] != "COMPLETE":
            raise ValueError("heartbeat confused with qualification evidence")
        if list(root.glob("attempt.json")) or list(root.glob("completion.json")):
            raise ValueError("candidate evidence appeared in synthetic smoke")
        print(json.dumps({
            "verdict": "PASS",
            "smoke_run_identity": supervisor.verify_smoke_plan(plan),
            "accepted_checkpoints": result["accepted_checkpoints"],
            "completed_rows": result["completed_rows"],
            "restart_without_recalculation": "PASS",
            "candidate_execution": 0,
            "new_attempt_consumption": 0,
        }, sort_keys=True))
    lifecycle_probe(signal.SIGKILL, "COMPLETE")
    lifecycle_probe(signal.SIGTERM, "TERMINAL_FAILURE")
    worker_sigkill_probe()
    return 0


def lifecycle_probe(stop_signal: int, expected_phase: str) -> None:
    plan = {
        "schema": "pastila-production-core-v14-supervisor-smoke-plan",
        "authority_identity": supervisor.AUTHORITY,
        "candidate_execution": False,
        "attempt_consumption": False,
        "tasks": [{"ordinal": 1, "rows": 200, "delay_ms": 5000}],
    }
    with tempfile.TemporaryDirectory(prefix="pf9-v14-supervisor-lifecycle-") as temporary:
        root = Path(temporary)
        root.chmod(0o700)
        plan_path = root / "plan.json"
        plan_path.write_bytes(supervisor.canonical(plan))
        unit = supervisor.unit_name(supervisor.verify_smoke_plan(plan), 1)
        process = subprocess.Popen([
            sys.executable, str(Path(supervisor.__file__).resolve()),
            "--root", str(root), "--plan", str(plan_path),
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                state_path = root / "supervisor-state.json"
                if state_path.exists() and json.loads(state_path.read_bytes()).get("phase") == "ACTIVE":
                    break
                time.sleep(0.05)
            else:
                raise ValueError("supervisor did not enter ACTIVE")
            process.send_signal(stop_signal)
            process.wait(timeout=5)
            if stop_signal == signal.SIGKILL:
                result = supervisor.supervise(root, plan)
            else:
                result = supervisor.read_state(state_path, supervisor.verify_smoke_plan(plan))
            if result["phase"] != expected_phase:
                raise ValueError("supervisor lifecycle recovery mismatch")
            status = supervisor.systemd_state(unit)
            if status["ActiveState"] in ("active", "activating"):
                raise ValueError("worker unit remained active after lifecycle probe")
            print(json.dumps({
                "probe": "SIGKILL_RESTART" if stop_signal == signal.SIGKILL else "SIGTERM_PROPAGATION",
                "verdict": "PASS",
                "phase": expected_phase,
                "candidate_execution": 0,
                "new_attempt_consumption": 0,
            }, sort_keys=True))
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            subprocess.run(["systemctl", "stop", unit], check=False, capture_output=True)


def worker_sigkill_probe() -> None:
    plan = {
        "schema": "pastila-production-core-v14-supervisor-smoke-plan",
        "authority_identity": supervisor.AUTHORITY,
        "candidate_execution": False,
        "attempt_consumption": False,
        "tasks": [{"ordinal": 1, "rows": 200, "delay_ms": 5000}],
    }
    with tempfile.TemporaryDirectory(prefix="pf9-v14-supervisor-kill-") as temporary:
        root = Path(temporary)
        root.chmod(0o700)
        plan_path = root / "plan.json"
        plan_path.write_bytes(supervisor.canonical(plan))
        unit = supervisor.unit_name(supervisor.verify_smoke_plan(plan), 1)
        process = subprocess.Popen([
            sys.executable, str(Path(supervisor.__file__).resolve()),
            "--root", str(root), "--plan", str(plan_path),
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        try:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                state_path = root / "supervisor-state.json"
                if state_path.exists() and json.loads(state_path.read_bytes()).get("phase") == "ACTIVE":
                    break
                time.sleep(0.05)
            else:
                raise ValueError("worker did not enter ACTIVE")
            subprocess.run(["systemctl", "kill", "--kill-who=all", "--signal=SIGKILL", unit], check=True)
            process.wait(timeout=10)
            result = supervisor.read_state(state_path, supervisor.verify_smoke_plan(plan))
            if result["phase"] != "TERMINAL_FAILURE" or result["accepted_checkpoints"] != 0:
                raise ValueError("worker SIGKILL was not terminal")
            if supervisor.systemd_state(unit)["ActiveState"] in ("active", "activating"):
                raise ValueError("SIGKILL left an active worker")
            print(json.dumps({"probe": "WORKER_SIGKILL", "verdict": "PASS",
                              "candidate_execution": 0, "new_attempt_consumption": 0}, sort_keys=True))
        finally:
            if process.poll() is None:
                process.kill()
                process.wait(timeout=5)
            subprocess.run(["systemctl", "stop", unit], check=False, capture_output=True)


if __name__ == "__main__":
    raise SystemExit(main())
