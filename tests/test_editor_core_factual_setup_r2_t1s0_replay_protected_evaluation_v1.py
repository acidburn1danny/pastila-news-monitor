import ast
from pathlib import Path


SOURCE = Path("scripts/evaluate_editor_core_factual_setup_r2_t1s0_replay_protected_v1.py")


def test_frozen_candidate_partition_and_decoding_contract():
    text = SOURCE.read_text(encoding="utf-8")
    tree = ast.parse(text)
    assert "ROWS = 48" in text and "CANDIDATES = 7" in text
    assert '"INDEPENDENT_SELECTION_BENCHMARK": 24' in text
    assert '"REPLAY_RETENTION": 24' in text
    assert "do_sample=False" in text and "num_beams=1" in text
    assert "max_new_tokens=MAX_NEW_TOKENS" in text
    assert "prefix_allowed_tokens_fn=allowed" in text
    assert "validate_generated_response(text, payload, eos)" in text
    assert "answer_key_accessed\": False" in text
    assert "historical_holdout_accessed\": False" in text
    assert "training_performed\": False" in text and "optimizer_steps\": 0" in text
    assert not any(isinstance(node, ast.ImportFrom) and node.module and "holdout" in node.module for node in ast.walk(tree))


def test_worker_is_fail_closed_before_ml_imports():
    text = SOURCE.read_text(encoding="utf-8")
    authority = text.index('EDITOR_T1S0_REPLAY_EVALUATION_AUTHORIZED')
    torch_import = text.index("    import torch")
    assert authority < torch_import
    assert "any(args.output.iterdir())" in text
    assert "adapter identity" in text and "requests identity" in text
