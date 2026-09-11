import importlib.util
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/materialize_production_core_successor_root_cause_addendum_v3.py"
ARTIFACT = ROOT / "docs/artifacts/production-core-successor-root-cause-addendum-v3.json"
SCHEMA = ROOT / "docs/schemas/production-core-successor-root-cause-addendum-v3.schema.json"


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


def test_builder_rejects_supervisor_evidence_drift(tmp_path):
    execution = tmp_path / "execution"
    disposition = tmp_path / "disposition.json"
    source = ROOT / ".pastila-runtime/production-core-successor-execution-v3-attempt1"
    disposition.write_bytes(
        (ROOT / "docs/artifacts/production-core-successor-terminal-disposition-v3.json").read_bytes()
    )
    target = execution / module().FAILED_DIRECTORY / "results"
    target.mkdir(parents=True)
    for relative in ("terminal-failure.json",):
        (execution / relative).write_bytes((source / relative).read_bytes())
    failed_source = source / module().FAILED_DIRECTORY
    (target / "heartbeat.json").write_bytes((failed_source / "results/heartbeat.json").read_bytes())
    supervisor = json.loads((failed_source / "results/supervisor-failure.json").read_bytes())
    supervisor["code"] = "INVALID_HEARTBEAT_AUTHORITY"
    (target / "supervisor-failure.json").write_bytes(module().canonical(supervisor))
    (target.parent / "batch.json").write_bytes((failed_source / "batch.json").read_bytes())
    with pytest.raises(SystemExit, match="supervisor evidence drift"):
        module().build(execution, disposition)
