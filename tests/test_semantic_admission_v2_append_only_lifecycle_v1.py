import json
import sys

import pytest

from pastila_scout.semantic_admission_v2.append_only_lifecycle_v1 import AppendOnlyLifecycleV1,run_synthetic_timeout_probe_v1


def test_events_are_monotonic_exclusive_and_fsynced_shape(tmp_path) -> None:
    lifecycle=AppendOnlyLifecycleV1(tmp_path,actor="host")
    first=lifecycle.emit("RUNNER_STARTED",request_sha256="a"*64)
    second=lifecycle.emit("TIMEOUT",elapsed_ms=240000)
    assert first.name.startswith("host-00001-") and second.name.startswith("host-00002-")
    assert json.loads(first.read_text("utf-8"))["sequence"]==1
    with pytest.raises(FileExistsError):
        AppendOnlyLifecycleV1(tmp_path,actor="host").emit("RUNNER_STARTED")


def test_synthetic_timeout_events_survive_child_termination(tmp_path) -> None:
    result=run_synthetic_timeout_probe_v1(command=[sys.executable,"-c","import time; time.sleep(2)"],
        root=tmp_path,timeout_seconds=0.05)
    events=[json.loads(path.read_text("utf-8")) for path in sorted(tmp_path.glob("*.json"))]
    assert result in {"TERMINATED","KILLED"}
    assert [item["event"] for item in events]==["PROCESS_STARTED","TIMEOUT","TERMINATION_OBSERVED"]
