import hashlib, json
from pathlib import Path

RESULT=Path("docs/artifacts/editor-core-factual-setup-r2-anchored-contrastive-safety-deterministic-result-v1.json")
SCORER=Path("scripts/score_editor_core_factual_setup_r2_anchored_contrastive_safety_v1.py")

def canonical(v):
    return json.dumps(v,ensure_ascii=False,allow_nan=False,sort_keys=True,separators=(",", ":")).encode()

def test_terminal_result_is_identity_closed_and_research_only():
    value=json.loads(RESULT.read_text(encoding="utf-8")); identity=value.pop("result_identity")
    assert identity==hashlib.sha256(canonical(value)).hexdigest()
    assert value["decision"]=="STOP"
    assert value["rows"]==value["terminal_eos"]==624
    assert value["development_parent"]=="R2_STEP_9" and not value["parent_changed"]
    assert not value["parent_selection_authority"] and not value["historical_holdout_accessed"]
    assert value["material_candidate_regressions"]==8
    assert set(value["replicated_development_gain_seeds"].values())=={0}

def test_scorer_fails_closed_and_keeps_factorial_axes_explicit():
    source=SCORER.read_text(encoding="utf-8")
    for marker in ("program closure","receipt_identity","program binding","P1_MINUS_P0_AT_K0","K1_MINUS_K0_AT_P1","no overwrite"):
        assert marker in source
