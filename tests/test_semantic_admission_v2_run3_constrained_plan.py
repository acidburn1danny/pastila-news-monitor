from __future__ import annotations

import json
from pathlib import Path

import pytest

from pastila_scout.semantic_admission_v2 import GateIdV2
from scripts.run_semantic_admission_v2_ten_case_conformance_run3_constrained_v1 import (
    DurableGateCaptureV1,
)

ROOT = Path(__file__).resolve().parents[1]


def test_run3_plan_is_frozen_but_not_execution_authority() -> None:
    plan = json.loads(
        (
            ROOT / "docs/artifacts/semantic-admission-v2-run3-constrained-plan.json"
        ).read_text(encoding="utf-8")
    )
    assert len(plan["case_ids"]) == 10 and plan["exact_provider_call_ceiling"] == 20
    assert plan["gate_order_per_case"] == ["FACTUAL_SEMANTIC", "STORY_SPECIFICITY"]
    assert plan["inference_authorized"] is plan["run3_execution_authorized"] is False
    assert plan["silent_retry"] is plan["repair"] is plan["selection"] is False


def test_durable_wrapper_persists_success_before_return(tmp_path: Path) -> None:
    path = tmp_path / "ledger.json"
    ledger = {"calls": []}
    wrapper = DurableGateCaptureV1(
        gate_id=GateIdV2.FACTUAL_SEMANTIC,
        evaluator=lambda request: '{"ok":true}',
        ledger_path=path,
        ledger=ledger,
    )
    wrapper.bind_case("CASE-1")
    assert wrapper({}) == '{"ok":true}'
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["calls"][0]["raw_response"] == '{"ok":true}'
    assert saved["calls"][0]["exception_type"] is None


def test_durable_wrapper_persists_exception_before_propagation(tmp_path: Path) -> None:
    def fail(request):
        raise RuntimeError("boom")

    path = tmp_path / "ledger.json"
    ledger = {"calls": []}
    wrapper = DurableGateCaptureV1(
        gate_id=GateIdV2.STORY_SPECIFICITY,
        evaluator=fail,
        ledger_path=path,
        ledger=ledger,
    )
    wrapper.bind_case("CASE-2")
    with pytest.raises(RuntimeError, match="boom"):
        wrapper({})
    saved = json.loads(path.read_text(encoding="utf-8"))
    assert saved["calls"][0]["raw_response"] is None
    assert saved["calls"][0]["exception_type"] == "RuntimeError"


def test_run3_completed_evidence_is_sealed_and_non_authorizing() -> None:
    out = ROOT / ".semantic-admission-v2-ten-case-conformance-run-v3-evidence"
    authority = json.loads((out / "run3-execution-authority.json").read_text("utf-8"))
    manifest = json.loads((out / "manifest.json").read_text("utf-8"))

    assert authority["inference_authorized"] is True
    assert authority["runtime_authority"] is False
    assert authority["training_authority"] is False
    assert (
        manifest["lifecycle"] == "FROZEN_COMPLETED_FAIL_CLOSED_INFRASTRUCTURE_FAILURE"
    )
    assert manifest["runtime_authority"] is False
    assert manifest["run3_retry_authorized"] is False
