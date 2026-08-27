import ast
from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]
RUNNER=ROOT/"src/pastila_scout/semantic_admission_v2/run_stage_p_case01_v3_probe.py"


def test_probe_is_case01_stage_p_only_and_one_call() -> None:
    source=RUNNER.read_text("utf-8")
    assert 'CASE_ID="HMCV1-SASC-01"' in source
    assert 'stage="P"' in source and 'stage="C"' not in source
    assert "ConstrainedGateFCoreV12Executor" not in source
    assert source.count("output=evaluator(request)")==1
    assert '"maximum_provider_calls":1' in source
    assert '"stage_c_constructed":False' in source and '"stage_c_called":False' in source


def test_probe_is_syntax_valid_and_uses_v3_durable_executor() -> None:
    source=RUNNER.read_text("utf-8")
    ast.parse(source)
    assert "DurableConstrainedStagePCoreV12ExecutorV3" in source
    assert "timeout_seconds=240.0" in source and "max_output_tokens" not in source
    assert "retry_count\":0" in source and "repair_count\":0" in source and "selection_count\":0" in source
