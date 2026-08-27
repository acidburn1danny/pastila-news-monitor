from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_assessment_is_zero_inference_and_non_authorizing() -> None:
    source = (ROOT / "scripts/assess_semantic_admission_v2_tokenizer_regex_impact_v1.py").read_text("utf-8")
    worker = (ROOT / "scripts/tokenizer_regex_impact_worker_v1.py").read_text("utf-8")
    assert '"model_calls": 0' in source and '"provider_calls": 0' in source
    assert '"run4_execution_authorized": False' in source
    assert "AutoModel" not in worker and ".generate(" not in worker


def test_assessment_binds_ten_prompts_and_constraint_samples() -> None:
    source = (ROOT / "scripts/assess_semantic_admission_v2_tokenizer_regex_impact_v1.py").read_text("utf-8")
    assert '"exact_gate_f_prompt_count": 10' in source
    assert "canonical:pass" in source and "prefix:fail-span" in source
