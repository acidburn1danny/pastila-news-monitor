"""Bounded DrvFS and synthetic child-lifecycle operational preflight."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import sys
import time
import uuid
from pathlib import Path

from pastila_scout.wsl_execution_v1 import (
    canonical_model_profile_v1,
    canonical_receipt_bytes_v1,
    windows_path_to_wsl_v1,
)
from pastila_scout.wsl_execution_v1_1 import WslExecutionBoundaryV1_1

ZERO_MODEL_PREFLIGHT_IDENTITY = (
    "2dfef8ec30a914907fbb5b4201d14b532623c3d8ca42ebe0376c70c3840c8d84"
)
MODULE_NAME = (
    "pastila_scout.semantic_admission_v2."
    "stage_p_construction_obligation_v2_zero_model_operational_preflight_v1"
)
_PROOF_BYTES = b"PASTILA_CONSTRUCTION_OBLIGATION_V2_DRVFS_HARDLINK_PROOF_V1\n"


def run_zero_model_worker_v1(*, evidence_root: Path) -> bytes:
    """Run one hard-link proof and reap one synthetic sleeping child."""
    if evidence_root.exists() or evidence_root.is_symlink():
        raise FileExistsError("ZERO_MODEL_PREFLIGHT_EVIDENCE_ROOT_EXISTS")
    if (
        not evidence_root.is_absolute()
        or evidence_root.parent.resolve(strict=True) != evidence_root.parent
    ):
        raise ValueError("ZERO_MODEL_PREFLIGHT_EVIDENCE_ROOT_INVALID")
    evidence_root.mkdir(mode=0o700, parents=False, exist_ok=False)
    proof = evidence_root / "hardlink-proof.bin"
    _publish(proof, _PROOF_BYTES)
    if proof.read_bytes() != _PROOF_BYTES:
        raise RuntimeError("ZERO_MODEL_PREFLIGHT_DRVFS_BYTES_MISMATCH")

    context = multiprocessing.get_context("spawn")
    ready = context.Queue(maxsize=1)
    child = context.Process(target=_synthetic_sleeper, args=(ready,), daemon=False)
    child.start()
    child_pid = ready.get(block=True, timeout=10.0)
    if type(child_pid) is not int or child_pid <= 0 or not child.is_alive():
        raise RuntimeError("ZERO_MODEL_PREFLIGHT_CHILD_START_UNCONFIRMED")
    child.terminate()
    child.join(10.0)
    termination = "TERMINATED"
    if child.is_alive():
        child.kill()
        child.join(10.0)
        termination = "KILLED"
    ready.close()
    ready.join_thread()
    if child.is_alive() or child.exitcode is None:
        raise RuntimeError("ZERO_MODEL_PREFLIGHT_CHILD_REAP_UNCONFIRMED")
    proc_absent = not Path(f"/proc/{child_pid}").exists()
    if not proc_absent:
        raise RuntimeError("ZERO_MODEL_PREFLIGHT_CHILD_PROC_STILL_PRESENT")
    value = {
        "schema_name": "pastila-construction-obligation-v2-zero-model-operational-preflight",
        "schema_version": "1.0.0",
        "preflight_identity": ZERO_MODEL_PREFLIGHT_IDENTITY,
        "drvfs_hardlink_publication": "PASS",
        "hardlink_proof_byte_count": len(_PROOF_BYTES),
        "hardlink_proof_sha256": hashlib.sha256(_PROOF_BYTES).hexdigest(),
        "synthetic_child_pid": child_pid,
        "termination": termination,
        "child_exit_code": child.exitcode,
        "child_reaped": True,
        "child_proc_absent": proc_absent,
        "tokenizer_loads": 0,
        "model_loads": 0,
        "generation_calls": 0,
        "report_identity": "",
    }
    value["report_identity"] = hashlib.sha256(
        _canonical(
            {key: item for key, item in value.items() if key != "report_identity"}
        )
    ).hexdigest()
    raw = _canonical(value)
    _publish(evidence_root / "worker-report.json", raw)
    return raw


def run_zero_model_host_v1(*, project_root: Path, evidence_root: Path) -> bytes:
    """Execute the worker once through canonical WSL V1.1 and seal receipts."""
    project_root.resolve(strict=True)
    if evidence_root.exists() or not evidence_root.is_absolute():
        raise FileExistsError("ZERO_MODEL_PREFLIGHT_EVIDENCE_ROOT_EXISTS_OR_INVALID")
    boundary = WslExecutionBoundaryV1_1(
        canonical_model_profile_v1(with_pydantic_bridge=True)
    )
    invocation = boundary.build_invocation(
        consumer_id="construction-obligation-v2-zero-model-preflight-v1",
        authority_reference="zero-model-operational-preflight:"
        + ZERO_MODEL_PREFLIGHT_IDENTITY,
        arguments=("-m", MODULE_NAME, "worker", windows_path_to_wsl_v1(evidence_root)),
    )
    result = boundary.execute(invocation, timeout_seconds=60.0)
    if not result.succeeded:
        raise RuntimeError(
            f"ZERO_MODEL_PREFLIGHT_WSL_FAILED:{result.receipt.failure_code}"
        )
    worker_raw = (evidence_root / "worker-report.json").read_bytes()
    worker = json.loads(worker_raw)
    if (
        worker.get("preflight_identity") != ZERO_MODEL_PREFLIGHT_IDENTITY
        or worker.get("drvfs_hardlink_publication") != "PASS"
        or worker.get("child_reaped") is not True
        or worker.get("child_proc_absent") is not True
        or worker.get("tokenizer_loads") != 0
        or worker.get("model_loads") != 0
        or worker.get("generation_calls") != 0
    ):
        raise RuntimeError("ZERO_MODEL_PREFLIGHT_WORKER_REPORT_INVALID")
    expected = hashlib.sha256(
        _canonical(
            {key: item for key, item in worker.items() if key != "report_identity"}
        )
    ).hexdigest()
    if worker.get("report_identity") != expected or worker_raw != _canonical(worker):
        raise RuntimeError("ZERO_MODEL_PREFLIGHT_WORKER_REPORT_SEAL_INVALID")
    wsl_raw = canonical_receipt_bytes_v1(result.receipt)
    _publish(evidence_root / "wsl-execution-receipt.json", wsl_raw)
    value = {
        "schema_name": "pastila-construction-obligation-v2-zero-model-preflight-host-receipt",
        "schema_version": "1.0.0",
        "preflight_identity": ZERO_MODEL_PREFLIGHT_IDENTITY,
        "command_identity": invocation.command_identity,
        "worker_report_identity": expected,
        "wsl_execution_receipt_sha256": hashlib.sha256(wsl_raw).hexdigest(),
        "wsl_return_code": result.return_code,
        "stdout_sha256": hashlib.sha256(result.stdout.encode()).hexdigest(),
        "stderr_sha256": hashlib.sha256(result.stderr.encode()).hexdigest(),
        "tokenizer_loads": 0,
        "model_loads": 0,
        "generation_calls": 0,
        "receipt_identity": "",
    }
    value["receipt_identity"] = hashlib.sha256(
        _canonical(
            {key: item for key, item in value.items() if key != "receipt_identity"}
        )
    ).hexdigest()
    raw = _canonical(value)
    _publish(evidence_root / "host-receipt.json", raw)
    return raw


def _synthetic_sleeper(ready) -> None:
    ready.put(os.getpid(), block=True, timeout=5.0)
    while True:
        time.sleep(1.0)


def _publish(target: Path, raw: bytes) -> None:
    pending = target.parent / (".pending-" + uuid.uuid4().hex)
    descriptor = None
    try:
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0)
        descriptor = os.open(pending, flags, 0o600)
        written = 0
        while written < len(raw):
            written += os.write(descriptor, raw[written:])
        os.fsync(descriptor)
        os.close(descriptor)
        descriptor = None
        os.link(pending, target)
    finally:
        if descriptor is not None:
            os.close(descriptor)
        pending.unlink(missing_ok=True)


def _canonical(value: dict[str, object]) -> bytes:
    return (
        json.dumps(
            value,
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
        + "\n"
    ).encode()


def main(arguments: list[str]) -> int:
    if len(arguments) == 2 and arguments[0] == "worker":
        run_zero_model_worker_v1(evidence_root=Path(arguments[1]))
        return 0
    if len(arguments) == 3 and arguments[0] == "host":
        run_zero_model_host_v1(
            project_root=Path(arguments[1]), evidence_root=Path(arguments[2])
        )
        return 0
    raise SystemExit(
        "usage: preflight worker EVIDENCE_ROOT | host PROJECT_ROOT EVIDENCE_ROOT"
    )


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))

__all__ = (
    "MODULE_NAME",
    "ZERO_MODEL_PREFLIGHT_IDENTITY",
    "run_zero_model_host_v1",
    "run_zero_model_worker_v1",
)
