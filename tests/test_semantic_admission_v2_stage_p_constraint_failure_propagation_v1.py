from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

import pytest

from pastila_scout.provider_execution_v2 import ExecutionOutcomeV2, ProviderExecutionResultV2
from pastila_scout.semantic_admission_v2.stage_p_constraint_failure_propagation_v1 import (
    recover_constraint_liveness_v1, validate_constraint_liveness_root_v1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_role_durable_executor_v1 import (
    DurableConstructionRoleStagePExecutorV1,
)
from pastila_scout.semantic_admission_v2.stage_p_construction_role_evaluator_v1_1 import (
    StagePConstructionRoleEvaluatorV1_1,
)
from pastila_scout.semantic_admission_v2.stage_p_scope_graph_durable_executor_v1_2 import (
    StagePConstraintLivenessExecutionErrorV1,
)


ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / ".semantic-admission-v2-stage-p-construction-role-case01-run-v1-evidence/durable-lifecycle"
FROZEN = next(RUN.iterdir())


def _failure(request_id: str, outcome: ExecutionOutcomeV2 = ExecutionOutcomeV2.INTERNAL_EXECUTION_FAILURE):
    return ProviderExecutionResultV2(request_id=request_id, provider_id="ollama",
        request_envelope_identity="fixture-envelope", outcome=outcome, finished_at=datetime.now(UTC),
        failure_code="fixture-failure", failure_message="Captured-fixture failure.")


def _install_receipts(root: Path, request_id: str, *, mutate_host: bool = False):
    target = root / hashlib.sha256(request_id.encode()).hexdigest(); target.mkdir(parents=True)
    runner = next(FROZEN.glob("runner-*-runner-exception.json"))
    host = next(FROZEN.glob("host-*-host-constraint-liveness-failure-classified.json"))
    (target / runner.name).write_bytes(runner.read_bytes())
    host_value = json.loads(host.read_bytes())
    if mutate_host: host_value["entry_count"] = 7
    (target / host.name).write_text(json.dumps(host_value, separators=(",", ":")), "utf-8")
    return target


def test_frozen_case01_runner_and_host_receipts_validate_exactly():
    receipt = validate_constraint_liveness_root_v1(FROZEN)
    assert receipt is not None
    assert receipt.code == "CONSTRAINT_LIVENESS_FAILURE"
    assert receipt.decoded_utf8_bytes == 2911 and receipt.entry_count == 2
    assert receipt.dfa_next_step == "COVERAGE"


def test_internal_failure_recovers_typed_receipt_but_transport_and_completed_do_not(tmp_path):
    request_id = "captured-case01-fixture"; _install_receipts(tmp_path, request_id)
    receipt = recover_constraint_liveness_v1(result=_failure(request_id), durable_lifecycle_root=tmp_path)
    assert receipt is not None and receipt.decoded_sha256 == "1a11286cad937c5faf19021f1cada98077867cb63aeae7e2923a489219be1a4a"
    assert recover_constraint_liveness_v1(
        result=_failure("transport-only"), durable_lifecycle_root=tmp_path) is None
    assert recover_constraint_liveness_v1(
        result=_failure(request_id, ExecutionOutcomeV2.TIMEOUT), durable_lifecycle_root=tmp_path) is None


def test_malformed_or_mismatched_liveness_fixture_fails_closed(tmp_path):
    request_id = "mismatched-fixture"; _install_receipts(tmp_path, request_id, mutate_host=True)
    with pytest.raises(ValueError, match="LIVENESS_RUNNER_HOST_MISMATCH"):
        recover_constraint_liveness_v1(result=_failure(request_id), durable_lifecycle_root=tmp_path)


def test_evaluator_propagates_typed_failure_without_second_execute(monkeypatch, tmp_path):
    request_id = "typed-evaluator-fixture"; _install_receipts(tmp_path, request_id)
    executor = DurableConstructionRoleStagePExecutorV1(
        project_root=ROOT, durable_lifecycle_root=tmp_path)
    calls = []
    def captured(_authority): calls.append(1); return _failure(request_id)
    monkeypatch.setattr(executor, "execute", captured)
    evaluator = StagePConstructionRoleEvaluatorV1_1(project_root=ROOT, executor=executor)
    with pytest.raises(StagePConstraintLivenessExecutionErrorV1) as raised:
        evaluator({"candidate": "Raport literal.", "factual_summary": "Raport literal."})
    assert raised.value.receipt.entry_count == 2 and calls == [1]
