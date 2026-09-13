import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/materialize_production_core_v10_token_materialization_evidence.py"


def module():
    spec = importlib.util.spec_from_file_location("v10_token_materializations", SCRIPT)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def test_two_materializations_are_sealed_byte_exact():
    m = module()
    published = json.loads(m.OUTPUT.read_bytes())
    assert m.build(ROOT / ".audit-tmp/v10-token-summary-3072.json", ROOT / ".audit-tmp/v10-token-summary-3072-B.json") == published
    assert published["materializations"] == ["A", "B"]
    assert published["training_performed"] is False


def test_divergent_materialization_fails_closed(tmp_path):
    m = module()
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"
    first.write_text("{}", encoding="utf-8")
    second.write_text('{"different":true}', encoding="utf-8")
    with pytest.raises(ValueError, match="differ"):
        m.build(first, second)
