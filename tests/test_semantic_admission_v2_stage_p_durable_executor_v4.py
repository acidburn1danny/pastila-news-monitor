import json
from pathlib import Path

from pastila_scout.semantic_admission_v2.append_only_lifecycle_v1 import AppendOnlyLifecycleV1
from pastila_scout.semantic_admission_v2.stage_p_durable_executor_v4 import (
    DEPENDENCY_IDENTITIES,RUNNER_SHA256,DurableConstrainedStagePCoreV12ExecutorV4,
)


ROOT=Path(__file__).resolve().parents[1]


def _runner_dependencies():
    return {path.as_posix():value for path,value in DEPENDENCY_IDENTITIES.items()
        if path.name!="durable_lifecycle_reconciliation_v1.py"}


def test_v4_constructs_without_wsl_model_or_events(tmp_path) -> None:
    executor=DurableConstrainedStagePCoreV12ExecutorV4(project_root=ROOT,durable_lifecycle_root=tmp_path)
    assert executor is not None and list(tmp_path.iterdir())==[]


def test_v4_reconciles_synthetic_complete_lifecycle_into_generic_trace(tmp_path) -> None:
    durable=tmp_path/"durable";executor=DurableConstrainedStagePCoreV12ExecutorV4(project_root=ROOT,durable_lifecycle_root=durable)
    lifecycle=durable/"request";host=AppendOnlyLifecycleV1(lifecycle,actor="host");runner=AppendOnlyLifecycleV1(lifecycle,actor="runner")
    host.emit("HOST_LAUNCH",runner_sha256=RUNNER_SHA256,dependency_identities=_runner_dependencies())
    host.emit("HOST_PROCESS_EXITED")
    for event in ("RUNNER_STARTED","MODEL_LOAD_STARTED","MODEL_LOAD_COMPLETED","GENERATION_STARTED","TERMINAL_EOS","RESPONSE_PERSISTED"):
        runner.emit(event)
    trace_path=tmp_path/"trace.json";trace={"model_load_started":False,"model_load_succeeded":False,
        "inference_started":False,"inference_succeeded":False}
    executor._reconcile(trace_path,trace,lifecycle,"request",_runner_dependencies())
    persisted=json.loads(trace_path.read_text("utf-8"));receipt=persisted["durable_lifecycle_reconciliation"]
    assert receipt["reconciliation_status"]=="VALID"
    assert receipt["model_load"]==receipt["generation"]==receipt["terminal_eos"]=="OBSERVED"
    assert persisted["model_load_started"] is persisted["model_load_succeeded"] is True
    assert persisted["inference_started"] is persisted["inference_succeeded"] is True


def test_v4_source_has_timeout_reconciliation_before_raise() -> None:
    source=(ROOT/"src/pastila_scout/semantic_admission_v2/stage_p_durable_executor_v4.py").read_text("utf-8")
    timeout=source.index('events.emit("HOST_TIMEOUT"')
    reconcile=source.index("self._reconcile(trace_path,trace,lifecycle_root,request_digest,dependencies);raise")
    assert timeout<reconcile
    assert "LIFECYCLE_UNAVAILABLE" not in source
