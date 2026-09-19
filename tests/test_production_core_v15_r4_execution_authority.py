"""Fixture-only R4 namespace and fail-closed boundary tests."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
sys.path.insert(0, str(ROOT / "src"))

import audit_production_core_v15_r4_execution_authority as signed  # noqa: E402
import execute_production_core_candidate_qualification_v15_r4 as route  # noqa: E402
import materialize_production_core_v15_r4_execution_authority as issuer  # noqa: E402
import preflight_production_core_candidate_qualification_v15_r4 as gate  # noqa: E402
import project_production_core_candidate_qualification_v15_r4 as projection  # noqa: E402
import supervise_production_core_candidate_qualification_v15_r4 as supervisor  # noqa: E402
import smoke_production_core_v15_attempt_execution_boundary as fixture_smoke  # noqa: E402


def fixture_boundary() -> dict:
    r3 = json.loads((issuer.r3.OUTPUT / "authority.json").read_bytes())
    sources = dict(r3["source_sha256"])
    path = ROOT / projection.SOURCE
    sources[projection.SOURCE] = hashlib.sha256(path.read_bytes()).hexdigest()
    return {"boundary_identity": "a" * 64, "source_sha256": sources}


def test_r3_demonstrated_stale_namespace_and_r4_repair() -> None:
    boundary = fixture_boundary()
    stale = projection.r3.build_namespace(boundary)
    assert stale["NAMES"] != projection.expected_bindings()["NAMES"]
    assert stale["LAUNCHER"] != projection.expected_bindings()["LAUNCHER"]
    assert stale["RUNNER"] != projection.expected_bindings()["RUNNER"]
    assert stale["PROMPT_SHA256"] != projection.expected_bindings()["PROMPT_SHA256"]
    assert stale["lock_directory"] is not projection.expected_bindings()["lock_directory"]
    with pytest.raises(ValueError, match="namespace mismatch"):
        projection.verify_namespace(stale, boundary)
    repaired = projection.build_namespace(boundary)
    for key, value in projection.expected_bindings().items():
        assert repaired[key] is value if callable(value) else repaired[key] == value
    assert repaired["PINNED_EXECUTION_MECHANISM"]["execution_authority_identity"] == "a" * 64


@pytest.mark.parametrize("key", [
    "NAMES", "LAUNCHER", "RUNNER", "PROMPTS", "PROMPT_SHA256",
    "lock_directory", "atomic", "SNAPSHOT", "DRIVER_HELPER", "object_authority", "wsl",
    "validate_manifest_contract", "case_for_row", "close_post_claim_failure",
])
def test_each_execution_global_substitution_rejected(key: str) -> None:
    boundary = fixture_boundary()
    live = projection.build_namespace(boundary)
    live[key] = object()
    with pytest.raises(ValueError, match="namespace mismatch"):
        projection.verify_namespace(live, boundary)


def test_source_and_mechanism_substitution_rejected() -> None:
    boundary = fixture_boundary()
    live = projection.build_namespace(boundary)
    live["PINNED_EXECUTION_MECHANISM"] = {"execution_authority_identity": "b" * 64}
    with pytest.raises(ValueError, match="mechanism mismatch"):
        projection.verify_namespace(live, boundary)
    boundary["source_sha256"] = {**boundary["source_sha256"], projection.SOURCE: "0" * 64}
    with pytest.raises(ValueError, match="source drift"):
        projection.build_namespace(boundary)


def test_binding_claim_pins_frozen_values() -> None:
    sources = fixture_boundary()["source_sha256"]
    claim = projection.binding_claim(sources)
    assert claim["snapshot_set"][0].endswith("generation-v13.json")
    assert claim["launcher_path"].endswith("v15.sh")
    assert claim["runner_path"].endswith("runner_v14.py")
    assert claim["matrix_rows"] == 2400
    assert claim["lock_source_sha256"] == sources["scripts/execute_production_core_candidate_qualification_v15.py"]


def test_no_owner_consent_or_historical_output_rejected_before_gate(monkeypatch, tmp_path: Path) -> None:
    def forbidden(*_args, **_kwargs):
        raise AssertionError("preflight must not run")
    monkeypatch.setattr(gate, "issue", forbidden)
    paths = (tmp_path,) * 8
    with pytest.raises(ValueError, match="owner authorization"):
        route.run(*paths, tmp_path, owner_authorized=False)
    for output in (issuer.r3.R2_OUTPUT, issuer.r3.R3_OUTPUT):
        with pytest.raises(ValueError, match="output path"):
            route.run(*paths, output, owner_authorized=True)
    assert not (tmp_path / "attempt.json").exists()


def test_publication_gate_rejects_unpublished_r4(monkeypatch) -> None:
    monkeypatch.setattr(issuer, "git", lambda *args: issuer.R3_COMMIT if args[0] == "rev-parse" else "")
    with pytest.raises(ValueError, match="unpublished"):
        gate.current_publication({"source_sha256": {}})


def test_signature_tamper_rejected_before_runtime_audit(monkeypatch, tmp_path: Path) -> None:
    if not issuer.OUTPUT.is_dir():
        pytest.skip("R4 signed artifacts not yet materialized")
    for name in issuer.ARTIFACT_NAMES:
        (tmp_path / name).write_bytes((issuer.OUTPUT / name).read_bytes())
    altered = bytearray((tmp_path / "binding.sig").read_bytes())
    altered[0] ^= 1
    (tmp_path / "binding.sig").write_bytes(altered)
    monkeypatch.setattr(issuer, "OUTPUT", tmp_path)
    with pytest.raises(Exception):
        signed.audit(*((tmp_path,) * 9))


def test_r4_fixture_only_supervision_and_no_clobber(monkeypatch) -> None:
    if not issuer.R4_OUTPUT.is_dir():
        pytest.skip("requires native WSL R4 output")
    monkeypatch.setattr(fixture_smoke, "REAL_OUTPUT", issuer.R4_OUTPUT)
    result = fixture_smoke.smoke()
    assert result["parallel_owner"] == "REJECTED"
    assert result["fixture_no_clobber"] == "PASS"
    assert result["terminal_process_failure"] == "PROPAGATED"
    assert result["sigkill_after_claim"] == "NO_RECONSUMPTION_NO_ORPHAN"
    assert result["real_attempt_json"] == "ABSENT"
    assert list(issuer.R4_OUTPUT.iterdir()) == []


def test_persistent_supervisor_requires_owner_and_projects_exact_route(tmp_path: Path) -> None:
    paths = (tmp_path,) * 9
    with pytest.raises(ValueError, match="owner authorization"):
        supervisor.supervise(tmp_path, *paths, owner_authorized=False)
    command = supervisor.command(*paths)
    assert command[1].endswith("execute_production_core_candidate_qualification_v15_r4.py")
    assert command[-1] == "--consume-attempt"
    assert command.count("--output") == 1


def test_supervisor_state_is_durable_nonqualification_evidence(tmp_path: Path) -> None:
    run = "a" * 64
    core = {"schema": supervisor.SCHEMA, "run_identity": run,
            "authority_identity": "b" * 64, "qualification_evidence": False,
            "phase": "ACTIVE", "unit": "fixture.service", "accepted_checkpoints": 3,
            "completed_rows": 600, "sequence": 4, "adjudication": False,
            "promotion": False}
    path = tmp_path / "state.json"
    supervisor.atomic_state(path, core)
    assert supervisor.read_state(path, run) == core
    altered = json.loads(path.read_bytes()); altered["completed_rows"] = 800
    path.write_text(json.dumps(altered))
    with pytest.raises(ValueError, match="state rejected"):
        supervisor.read_state(path, run)


def test_supervisor_source_binds_no_restart_cgroup_and_terminal_closure() -> None:
    source = (ROOT / "scripts/supervise_production_core_candidate_qualification_v15_r4.py").read_text("utf-8")
    assert '"--property=Restart=no"' in source
    assert '"--property=KillMode=control-group"' in source
    assert "seal_uncaught(output, authority)" in source
    assert "UNHANDLED_SUPERVISED_PROCESS_EXIT" in source
    assert "systemctl\", \"kill\", \"--kill-who=all" in source
