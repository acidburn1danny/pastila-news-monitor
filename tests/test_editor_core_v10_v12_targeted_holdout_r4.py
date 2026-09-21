import importlib.util
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "scripts/evaluate_editor_core_v10_v12_targeted_holdout_r4.py"
AUDITOR = ROOT / "scripts/audit_editor_core_v10_v12_targeted_holdout_r4.py"
SHELL = ROOT / "scripts/run_editor_core_v10_v12_targeted_holdout_r4.sh"


def load(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(value)
    return value


def test_requests_are_complete_and_target_free():
    runner = load(RUNNER, "r4_runner")
    rows = runner.validate_requests(ROOT / "docs/artifacts/editor-core-v10-v12-targeted-continuation-r4-holdout-requests.jsonl")
    assert len({runner.request_identity(row) for row in rows}) == 12


def test_fixture_smoke_and_leakage_rejection():
    runner = load(RUNNER, "r4_smoke")
    rows = [{"messages": [{"role": "system"}, {"role": "user"}]} for _ in range(2)]
    assert runner.fixture_smoke(rows)["inference_performed"] is False
    rows[0]["messages"][1]["role"] = "assistant"
    with pytest.raises(ValueError, match="leakage"):
        runner.fixture_smoke(rows)


def test_auditor_closes_receipt_rows_and_classes(tmp_path):
    auditor = load(AUDITOR, "r4_auditor")
    output = tmp_path / "out"; output.mkdir()
    keys = tmp_path / "key.jsonl"; key_rows = []
    candidate, adapter, requests, runner = "fixture", "a", "q", "r"
    for index in range(1, 13):
        case = f"case-{index}"; rid = f"sha256:{index:064x}"
        response = json.dumps({"schema":"pastila-core-v2-structured-qualification-response","schema_version":2,"case_id":case,"request_identity":rid,"output_type":"FACTUAL","outcome":"ANSWER","text":"Comisia consemnează suspiciunea că operatorul ar fi greșit; acesta neagă, fără hotărâre finală.","claim_bindings":[],"abstention_code":None}, ensure_ascii=False, separators=(",", ":"))
        row = {"index":index,"example_id":case,"request_identity":rid,"candidate":candidate,"response":response,"response_sha256":auditor.sha(response.encode()),"terminal_eos":True,"within_byte_ceiling":True,"nfc":True}
        (output / f"{index:03d}.json").write_bytes(auditor.canonical(row))
        key_rows.append({"example_id":case,"request_identity":rid,"failure_class":"FIXTURE","diagnostic_pattern":"ATTRIBUTION_DENIAL_FINALITY","assistant_target":response})
    keys.write_text("".join(json.dumps(row) + "\n" for row in key_rows), encoding="utf-8")
    core = {"schema":"pastila-editor-core-targeted-r4-holdout-inference-receipt","schema_version":1,"candidate":candidate,"adapter_sha256":adapter,"requests_sha256":requests,"runner_sha256":runner,"rows":12,"terminal_eos":12,"within_byte_ceiling":12,"network_activity":False,"training_performed":False,"optimizer_activity":False,"answer_key_accessed":False}
    (output / "inference-receipt.json").write_bytes(auditor.canonical({**core,"receipt_identity":auditor.sha(auditor.canonical(core))}))
    result = auditor.audit(output, keys, candidate, adapter, requests, runner)
    assert result["structural_passed"] == result["exact_target_passed"] == 12


def test_semantic_audit_detects_epistemic_regression():
    auditor = load(AUDITOR, "r4_semantic")
    key = {"diagnostic_pattern": "ATTRIBUTION_DENIAL_FINALITY"}
    safe = {"text": "Comisia consemnează suspiciunea că operatorul ar fi greșit; acesta neagă, fără hotărâre finală."}
    asserted = {"text": "Comisia a consemnat pozițiile greșite; operatorul neagă, fără hotărâre finală."}
    assert auditor.semantic_case_passes(key, safe)
    assert not auditor.semantic_case_passes(key, asserted)


def test_auditor_rejects_extra_output(tmp_path):
    output = tmp_path / "out"; output.mkdir(); (output / "extra").write_text("x")
    with pytest.raises(ValueError, match="closure"):
        load(AUDITOR, "r4_extra").audit(output, tmp_path / "key", "x", "a", "q", "r")


def test_shell_binds_only_the_two_expected_adapters_and_excludes_answer_key():
    source = SHELL.read_text(encoding="utf-8")
    assert "r2-step-9" in source and "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02" in source
    assert "r4-step-6" in source and "b33ad877554809d92e6a85ad1ce988d82fb047ae59ec504f820af020913cd032" in source
    assert "EXPECTED_PARENT_COMMIT=36f6c1340d1ffc3765ad28d8aeee26d7d9063bae" in source
    assert 'rev-parse HEAD^)' in source and 'rev-parse HEAD^^{tree})' in source
    assert 'GIT=(git -c "safe.directory=$REPOSITORY" -C "$REPOSITORY")' in source
    assert "git config --global" not in source
    assert "answer-key" not in source and "answer_key" not in source
    assert "--net" in source and "EVALUATION_EXECUTION_AUTHORIZED=1" in source
