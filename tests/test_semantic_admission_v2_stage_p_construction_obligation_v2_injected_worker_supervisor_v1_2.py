from __future__ import annotations

from pathlib import Path

from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_injected_generation_supervisor_v1_2 as supervisor
from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_injected_generation_worker_v1_2 as worker

ROOT = Path(__file__).resolve().parents[1] / "src/pastila_scout/semantic_admission_v2"


def test_worker_v1_2_is_exact_authority_only_successor():
    old = (ROOT / "stage_p_construction_obligation_v2_injected_generation_worker_v1_1.py").read_text("utf-8")
    expected = old.replace("Launch-forbidden V1.1 injected worker", "Launch-forbidden V1.2 injected worker")
    expected = expected.replace("stage_p_construction_obligation_v2_generation_authority_preload_v1_1", "stage_p_construction_obligation_v2_generation_authority_preload_v1_2")
    expected = expected.replace("parse_generation_authority_v1_1", "parse_generation_authority_v1_2")
    expected = expected.replace("validate_generation_preload_v1_1", "validate_generation_preload_v1_2")
    expected = expected.replace("execute_injected_generation_worker_v1_1", "execute_injected_generation_worker_v1_2")
    expected = expected.replace("8f2b6e445375d2295583ee3eeec6c643dec57bb5f711bdcf2b12abf310e03489", worker.WORKER_IDENTITY)
    observed = (ROOT / "stage_p_construction_obligation_v2_injected_generation_worker_v1_2.py").read_text("utf-8")
    assert observed.rstrip() == expected.rstrip()


def test_supervisor_v1_2_is_exact_worker_only_successor():
    old = (ROOT / "stage_p_construction_obligation_v2_injected_generation_supervisor_v1_1.py").read_text("utf-8")
    expected = old.replace("stage_p_construction_obligation_v2_injected_generation_worker_v1_1", "stage_p_construction_obligation_v2_injected_generation_worker_v1_2")
    expected = expected.replace("execute_injected_generation_worker_v1_1", "execute_injected_generation_worker_v1_2")
    expected = expected.replace("supervise_injected_generation_v1_1", "supervise_injected_generation_v1_2")
    expected = expected.replace("7291139155c0e30c39733f28cb042541cb1e9c95f092f897828da71c2e9c34e3", supervisor.SUPERVISOR_IDENTITY)
    observed = (ROOT / "stage_p_construction_obligation_v2_injected_generation_supervisor_v1_2.py").read_text("utf-8")
    assert observed.rstrip() == expected.rstrip()


def test_new_exact_types_are_still_required():
    assert worker.execute_injected_generation_worker_v1_2.__name__.endswith("v1_2")
    assert supervisor.supervise_injected_generation_v1_2.__name__.endswith("v1_2")
