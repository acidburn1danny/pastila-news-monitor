import hashlib
import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/materialize_production_core_successor_execution_authority_v8.py"
ARTIFACT = ROOT / "docs/artifacts/production-core-candidate-execution-authority-v8.json"
SCHEMA = ROOT / "docs/schemas/production-core-candidate-execution-authority-v8.schema.json"


def module():
    spec = importlib.util.spec_from_file_location("execution_authority_v8", SCRIPT)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(value)
    return value


def test_v8_authority_is_closed_and_zero_effect():
    materializer = module()
    value = json.loads(ARTIFACT.read_bytes())
    Draft202012Validator(json.loads(SCHEMA.read_bytes())).validate(value)
    core = dict(value)
    assert core.pop("execution_authority_identity") == hashlib.sha256(
        materializer.canonical(core)
    ).hexdigest()
    assert value == materializer.build()
    assert set(value["source_sha256"]) == set(materializer.SOURCE_PATHS)
    assert value["attempt_consumption_authorized"] is False
    assert value["candidate_execution_authorized"] is False
    assert value["candidate_execution_performed"] is False
    assert value["retry_or_redraw_authorized"] is False
    assert value["adjudication_performed"] is False
    assert value["promotion_effect"] is False


def test_v8_schema_rejects_lifecycle_rollback_and_execution_authorization():
    schema = json.loads(SCHEMA.read_bytes())
    value = json.loads(ARTIFACT.read_bytes())
    validator = Draft202012Validator(schema)
    rollback = json.loads(json.dumps(value))
    rollback["lifecycle_completed_contract"]["termination_reason_required"] = False
    assert list(validator.iter_errors(rollback))
    execution = json.loads(json.dumps(value))
    execution["candidate_execution_authorized"] = True
    execution["attempt_consumption_authorized"] = True
    assert list(validator.iter_errors(execution))
    fallback = json.loads(json.dumps(value))
    fallback["source_sha256"]["host/fallback.py"] = "0" * 64
    assert list(validator.iter_errors(fallback))
    substituted = json.loads(json.dumps(value))
    substituted["source_sha256"].pop(
        "src/pastila_scout/production_core_candidate_execution_authority_v3.py"
    )
    substituted["source_sha256"]["host/fallback.py"] = "0" * 64
    assert list(validator.iter_errors(substituted))
