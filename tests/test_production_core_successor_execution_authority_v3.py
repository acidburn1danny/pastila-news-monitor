import hashlib
import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from pastila_scout.production_core_candidate_execution_authority_v3 import (
    validate_preflight,
)

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"


def executor_module():
    path = ROOT / "scripts/execute_production_core_candidate_qualification_v3.py"
    spec = importlib.util.spec_from_file_location("successor_executor_v4", path)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(value)
    return value


def identity(value):
    return hashlib.sha256(
        json.dumps(
            value, ensure_ascii=False, allow_nan=False, separators=(",", ":")
        ).encode()
    ).hexdigest()


def load(name):
    return json.loads((ART / name).read_bytes())


def test_successor_objects_and_training_provenance_are_closed():
    value = load("production-core-successor-candidate-object-manifest-v3.json")
    core = dict(value)
    assert core.pop("manifest_identity") == identity(core)
    assert set(value["adapter_manifest_sha256"]) == {
        "pastila-editor-core-v1.1-json-successor",
        "pastila-editor-core-v1.2-json-successor",
    }
    assert len(value["training_receipt_identity"]) == 2
    assert value["candidate_execution_performed"] is False
    assert value["qualification_attempt_consumed"] is False


def test_successor_generation_preserves_matrix_and_schedule_without_redraw():
    old = load("production-core-comparative-qualification-generation-v2.json")
    new = load("production-core-successor-comparative-qualification-generation-v3.json")
    core = dict(new)
    assert core.pop("qualification_generation_identity") == identity(core)
    assert new["schedule"] == old["schedule"]
    assert new["alias_secret_commitment"] != old["alias_secret_commitment"]
    assert new["schedule_lineage"] == "PREDECESSOR_ORDER_PRESERVED_NO_REDRAW"
    assert new["matrix"] == old["matrix"]
    assert new["retry_or_redraw_authorized"] is False
    assert new["candidate_execution_performed"] is False
    assert new["qualification_attempt_consumed"] is False


def test_successor_preflight_qualification_is_sealed_and_zero_effect():
    value = load("production-core-successor-candidate-generation-qualification-v3.json")
    core = dict(value)
    assert core.pop("qualification_identity") == identity(core)
    assert value["candidate_execution_performed"] is False
    assert value["qualification_attempt_consumed"] is False
    assert value["adjudication_performed"] is False
    assert value["promotion_effect"] is False


def test_executable_preflight_accepts_only_the_successor_authorities():
    rows = validate_preflight(
        load("production-core-successor-comparative-qualification-generation-v3.json"),
        load("production-core-candidate-request-manifest-v2.json"),
        load("production-core-successor-candidate-object-manifest-v3.json"),
        load("production-core-successor-candidate-generation-qualification-v3.json"),
    )
    assert len(rows) == 2400


def test_execution_authority_schema_is_closed():
    schema = json.loads(
        (
            ART.parent
            / "schemas/production-core-candidate-execution-authority-v3.schema.json"
        ).read_bytes()
    )
    value = load("production-core-candidate-execution-authority-v3.json")
    Draft202012Validator(schema).validate(value)


def test_preflight_only_returns_before_attempt_construction():
    source = (
        ROOT / "scripts/execute_production_core_candidate_qualification_v3.py"
    ).read_text("utf-8")
    assert source.index("if o.preflight_only:") < source.index("build_attempt(")


def test_typed_supervisor_failure_requires_closed_code_exit_binding(tmp_path):
    module = executor_module()
    result = tmp_path / "results"
    result.mkdir()
    value = {
        "schema": "pastila-production-core-supervisor-failure",
        "schema_version": 2,
        "code": "INFERENCE_WALL_TIME_EXCEEDED",
        "ceiling_ns": 600_000_000_000,
        "watchdog_exit_code": 124,
        "last_sequence": 115,
        "last_completed_count": 114,
        "last_stage": "GENERATE",
    }
    (result / "supervisor-failure.json").write_bytes(module.canonical(value))
    assert (
        module.typed_supervisor_failure(result, 124) == "INFERENCE_WALL_TIME_EXCEEDED"
    )
    assert (
        module.typed_supervisor_failure(result, 125)
        == "UNCAUGHT_AFTER_ATTEMPT_CONSUMPTION"
    )
    value["code"] = "HOST_INVENTED_FAILURE"
    (result / "supervisor-failure.json").write_bytes(module.canonical(value))
    assert (
        module.typed_supervisor_failure(result, 124)
        == "UNCAUGHT_AFTER_ATTEMPT_CONSUMPTION"
    )


