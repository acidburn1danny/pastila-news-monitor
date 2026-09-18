"""Fail-closed state and plan checks for the synthetic V14 supervisor."""
from __future__ import annotations

import fcntl
import json

import pytest

from pastila_scout import production_core_overnight_supervisor_v14 as supervisor
from pastila_scout import production_core_qualification_supervisor_v14 as production


def plan():
    return {
        "schema": "pastila-production-core-v14-supervisor-smoke-plan",
        "authority_identity": supervisor.AUTHORITY,
        "candidate_execution": False,
        "attempt_consumption": False,
        "tasks": [{"ordinal": 1, "rows": 200, "delay_ms": 100}],
    }


@pytest.mark.parametrize("change", [
    {"candidate_execution": True},
    {"attempt_consumption": True},
    {"authority_identity": "0" * 64},
    {"tasks": [{"ordinal": 2, "rows": 200, "delay_ms": 100}]},
    {"tasks": [{"ordinal": 1, "rows": 199, "delay_ms": 100}]},
])
def test_unauthorized_plan_rejected(change):
    with pytest.raises(ValueError):
        supervisor.verify_smoke_plan({**plan(), **change})


def test_parallel_supervisor_rejected(tmp_path):
    tmp_path.chmod(0o700)
    with (tmp_path / "supervisor.lock").open("a+b") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(ValueError, match="parallel supervisor"):
            supervisor.supervise(tmp_path, plan())


def test_state_substitution_rejected(tmp_path):
    path = tmp_path / "supervisor-state.json"
    path.write_text(json.dumps({
        "schema": supervisor.SCHEMA,
        "authority_identity": supervisor.AUTHORITY,
        "run_identity": supervisor.verify_smoke_plan(plan()),
        "qualification_evidence": False,
        "accepted_checkpoints": 1,
        "completed_rows": 0,
    }))
    with pytest.raises(ValueError, match="state substitution"):
        supervisor.read_state(path, supervisor.verify_smoke_plan(plan()))


def test_false_completion_rejected(tmp_path):
    tmp_path.chmod(0o700)
    run_identity = supervisor.verify_smoke_plan(plan())
    supervisor.write_state(tmp_path / "supervisor-state.json", {
        "schema": supervisor.SCHEMA,
        "authority_identity": supervisor.AUTHORITY,
        "run_identity": run_identity,
        "qualification_evidence": False,
        "phase": "COMPLETE",
        "active_unit": None,
        "accepted_checkpoints": 0,
        "completed_rows": 0,
        "sequence": 1,
    })
    with pytest.raises(ValueError, match="false completion"):
        supervisor.supervise(tmp_path, plan())


def test_forged_marker_rejected(tmp_path):
    marker = tmp_path / "smoke-checkpoint-01.json"
    marker.write_text(json.dumps({
        "schema": "pastila-production-core-v14-synthetic-smoke-marker",
        "run_identity": supervisor.verify_smoke_plan(plan()),
        "ordinal": 1,
        "rows": 200,
        "qualification_evidence": True,
    }))
    assert not supervisor.marker_valid(marker, supervisor.verify_smoke_plan(plan()), 1)


def test_uncertain_start_never_relaunches(tmp_path):
    tmp_path.chmod(0o700)
    run_identity = supervisor.verify_smoke_plan(plan())
    supervisor.write_state(tmp_path / "supervisor-state.json", {
        "schema": supervisor.SCHEMA,
        "authority_identity": supervisor.AUTHORITY,
        "run_identity": run_identity,
        "qualification_evidence": False,
        "phase": "STARTING",
        "active_unit": supervisor.unit_name(run_identity, 1),
        "accepted_checkpoints": 0,
        "completed_rows": 0,
        "sequence": 1,
    })
    result = supervisor.supervise(tmp_path, plan())
    assert result["phase"] == "TERMINAL_FAILURE"
    assert not (tmp_path / "smoke-checkpoint-01.json").exists()


def test_production_path_requires_separate_owner_authorization(tmp_path):
    with pytest.raises(ValueError, match="owner authorization"):
        production.run(*(tmp_path for _ in range(7)), owner_authorized=False)


def test_production_command_uses_only_v14_launcher_and_new_output(tmp_path):
    command = production.command(*(tmp_path for _ in range(6)))
    assert command[1].endswith("launch_production_core_candidate_qualification_v14.py")
    assert command[-1] == "--consume-attempt"
    assert "--terminal-root" in command
    assert "--output" in command
    assert "v13.py" not in command[1]


def test_production_connector_verifies_current_signed_launcher():
    boundary = json.loads((production.ART / "production-core-v14-preconsumption-launcher-boundary/boundary.json").read_bytes())
    assert production.signed_launcher_identity() == boundary["boundary_identity"]


def test_supervisor_terminal_observation_is_not_qualification_evidence(tmp_path):
    production.terminal_observation(tmp_path, "0" * 64, "SUPERVISOR_VALIDATION_ERROR")
    observed = json.loads((tmp_path / "supervisor-terminal-observation.json").read_bytes())
    assert observed["qualification_evidence"] is False
    assert observed["attempt_identity"] is None
    assert observed["adjudication"] is False
    assert observed["promotion"] is False


def test_final_heartbeat_cannot_look_active(tmp_path):
    production.final_heartbeat(tmp_path, "0" * 64, "1" * 64, {
        "phase": "TERMINAL_FAILURE", "accepted_checkpoints": 0, "completed_rows": 0,
    })
    heartbeat = json.loads((tmp_path / "supervisor-heartbeat.json").read_bytes())
    assert heartbeat["phase"] == "TERMINAL_FAILURE"
    assert heartbeat["active_state"] == "inactive"
    assert heartbeat["qualification_evidence"] is False
