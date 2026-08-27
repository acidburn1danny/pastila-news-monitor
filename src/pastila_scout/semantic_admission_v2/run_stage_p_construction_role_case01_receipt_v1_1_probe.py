"""Prepared exclusive Case 01 probe bound to receipt-preserving Evaluator V1.1."""
from __future__ import annotations

import hashlib
import json
import os
import sys
from pathlib import Path

from .stage_p_construction_role_contract_v1 import (
    ConstructionRoleLedgerV1, validate_construction_role_sources,
)
from .stage_p_construction_role_durable_executor_v1 import DurableConstructionRoleStagePExecutorV1
from .stage_p_construction_role_evaluator_v1_1 import StagePConstructionRoleEvaluatorV1_1
from .stage_p_phase_receipt_v2 import (
    EvidencePhaseStatusV2, StagePPhaseReceiptV2, classify_persisted_stage_p_v2,
    persist_phase_receipt_v2,
)
from .stage_p_scope_graph_durable_executor_v1_2 import StagePConstraintLivenessExecutionErrorV1


PACK_RELATIVE = Path("docs/artifacts/semantic-admission-v2-staged-gate-f-two-case-proof-pack-v1.json")
PACK_SHA256 = "4163307ccb8cfa8997b520a1cea04cddacd347e9b1ffde498db925ffccac6c2d"
CASE_ID = "HMCV1-SASC-01"
RECEIPT_PROPAGATION_CANDIDATE_IDENTITY = "aae3212858b87ae7e3876c497fb9b554d5c606426fa692d6df9f26982c9d7b08"
EVALUATOR_IDENTITY = "7924fa7331b0284c68f1bf35a28651ad9a7de9f8f996d2fb1774873b92c1af5a"


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
    executor = DurableConstructionRoleStagePExecutorV1(
        project_root=project_root, durable_lifecycle_root=evidence_root / "durable-lifecycle")
    evaluator = StagePConstructionRoleEvaluatorV1_1(
        project_root=project_root, executor=executor, timeout_seconds=240.0)
    if evaluator.evaluator_identity != EVALUATOR_IDENTITY:
        raise RuntimeError("Evaluator V1.1 identity drift")
    binding = {"case_id": CASE_ID, "pack_sha256": PACK_SHA256,
        "factual_summary_sha256": case["factual_summary_sha256"],
        "candidate_sha256": case["candidate_sha256"],
        "receipt_propagation_candidate_identity": RECEIPT_PROPAGATION_CANDIDATE_IDENTITY,
        "evaluator_identity": EVALUATOR_IDENTITY,
        "request_candidate_identity": evaluator.candidate_identity,
        "prompt_identity": evaluator.prompt_identity, "schema_identity": evaluator.schema_identity,
        "constraint_identity": evaluator.constraint_identity, "grammar_identity": evaluator.grammar_identity,
        "tokenizer_identity": evaluator.tokenizer_identity, "model_identity": evaluator.model_identity,
        "maximum_provider_calls": 1, "retry_count": 0, "repair_count": 0, "selection_count": 0,
        "typed_liveness_reason": "STAGE_P_CONSTRAINT_LIVENESS_FAILURE",
        "generic_failure_reason": "STAGE_P_PROVIDER_OR_TRANSPORT_FAILURE",
        "stage_c_constructed": False, "stage_c_called": False}
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
        return classify_persisted_stage_p_v2(raw_path=None, provider_called=True,
            transport_succeeded=False,
            schema_validator=lambda data: ConstructionRoleLedgerV1.model_validate_json(data, strict=True),
            membership_validator=lambda ledger: validate_construction_role_sources(
                ledger, factual_summary=request["factual_summary"], candidate=request["candidate"]))
    data = output.encode("utf-8")
    try:
        with raw_path.open("xb") as handle:
            handle.write(data); handle.flush(); os.fsync(handle.fileno())
    except Exception:
        return classify_persisted_stage_p_v2(raw_path=None, provider_called=True,
            transport_succeeded=True,
            schema_validator=lambda item: ConstructionRoleLedgerV1.model_validate_json(item, strict=True),
            membership_validator=lambda ledger: validate_construction_role_sources(
                ledger, factual_summary=request["factual_summary"], candidate=request["candidate"]))
    return classify_persisted_stage_p_v2(raw_path=raw_path, provider_called=True,
        transport_succeeded=True,
        schema_validator=lambda item: ConstructionRoleLedgerV1.model_validate_json(item, strict=True),
        membership_validator=lambda ledger: validate_construction_role_sources(
            ledger, factual_summary=request["factual_summary"], candidate=request["candidate"]))


def run(*, project_root: Path, evidence_root: Path):
    request, binding, evaluator = construct(project_root=project_root, evidence_root=evidence_root)
    _write_exclusive(evidence_root / "stage-p-request.json", request)
    _write_exclusive(evidence_root / "identity-binding.json", binding)
    receipt = _execute_once(evaluator=evaluator, request=request,
                            raw_path=evidence_root / "stage-p-raw.bin",
                            failure_path=evidence_root / "constraint-liveness-failure.json")
    persist_phase_receipt_v2(evidence_root / "stage-p-phase-receipt-v2.json", receipt)
    return receipt


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit("usage: probe PROJECT_ROOT EVIDENCE_ROOT")
    value = run(project_root=Path(sys.argv[1]), evidence_root=Path(sys.argv[2]))
    print(json.dumps(value.as_json_value(), ensure_ascii=False))