def test_inference_lifecycle_is_content_addressed_and_cross_bound():
    module = executor_module()
    row = {"case_id": "case-1", "request_identity": "sha256:" + "a" * 64}
    observation = {
        "input_tokens": 42,
        "generation_wall_ns": 123,
        "output_tokens": 7,
        "terminal_eos": True,
    }
    started_core = {
        "schema": "pastila-production-core-inference-lifecycle-event",
        "schema_version": 1,
        "phase": "STARTED",
        "sequence": 1,
        "completed_count": 0,
        "case_id": "case-1",
        "request_identity": row["request_identity"],
        "input_tokens": 42,
        "started_boottime_ns": 1000,
    }
    started = {**started_core, "event_identity": module.identity(started_core)}
    completed_core = {
        "schema": "pastila-production-core-inference-lifecycle-event",
        "schema_version": 1,
        "phase": "COMPLETED",
        "sequence": 1,
        "completed_count": 1,
        "case_id": "case-1",
        "request_identity": row["request_identity"],
        "started_event_identity": started["event_identity"],
        "generation_wall_ns": 123,
        "output_tokens": 7,
        "terminal_eos": True,
    }
    completed = {**completed_core, "event_identity": module.identity(completed_core)}
    module.validate_inference_lifecycle(
        module.canonical(started),
        module.canonical(completed),
        sequence=1,
        row=row,
        observation=observation,
    )
    completed["generation_wall_ns"] = 124
    import pytest

    with pytest.raises(SystemExit, match="lifecycle evidence mismatch"):
        module.validate_inference_lifecycle(
            module.canonical(started),
            module.canonical(completed),
            sequence=1,
            row=row,
            observation=observation,
        )


def test_completion_authority_closure_includes_lifecycle_events():
    source = (
        ROOT / "src/pastila_scout/production_core_candidate_execution_authority_v3.py"
    ).read_text("utf-8")
    assert (
        "validate_inference_lifecycle_events(started, completed, row, observation)"
        in source
    )
    assert (
        "f\"{directory}/results/inference-{row['batch_ordinal']:03d}-started.json\""
        in source
    )
    assert (
        "f\"{directory}/results/inference-{row['batch_ordinal']:03d}-completed.json\""
        in source
    )


def test_successor_v4_authority_is_frozen_without_execution_or_attempt():
    schema = json.loads(
        (
            ART.parent
            / "schemas/production-core-candidate-execution-authority-v4.schema.json"
        ).read_bytes()
    )
    value = load("production-core-candidate-execution-authority-v4.json")
    Draft202012Validator(schema).validate(value)
    core = dict(value)
    assert core.pop("execution_authority_identity") == identity(core)
    assert value["bound_source_commit"] == "6c72a3c45c4a251a8fe61db82aea5bd462238120"
    assert value["predecessor_attempt_consumed_permanently"] is True
    assert value["attempt_consumption_authorized"] is False
    assert value["candidate_execution_authorized"] is False
    assert value["candidate_execution_performed"] is False
    assert value["adjudication_performed"] is False
    assert value["promotion_effect"] is False


def test_successor_v4_schema_rejects_extra_source_and_execution_authorization():
    schema = json.loads(
        (
            ART.parent
            / "schemas/production-core-candidate-execution-authority-v4.schema.json"
        ).read_bytes()
    )
    validator = Draft202012Validator(schema)
    value = load("production-core-candidate-execution-authority-v4.json")
    extra = json.loads(json.dumps(value))
    extra["source_sha256"]["host/fallback.py"] = "0" * 64
    assert list(validator.iter_errors(extra))
    execution = json.loads(json.dumps(value))
    execution["candidate_execution_authorized"] = True
    execution["attempt_consumption_authorized"] = True
    assert list(validator.iter_errors(execution))
