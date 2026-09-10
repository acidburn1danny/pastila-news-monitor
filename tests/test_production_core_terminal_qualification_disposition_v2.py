import importlib.util
import json
from pathlib import Path

import jsonschema

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/materialize_production_core_terminal_qualification_disposition_v2.py"
ARTIFACT = ROOT / "docs/artifacts/production-core-terminal-qualification-disposition-v2.json"
SCHEMA = ROOT / "docs/schemas/production-core-terminal-qualification-disposition-v2.schema.json"


def load_module():
    spec = importlib.util.spec_from_file_location("terminal_disposition_v2", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def test_published_terminal_disposition_is_self_identifying_and_closed():
    module = load_module()
    value = json.loads(ARTIFACT.read_bytes())
    jsonschema.Draft202012Validator(json.loads(SCHEMA.read_bytes())).validate(value)
    core = dict(value)
    observed = core.pop("disposition_identity")
    assert observed == module.identity(core)
    assert value["status"] == "TERMINAL_STRUCTURAL_REJECTION_BOTH_CANDIDATES"
    assert value["attempt_ordinal"] == 1
    assert value["attempt_consumed_permanently"] is True
    assert value["evidence"]["completed_rows"] == 2400
    assert value["evidence"]["structural_status_counts"] == {"FAIL_CLOSED_INVALID_OUTPUT": 2400}
    assert {row["candidate"] for row in value["candidate_dispositions"]} == set(module.CANDIDATES)
    assert {row["disposition"] for row in value["candidate_dispositions"]} == {"REJECTED_STRUCTURALLY"}
    assert value["retry_or_redraw"] is False
    assert value["adjudication_performed"] is False
    assert value["promotion_effect"] is False
    assert value["successor_requirement"] == "NEW_SUCCESSOR_LINEAGE_AND_NEW_EXECUTION_AUTHORITY"
