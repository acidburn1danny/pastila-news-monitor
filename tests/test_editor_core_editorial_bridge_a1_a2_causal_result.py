import hashlib
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RESULT = ROOT / "docs/artifacts/editor-core-editorial-bridge-a1-a2-causal-result-v1.json"
NOTE = ROOT / "docs/editor-core-editorial-bridge-a1-a2-causal-result-v1.md"
ACTIVE = ROOT / "docs/editor-core-active-development-state.md"


def canonical(value: object) -> bytes:
    return json.dumps(value, ensure_ascii=False, allow_nan=False, sort_keys=True,
                      separators=(",", ":")).encode()


def load() -> dict:
    return json.loads(RESULT.read_bytes())


def test_result_identity_and_evidence_closure():
    value = load()
    core = {key: item for key, item in value.items() if key != "result_identity"}
    assert value["result_identity"] == hashlib.sha256(canonical(core)).hexdigest()
    evidence = value["evidence"]
    assert evidence["primary_closure_identity"] == "9e6f64a8ce6ac8a59cb8c7bf1d3ab230e784081d979a1dc3bf49083b8276ec56"
    assert evidence["reference_closure_identity"] == "0336aa36d334042a8b14ce934af2b39f31c03fda04110185d7ccf28bcd0780d8"
    assert evidence["primary_records"] == 72
    assert evidence["reference_records"] == 24
    assert evidence["records_modified_by_decision"] is False


def test_aggregates_and_stop_decision_close():
    value = load()
    assert sum(value["pair_winners"][key] for key in ("A1", "A2", "TIE", "INDETERMINATE")) == 72
    assert sum(value["case_aggregation"][key] for key in ("A1_WIN", "A2_WIN", "TIE_OR_INDETERMINATE")) == 24
    assert all(seed["a2_net"] < 0 for seed in value["seed_results"])
    assert value["regressions"]["confirmed_material_factual_or_epistemic_seed_results"] > 0
    assert value["decision"]["outcome"] == "STOP"
    assert value["decision"]["target_design_state"] == "CLOSED_NOT_TO_BE_RESUMED"
    assert value["decision"]["continue_criteria_satisfied"] is False


def test_r2_parent_and_claim_boundaries_remain_closed():
    value = load()
    parent = value["development_parent"]
    assert parent["name"] == "R2_STEP_9"
    assert parent["adapter_identity"] == "c680d686f0b139e618d99fab235c62267caa9482df0efbccb44cb2c58c124f02"
    assert parent["changed"] is False
    assert "NATURALISTIC_TRANSFER" in value["claim_limits"]["forbidden"]
    assert value["holdout_opened"] is False
    assert value["training_performed_by_decision"] is False
    assert value["inference_performed_by_decision"] is False
    assert value["promotion"] is value["release"] is False


def test_publication_safe_note_and_active_state():
    combined = RESULT.read_text(encoding="utf-8") + NOTE.read_text(encoding="utf-8")
    assert "/root/" not in combined and "C:\\" not in combined and "D:\\" not in combined
    active = ACTIVE.read_text(encoding="utf-8")
    assert "A2 causal pilot" in active
    assert "R2 step-9 therefore remains the single development parent" in active
