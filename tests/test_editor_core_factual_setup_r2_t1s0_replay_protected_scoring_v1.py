from pathlib import Path


SOURCE = Path("scripts/score_editor_core_factual_setup_r2_t1s0_replay_protected_v1.py").read_text(encoding="utf-8")


def test_scoring_is_bound_to_closed_inference_and_has_no_selection_authority():
    assert 'PASS_7_DEVELOPMENT_REPLAY_BUNDLES' in SOURCE
    assert 'receipt["responses_sha256"] != sha(response_bytes)' in SOURCE
    assert 'receipt.get("receipt_identity") != sha(canonical(receipt_core))' in SOURCE
    assert 'program["receipts"] != [receipts[candidate] for candidate in EXPECTED]' in SOURCE
    assert '"PARENT_SELECTION"' in SOURCE
    assert '"parent_changed": False' in SOURCE
    assert '"historical_holdout_accessed": False' in SOURCE
    assert '"optimizer_steps": 0' in SOURCE


def test_frozen_decision_gates_are_applied_per_protected_seed():
    assert 'MATERIAL_NUMERIC_RECONCILIATION_REGRESSION' in SOURCE
    assert '"NOVEL_ACTOR"' in SOURCE
    assert 'replicated_gain and zero_material_replay_regressions and common_gate' in SOURCE
    assert 'SEEDS = (161803, 271828, 314159)' in SOURCE
    assert 'row["split"] == "INDEPENDENT_SELECTION_BENCHMARK"' in SOURCE
    assert 'row["split"] == "REPLAY_RETENTION"' in SOURCE
    assert 'len(dev) != 24 or len(replay) != 24' in SOURCE
    assert 'def has_repeated_clause' in SOURCE
    assert 'normalized_repeated_clause_cases' in SOURCE
