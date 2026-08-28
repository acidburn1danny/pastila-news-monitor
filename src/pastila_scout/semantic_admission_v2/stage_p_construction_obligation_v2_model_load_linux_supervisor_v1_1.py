"""V1.1 supervisor binding completion to exact adapter compatibility."""
from __future__ import annotations

import json
import multiprocessing
import queue
import sys
from pathlib import Path

from .append_only_lifecycle_v1 import AppendOnlyLifecycleV1
from .stage_p_construction_obligation_v2_model_load_authority_contract_v1 import (
    parse_load_only_authority_v1, validate_preload_environment_v1,
)
from .stage_p_construction_obligation_v2_model_load_linux_supervisor_v1 import (
    DEFAULT_TIMEOUT_SECONDS, _sha256_file, observe_preload_environment_v1,
)
from .stage_p_construction_obligation_v2_model_load_linux_worker_v1_1 import (
    run_load_only_linux_child_v1_1,
)
from .stage_p_construction_obligation_v2_model_load_only_candidate_v1_5 import (
    LOAD_ONLY_CANDIDATE_IDENTITY,
)
from .stage_p_construction_obligation_v2_model_load_policy_gate_v1 import (
    canonical_observed_model_load_policy_v1, validate_model_load_policy_gate_v1,
)


SUPERVISOR_V1_1_IDENTITY = "cb586b500b2cd0e23a8af86713153e36c0875170a6017e51cbea1ee8b45440ae"
WORKER_V1_1_SOURCE_SHA256 = "6a7e6ec0c920eb4e73c95e97836a37c120c6c95e557198bc12d3945b292465d5"


def supervise_load_only_v1_1(*, policy_receipt_path: Path, authority_receipt_path: Path,
                             lifecycle_root: Path, timeout_seconds: float = DEFAULT_TIMEOUT_SECONDS) -> str:
    if type(timeout_seconds) is not float or not 1.0 <= timeout_seconds <= DEFAULT_TIMEOUT_SECONDS:
        raise ValueError("MODEL_LOAD_SUPERVISOR_TIMEOUT_INVALID")
    expected_policy = validate_model_load_policy_gate_v1(
        observed=canonical_observed_model_load_policy_v1())
    if policy_receipt_path.read_bytes() != expected_policy:
        raise ValueError("MODEL_LOAD_POLICY_RECEIPT_MISMATCH")
    authority = parse_load_only_authority_v1(
        raw_receipt=authority_receipt_path.read_bytes(),
        expected_load_candidate_identity=LOAD_ONLY_CANDIDATE_IDENTITY)
    validate_preload_environment_v1(observed=observe_preload_environment_v1(), authority=authority)
    worker_path = Path(__file__).with_name(
        "stage_p_construction_obligation_v2_model_load_linux_worker_v1_1.py")
    if _sha256_file(worker_path) != WORKER_V1_1_SOURCE_SHA256:
        raise ValueError("MODEL_LOAD_LINUX_WORKER_V1_1_SOURCE_DRIFT")

    lifecycle=AppendOnlyLifecycleV1(lifecycle_root,actor="model-load-supervisor-v1-1")
    lifecycle.emit("MODEL_LOAD_STARTED",supervisor_identity=SUPERVISOR_V1_1_IDENTITY,
                   authority_receipt_identity=authority.authority_receipt_identity)
    context=multiprocessing.get_context("spawn");event_queue=context.Queue()
    child=context.Process(target=run_load_only_linux_child_v1_1,
                          kwargs={"events":event_queue},daemon=False)
    child.start();child.join(timeout_seconds)
    if child.is_alive():
        lifecycle.emit("MODEL_LOAD_TIMEOUT",child_pid=child.pid)
        child.terminate();child.join(10.0);termination="TERMINATED"
        if child.is_alive():child.kill();child.join(10.0);termination="KILLED"
        lifecycle.emit("MODEL_LOAD_CHILD_TERMINATION_OBSERVED",child_pid=child.pid,
                       termination=termination,exitcode=child.exitcode)
    compatibility_validated=False
    while True:
        try:event,failure_type,raw_compatibility=event_queue.get_nowait()
        except queue.Empty:break
        detail={"failure_type":failure_type}
        if raw_compatibility is not None:
            value=json.loads(raw_compatibility)
            if (value.get("classification")!="STRUCTURAL_NO_OP_VISION_TARGET_OVERMATCH" or
                    value.get("generation_authorized") is not False):
                raise ValueError("MODEL_LOAD_ADAPTER_COMPATIBILITY_RECEIPT_INVALID")
            detail["adapter_compatibility_receipt_identity"]=value["receipt_identity"]
            compatibility_validated=True
        lifecycle.emit(event,**detail)
    event_queue.close();event_queue.join_thread()
    if child.is_alive():raise RuntimeError("MODEL_LOAD_CHILD_TERMINATION_UNCONFIRMED")
    completed=child.exitcode==0 and compatibility_validated
    status="LOAD_ONLY_COMPLETED_COMPATIBILITY_VALIDATED_AND_RELEASED" if completed else "LOAD_ONLY_FAILED_AND_RELEASED"
    lifecycle.emit("MODEL_LOAD_SUPERVISOR_TERMINAL",status=status,child_exitcode=child.exitcode,
                   adapter_compatibility_validated=compatibility_validated)
    return status


def main(arguments:list[str])->int:
    if len(arguments)!=3:raise SystemExit("usage: supervisor POLICY_RECEIPT AUTHORITY_RECEIPT LIFECYCLE_ROOT")
    status=supervise_load_only_v1_1(policy_receipt_path=Path(arguments[0]),
      authority_receipt_path=Path(arguments[1]),lifecycle_root=Path(arguments[2]))
    return 0 if status=="LOAD_ONLY_COMPLETED_COMPATIBILITY_VALIDATED_AND_RELEASED" else 1


if __name__=="__main__":raise SystemExit(main(sys.argv[1:]))


__all__=("SUPERVISOR_V1_1_IDENTITY","WORKER_V1_1_SOURCE_SHA256","main",
         "supervise_load_only_v1_1")
