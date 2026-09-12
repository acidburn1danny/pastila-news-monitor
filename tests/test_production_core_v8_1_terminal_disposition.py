import hashlib
import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/materialize_production_core_v8_1_terminal_disposition.py"
ARTIFACT = ROOT / "docs/artifacts/production-core-v8-1-terminal-disposition.json"
SCHEMA = ROOT / "docs/schemas/production-core-v8-1-terminal-disposition.schema.json"


def module():
    spec = importlib.util.spec_from_file_location("v8_1_disposition", SCRIPT)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(value)
    return value


def test_disposition_is_reproducible_terminal_and_non_promotional():
    materializer = module()
    value = json.loads(ARTIFACT.read_bytes())
    Draft202012Validator(json.loads(SCHEMA.read_bytes())).validate(value)
    core = dict(value)
    assert core.pop("disposition_identity") == hashlib.sha256(
        materializer.canonical(core)
    ).hexdigest()
    assert value == materializer.build()
    assert value["adjudication_authorized"] is True
    assert value["semantic_adjudication_required"] is False
    assert value["semantic_adjudication_performed"] is False
    assert value["promotion_effect"] is False


def test_schema_rejects_semantic_adjudication_promotion_and_stale_custody():
    value = json.loads(ARTIFACT.read_bytes())
    validator = Draft202012Validator(json.loads(SCHEMA.read_bytes()))
    for field in (
        "semantic_adjudication_performed",
        "promotion_effect",
        "stale_custody_exports_used",
    ):
        changed = json.loads(json.dumps(value))
        changed[field] = True
        assert list(validator.iter_errors(changed))
