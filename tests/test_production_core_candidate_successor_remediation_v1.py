import importlib.util
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts/materialize_production_core_candidate_successor_remediation_v1.py"
ART = ROOT / "docs/artifacts"


def module():
    spec = importlib.util.spec_from_file_location("successor_remediation", SCRIPT)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(value)
    return value


def test_remediation_examples_are_raw_canonical_json_and_holdout_isolated():
    value = module()
    rows = value.examples()
    assert len(rows) == 240
    value.assert_isolated(rows)
    assert all(row["example_id"].startswith("rem3-") for row in rows)
    assert all("```" not in row["messages"][2]["content"] for row in rows)


def test_published_corpus_and_configs_are_reproducible(tmp_path):
    value = module()
    import sys

    prior = sys.argv
    try:
        sys.argv = [str(SCRIPT), "--output-dir", str(tmp_path)]
        assert value.main() == 0
    finally:
        sys.argv = prior
    names = [
        "production-core-candidate-successor-remediation-corpus-v1.jsonl",
        "production-core-candidate-successor-remediation-corpus-v1.json",
        "production-core-v1.1-json-successor-training-config-v1.json",
        "production-core-v1.2-json-successor-training-config-v1.json",
    ]
    for name in names:
        assert (tmp_path / name).read_bytes() == (ART / name).read_bytes()
    manifest = json.loads((ART / names[1]).read_bytes())
    assert manifest["qualification_or_holdout_examples_used"] == 0
    assert manifest["consumed_attempt_outputs_used"] == 0
    assert manifest["target_markdown_fence_count"] == 0
