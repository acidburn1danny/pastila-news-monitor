import hashlib, json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "docs" / "artifacts"

def identity(value, field):
    body = {k: v for k, v in value.items() if k != field}
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(raw).hexdigest()

def load(name):
    return json.loads((ART / name).read_text(encoding="utf-8"))

def test_experiment_is_non_promotable_and_three_seed():
    result = load("vnext-qwen3-experimental-lora-v1-training-result.json")
    assert [x["seed"] for x in result["runs"]] == [1701, 2903, 4517]
    assert result["promotion"] is False
    assert result["result_identity"] == identity(result, "result_identity")

def test_blind_evaluation_fail_closed():
    result = load("vnext-qwen3-experimental-lora-v1-evaluation-result.json")
    assert result["terminal"] == "CONTINUE_EXPERIMENTAL_EVIDENCE"
    assert result["acceptance"]["quality_gain_ge_0_50"] is False
    assert result["holdout"]["unsealed"] is False
    assert all(x["unsupported_fact_rate_after_projection"] == 0 for x in result["factual_projection"].values())
    assert result["result_identity"] == identity(result, "result_identity")

def test_car_and_protected_state_closure():
    audit = load("vnext-qwen3-experimental-lora-v1-audit.json")
    assert audit["status"] == "PASS_0_INTEGRITY_BLOCKERS_NON_PROMOTABLE"
    assert audit["cars"][0]["pre_car_evidence_used"] is False
    assert audit["active_product_modified"] is False
    assert audit["canonical_rollback_modified"] is False
    assert audit["audit_identity"] == identity(audit, "audit_identity")
