from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_generation_wsl_host_executor_v1_1 import (
    GENERATION_WSL_HOST_EXECUTOR_IDENTITY,
    execute_generation_wsl_host_v1_1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_generation_wsl_invocation_binding_v1_1 import (
    PreparedGenerationWslInvocationV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_linux_generation_supervisor_candidate_v1_1 import (
    SUPERVISOR_CANDIDATE_IDENTITY,
)
from pastila_scout.wsl_execution_v1 import (
    WslExecutionReceiptV1,
    WslExecutionResultV1,
    WslInvocationV1,
    canonical_model_profile_v1,
)
from pastila_scout.wsl_execution_v1_1 import WslExecutionBoundaryV1_1

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = (
    ROOT
    / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-generation-wsl-host-executor-v1.json"
)


def _canonical(v):
    return (
        json.dumps(v, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n"
    ).encode()


def _prepared(tmp_path, boundary):
    inv = WslInvocationV1(
        "consumer", "a" * 64, boundary.profile.identity, ("wsl.exe",), "c" * 64
    )
    outer = tmp_path / "outer"
    return PreparedGenerationWslInvocationV1(
        "b" * 64,
        inv,
        "a" * 64,
        "request",
        "1" * 64,
        "d" * 64,
        outer,
        outer / "linux-generation",
    )


def _result(inv, code=0):
    receipt = WslExecutionReceiptV1(
        "pastila-canonical-wsl-execution-receipt",
        "1.0.0",
        inv.consumer_id,
        inv.authority_reference,
        inv.profile_identity,
        inv.command_identity,
        True,
        code,
        False,
        1.0,
        hashlib.sha256(b"").hexdigest(),
        hashlib.sha256(b"").hexdigest(),
        None,
    )
    return WslExecutionResultV1(code, "", "", receipt)


def _linux(path, authority, status="EXECUTION_FAILURE"):
    value = {
        "schema_name": "pastila-semantic-admission-v2-construction-obligation-v2-linux-generation-supervisor-receipt",
        "schema_version": "1.0.0",
        "supervisor_candidate_identity": SUPERVISOR_CANDIDATE_IDENTITY,
        "authority_receipt_identity": authority,
        "status": status,
        "child_exit_code": 0,
        "timed_out": False,
        "termination": None,
        "persisted_artifacts": [],
        "retry_count": 0,
        "receipt_identity": "",
    }
    value["receipt_identity"] = hashlib.sha256(
        _canonical({k: v for k, v in value.items() if k != "receipt_identity"})
    ).hexdigest()
    path.parent.mkdir(parents=True)
    path.write_bytes(_canonical(value))
    return value["receipt_identity"]


def test_executes_injected_transport_once_and_reconciles_typed_failure(
    tmp_path, monkeypatch
):
    boundary = WslExecutionBoundaryV1_1(
        canonical_model_profile_v1(with_pydantic_bridge=True)
    )
    prepared = _prepared(tmp_path, boundary)
    expected = _linux(
        prepared.linux_evidence_root / "supervisor-receipt.json",
        prepared.authority_receipt_identity,
    )
    # Move the synthetic Linux tree aside: the executor must create the outer root first.
    staged = tmp_path / "staged"
    prepared.linux_evidence_root.rename(staged)
    prepared.outer_evidence_root.rmdir()
    calls = []

    def fake(self, invocation, *, timeout_seconds):
        calls.append(timeout_seconds)
        prepared.outer_evidence_root.mkdir(exist_ok=True)
        staged.rename(prepared.linux_evidence_root)
        return _result(invocation)

    monkeypatch.setattr(WslExecutionBoundaryV1_1, "execute", fake)
    outcome = execute_generation_wsl_host_v1_1(prepared=prepared, boundary=boundary)
    assert calls == [1260.0] and outcome.status == "RECONCILED:EXECUTION_FAILURE"
    assert outcome.linux_supervisor_receipt_identity == expected
    assert (prepared.outer_evidence_root / "wsl-execution-receipt.json").is_file()
    assert (prepared.outer_evidence_root / "host-reconciliation.json").is_file()


def test_success_without_linux_receipt_fails_closed_after_transport_receipt(
    tmp_path, monkeypatch
):
    boundary = WslExecutionBoundaryV1_1(
        canonical_model_profile_v1(with_pydantic_bridge=True)
    )
    prepared = _prepared(tmp_path, boundary)
    monkeypatch.setattr(
        WslExecutionBoundaryV1_1,
        "execute",
        lambda self, invocation, **kw: _result(invocation),
    )
    with pytest.raises(RuntimeError, match="RECONCILIATION_FAILED"):
        execute_generation_wsl_host_v1_1(prepared=prepared, boundary=boundary)
    assert (prepared.outer_evidence_root / "wsl-execution-receipt.json").is_file()
    value = json.loads(
        (prepared.outer_evidence_root / "host-reconciliation.json").read_bytes()
    )
    assert value["status"] == "LINUX_EVIDENCE_RECONCILIATION_FAILURE"

def test_artifact_identity_and_no_real_execution():
    value = json.loads(ARTIFACT.read_bytes())
    fields = value["identity_derivation"]["ordered_utf8_fields"]
    assert (
        hashlib.sha256("\n".join(fields).encode()).hexdigest()
        == GENERATION_WSL_HOST_EXECUTOR_IDENTITY
    )
    assert value["authority"]["wsl_execution_during_verification"] is False
