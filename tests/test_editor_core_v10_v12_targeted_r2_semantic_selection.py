import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "docs/artifacts/editor-core-v10-v12-targeted-r2-semantic-result.json"
PLAN = ROOT / "docs/editor-core-v10-v12-targeted-r3-failure-mining-plan.md"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True, separators=(",", ":")).encode()


def test_semantic_result_identity_and_development_selection():
    value = json.loads(RESULT.read_bytes())
    core = {key: item for key, item in value.items() if key != "result_identity"}
    assert value["result_identity"] == hashlib.sha256(canonical(core)).hexdigest()
    assert value["selection"]["scope"] == "DEVELOPMENT_ONLY"
    assert value["selection"]["selected_adapter_identity"] == "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02"
    assert value["selection"]["promotion"] is value["selection"]["release"] is False
    assert value["r2"]["semantic_passed"] == 12 > value["r1"]["semantic_passed"] == 8


def test_failure_mining_scope_is_exactly_six_epistemic_cases():
    value = json.loads(RESULT.read_bytes())
    cases = value["unresolved_r2_case_ids"]
    assert len(cases) == len(set(cases)) == 6
    assert all("holdout-epistemic-calibration" in case for case in cases)
    plan = PLAN.read_text(encoding="utf-8")
    assert "24 new targeted training rows" in plan
    assert "24 replay anchors" in plan
    assert "new independent 12-case holdout" in plan
    assert "six optimizer" in plan


def test_case_decisions_reproduce_semantic_totals():
    value = json.loads(RESULT.read_bytes())
    decisions = value["case_decisions"]
    assert len(decisions) == len({row["case_id"] for row in decisions}) == 18
    r1 = sum(row["verdict"] in {"BOTH_PASS", "R1_PASS_R2_FAIL"} for row in decisions)
    r2 = sum(row["verdict"] in {"BOTH_PASS", "R1_FAIL_R2_PASS"} for row in decisions)
    assert (r1, r2) == (value["r1"]["semantic_passed"], value["r2"]["semantic_passed"]) == (8, 12)


def test_publication_safe_and_no_execution_claims():
    raw = RESULT.read_text(encoding="utf-8")
    assert "/root/" not in raw and "C:\\" not in raw and "D:\\" not in raw
    value = json.loads(raw)
    assert value["training_performed_by_selection"] is False
    assert value["adjudication_performed"] is False
    assert value["local_paths_published"] is False
