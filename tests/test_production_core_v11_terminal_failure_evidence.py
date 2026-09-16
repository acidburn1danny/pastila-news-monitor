import importlib.util
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/materialize_production_core_v11_terminal_failure_evidence.py"
DISPOSITION = ROOT / "docs/artifacts/production-core-v11-terminal-failure-disposition.json"
ADDENDUM = ROOT / "docs/artifacts/production-core-v11-root-cause-addendum.json"


def module():
    spec = importlib.util.spec_from_file_location("v11_failure_evidence", SCRIPT)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(value)
    return value


def test_published_v11_failure_evidence_reproduces_and_validates():
    value = module()
    disposition, addendum = value.build()
    assert json.loads(DISPOSITION.read_bytes()) == disposition
    assert json.loads(ADDENDUM.read_bytes()) == addendum
    Draft202012Validator(json.loads((ROOT / "docs/schemas/production-core-v11-terminal-failure-disposition.schema.json").read_bytes())).validate(disposition)
    Draft202012Validator(json.loads((ROOT / "docs/schemas/production-core-v11-root-cause-addendum.schema.json").read_bytes())).validate(addendum)
    assert addendum["execution_boundary_cause"] == "STALE_RUNNER_QUALIFICATION_GENERATION_BINDING"
    assert addendum["inference_started"] is False
    assert addendum["terminal_disposition_reinterpreted"] is False
    assert disposition["attempt_consumed_permanently"] is True
    assert disposition["retry_or_redraw"] is addendum["retry_or_redraw"] is False


def test_tampered_attempt_evidence_is_rejected(tmp_path):
    value = module()
    target = tmp_path / "execution"
    target.mkdir()
    for source in value.EXECUTION.rglob("*"):
        relative = source.relative_to(value.EXECUTION)
        if source.is_dir():
            (target / relative).mkdir(parents=True, exist_ok=True)
        else:
            (target / relative).parent.mkdir(parents=True, exist_ok=True)
            (target / relative).write_bytes(source.read_bytes())
    (target / "attempt.json").write_bytes((target / "attempt.json").read_bytes() + b"x")
    with pytest.raises(ValueError, match="evidence drift"):
        value.build(target)
