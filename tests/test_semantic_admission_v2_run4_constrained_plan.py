import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_run4_plan_preserves_bounded_contract() -> None:
    plan = json.loads((ROOT / "docs/artifacts/semantic-admission-v2-run4-constrained-plan.json").read_text("utf-8"))
    assert plan["run_id"] == "SAV2_TEN_CASE_CONFORMANCE_RUN_4_CONSTRAINED_V1"
    assert len(plan["case_ids"]) == 10
    assert plan["exact_provider_call_ceiling"] == 20
    assert plan["attempts_per_case_per_gate"] == 1
    assert plan["gate_order_per_case"] == ["FACTUAL_SEMANTIC", "STORY_SPECIFICITY"]
    assert plan["silent_retry"] is plan["repair"] is plan["selection"] is False
    assert plan["unrestricted_wsl_context_required"] is True
    assert plan["legacy_tokenizer_behavior_frozen"] is True


def test_run4_thin_runner_does_not_change_frozen_implementation() -> None:
    source = (ROOT / "scripts/run_semantic_admission_v2_ten_case_conformance_run4_constrained_v1.py").read_text("utf-8")
    assert "implementation.run()" in source
    assert "run4-execution-authority.json" in source
    assert ".generate(" not in source
