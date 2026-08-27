import json
from pathlib import Path

from pastila_scout.experimental_core_v1_2 import (
    ADAPTER_PATH,
    BASE_PATH,
    DISPLAY_NAME,
    MODEL_ID,
    SYSTEM_PROMPT_SHA256,
    ExperimentalCoreV12Executor,
    _wsl_path,
    is_experimental_core_v1_2,
    load_frozen_system_prompt,
)


def test_v1_2_is_explicit_experimental_and_non_default() -> None:
    assert DISPLAY_NAME == "PastilaAcida Editor Core V1.2 Experimental"
    assert MODEL_ID == "pastila-editor-core-v1.2-experimental"
    assert is_experimental_core_v1_2(MODEL_ID)
    assert not is_experimental_core_v1_2("qwen3:14b")
    assert not is_experimental_core_v1_2("pastila-editor-core-v1.1-experimental")


def test_v1_2_package_bindings_are_frozen() -> None:
    project_root = Path(__file__).resolve().parents[1]
    assert load_frozen_system_prompt(project_root=project_root)
    assert len(SYSTEM_PROMPT_SHA256) == 64
    assert BASE_PATH.endswith("3cea74c1ebaf5ce5f5a2553de470e2ceab825142")
    assert ADAPTER_PATH.endswith("checkpoint-final/adapter")


def test_v1_2_lifecycle_markers_are_durably_serialized(tmp_path) -> None:
    path = tmp_path / "lifecycle.json"
    markers = {
        "executor_invoked": True,
        "runner_launch_attempted": True,
        "model_load_started": True,
        "model_load_succeeded": False,
        "inference_started": False,
        "inference_succeeded": False,
        "response_received": False,
        "response_validation_passed": False,
        "stderr_tail": "bounded failure",
    }

    ExperimentalCoreV12Executor._write_trace(path, markers)

    assert json.loads(path.read_text("utf-8")) == markers


def test_v1_2_executor_binds_authoritative_runtime_max_output_tokens() -> None:
    project_root = Path(__file__).resolve().parents[1]
    executor = ExperimentalCoreV12Executor(
        project_root=project_root, max_output_tokens=731
    )

    assert executor._max_output_tokens == 731


def test_v1_2_wsl_path_converts_c_drive() -> None:
    assert _wsl_path(Path(r"C:\Projects\pastila-news-monitor")) == (
        "/mnt/c/Projects/pastila-news-monitor"
    )


def test_v1_2_wsl_path_normalizes_drive_letter() -> None:
    assert _wsl_path(Path(r"D:\Data\News")) == "/mnt/d/Data/News"
    assert _wsl_path(Path(r"d:\Data\News")) == "/mnt/d/Data/News"


def test_v1_2_wsl_path_preserves_spaces() -> None:
    assert _wsl_path(Path(r"E:\Model Lab\run files\request.json")) == (
        "/mnt/e/Model Lab/run files/request.json"
    )


def test_v1_2_wsl_path_converts_exact_runner_path() -> None:
    runner = Path(
        r"C:\Projects\pastila-news-monitor\src\pastila_scout\experimental_core_v1_2_runner.py"
    )
    assert _wsl_path(runner) == (
        "/mnt/c/Projects/pastila-news-monitor/src/pastila_scout/"
        "experimental_core_v1_2_runner.py"
    )


def test_v1_2_path_conversion_does_not_replace_v1_1_behavior() -> None:
    from pastila_scout.experimental_core_v1_1 import _wsl_path as v1_1_wsl_path

    assert v1_1_wsl_path is not _wsl_path


def test_v1_2_uses_canonical_utf8_wsl_boundary_and_tolerates_absent_stderr(
    tmp_path,
) -> None:
    consumer_source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "pastila_scout"
        / "experimental_core_v1_2.py"
    ).read_text("utf-8")
    boundary_source = (
        Path(__file__).resolve().parents[1]
        / "src"
        / "pastila_scout"
        / "wsl_execution_v1_1"
        / "boundary.py"
    ).read_text("utf-8")

    assert 'encoding="utf-8"' in boundary_source
    assert 'errors="replace"' in boundary_source
    assert "canonical_model_profile_v1()" in consumer_source
    assert '(completed.stderr or "")[-4000:]' in consumer_source
    assert '(completed.stdout or "")[-4000:]' in consumer_source
