"""Non-consuming R3 authority and route adversarial tests."""

from __future__ import annotations

import ast
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import audit_production_core_v15_r3_execution_authority as signed  # noqa: E402
import execute_production_core_candidate_qualification_v15_r3 as route  # noqa: E402
import materialize_production_core_v15_r3_execution_authority as issuer  # noqa: E402
import preflight_production_core_candidate_qualification_v15_r3 as gate  # noqa: E402
import project_production_core_candidate_qualification_v15_r3 as projection  # noqa: E402
import smoke_production_core_v15_attempt_execution_boundary as fixture_smoke  # noqa: E402


def test_r2_historical_signature_and_evidence_are_read_only() -> None:
    if not issuer.R2_OUTPUT.is_dir():
        pytest.skip("requires native WSL R2 evidence")
    evidence = issuer.historical_r2()
    assert evidence["attempt_identity"] == issuer.R2_ATTEMPT
    assert evidence["evidence_inventory_root"] == issuer.R2_INVENTORY_ROOT
    assert evidence["terminal_failure"] == "ABSENT_HISTORICAL"


def test_historical_audit_accepts_only_direct_successor_head(monkeypatch) -> None:
    original = issuer.git
    future = "f" * 40
    def direct(*args):
        if args == ("rev-parse", "HEAD"):
            return future
        if args == ("show", "-s", "--format=%P", future):
            return issuer.R2_COMMIT
        return original(*args)
    monkeypatch.setattr(issuer, "git", direct)
    if issuer.R2_OUTPUT.is_dir():
        assert issuer.historical_r2()["attempt_identity"] == issuer.R2_ATTEMPT
    def grandchild(*args):
        if args == ("show", "-s", "--format=%P", future):
            return "0" * 40
        return direct(*args)
    monkeypatch.setattr(issuer, "git", grandchild)
    with pytest.raises(ValueError, match="direct successor"):
        issuer.historical_r2()


def test_successor_projection_precedes_claim_and_closes_after_claim() -> None:
    source = projection.projected_mechanics()
    ast.parse(source)
    assert source.count("successor_cases = validate_manifest_contract(requests)") == 1
    assert source.count("case = case_for_row(successor_cases, row)") == 1
    assert source.count("close_post_claim_failure(") == 1
    assert source.index("successor_cases = validate_manifest_contract(requests)") < source.index(
        'atomic(output / "attempt.json", canonical(attempt))')
    assert source.index("    try:\n        attempt = recovered_attempt") < source.index(
        'atomic(output / "attempt.json", canonical(attempt))')
    assert source.index("close_post_claim_failure(") > source.index(
        'atomic(output / "attempt.json", canonical(attempt))')
    assert "case = next(" not in source


def test_r2_output_and_missing_owner_consent_rejected_before_gate(monkeypatch, tmp_path: Path) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("preflight must not run")
    monkeypatch.setattr(gate, "issue", forbidden)
    paths = (tmp_path,) * 8
    with pytest.raises(ValueError, match="owner authorization"):
        route.run(*paths, tmp_path, owner_authorized=False)
    with pytest.raises(ValueError, match="output path"):
        route.run(*paths, issuer.R2_OUTPUT, owner_authorized=True)
    assert not (tmp_path / "attempt.json").exists()


def test_r3_publication_gate_rejects_unpublished_head(monkeypatch) -> None:
    monkeypatch.setattr(issuer, "git", lambda *args: issuer.R2_COMMIT if args[0] == "rev-parse" else "")
    with pytest.raises(ValueError, match="unpublished"):
        gate.current_publication({"source_sha256": {}})


def test_r3_binding_rejects_substituted_identity() -> None:
    authority = {
        "authority_identity": "a" * 64,
        "historical_r2": {"attempt_identity": issuer.R2_ATTEMPT},
        "bound_executor_sha256": "b" * 64,
        "bound_preflight_sha256": "c" * 64,
        "contract_sha256": "d" * 64,
        "projection_sha256": "e" * 64,
        "r3_projected_mechanics_sha256": "f" * 64,
        "qualification_generation_identity": "1" * 64,
        "driver_snapshot": {}, "output": {},
    }
    original = issuer.binding_for(authority, b"fixture")
    altered = issuer.binding_for({**authority, "bound_executor_sha256": "0" * 64}, b"fixture")
    assert original != altered
    assert original["publication_parent_commit"] == issuer.R2_COMMIT


def test_signed_artifact_tampering_fails_before_runtime_audit(monkeypatch, tmp_path: Path) -> None:
    if not issuer.OUTPUT.is_dir():
        pytest.skip("signed R3 artifacts not yet materialized")
    for name in issuer.ARTIFACT_NAMES:
        (tmp_path / name).write_bytes((issuer.OUTPUT / name).read_bytes())
    data = bytearray((tmp_path / "binding.sig").read_bytes())
    data[0] ^= 1
    (tmp_path / "binding.sig").write_bytes(data)
    monkeypatch.setattr(issuer, "OUTPUT", tmp_path)
    with pytest.raises(Exception):
        signed.audit(*((tmp_path,) * 9))


def test_source_map_closure_contains_only_inherited_and_r3_sources() -> None:
    if not issuer.R2_OUTPUT.is_dir():
        pytest.skip("requires native WSL R2 evidence")
    r2 = json.loads((ROOT / "docs/artifacts/production-core-v15-execution-bound-preflight-r2/authority.json").read_bytes())
    sources = issuer.source_closure(r2)
    assert set(sources) == set(r2["source_sha256"]) | set(issuer.NEW_SOURCES)
    assert sources["scripts/execute_production_core_candidate_qualification_v15_r3.py"] != r2["bound_executor_sha256"]


def test_r3_fixture_concurrency_no_clobber_and_sigkill(monkeypatch) -> None:
    if not issuer.R3_OUTPUT.is_dir():
        pytest.skip("requires native WSL R3 output")
    monkeypatch.setattr(fixture_smoke, "REAL_OUTPUT", issuer.R3_OUTPUT)
    result = fixture_smoke.smoke()
    assert result["parallel_owner"] == "REJECTED"
    assert result["fixture_no_clobber"] == "PASS"
    assert result["terminal_process_failure"] == "PROPAGATED"
    assert result["sigkill_after_claim"] == "NO_RECONSUMPTION_NO_ORPHAN"
    assert result["real_attempt_json"] == "ABSENT"
    assert list(issuer.R3_OUTPUT.iterdir()) == []
