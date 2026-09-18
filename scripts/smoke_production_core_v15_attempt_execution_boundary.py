"""Fixture-only V15 ownership smoke. Never touches the real V15 output."""
from __future__ import annotations

import json
import multiprocessing as mp
import os
import signal
import subprocess
import sys
import tempfile
from pathlib import Path

import execute_production_core_candidate_qualification_v15 as executor

REAL_OUTPUT = Path("/root/pf9-v15-preconsumption-output")


def _holder(output: str, acquired: mp.Event, release: mp.Event, events: mp.Queue) -> None:
    descriptor = executor.lock_directory(Path(output))
    events.put("OWNER_LOCKED")
    acquired.set()
    if not release.wait(10):
        events.put("OWNER_TIMEOUT")
        os.close(descriptor)
        return
    executor.atomic_no_replace(Path(output) / "attempt.json", b"fixture-only")
    events.put("OWNER_FIXTURE_CLAIMED")
    os.close(descriptor)


def _challenger(output: str, acquired: mp.Event, events: mp.Queue) -> None:
    if not acquired.wait(10):
        events.put("CHALLENGER_TIMEOUT")
        return
    try:
        descriptor = executor.lock_directory(Path(output))
    except SystemExit:
        events.put("CHALLENGER_REJECTED")
    else:
        os.close(descriptor)
        events.put("CHALLENGER_UNEXPECTED_OWNER")


def _crash_after_claim(output: str) -> None:
    executor.lock_directory(Path(output))
    executor.atomic_no_replace(Path(output) / "attempt.json", b"fixture-crash-claim")
    os.kill(os.getpid(), signal.SIGKILL)


def smoke() -> dict[str, object]:
    if os.name == "nt" or os.geteuid() != 0:
        raise ValueError("fixture smoke requires Linux root")
    source = executor.projected_mechanics()
    if ("            str(SNAPSHOT),\n" not in source
            or "            str(DRIVER_HELPER),\n" not in source
            or "            hashlib.sha256(read(DRIVER_HELPER)).hexdigest(),\n" not in source):
        raise ValueError("V15 16-argument projection missing")
    with tempfile.TemporaryDirectory(prefix="pcq-v15-fixture-", dir="/tmp") as temporary:
        output = Path(temporary) / "output"
        output.mkdir(mode=0o700)
        if output.resolve() == REAL_OUTPUT or REAL_OUTPUT.is_relative_to(output.resolve()):
            raise ValueError("fixture output overlaps real V15 output")
        context = mp.get_context("fork")
        acquired, release, events = context.Event(), context.Event(), context.Queue()
        holder = context.Process(target=_holder, args=(str(output), acquired, release, events))
        challenger = context.Process(target=_challenger, args=(str(output), acquired, events))
        holder.start()
        if events.get(timeout=15) != "OWNER_LOCKED":
            raise ValueError("fixture owner did not lock")
        challenger.start()
        if events.get(timeout=15) != "CHALLENGER_REJECTED":
            raise ValueError("parallel fixture attempt was not rejected")
        challenger.join(timeout=5)
        release.set()
        if events.get(timeout=15) != "OWNER_FIXTURE_CLAIMED":
            raise ValueError("fixture attempt claim failed")
        holder.join(timeout=5)
        if holder.exitcode != 0 or challenger.exitcode != 0:
            raise ValueError("fixture process lifecycle failed")
        fixture = output / "attempt.json"
        if fixture.read_bytes() != b"fixture-only":
            raise ValueError("fixture attempt was overwritten")
        try:
            executor.atomic_no_replace(fixture, b"illegal-retry")
        except SystemExit:
            pass
        else:
            raise ValueError("fixture retry unexpectedly overwrote attempt")
        failed = subprocess.run([sys.executable, "-B", "-c", "raise SystemExit(23)"],
                                capture_output=True, check=False)
        if failed.returncode != 23:
            raise ValueError("fixture terminal process failure not propagated")
        crashed_output = Path(temporary) / "crashed-output"
        crashed_output.mkdir(mode=0o700)
        crashed = context.Process(target=_crash_after_claim, args=(str(crashed_output),))
        crashed.start()
        crashed.join(timeout=5)
        if crashed.is_alive():
            crashed.kill()
            crashed.join(timeout=5)
            raise ValueError("fixture crashed worker orphaned")
        if crashed.exitcode != -signal.SIGKILL:
            raise ValueError("fixture SIGKILL lifecycle mismatch")
        recovered_lock = executor.lock_directory(crashed_output)
        try:
            try:
                executor.atomic_no_replace(crashed_output / "attempt.json", b"illegal-retry")
            except SystemExit:
                pass
            else:
                raise ValueError("crashed fixture attempt was reconsumed")
        finally:
            os.close(recovered_lock)
        if (crashed_output / "attempt.json").read_bytes() != b"fixture-crash-claim":
            raise ValueError("crashed fixture claim changed")
    if (REAL_OUTPUT / "attempt.json").exists() or any(REAL_OUTPUT.iterdir()):
        raise ValueError("real V15 output changed during fixture smoke")
    return {"verdict": "PASS", "candidate_inference": 0, "real_attempt_consumption": 0,
            "fixture_output": "ISOLATED_TEMPORARY", "parallel_owner": "REJECTED",
            "fixture_no_clobber": "PASS", "terminal_process_failure": "PROPAGATED",
            "sigkill_after_claim": "NO_RECONSUMPTION_NO_ORPHAN",
            "real_attempt_json": "ABSENT"}


if __name__ == "__main__":
    print(json.dumps(smoke(), sort_keys=True))
