from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from test_semantic_admission_v2_stage_p_construction_obligation_v2_injected_generation_worker_supervisor_v1 import (
    _policy,
)
from test_semantic_admission_v2_stage_p_construction_obligation_v2_linux_source_binding_v1_1 import (
    _authority,
)
from test_semantic_admission_v2_stage_p_construction_obligation_v2_runner_protocol_codec_v1 import (
    _fixture,
)

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_generation_wsl_invocation_binding_v1_1 import (
    OUTER_TIMEOUT_SECONDS,
    RUNNER_MODULE,
    RUNNER_SOURCE_SHA256,
    build_generation_wsl_invocation_v1_1,
)
from pastila_scout.wsl_execution_v1 import canonical_model_profile_v1
from pastila_scout.wsl_execution_v1_1 import WslExecutionBoundaryV1_1

ROOT = Path(__file__).resolve().parents[1]
PROMPT = ROOT / ".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt"


def _inputs(tmp_path):
    raw, request = _fixture()
    policy = tmp_path / "policy"
    policy.write_bytes(_policy())
    authority = tmp_path / "authority"
    authority.write_bytes(_authority(raw, request))
    request_path = tmp_path / "request"
    request_path.write_bytes(raw)
    return policy, authority, request_path


def test_builds_exact_v1_1_runner_invocation_without_launch(tmp_path) -> None:
    policy, authority, request = _inputs(tmp_path)
    outer = tmp_path / "evidence"
    boundary = WslExecutionBoundaryV1_1(
        canonical_model_profile_v1(with_pydantic_bridge=True))
    prepared = build_generation_wsl_invocation_v1_1(
        project_root=ROOT, policy_receipt_path=policy,
        authority_receipt_path=authority, runner_request_path=request,
        system_prompt_path=PROMPT, outer_evidence_root=outer, boundary=boundary)
    command = prepared.invocation.command
    assert ("-m", RUNNER_MODULE) == command[7:9]
    assert RUNNER_MODULE.endswith("linux_generation_runner_v1_1")
    assert OUTER_TIMEOUT_SECONDS == 1260.0 and not outer.exists()
    runner = ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_linux_generation_runner_v1_1.py"
    assert hashlib.sha256(runner.read_bytes()).hexdigest() == RUNNER_SOURCE_SHA256


def test_cross_request_authority_fails_before_invocation(tmp_path) -> None:
    policy, authority, request = _inputs(tmp_path)
    raw, _ = _fixture()
    request.write_bytes(raw + b"x")
    boundary = WslExecutionBoundaryV1_1(
        canonical_model_profile_v1(with_pydantic_bridge=True))
    with pytest.raises(ValueError):
        build_generation_wsl_invocation_v1_1(
            project_root=ROOT, policy_receipt_path=policy,
            authority_receipt_path=authority, runner_request_path=request,
            system_prompt_path=PROMPT, outer_evidence_root=tmp_path / "evidence",
            boundary=boundary)
