import importlib.util
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT / "scripts/materialize_production_core_successor_root_cause_addendum_v3.py"
)
ARTIFACT = ROOT / "docs/artifacts/production-core-successor-root-cause-addendum-v3.json"
SCHEMA = (
    ROOT / "docs/schemas/production-core-successor-root-cause-addendum-v3.schema.json"
)


def module():
    spec = importlib.util.spec_from_file_location("root_cause_addendum_v3", SCRIPT)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(value)
    return value


def test_published_addendum_is_closed_and_preserves_historical_disposition():
    value = json.loads(ARTIFACT.read_bytes())
    Draft202012Validator(json.loads(SCHEMA.read_bytes())).validate(value)
    core = dict(value)
    assert core.pop("addendum_identity") == module().identity(core)
    assert value["execution_boundary_cause"] == "INFERENCE_WALL_TIME_EXCEEDED"
    assert value["internal_generate_stall_cause"] == "UNDETERMINED"
    assert value["historical_disposition_reinterpreted"] is False
    assert value["attempt_consumed_permanently"] is True
    assert value["retry_or_redraw"] is False
    assert value["adjudication_performed"] is False
    assert value["promotion_effect"] is False


def test_builder_rejects_supervisor_evidence_drift(tmp_path, monkeypatch):
    materializer = module()
    execution = tmp_path / "execution"
    disposition = tmp_path / "disposition.json"
    disposition.write_bytes(
        (
            ROOT
            / "docs/artifacts/production-core-successor-terminal-disposition-v3.json"
        ).read_bytes()
    )
    failure = {
        "attempt_identity": materializer.ATTEMPT,
        "failure_class": "UNCAUGHT_AFTER_ATTEMPT_CONSUMPTION",
        "terminal_failure_identity": materializer.TERMINAL_FAILURE,
    }
    execution.mkdir()
    failure_raw = materializer.canonical(failure)
    (execution / "terminal-failure.json").write_bytes(failure_raw)
    target = execution / materializer.FAILED_DIRECTORY / "results"
    target.mkdir(parents=True)
    heartbeat = {
        "stage": "GENERATE",
        "sequence": 115,
        "completed_count": 114,
        "case_id": "pcq-unc-025",
        "deadline_boottime_ns": 39_819_100_000_000,
    }
    heartbeat_raw = materializer.canonical(heartbeat)
    (target / "heartbeat.json").write_bytes(heartbeat_raw)
    supervisor = {
        "schema": "pastila-production-core-supervisor-failure",
        "schema_version": 1,
        "code": "INFERENCE_WALL_TIME_EXCEEDED",
        "ceiling_ns": 600_000_000_000,
    }
    supervisor_raw = materializer.canonical(supervisor)
    (target / "supervisor-failure.json").write_bytes(supervisor_raw)
    batch = [{} for _ in range(200)]
    batch[114] = {"case_id": "pcq-unc-025"}
    (target.parent / "batch.json").write_bytes(json.dumps(batch).encode())
    monkeypatch.setattr(
        materializer,
        "TERMINAL_FAILURE_SHA256",
        materializer.hashlib.sha256(failure_raw).hexdigest(),
    )
    monkeypatch.setattr(
        materializer,
        "SUPERVISOR_SHA256",
        materializer.hashlib.sha256(supervisor_raw).hexdigest(),
    )
    monkeypatch.setattr(
        materializer,
        "HEARTBEAT_SHA256",
        materializer.hashlib.sha256(heartbeat_raw).hexdigest(),
    )
    supervisor["code"] = "INVALID_HEARTBEAT_AUTHORITY"
    (target / "supervisor-failure.json").write_bytes(materializer.canonical(supervisor))
    with pytest.raises(SystemExit, match="supervisor evidence drift"):
        materializer.build(execution, disposition)
