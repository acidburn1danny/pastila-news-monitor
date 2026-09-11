import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT / "scripts/materialize_production_core_successor_terminal_disposition_v4.py"
)
ARTIFACT = (
    ROOT / "docs/artifacts/production-core-successor-terminal-disposition-v4.json"
)
SCHEMA = (
    ROOT / "docs/schemas/production-core-successor-terminal-disposition-v4.schema.json"
)


def module():
    spec = importlib.util.spec_from_file_location("terminal_disposition_v4", SCRIPT)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(value)
    return value


def test_published_v4_disposition_is_closed_typed_and_zero_effect():
    value = json.loads(ARTIFACT.read_bytes())
    Draft202012Validator(json.loads(SCHEMA.read_bytes())).validate(value)
    core = dict(value)
    assert core.pop("disposition_identity") == module().identity(core)
    assert value["failure_class"] == "INFERENCE_WALL_TIME_EXCEEDED"
    assert value["execution_boundary_cause_determined"] is True
    assert value["internal_generate_stall_cause"] == "UNDETERMINED"
    assert value["attempt_consumed_permanently"] is True
    assert value["attempt_relaunch_authorized"] is False
    assert value["finalized_rows"] == {"completed": 600, "matrix": 2400}
    assert value["partial_raw_outputs"] == {"completed": 612, "matrix": 2400}
    assert value["watchdog_exit_code"] == 124
    assert value["retry_or_redraw"] is False
    assert value["adjudication_performed"] is False
    assert value["promotion_effect"] is False


def test_schema_rejects_internal_cause_invention_and_relaunch():
    schema = json.loads(SCHEMA.read_bytes())
    value = json.loads(ARTIFACT.read_bytes())
    validator = Draft202012Validator(schema)
    invented = json.loads(json.dumps(value))
    invented["internal_generate_stall_cause"] = "GPU_DRIVER_STALL"
    assert list(validator.iter_errors(invented))
    relaunched = json.loads(json.dumps(value))
    relaunched["attempt_relaunch_authorized"] = True
    assert list(validator.iter_errors(relaunched))
