from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_durable_executor_v2 import DurableConstrainedStagePCoreV12ExecutorV2


ROOT=Path(__file__).resolve().parents[1]


def test_executor_constructs_without_wsl_or_model(tmp_path) -> None:
    executor=DurableConstrainedStagePCoreV12ExecutorV2(project_root=ROOT,durable_lifecycle_root=tmp_path)
    assert executor is not None and list(tmp_path.iterdir())==[]


def test_executor_uses_popen_pid_timeout_and_durable_root() -> None:
    source=(ROOT/"src/pastila_scout/semantic_admission_v2/stage_p_durable_executor_v2.py").read_text("utf-8")
    assert "subprocess.Popen" in source and "process.pid" in source
    assert "HOST_TIMEOUT" in source and "HOST_TERMINATION_OBSERVED" in source
    assert "lifecycle_root=self._durable_root/request_digest" in source
    assert "TemporaryDirectory" in source and "_wsl_path(lifecycle_root)" in source
