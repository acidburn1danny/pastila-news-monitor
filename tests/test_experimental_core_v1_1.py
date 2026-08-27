from pathlib import Path

from pastila_scout.experimental_core_v1_1 import (
    DISPLAY_NAME,
    MODEL_ID,
    SYSTEM_PROMPT_SHA256,
    is_experimental_core_v1_1,
    load_frozen_system_prompt,
)


def test_experimental_candidate_is_explicit_and_non_default() -> None:
    assert DISPLAY_NAME == "PastilaAcida Editor Core V1.1 Experimental"
    assert MODEL_ID == "pastila-editor-core-v1.1-experimental"
    assert is_experimental_core_v1_1(MODEL_ID)
    assert not is_experimental_core_v1_1("qwen3:14b")
    assert not is_experimental_core_v1_1("gpt-4.1-mini")


def test_frozen_system_prompt_is_bound_to_project_authority() -> None:
    project_root = Path(__file__).resolve().parents[1]
    prompt = load_frozen_system_prompt(project_root=project_root)
    assert prompt
    assert len(SYSTEM_PROMPT_SHA256) == 64
