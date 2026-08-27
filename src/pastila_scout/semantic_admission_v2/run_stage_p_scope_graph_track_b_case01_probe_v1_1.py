"""Prepared exclusive V1.3 Track-B Case 01 probe; construction does not execute it."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

from .stage_p_phase_receipt_v2 import (
    EvidencePhaseStatusV2,
    StagePPhaseReceiptV2,
    classify_persisted_stage_p_v2,
    persist_phase_receipt_v2,
)
from .stage_p_scope_graph_contract_v1_1 import ScopeGraphLedgerV1_1, validate_scope_graph_sources
from .stage_p_scope_graph_durable_executor_v1_2 import StagePConstraintLivenessExecutionErrorV1
from .stage_p_scope_graph_durable_executor_v1_3 import DurableScopeGraphStagePExecutorV1_3
from .stage_p_scope_graph_track_b_evaluator_v1_1 import StagePScopeGraphTrackBEvaluatorV1_1


PACK_RELATIVE = Path("docs/artifacts/semantic-admission-v2-staged-gate-f-two-case-proof-pack-v1.json")
PACK_SHA256 = "4163307ccb8cfa8997b520a1cea04cddacd347e9b1ffde498db925ffccac6c2d"
CASE_ID = "HMCV1-SASC-01"
EVALUATOR_BINDING_IDENTITY = "3478e78e710c9bfb389fc6f4b34ac7b236ec749dc5a5d6b5d119e32aebe2c49e"
EVALUATOR_IDENTITY = "2a8e25f9c54ccb60c5c2edbb775722cb509e94fbc85966d381215239f397706e"


def _write_exclusive(path: Path, value: object) -> None:
    data = (json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                       allow_nan=False) + "\n").encode()
    with path.open("xb") as handle:
        handle.write(data); handle.flush(); os.fsync(handle.fileno())


def construct(*, project_root: Path, evidence_root: Path):
    if evidence_root.exists():
        raise FileExistsError(f"exclusive evidence root already exists: {evidence_root}")
    raw = (project_root / PACK_RELATIVE).read_bytes()
    if hashlib.sha256(raw).hexdigest() != PACK_SHA256:
        raise RuntimeError("proof pack identity drift")
    matches = [item for item in json.loads(raw)["cases"] if item["case_id"] == CASE_ID]
    if len(matches) != 1:
        raise RuntimeError("Case 01 selection drift")
    case = matches[0]
    request = {"stage_id": "PROPOSITION_LEDGER", "factual_summary": case["factual_summary"],
               "candidate": case["candidate"]}
    executor = DurableScopeGraphStagePExecutorV1_3(
        project_root=project_root, durable_lifecycle_root=evidence_root / "durable-lifecycle")
    evaluator = StagePScopeGraphTrackBEvaluatorV1_1(
        project_root=project_root, executor=executor, timeout_seconds=240.0)
    if evaluator.evaluator_identity != EVALUATOR_IDENTITY:
        raise RuntimeError("Track-B evaluator identity drift")
    binding = {
        "case_id": CASE_ID, "pack_sha256": PACK_SHA256,
        "factual_summary_sha256": case["factual_summary_sha256"],
        "candidate_sha256": case["candidate_sha256"],
        "evaluator_binding_identity": EVALUATOR_BINDING_IDENTITY,
        "evaluator_identity": EVALUATOR_IDENTITY,
        "request_candidate_identity": evaluator.candidate_identity,
        "prompt_identity": evaluator.prompt_identity, "schema_identity": evaluator.schema_identity,
        "constraint_identity": evaluator.constraint_identity, "grammar_identity": evaluator.grammar_identity,
        "tokenizer_identity": evaluator.tokenizer_identity, "model_identity": evaluator.model_identity,
        "maximum_provider_calls": 1, "retry_count": 0, "repair_count": 0, "selection_count": 0,
        "constraint_liveness_reason": "STAGE_P_CONSTRAINT_LIVENESS_FAILURE",
        "stage_c_constructed": False, "stage_c_called": False,
    }
    return request, binding, evaluator


def _execute_once(*, evaluator, request: dict[str, object], raw_path: Path, failure_path: Path):
    try:
        output = evaluator(request)
        if type(output) is not str:
            raise TypeError("STAGE_P_OUTPUT_NOT_STRING")
    except StagePConstraintLivenessExecutionErrorV1 as exc:
        _write_exclusive(failure_path, exc.receipt.as_json_value())
        return StagePPhaseReceiptV2(
            "pastila-semantic-admission-v2-stage-p-phase-receipt", "2.0.0-evaluation.1", 1,
            EvidencePhaseStatusV2.FAIL, EvidencePhaseStatusV2.NOT_RUN, None, None, 0,
            EvidencePhaseStatusV2.NOT_RUN, EvidencePhaseStatusV2.NOT_RUN,
            "STAGE_P_CONSTRAINT_LIVENESS_FAILURE", "ABSTAIN_FAIL_CLOSED")
    except Exception:
        return classify_persisted_stage_p_v2(
            raw_path=None, provider_called=True, transport_succeeded=False,
            schema_validator=lambda data: ScopeGraphLedgerV1_1.model_validate_json(data, strict=True),
            membership_validator=lambda ledger: validate_scope_graph_sources(
                ledger, factual_summary=request["factual_summary"], candidate=request["candidate"]))
    data = output.encode("utf-8")
    try:
        with raw_path.open("xb") as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno())
    except Exception:
        return classify_persisted_stage_p_v2(
            raw_path=None, provider_called=True, transport_succeeded=True,
            schema_validator=lambda item: ScopeGraphLedgerV1_1.model_validate_json(item, strict=True),
            membership_validator=lambda ledger: validate_scope_graph_sources(
                ledger, factual_summary=request["factual_summary"], candidate=request["candidate"]))
    return classify_persisted_stage_p_v2(
        raw_path=raw_path, provider_called=True, transport_succeeded=True,
        schema_validator=lambda item: ScopeGraphLedgerV1_1.model_validate_json(item, strict=True),
        membership_validator=lambda ledger: validate_scope_graph_sources(
            ledger, factual_summary=request["factual_summary"], candidate=request["candidate"]))


def run(*, project_root: Path, evidence_root: Path):
    request, binding, evaluator = construct(project_root=project_root, evidence_root=evidence_root)
    _write_exclusive(evidence_root / "stage-p-request.json", request)
    _write_exclusive(evidence_root / "identity-binding.json", binding)
    receipt = _execute_once(
        evaluator=evaluator, request=request, raw_path=evidence_root / "stage-p-raw.bin",
        failure_path=evidence_root / "constraint-liveness-failure.json")
    persist_phase_receipt_v2(evidence_root / "stage-p-phase-receipt-v2.json", receipt)
    return receipt


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: probe PROJECT_ROOT EVIDENCE_ROOT")
    value = run(project_root=Path(sys.argv[1]), evidence_root=Path(sys.argv[2]))
    print(json.dumps(value.as_json_value(), ensure_ascii=False))
