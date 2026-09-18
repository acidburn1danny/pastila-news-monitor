from __future__ import annotations

import json
from pathlib import Path

import pytest

from pastila_scout import production_core_isolated_gpu_boundary_v15 as boundary


def receipt(mode: str, *, cuda: bool, cu_init: int) -> dict:
    return {
        "schema": "pastila-production-core-v15-isolated-gpu-probe",
        "wsl_lib_source": mode,
        "rootfs_sha256": boundary.ROOTFS,
        "versions": {"bitsandbytes": "0.50.1", "peft": "0.20.0", "torch": "2.13.0+cu130", "transformers": "5.15.0"},
        "cuda_available": cuda,
        "device_dxg": True,
        "libcuda_load": "PASS",
        "cu_init_result": cu_init,
        "cu_device_count": 1 if cuda else None,
        "torch_cuda_init_error": None if cuda else "RuntimeError: no NVIDIA driver",
        "network_isolated": True,
        "pid_isolated": True,
    }


def test_terminal_closure_rejects_substituted_attempt(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "attempt.json").write_text(json.dumps({"attempt_identity": "0" * 64}), encoding="utf-8")
    (tmp_path / "terminal-failure.json").write_text(json.dumps({"terminal_failure_identity": boundary.FAILURE}), encoding="utf-8")
    monkeypatch.setattr(boundary.validator, "validate_attempt", lambda *_: None)
    monkeypatch.setattr(boundary.validator, "validate_terminal_failure", lambda *_: None)
    with pytest.raises(ValueError, match="terminal state mismatch"):
        boundary.terminal_closure(tmp_path)


def test_audit_binds_terminal_failure_and_fails_closed_on_gpu_witness(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(boundary, "source_closure", lambda: {"runner": "a" * 64})
    monkeypatch.setattr(boundary, "terminal_closure", lambda _: {"attempt_identity": boundary.ATTEMPT, "terminal_failure_identity": boundary.FAILURE})
    monkeypatch.setattr(boundary, "driver_manifest", lambda: {"file_count": 1, "manifest_identity": "b" * 64})
    monkeypatch.setattr(boundary, "probe", lambda _, mode="canonical": receipt(mode, cuda=mode != "canonical", cu_init=100 if mode == "canonical" else 0))
    report = boundary.audit(Path("terminal"), Path("rootfs"))
    assert report["verdict"] == "DESIGN_AUDIT_PASS; EXECUTION_READINESS_BLOCKED"
    assert report["execution_authorized"] is False
    assert report["v15_candidate_execution"] == 0
    assert report["new_attempt_consumption"] == 0
    assert report["bound_v14_terminal"]["terminal_failure_identity"] == boundary.FAILURE
    monkeypatch.setattr(boundary, "probe", lambda _, mode="canonical": receipt(mode, cuda=False, cu_init=100))
    with pytest.raises(ValueError, match="driver witness changed"):
        boundary.audit(Path("terminal"), Path("rootfs"))


def test_probe_rejects_mode_outside_diagnostic_contract() -> None:
    with pytest.raises(ValueError, match="unapproved GPU probe mode"):
        boundary.probe(Path("unused"), "candidate-execution")


def test_audit_rejects_driver_drift_during_probe(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(boundary, "source_closure", lambda: {})
    monkeypatch.setattr(boundary, "terminal_closure", lambda _: {})
    monkeypatch.setattr(boundary, "probe", lambda _, mode="canonical": receipt(mode, cuda=mode != "canonical", cu_init=100 if mode == "canonical" else 0))
    manifests = iter(({"file_count": 1, "manifest_identity": "a" * 64}, {"file_count": 1, "manifest_identity": "b" * 64}))
    monkeypatch.setattr(boundary, "driver_manifest", lambda: next(manifests))
    with pytest.raises(ValueError, match="changed during audit"):
        boundary.audit(Path("terminal"), Path("rootfs"))
