import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/evaluate_editor_core_v10_v12_targeted_holdout_v1.py"
AUDITOR = ROOT / "scripts/audit_editor_core_v10_v12_targeted_holdout_v1.py"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(value)
    return value


def test_fixture_smoke_has_no_model_or_training():
    rows = [{"messages": [{"role": "system"}, {"role": "user"}]} for _ in range(2)]
    result = load(RUNNER, "holdout_runner").fixture_smoke(rows)
    assert result["model_loaded"] is False
    assert result["inference_performed"] is False
    assert result["training_performed"] is False


def test_fixture_rejects_target_leakage():
    rows = [{"messages": [{"role": "system"}, {"role": "assistant"}]} for _ in range(2)]
    with pytest.raises(ValueError, match="leakage"):
        load(RUNNER, "holdout_runner_bad").fixture_smoke(rows)


def test_published_request_projection_is_complete():
    runner = load(RUNNER, "holdout_runner_projection")
    requests = ROOT / "docs/artifacts/editor-core-v10-v12-targeted-continuation-v1-holdout-requests.jsonl"
    rows = runner.validate_requests(requests)
    identities = [runner.request_identity(row) for row in rows]
    assert len(identities) == 32
    assert len(set(identities)) == 32


def test_auditor_counts_structural_and_exact(tmp_path):
    keys = tmp_path / "keys.jsonl"
    output = tmp_path / "output"
    output.mkdir()
    key_rows = []
    for index in range(1, 33):
        example = f"case-{index}"
        response = json.dumps({"schema":"x","schema_version":1,"case_id":example,"request_identity":f"sha256:{index}","output_type":"FACTUAL","outcome":"ABSTAIN","text":None,"claim_bindings":[],"abstention_code":"INSUFFICIENT_AUTHORITY"}, ensure_ascii=False, separators=(",", ":"))
        key_rows.append({"example_id":example,"failure_class":"FIXTURE","assistant_target":response})
        row = {"example_id":example,"request_identity":f"sha256:{index}","candidate":"fixture","response":response,"terminal_eos":True,"within_byte_ceiling":True,"nfc":True}
        (output / f"{index:03d}.json").write_text(json.dumps(row), encoding="utf-8")
    keys.write_text("".join(json.dumps(row) + "\n" for row in key_rows), encoding="utf-8")
    result = load(AUDITOR, "holdout_auditor").audit(output, keys)
    assert result["structural_passed"] == 32
    assert result["exact_target_passed"] == 32
