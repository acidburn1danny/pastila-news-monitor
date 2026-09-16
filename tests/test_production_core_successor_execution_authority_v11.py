import hashlib
import importlib.util
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module(path, name):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    assert spec.loader
    spec.loader.exec_module(value)
    return value


def test_v11_entry_binds_v11_executor_validator_and_capacity_gate():
    value = module(ROOT / "scripts/launch_production_core_candidate_qualification_v11.py", "launch_v11")
    assert value.EXECUTOR.name == "execute_production_core_candidate_qualification_v11.py"
    assert value.CORE.name == "production_core_candidate_execution_authority_v11.py"
    assert value.CAPACITY.name == "preflight_production_core_wsl_host_capacity_v11.py"
    assert value.CAPACITY_SHA == hashlib.sha256(value.CAPACITY.read_bytes()).hexdigest()


def test_v11_executor_and_validator_bind_no_copy_runner():
    executor = (ROOT / "scripts/execute_production_core_candidate_qualification_v11.py").read_text("utf-8")
    validator = (ROOT / "src/pastila_scout/production_core_candidate_execution_authority_v11.py").read_text("utf-8")
    assert "run_production_core_candidate_qualification_v11.sh" in executor
    assert "run_production_core_candidate_qualification_v11.sh" in validator
    assert "run_production_core_candidate_qualification_v3.sh':'run_production_core_candidate_qualification_v11.sh" in executor


def test_authority_builder_is_zero_attempt_and_requires_committed_closure():
    value = module(ROOT / "scripts/materialize_production_core_successor_execution_authority_v11.py", "authority_v11")
    assert "scripts/run_production_core_candidate_qualification_v11.sh" in value.SOURCES
    assert "scripts/preflight_production_core_wsl_host_capacity_v11.py" in value.SOURCES
    with pytest.raises(ValueError, match="source absent from bound commit"):
        value.build("c7024267e4e4a5e55fa7ddfde42691fa592aadd8")


def test_v11_authority_keeps_candidates_and_matrix_unchanged():
    value = module(ROOT / "scripts/materialize_production_core_successor_execution_authority_v11.py", "authority_v11_ids")
    assert value.IDS["candidate_object_manifest_identity"] == "6c3bf1d21e85a454069ccd4e80f542fa5005ea6b89b41bb0d90b4acad2533314"
    assert value.IDS["qualification_generation_identity"] == "a2bfb6b3ed0f9d77bcc54ed7be0c11380b62b6df0863e2ef41302333f65688d7"
