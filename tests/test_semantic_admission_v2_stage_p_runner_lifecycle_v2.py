from pathlib import Path


ROOT=Path(__file__).resolve().parents[1]


def test_runner_lifecycle_has_all_required_durable_events() -> None:
    source=(ROOT/"src/pastila_scout/experimental_core_v1_2_stage_p_constrained_runner_v2.py").read_text("utf-8")
    for event in ("RUNNER_STARTED","REQUEST_VALIDATED","TOKENIZER_LOAD_STARTED","TOKENIZER_LOAD_COMPLETED",
                  "TRIE_BUILD_STARTED","TRIE_BUILD_COMPLETED","PREWARM_STARTED","PREWARM_COMPLETED",
                  "MODEL_LOAD_STARTED","MODEL_LOAD_COMPLETED","PROMPT_TOKENIZED","GENERATION_STARTED",
                  "GENERATION_HEARTBEAT","TERMINAL_EOS","RESPONSE_PERSISTED","RUNNER_EXCEPTION"):
        assert f'"{event}"' in source


def test_heartbeat_preserves_partial_output_and_constraint_progress() -> None:
    source=(ROOT/"src/pastila_scout/experimental_core_v1_2_stage_p_constrained_runner_v2.py").read_text("utf-8")
    assert "partial_output=decoded" in source
    assert "generated_tokens=" in source and "dfa_mode=state.mode" in source
    assert ">=16" in source and ">=10" in source
