import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/validate_production_core_v10_training_inputs.py"
ART = ROOT / "docs/artifacts"


def module():
    spec = importlib.util.spec_from_file_location("v10_training_boundary", SCRIPT)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


def paths(candidate: str):
    return (
        ART / f"{candidate}-train.jsonl",
        ART / f"{candidate}-training-config-v10.json",
    )


@pytest.mark.parametrize("candidate", [
    "pastila-editor-core-v1.1-json-successor-v10",
    "pastila-editor-core-v1.2-json-successor-v10",
])
def test_published_training_inputs_are_contract_bound(candidate):
    result = module().validate(*paths(candidate))
    assert result["rows"] == 480
    assert result["maximum_training_sequence_tokens"] == 3072
    assert result["model_loaded"] is False and result["training_performed"] is False


def test_wrong_contract_and_renderer_fail_closed(tmp_path):
    m = module()
    corpus, config = paths("pastila-editor-core-v1.1-json-successor-v10")
    wrong_config = json.loads(config.read_bytes())
    wrong_config["execution_contract_identity"] = "0" * 64
    config_copy = tmp_path / "config.json"
    config_copy.write_text(json.dumps(wrong_config), encoding="utf-8")
    with pytest.raises(ValueError, match="contract identity"):
        m.validate(corpus, config_copy)

    rows = corpus.read_text("utf-8").splitlines()
    first = json.loads(rows[0])
    first["messages"][0]["content"] += "\n"
    rows[0] = json.dumps(first, ensure_ascii=False, separators=(",", ":"))
    corpus_copy = tmp_path / "corpus.jsonl"
    corpus_copy.write_text("\n".join(rows) + "\n", encoding="utf-8")
    matching_config = json.loads(config.read_bytes())
    matching_config["training_corpus_sha256"] = m.sha(corpus_copy.read_bytes())
    config_copy.write_text(json.dumps(matching_config), encoding="utf-8")
    with pytest.raises(ValueError, match="renderer divergence"):
        m.validate(corpus_copy, config_copy)


@pytest.mark.parametrize("field", ["training_execution_profile", "performance_freeze_identity"])
def test_wrong_performance_profile_binding_fails_closed(tmp_path, field):
    m = module()
    corpus, config = paths("pastila-editor-core-v1.1-json-successor-v10")
    wrong_config = json.loads(config.read_bytes())
    wrong_config[field] = "WRONG"
    config_copy = tmp_path / "config.json"
    config_copy.write_text(json.dumps(wrong_config), encoding="utf-8")
    with pytest.raises(ValueError, match="training execution profile|performance freeze identity"):
        m.validate(corpus, config_copy)
