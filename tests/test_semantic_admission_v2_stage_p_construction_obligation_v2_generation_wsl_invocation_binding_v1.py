from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_generation_wsl_invocation_binding_v1 import (
    GENERATION_WSL_INVOCATION_BINDING_IDENTITY,
    OUTER_TIMEOUT_SECONDS,
    RUNNER_MODULE,
    build_generation_wsl_invocation_v1,
)
from pastila_scout.wsl_execution_v1 import canonical_model_profile_v1
from pastila_scout.wsl_execution_v1_1 import WslExecutionBoundaryV1_1

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = (
    ROOT
    / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-generation-wsl-invocation-binding-v1.json"
)
PROMPT = (
    ROOT
    / ".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt"
)
sys.path.insert(0, str(ROOT / "tests"))
from test_semantic_admission_v2_stage_p_construction_obligation_v2_injected_generation_worker_supervisor_v1 import (
    _policy,
)
from test_semantic_admission_v2_stage_p_construction_obligation_v2_linux_generation_supervisor_candidate_v1 import (
    _authority,
)
from test_semantic_admission_v2_stage_p_construction_obligation_v2_runner_protocol_codec_v1 import (
    _fixture,
)


def test_builds_exact_bridge_invocation_without_launch(tmp_path):
    raw, request = _fixture()
    policy = tmp_path / "policy"
    policy.write_bytes(_policy())
    authority = tmp_path / "authority"
    authority.write_bytes(_authority(request))
    request_path = tmp_path / "request"
    request_path.write_bytes(raw)
    outer = tmp_path / "evidence"
    boundary = WslExecutionBoundaryV1_1(
        canonical_model_profile_v1(with_pydantic_bridge=True)
    )
    prepared = build_generation_wsl_invocation_v1(
        project_root=ROOT,
        policy_receipt_path=policy,
        authority_receipt_path=authority,
        runner_request_path=request_path,
        system_prompt_path=PROMPT,
        outer_evidence_root=outer,
        boundary=boundary,
    )
    command = prepared.invocation.command
    assert command[:5] == ("wsl.exe", "-d", "Ubuntu-24.04", "--", "env")
    assert ("-m", RUNNER_MODULE) == command[7:9]
    assert command[-1].endswith("/evidence/linux-generation")
    assert (
        prepared.invocation.authority_reference == prepared.authority_receipt_identity
    )
    assert OUTER_TIMEOUT_SECONDS == 1260.0 and not outer.exists()


def test_artifact_identity_and_no_execution():
    value = json.loads(ARTIFACT.read_bytes())
    fields = value["identity_derivation"]["ordered_utf8_fields"]
    assert (
        hashlib.sha256("\n".join(fields).encode()).hexdigest()
        == GENERATION_WSL_INVOCATION_BINDING_IDENTITY
    )
    assert value["authority"]["wsl_execution"] is False
    assert value["authority"]["generation_or_inference"] is False
