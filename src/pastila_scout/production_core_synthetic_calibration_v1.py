"""Candidate-free structural calibration for Production Core qualification."""

from __future__ import annotations

import argparse
import ctypes
import hashlib
import json
import math
import os
import platform
import subprocess
import sys
import time
from pathlib import Path


def _canonical(value: object) -> bytes:
    return (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n").encode()


def _synthetic_payload() -> tuple[dict[str, object], ...]:
    return tuple(
        {
            "case_id": f"synthetic-{index:03d}",
            "authority": hashlib.sha256(f"authority-{index}".encode()).hexdigest(),
            "romanian_text": "Știință, incertitudine și sursă explicită.",
            "claims": tuple(f"claim-{index}-{part}" for part in range(8)),
        }
        for index in range(200)
    )


def structural_probe(*, rounds: int) -> dict[str, object]:
    if type(rounds) is not int or not 1 <= rounds <= 10_000:
        raise ValueError("invalid synthetic round count")
    payload = _synthetic_payload()
    started = time.monotonic_ns()
    digest = b""
    output_bytes = 0
    for iteration in range(rounds):
        encoded = _canonical({"iteration": iteration, "cases": payload})
        output_bytes = len(encoded)
        digest = hashlib.sha256(digest + encoded).digest()
    elapsed = time.monotonic_ns() - started
    return {
        "elapsed_ns": elapsed,
        "output_bytes": output_bytes,
        "result_sha256": digest.hex(),
        "peak_rss_bytes": _peak_rss_bytes(),
    }


def _peak_rss_bytes() -> int:
    if platform.system() != "Windows":
        import resource

        return int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss) * 1024

    class Counters(ctypes.Structure):
        _fields_ = [
            ("cb", ctypes.c_ulong),
            ("PageFaultCount", ctypes.c_ulong),
            ("PeakWorkingSetSize", ctypes.c_size_t),
            ("WorkingSetSize", ctypes.c_size_t),
            ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPagedPoolUsage", ctypes.c_size_t),
            ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
            ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
            ("PagefileUsage", ctypes.c_size_t),
            ("PeakPagefileUsage", ctypes.c_size_t),
        ]

    counters = Counters()
    counters.cb = ctypes.sizeof(counters)
    kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)
    psapi = ctypes.WinDLL("psapi", use_last_error=True)
    kernel32.GetCurrentProcess.argtypes = []
    kernel32.GetCurrentProcess.restype = ctypes.c_void_p
    psapi.GetProcessMemoryInfo.argtypes = [
        ctypes.c_void_p,
        ctypes.POINTER(Counters),
        ctypes.c_ulong,
    ]
    psapi.GetProcessMemoryInfo.restype = ctypes.c_int
    process = kernel32.GetCurrentProcess()
    if not psapi.GetProcessMemoryInfo(process, ctypes.byref(counters), counters.cb):
        raise ctypes.WinError(ctypes.get_last_error())
    return int(counters.PeakWorkingSetSize)


def _child(arguments: tuple[str, ...]) -> subprocess.Popen[str]:
    environment = {"PYTHONHASHSEED": "0", "PYTHONIOENCODING": "utf-8"}
    return subprocess.Popen(
        [sys.executable, "-I", str(Path(__file__).resolve()), *arguments],
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        env=environment,
    )


def calibrate(*, trials: int = 20, rounds: int = 25) -> dict[str, object]:
    if type(trials) is not int or not 2 <= trials <= 100:
        raise ValueError("invalid trial count")
    samples: list[dict[str, object]] = []
    for _ in range(trials):
        child = _child(("--structural-worker", str(rounds)))
        stdout, stderr = child.communicate(timeout=60)
        if child.returncode != 0 or stderr or not stdout.endswith("\n"):
            raise RuntimeError("structural worker failed closed")
        samples.append(json.loads(stdout))
    cancellation_ns: list[int] = []
    for _ in range(trials):
        child = _child(("--cancellation-worker",))
        assert child.stdout is not None
        if child.stdout.readline() != "READY\n":
            child.kill()
            raise RuntimeError("cancellation worker failed to become ready")
        started = time.monotonic_ns()
        child.terminate()
        child.wait(timeout=10)
        cancellation_ns.append(time.monotonic_ns() - started)
    elapsed = sorted(int(sample["elapsed_ns"]) for sample in samples)
    rss = [int(sample["peak_rss_bytes"]) for sample in samples]
    output = {int(sample["output_bytes"]) for sample in samples}
    identities = {str(sample["result_sha256"]) for sample in samples}
    p99 = elapsed[math.ceil(len(elapsed) * 0.99) - 1]
    max_cancel = max(cancellation_ns)
    return {
        "schema": "pastila-production-core-candidate-free-calibration",
        "schema_version": 1,
        "authority_status": "NON_AUTHORITATIVE_HOST_SUPERVISOR_PROBE",
        "candidate_model_loaded": False,
        "candidate_result_inspected": False,
        "platform": {"os": platform.system(), "machine": platform.machine()},
        "runtime_sha256": hashlib.sha256(Path(sys.executable).read_bytes()).hexdigest(),
        "trials": trials,
        "rounds": rounds,
        "observed": {
            "wall_time_ns_p99": p99,
            "peak_rss_bytes_max": max(rss),
            "cancellation_ns_max": max_cancel,
            "structural_output_bytes": output.pop() if len(output) == 1 else None,
            "deterministic_result_identity": identities.pop() if len(identities) == 1 else None,
        },
        "proposed_envelopes": {
            "cancellation_deadline_ns": max(500_000_000, math.ceil(3 * max_cancel / 50_000_000) * 50_000_000),
            "wall_time_ns": max(1_000_000_000, math.ceil(2 * p99 / 100_000_000) * 100_000_000),
            "peak_rss_bytes": math.ceil(1.5 * max(rss) / 67_108_864) * 67_108_864,
            "technical_output_bytes": None,
            "technical_output_tokens": None,
        },
    }


def _main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--structural-worker", type=int)
    parser.add_argument("--cancellation-worker", action="store_true")
    parser.add_argument("--trials", type=int, default=20)
    arguments = parser.parse_args()
    if arguments.structural_worker is not None:
        print(json.dumps(structural_probe(rounds=arguments.structural_worker), sort_keys=True))
        return 0
    if arguments.cancellation_worker:
        print("READY", flush=True)
        while True:
            hashlib.sha256(os.urandom(32)).digest()
    print(json.dumps(calibrate(trials=arguments.trials), sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
