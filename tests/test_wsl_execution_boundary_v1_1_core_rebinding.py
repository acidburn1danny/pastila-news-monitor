from pathlib import Path

from pastila_scout.experimental_core_v1_1 import ExperimentalCoreV11Executor
from pastila_scout.experimental_core_v1_2 import ExperimentalCoreV12Executor
from pastila_scout.wsl_execution_v1 import (
    WslExecutionBoundaryV1,
    canonical_model_profile_v1,
)
from pastila_scout.wsl_execution_v1_1 import WslExecutionBoundaryV1_1


ROOT = Path(__file__).resolve().parents[1]


def test_v1_1_candidate_command_is_byte_equivalent_to_frozen_v1():
    profile = canonical_model_profile_v1()
    frozen = WslExecutionBoundaryV1(profile)
    candidate = WslExecutionBoundaryV1_1(profile)
    arguments = (
        "/mnt/c/Projects/pastila-news-monitor/runner.py",
        "/mnt/c/Projects/pastila-news-monitor/request știre.json",
        "--literal=$()",
    )
    kwargs = {
        "consumer_id": "editor-core-v1.2",
        "authority_reference": "zero-inference:command-equivalence",
        "arguments": arguments,
    }
    before = frozen.build_invocation(**kwargs)
    after = candidate.build_invocation(**kwargs)
    assert after == before
    assert after.command_identity == before.command_identity


def test_active_core_defaults_bind_only_to_v1_1_without_execution():
    v11 = ExperimentalCoreV11Executor(project_root=ROOT)
    v12 = ExperimentalCoreV12Executor(project_root=ROOT, max_output_tokens=64)
    assert type(v11._wsl_boundary) is WslExecutionBoundaryV1_1
    assert type(v12._wsl_boundary) is WslExecutionBoundaryV1_1


def test_rebinding_changes_no_model_prompt_or_request_constants():
    for relative in (
        "src/pastila_scout/experimental_core_v1_1.py",
        "src/pastila_scout/experimental_core_v1_2.py",
    ):
        source = (ROOT / relative).read_text("utf-8")
        assert "canonical_model_profile_v1()" in source
        assert "WslExecutionBoundaryV1_1" in source
        assert "subprocess.run" not in source
        assert '"wsl.exe"' not in source
