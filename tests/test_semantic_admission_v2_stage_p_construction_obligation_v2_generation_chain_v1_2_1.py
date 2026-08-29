from __future__ import annotations

import ast
import hashlib
import json
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_generation_v1_2_1_identity_contract as identities
from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_generation_authority_preload_v1_2_1 as authority
from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_generation_wsl_host_executor_v1_2_1 as host
from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_generation_wsl_invocation_binding_v1_2_1 as binding
from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_injected_generation_supervisor_v1_2_1 as injected
from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_injected_generation_worker_v1_2_1 as worker
from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_linux_child_process_adapter_v1_2_1 as child
from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_linux_generation_composition_v1_2_1 as composition
from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_linux_generation_runner_v1_2_1 as runner
from pastila_scout.semantic_admission_v2 import stage_p_construction_obligation_v2_linux_generation_supervisor_candidate_v1_2_1 as supervisor

ROOT = Path(__file__).resolve().parents[1]


def _canonical(value):
    return (json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":")) + "\n").encode()


def test_exact_identity_propagation_and_single_prospective_edge():
    assert authority.AUTHORITY_PRELOAD_IDENTITY == identities.AUTHORITY_PRELOAD_IDENTITY
    assert worker.WORKER_IDENTITY == identities.WORKER_IDENTITY
    assert injected.SUPERVISOR_IDENTITY == identities.INJECTED_SUPERVISOR_IDENTITY
    assert supervisor.SUPERVISOR_CANDIDATE_IDENTITY == identities.SUPERVISOR_IDENTITY
    assert child.LINUX_CHILD_PROCESS_ADAPTER_IDENTITY == identities.CHILD_ADAPTER_IDENTITY
    assert composition.LINUX_GENERATION_COMPOSITION_IDENTITY == identities.COMPOSITION_IDENTITY
    assert runner.LINUX_GENERATION_RUNNER_IDENTITY == identities.RUNNER_IDENTITY
    assert host.GENERATION_WSL_HOST_EXECUTOR_IDENTITY == identities.HOST_EXECUTOR_IDENTITY
    assert binding.GENERATION_WSL_INVOCATION_BINDING_IDENTITY == identities.WSL_BINDING_IDENTITY
    tree = ast.parse((ROOT / "src/pastila_scout/semantic_admission_v2/stage_p_construction_obligation_v2_generation_wsl_host_executor_v1_2_1.py").read_text("utf-8"))
    calls = [n for n in ast.walk(tree) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute) and n.func.attr == "execute"]
    assert len(calls) == 1


def test_v1_2_receipt_is_rejected_without_structural_compatibility():
    old = ROOT / "docs/artifacts/semantic-admission-v2-stage-p-construction-obligation-v2-case01-successor-issuance-packet-v1-2/authority-receipt-issued.json"
    old_value = json.loads(old.read_bytes())
    with pytest.raises(ValueError):
        authority.parse_generation_authority_v1_2_1(
            raw_receipt=old.read_bytes(),
            expected_host_payload_sha256=old_value["host_payload_sha256"],
            expected_runner_request_sha256=old_value["runner_request_sha256"],
            expected_provider_request_id=old_value["provider_request_id"],
            expected_source_context_identity=old_value["source_context_identity"],
        )


def test_runner_source_binding_is_exact_and_imports_are_inert():
    path = ROOT / binding.RUNNER_RELATIVE
    assert hashlib.sha256(path.read_bytes()).hexdigest() == binding.RUNNER_SOURCE_SHA256
    for module in (worker, injected, supervisor, child, composition, runner, host, binding):
        assert module.__name__.endswith("v1_2_1")
