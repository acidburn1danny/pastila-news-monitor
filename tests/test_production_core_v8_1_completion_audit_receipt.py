import hashlib
import importlib.util
import json
from pathlib import Path

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/materialize_production_core_v8_1_completion_audit_receipt.py"
ARTIFACT = ROOT / "docs/artifacts/production-core-v8-1-completion-audit-receipt.json"
SCHEMA = ROOT / "docs/schemas/production-core-v8-1-completion-audit-receipt.schema.json"


def module():
    spec = importlib.util.spec_from_file_location("v8_1_completion_audit", SCRIPT)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(value)
    return value


def test_receipt_is_reproducible_content_addressed_and_zero_effect():
    materializer = module()
    value = json.loads(ARTIFACT.read_bytes())
    Draft202012Validator(json.loads(SCHEMA.read_bytes())).validate(value)
    core = dict(value)
    assert core.pop("audit_receipt_identity") == hashlib.sha256(
        materializer.canonical(core)
    ).hexdigest()
    assert value == materializer.build()
    assert value["status"] == "PASS_ZERO_BLOCKERS"
    assert value["attempt_reexecuted"] is False
    assert value["adjudication_performed"] is False
    assert value["promotion_effect"] is False


def test_schema_rejects_adjudication_promotion_and_incomplete_checkpoint_set():
    value = json.loads(ARTIFACT.read_bytes())
    validator = Draft202012Validator(json.loads(SCHEMA.read_bytes()))
    for field in ("adjudication_performed", "promotion_effect"):
        changed = json.loads(json.dumps(value))
        changed[field] = True
        assert list(validator.iter_errors(changed))
    incomplete = json.loads(json.dumps(value))
    incomplete["checkpoints"].pop()
    assert list(validator.iter_errors(incomplete))
