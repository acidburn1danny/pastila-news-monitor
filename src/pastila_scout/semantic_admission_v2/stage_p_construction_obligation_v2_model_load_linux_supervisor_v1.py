"""Dedicated Linux supervisor for a bounded, one-child, load-only attempt."""
from __future__ import annotations

import hashlib
import json
import multiprocessing
import queue
import subprocess
import sys
from importlib.metadata import version
from pathlib import Path

from .append_only_lifecycle_v1 import AppendOnlyLifecycleV1
from .stage_p_construction_obligation_v2_model_load_authority_contract_v1 import (
    PACKAGE_IDENTITIES, PreloadEnvironmentV1, parse_load_only_authority_v1,
    validate_preload_environment_v1,
)
from .stage_p_construction_obligation_v2_model_load_only_candidate_v1_5 import (
    LOAD_ONLY_CANDIDATE_IDENTITY,
)
from .stage_p_construction_obligation_v2_model_load_policy_gate_v1 import (
    canonical_observed_model_load_policy_v1, validate_model_load_policy_gate_v1,
)
from .stage_p_construction_obligation_v2_model_load_linux_worker_v1 import (
    ADAPTER_PATH, BASE_MODEL_PATH, run_load_only_linux_child_v1,
)


SUPERVISOR_IDENTITY = "8e228417a6644a8351da653560874295c7ead8ac23f4df7cfc8ff93d22895453"
DEFAULT_TIMEOUT_SECONDS = 900.0
IMMUTABLE_MANIFEST_ARTIFACT_SHA256 = "a96745c2554c84bf43616a4f8184a1c1f6081167aea280f9cac0b48e3ca4a4cd"
WORKER_SOURCE_SHA256 = "c4ad1c3397c48b40729561ad64e05cda6ba123d7f9ed90c8cbf7b77479b047b6"


