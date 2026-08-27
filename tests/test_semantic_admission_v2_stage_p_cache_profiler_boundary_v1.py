from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]


def test_profiler_is_zero_inference_and_binds_candidate() -> None:
    source=(ROOT/"src/pastila_scout/experimental_core_v1_2_stage_p_cache_profiler.py").read_text("utf-8")
    assert "AutoModel" not in source and "model.generate" not in source and "PeftModel" not in source
    assert "CANDIDATE_SOURCE_SHA256" in source and '"model_calls":0' in source and '"provider_calls":0' in source


def test_profiler_compares_six_shapes_and_targeted_string_lengths() -> None:
    source=(ROOT/"src/pastila_scout/experimental_core_v1_2_stage_p_cache_profiler.py").read_text("utf-8")
    assert "for entries in (1,4,8)" in source and '"MAX_BOUNDED",400' in source
    assert "for length in (0,1,2,8,64,256,400)" in source
