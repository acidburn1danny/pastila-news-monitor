from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]


def test_profiler_has_no_model_or_generation_edge() -> None:
    source=(ROOT/"src/pastila_scout/experimental_core_v1_2_stage_p_callback_profiler.py").read_text("utf-8")
    assert "AutoModel" not in source and "model.generate" not in source and "PeftModel" not in source
    assert '"model_calls":0' in source and '"provider_calls":0' in source


def test_profiler_covers_1_4_8_short_max_and_invalid_inputs() -> None:
    source=(ROOT/"src/pastila_scout/experimental_core_v1_2_stage_p_callback_profiler.py").read_text("utf-8")
    assert "for entries in (1,4,8)" in source
    assert '"SHORT",24' in source and '"MAX_BOUNDED",400' in source
    assert "WRONG_ROOT" in source and "INVALID_ENUM" in source and "TRAILING_BYTES" in source
    assert "9_EVEN_DETERMINISTIC_CHECKPOINTS" in source
