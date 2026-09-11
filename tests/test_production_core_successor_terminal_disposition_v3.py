import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = (
    ROOT / "scripts/materialize_production_core_successor_terminal_disposition_v3.py"
)
ARTIFACT = (
    ROOT / "docs/artifacts/production-core-successor-terminal-disposition-v3.json"
)
SCHEMA = (
    ROOT / "docs/schemas/production-core-successor-terminal-disposition-v3.schema.json"
)


def module():
    spec = importlib.util.spec_from_file_location("successor_terminal_v3", SCRIPT)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(value)
    return value


def test_published_failure_disposition_is_closed_and_non_inferential():
    value = json.loads(ARTIFACT.read_bytes())
    Draft202012Validator(json.loads(SCHEMA.read_bytes())).validate(value)
    core = dict(value)
    assert core.pop("disposition_identity") == module().identity(core)
    assert value["terminal_state"] == "FAILURE"
    assert value["root_cause_determined"] is False
    assert value["attempt_consumed_permanently"] is True
    assert value["attempt_relaunch_authorized"] is False
    assert value["finalized_rows"] == {"completed": 1800, "matrix": 2400}
    assert value["partial_raw_outputs"] == {"completed": 1914, "matrix": 2400}
    assert value["retry_or_redraw"] is False
    assert value["adjudication_performed"] is False
    assert value["promotion_effect"] is False
