from __future__ import annotations

import hashlib
from pathlib import Path

from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_generation_wsl_host_executor_v1_2 import GENERATION_WSL_HOST_EXECUTOR_IDENTITY, GENERATION_WSL_HOST_EXECUTOR_IDENTITY_FIELDS, execute_generation_wsl_host_v1_2
from pastila_scout.semantic_admission_v2.stage_p_construction_obligation_v2_generation_wsl_invocation_binding_v1_1 import PreparedGenerationWslInvocationV1
from pastila_scout.wsl_execution_v1 import WslExecutionReceiptV1, WslExecutionResultV1, WslInvocationV1, canonical_model_profile_v1
from pastila_scout.wsl_execution_v1_1 import WslExecutionBoundaryV1_1


def test_nonzero_transport_persists_exact_streams_before_receipts(tmp_path, monkeypatch):
    boundary = WslExecutionBoundaryV1_1(canonical_model_profile_v1(with_pydantic_bridge=True))
    invocation = WslInvocationV1("consumer", "a" * 64, boundary.profile.identity, ("forbidden",), "c" * 64)
    outer = tmp_path / "outer"
    prepared = PreparedGenerationWslInvocationV1(
        "b" * 64, invocation, "a" * 64, "request", "1" * 64,
        "d" * 64, outer, outer / "linux-generation",
    )
    stdout, stderr = "out\n", "err\n"
    receipt = WslExecutionReceiptV1(
        "pastila-canonical-wsl-execution-receipt", "1.0.0", "consumer",
        "a" * 64, boundary.profile.identity, "c" * 64, True, 1, False, 1.0,
        hashlib.sha256(stdout.encode()).hexdigest(),
        hashlib.sha256(stderr.encode()).hexdigest(), None,
    )
    calls = []
    def fake(self, observed, *, timeout_seconds):
        calls.append((observed, timeout_seconds))
        return WslExecutionResultV1(1, stdout, stderr, receipt)
    monkeypatch.setattr(WslExecutionBoundaryV1_1, "execute", fake)
    outcome = execute_generation_wsl_host_v1_2(prepared=prepared, boundary=boundary)
    assert len(calls) == 1 and outcome.status == "TRANSPORT_FAILURE"
    assert (outer / "wsl-stdout.bin").read_bytes() == stdout.encode()
    assert (outer / "wsl-stderr.bin").read_bytes() == stderr.encode()
    assert (outer / "wsl-execution-receipt.json").is_file()
    assert (outer / "host-reconciliation-v1-2.json").is_file()
    assert GENERATION_WSL_HOST_EXECUTOR_IDENTITY == hashlib.sha256(
        "\n".join(GENERATION_WSL_HOST_EXECUTOR_IDENTITY_FIELDS).encode()
    ).hexdigest()
