import hashlib
import json
from pathlib import Path

from jsonschema import Draft202012Validator

from pastila_scout.production_core_candidate_execution_authority_v3 import (
    validate_preflight,
)

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"


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