def supervise_load_only_v1(*, policy_receipt_path: Path, authority_receipt_path: Path,
                           lifecycle_root: Path, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> str:
    if type(timeout_seconds) is not float or not 1.0 <= timeout_seconds <= 900.0:
        raise ValueError("MODEL_LOAD_SUPERVISOR_TIMEOUT_INVALID")
    raw_policy = policy_receipt_path.read_bytes()
    expected_policy = validate_model_load_policy_gate_v1(
        observed=canonical_observed_model_load_policy_v1())
    if raw_policy != expected_policy:
        raise ValueError("MODEL_LOAD_POLICY_RECEIPT_MISMATCH")
    authority = parse_load_only_authority_v1(
        raw_receipt=authority_receipt_path.read_bytes(),
        expected_load_candidate_identity=LOAD_ONLY_CANDIDATE_IDENTITY)
    validate_preload_environment_v1(
        observed=observe_preload_environment_v1(), authority=authority)
    worker_path = Path(__file__).with_name(
        "stage_p_construction_obligation_v2_model_load_linux_worker_v1.py")
    if _sha256_file(worker_path) != WORKER_SOURCE_SHA256:
        raise ValueError("MODEL_LOAD_LINUX_WORKER_SOURCE_DRIFT")

    lifecycle = AppendOnlyLifecycleV1(lifecycle_root, actor="model-load-supervisor")
    lifecycle.emit("MODEL_LOAD_STARTED", supervisor_identity=SUPERVISOR_IDENTITY,
                   authority_receipt_identity=authority.authority_receipt_identity)
    context = multiprocessing.get_context("spawn")
    event_queue = context.Queue()
    child = context.Process(target=run_load_only_linux_child_v1,
                            kwargs={"events": event_queue}, daemon=False)
    child.start()
    child.join(timeout_seconds)
    if child.is_alive():
        lifecycle.emit("MODEL_LOAD_TIMEOUT", child_pid=child.pid)
        child.terminate(); child.join(10.0)
        termination = "TERMINATED"
        if child.is_alive():
            child.kill(); child.join(10.0); termination = "KILLED"
        lifecycle.emit("MODEL_LOAD_CHILD_TERMINATION_OBSERVED",
                       child_pid=child.pid, termination=termination,
                       exitcode=child.exitcode)
    while True:
        try:
            event, failure_type = event_queue.get_nowait()
        except queue.Empty:
            break
        lifecycle.emit(event, failure_type=failure_type)
    event_queue.close(); event_queue.join_thread()
    if child.is_alive():
        raise RuntimeError("MODEL_LOAD_CHILD_TERMINATION_UNCONFIRMED")
    status = "LOAD_ONLY_COMPLETED_AND_RELEASED" if child.exitcode == 0 else "LOAD_ONLY_FAILED_AND_RELEASED"
    lifecycle.emit("MODEL_LOAD_SUPERVISOR_TERMINAL", status=status,
                   child_exitcode=child.exitcode)
    return status


def observe_preload_environment_v1() -> PreloadEnvironmentV1:
    installed = tuple(f"{name}=={version(name)}" for name in
                      ("transformers", "torch", "peft", "accelerate", "bitsandbytes"))
    if installed != PACKAGE_IDENTITIES:
        raise ValueError("MODEL_LOAD_RUNTIME_PACKAGE_MISMATCH")
    _verify_immutable_manifests()
    completed = subprocess.run(
        ("nvidia-smi", "--query-gpu=index,name,memory.total,memory.free,compute_cap",
         "--format=csv,noheader,nounits"), check=True, capture_output=True,
        text=True, encoding="utf-8", errors="strict", timeout=10.0)
    fields = tuple(item.strip() for item in completed.stdout.strip().split(","))
    if len(fields) != 5 or fields[0] != "0":
        raise ValueError("MODEL_LOAD_CUDA_OBSERVATION_INVALID")
    return PreloadEnvironmentV1(
        installed, fields[1], int(fields[2]), int(fields[3]), fields[4], 0,
        "bb5a4767bb2eca6d2a71e0aacc2cbaaeab6e01a5baa693cb1330474385e5b6f9",
        "bd0f84711c825a2c213b458a0e2c41d189914ad5ac4bdf283c91a38daab0c090",
        "312d6f8cb7c14c769742901c4c80042c104f5a60ba2f80b2913487af22d67ae2",
        True, "5.0.0.dev0", "5.15.0", True)


def _verify_immutable_manifests() -> None:
    root = Path(__file__).resolve().parents[3]
    manifest_path = root / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-model-adapter-immutable-manifest-v1.json"
    raw_manifest = manifest_path.read_bytes()
    if hashlib.sha256(raw_manifest).hexdigest() != IMMUTABLE_MANIFEST_ARTIFACT_SHA256:
        raise ValueError("MODEL_LOAD_IMMUTABLE_MANIFEST_ARTIFACT_DRIFT")
    artifact = json.loads(raw_manifest.decode("utf-8", errors="strict"))
    for section, base in (("base_snapshot", Path(BASE_MODEL_PATH)), ("adapter", Path(ADAPTER_PATH))):
        entries = artifact[section]["files"]
        for entry in entries:
            target = base / entry["path"]
            if (not target.is_file() or target.stat().st_size != entry["size"] or
                    _sha256_file(target) != entry["sha256"]):
                raise ValueError(f"MODEL_LOAD_IMMUTABLE_MANIFEST_DRIFT:{section}:{entry['path']}")


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(8 * 1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def main(arguments: list[str]) -> int:
    if len(arguments) != 3:
        raise SystemExit("usage: supervisor POLICY_RECEIPT AUTHORITY_RECEIPT LIFECYCLE_ROOT")
    status = supervise_load_only_v1(
        policy_receipt_path=Path(arguments[0]), authority_receipt_path=Path(arguments[1]),
        lifecycle_root=Path(arguments[2]))
    return 0 if status == "LOAD_ONLY_COMPLETED_AND_RELEASED" else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))


__all__ = ("DEFAULT_TIMEOUT_SECONDS", "IMMUTABLE_MANIFEST_ARTIFACT_SHA256",
           "WORKER_SOURCE_SHA256",
           "SUPERVISOR_IDENTITY", "main",
           "observe_preload_environment_v1", "supervise_load_only_v1")
