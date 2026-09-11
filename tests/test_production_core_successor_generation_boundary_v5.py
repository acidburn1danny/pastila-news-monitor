import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / "src/pastila_scout/production_core_candidate_qualification_runner_v3.py"


def test_runner_stops_and_types_impossible_oversized_output():
    source = RUNNER.read_text("utf-8")
    ast.parse(source)
    assert "class OutputByteCeiling(StoppingCriteria):" in source
    assert "size > 6268" in source
    assert "response.shape[0] % 32" in source
    assert '"OUTPUT_BYTE_CEILING_EXCEEDED"' in source
    assert '"MAX_NEW_TOKENS_EXHAUSTED"' in source
    assert source.index("stopping_criteria=StoppingCriteriaList") < source.index(
        '"termination_reason": termination_reason'
    )


def test_boundary_remains_deterministic_and_fail_closed():
    source = RUNNER.read_text("utf-8")
    assert "do_sample=False" in source
    assert "num_beams=1" in source
    assert '"EXECUTION_ENVELOPE_FAIL_CLOSED"' in source
    assert "retry" not in source.lower()


def test_training_fails_closed_without_one_terminal_supervised_eos():
    source = (
        ROOT / "scripts/train_production_core_candidate_successor_v1.py"
    ).read_text("utf-8")
    assert "tokens[-1] != tokenizer.eos_token_id" in source
    assert "tokenizer.eos_token_id in tokens[len(prefix) : -1]" in source
    assert 'expected_rows = 320 if config.get("schema_version") == 2 else 240' in source
