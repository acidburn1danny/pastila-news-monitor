from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_linux_generation_composition_v1 import (
    LINUX_GENERATION_COMPOSITION_IDENTITY,
    LinuxGenerationCompositionOutcomeV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_linux_generation_runner_v1 import (
    INNER_TIMEOUT_SECONDS,
    LINUX_GENERATION_RUNNER_IDENTITY,
    run_linux_generation_runner_v1,
)

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = (
    ROOT
    / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-linux-generation-runner-v1.json"
)
PROMPT = (
    ROOT
    / ".experimental-0-3-core-v1-2-journalistic-deontology-prime-directive-v1-evidence/PASTILAACIDA_EDITOR_CORE_SYSTEM_PROMPT_V1_2.txt"
)


def test_five_path_boundary_calls_only_injected_composition(tmp_path):
    policy = tmp_path / "policy.json"
    policy.write_bytes(b"policy")
    authority = tmp_path / "authority.json"
    authority.write_bytes(b"authority")
    request = tmp_path / "request.json"
    request.write_bytes(b"request")
    evidence = tmp_path / "evidence"
    calls = []
    expected = LinuxGenerationCompositionOutcomeV1(
        LINUX_GENERATION_COMPOSITION_IDENTITY, "sink", object(), ()
    )

    def fake(**kwargs):
        calls.append(kwargs)
        return expected

    result = run_linux_generation_runner_v1(
        policy_receipt_path=policy,
        authority_receipt_path=authority,
        runner_request_path=request,
        system_prompt_path=PROMPT,
        evidence_root=evidence,
        composition=fake,
    )
    assert result is expected
    assert calls[0]["raw_policy_receipt"] == b"policy"
    assert calls[0]["raw_authority_receipt"] == b"authority"
    assert calls[0]["raw_runner_request"] == b"request"
    assert calls[0]["evidence_root"] == evidence
    assert calls[0]["timeout_seconds"] == INNER_TIMEOUT_SECONDS == 1200.0
    assert not evidence.exists()


def test_rejects_existing_root_and_prompt_drift_before_composition(tmp_path):
    files = []
    for name in ("policy", "authority", "request"):
        path = tmp_path / name
        path.write_bytes(b"x")
        files.append(path)
    drift = tmp_path / "prompt"
    drift.write_text("drift", "utf-8")
    calls = []
    with pytest.raises(ValueError, match="SYSTEM_PROMPT_IDENTITY"):
        run_linux_generation_runner_v1(
            policy_receipt_path=files[0],
            authority_receipt_path=files[1],
            runner_request_path=files[2],
            system_prompt_path=drift,
            evidence_root=tmp_path / "new",
            composition=lambda **kw: calls.append(kw),
        )
    assert calls == []
    existing = tmp_path / "existing"
    existing.mkdir()
    with pytest.raises(FileExistsError):
        run_linux_generation_runner_v1(
            policy_receipt_path=files[0],
            authority_receipt_path=files[1],
            runner_request_path=files[2],
            system_prompt_path=PROMPT,
            evidence_root=existing,
            composition=lambda **kw: calls.append(kw),
        )
    assert calls == []


def test_artifact_identity_and_no_execution_claim():
    value = json.loads(ARTIFACT.read_bytes())
    fields = value["identity_derivation"]["ordered_utf8_fields"]
    assert (
        hashlib.sha256("\n".join(fields).encode()).hexdigest()
        == LINUX_GENERATION_RUNNER_IDENTITY
    )
    assert value["authority"] == {
        "source_normalization": True,
        "module_import_execution": False,
        "runner_invoked_during_verification": False,
        "filesystem_or_process_execution": False,
        "tokenizer_or_model_loading": False,
        "generation_or_inference": False,
        "wsl_or_provider_execution": False,
        "stage_c": False,
        "runtime_or_production": False,
    }
