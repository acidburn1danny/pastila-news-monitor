import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/materialize_production_core_v7_lifecycle_terminal_failure.py"
ARTIFACT = ROOT / "docs/artifacts/production-core-successor-v7-root-cause-addendum-v1.json"
SCHEMA = ROOT / "docs/schemas/production-core-successor-v7-root-cause-addendum-v1.schema.json"


def module():
    spec = importlib.util.spec_from_file_location("v7_lifecycle_terminal", SCRIPT)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(value)
    return value


def test_v7_addendum_is_closed_and_preserves_consumed_attempt():
    materializer = module()
    value = json.loads(ARTIFACT.read_bytes())
    Draft202012Validator(json.loads(SCHEMA.read_bytes())).validate(value)
    core = dict(value)
    assert core.pop("addendum_identity") == materializer.identity(core, sorted_keys=True)
    assert value["completed_rows"] == 2400
    assert value["checkpoint_count"] == 12
    assert value["attempt_consumed_permanently"] is True
    assert value["attempt_relaunch_authorized"] is False
    assert value["retry_or_redraw"] is False
    assert value["adjudication_performed"] is False
    assert value["promotion_effect"] is False


def test_v7_addendum_records_the_exact_stale_schema_delta():
    materializer = module()
    value = json.loads(ARTIFACT.read_bytes())
    lifecycle = value["lifecycle_evidence"]
    assert tuple(lifecycle["executor_completed_keys"]) == materializer.COMPLETED_KEYS
    assert tuple(lifecycle["stale_final_validator_completed_keys"]) == materializer.STALE_VALIDATOR_KEYS
    assert set(materializer.COMPLETED_KEYS) - set(materializer.STALE_VALIDATOR_KEYS) == {"termination_reason"}
    assert lifecycle["termination_reason_counts"] == {
        "OUTPUT_BYTE_CEILING_EXCEEDED": 6,
        "TERMINAL_EOS": 2394,
    }
