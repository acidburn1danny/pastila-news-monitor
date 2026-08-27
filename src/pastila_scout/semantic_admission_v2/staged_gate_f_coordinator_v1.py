"""Evaluation-only two-stage Gate F coordinator with append-only raw capture."""
from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable
from enum import StrEnum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from .canonical_identity_v1 import canonical_identity
from .models import GateDecisionV2
from .source_span_validation_v1 import validate_reason_span_sources_v1
from .staged_gate_f_contract_v1 import PropositionLedgerV1, validate_source_membership

StageEvaluatorV1 = Callable[[dict[str, object]], str]


class StagedFinalDecisionV1(StrEnum):
    PASS_GATE_F = "PASS_GATE_F"
    REJECT_FACTUAL_SEMANTIC = "REJECT_FACTUAL_SEMANTIC"
    ABSTAIN = "ABSTAIN"


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class StageEvidenceReceiptV1(_Frozen):
    stage_id: str
    evaluator_identity: str
    prompt_identity: str
    grammar_identity: str
    model_identity: str
    called: bool
    request_sha256: str | None = Field(pattern=r"^[a-f0-9]{64}$")
    raw_path: str | None
    raw_sha256: str | None = Field(pattern=r"^[a-f0-9]{64}$")
    raw_bytes: int
    validation_result: str
    error_code: str | None
    elapsed_ms: float = Field(ge=0)


class StagedGateFReceiptV1(_Frozen):
    schema_name: str = "pastila-semantic-admission-v2-staged-gate-f-receipt"
    schema_version: str = "1.0.0-evaluation.1"
    case_id: str
    factual_summary_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    candidate_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    stage_p: StageEvidenceReceiptV1
    stage_c: StageEvidenceReceiptV1
    calls_consumed: int = Field(ge=0, le=2)
    unused_call_budget: int = Field(ge=0, le=2)
    final_decision: StagedFinalDecisionV1
    precedence_reason: str
    eligibility: str = "QUARANTINED_EVALUATION_ONLY"
    runtime_affected: bool = False
    receipt_identity: str = Field(pattern=r"^sha256:[a-f0-9]{64}$")


class StageIdentityBindingV1(_Frozen):
    evaluator_identity: str = Field(min_length=1)
    prompt_identity: str = Field(min_length=1)
    grammar_identity: str = Field(min_length=1)
    model_identity: str = Field(min_length=1)


class StagedGateFCoordinatorV1:
    """Call P once, then C at most once; never retry, repair, or select."""

    def __init__(self, *, stage_p: StageEvaluatorV1, stage_c: StageEvaluatorV1,
                 evidence_root: Path, stage_p_binding: StageIdentityBindingV1,
                 stage_c_binding: StageIdentityBindingV1) -> None:
        self._stage_p, self._stage_c = stage_p, stage_c
        self._root = evidence_root.resolve()
        self._p_binding, self._c_binding = stage_p_binding, stage_c_binding

    def evaluate(self, *, case_id: str, factual_summary: str, candidate: str) -> StagedGateFReceiptV1:
        case_root = self._root / case_id
        case_root.mkdir(parents=True, exist_ok=False)
        p_request = {"stage_id":"PROPOSITION_LEDGER","factual_summary":factual_summary,"candidate":candidate}
        p_receipt, p_raw = self._invoke_and_capture("stage-p", self._stage_p, self._p_binding, p_request, case_root)
        if p_receipt.error_code is not None:
            return self._finish(case_id, factual_summary, candidate, p_receipt, _not_called("stage-c"),
                                StagedFinalDecisionV1.ABSTAIN, p_receipt.error_code)
        try:
            ledger = PropositionLedgerV1.model_validate_json(p_raw, strict=True)
            validate_source_membership(ledger, factual_summary=factual_summary, candidate=candidate)
        except Exception as exc:
            p_receipt = p_receipt.model_copy(update={"validation_result":"FAIL","error_code":"STAGE_P_SCHEMA_OR_SOURCE_VALIDATION_FAILURE"})
            self._persist_validation(case_root / "stage-p-validation.json", p_receipt.error_code, exc)
            return self._finish(case_id, factual_summary, candidate, p_receipt, _not_called("stage-c"),
                                StagedFinalDecisionV1.ABSTAIN, p_receipt.error_code)
        if ledger.coverage_decision.value == "INDETERMINATE":
            p_receipt = p_receipt.model_copy(update={"validation_result":"VALID_INDETERMINATE","error_code":"STAGE_P_INDETERMINATE"})
            self._persist_validation(case_root / "stage-p-validation.json", p_receipt.error_code, None)
            return self._finish(case_id, factual_summary, candidate, p_receipt, _not_called("stage-c"),
                                StagedFinalDecisionV1.ABSTAIN, p_receipt.error_code)
        p_receipt = p_receipt.model_copy(update={"validation_result":"VALID_COMPLETE"})
        self._persist_validation(case_root / "stage-p-validation.json", "VALID_COMPLETE", None)

        c_request = {"gate_id":"FACTUAL_SEMANTIC","factual_summary":factual_summary,"candidate":candidate,
                     "stage_p_ledger":ledger.model_dump(mode="json"),"stage_p_raw_sha256":p_receipt.raw_sha256}
        c_receipt, c_raw = self._invoke_and_capture("stage-c", self._stage_c, self._c_binding, c_request, case_root)
        if c_receipt.error_code is not None:
            return self._finish(case_id, factual_summary, candidate, p_receipt, c_receipt,
                                StagedFinalDecisionV1.ABSTAIN, c_receipt.error_code)
        try:
            response = validate_reason_span_sources_v1(raw_response=c_raw, factual_summary=factual_summary, candidate=candidate)
            if response.gate_id.value != "FACTUAL_SEMANTIC":
                raise ValueError("Stage C returned wrong gate")
        except Exception as exc:
            c_receipt = c_receipt.model_copy(update={"validation_result":"FAIL","error_code":"STAGE_C_SCHEMA_OR_SOURCE_VALIDATION_FAILURE"})
            self._persist_validation(case_root / "stage-c-validation.json", c_receipt.error_code, exc)
            return self._finish(case_id, factual_summary, candidate, p_receipt, c_receipt,
                                StagedFinalDecisionV1.ABSTAIN, c_receipt.error_code)
        c_receipt = c_receipt.model_copy(update={"validation_result":"VALID"})
        self._persist_validation(case_root / "stage-c-validation.json", "VALID", None)
        if response.decision is GateDecisionV2.INDETERMINATE:
            final, reason = StagedFinalDecisionV1.ABSTAIN, "STAGE_C_INDETERMINATE"
        elif response.decision is GateDecisionV2.FAIL:
            final, reason = StagedFinalDecisionV1.REJECT_FACTUAL_SEMANTIC, "STAGE_C_FAIL"
        else:
            final, reason = StagedFinalDecisionV1.PASS_GATE_F, "STAGE_P_COMPLETE_AND_STAGE_C_PASS"
        return self._finish(case_id, factual_summary, candidate, p_receipt, c_receipt, final, reason)

    def _invoke_and_capture(self, stage: str, evaluator: StageEvaluatorV1, binding: StageIdentityBindingV1,
                            request: dict[str, object], case_root: Path):
        request_bytes = _canonical_bytes(request)
        request_sha = hashlib.sha256(request_bytes).hexdigest()
        _write_exclusive(case_root / f"{stage}-request.json", request_bytes)
        started = time.perf_counter()
        try:
            raw = evaluator(request)
            if type(raw) is not str:
                raise TypeError("evaluator response is not a string")
        except Exception as exc:
            elapsed = round((time.perf_counter()-started)*1000,3)
            error_path = case_root / f"{stage}-provider-exception.json"
            _write_exclusive(error_path, _canonical_bytes({"exception_type":type(exc).__name__}))
            return StageEvidenceReceiptV1(stage_id=stage,**binding.model_dump(),called=True,request_sha256=request_sha,
                raw_path=None,raw_sha256=None,raw_bytes=0,validation_result="NOT_VALIDATED",
                error_code=f"{stage.upper().replace('-', '_')}_PROVIDER_OR_TRANSPORT_FAILURE",elapsed_ms=elapsed), ""
        raw_bytes = raw.encode("utf-8")
        raw_path = case_root / f"{stage}-raw.bin"
        _write_exclusive(raw_path, raw_bytes)  # provider bytes durable before validation
        return StageEvidenceReceiptV1(stage_id=stage,**binding.model_dump(),called=True,request_sha256=request_sha,
            raw_path=str(raw_path),raw_sha256=hashlib.sha256(raw_bytes).hexdigest(),raw_bytes=len(raw_bytes),
            validation_result="PENDING",error_code=None,
            elapsed_ms=round((time.perf_counter()-started)*1000,3)), raw

    @staticmethod
    def _persist_validation(path: Path, result: str, exc: Exception | None) -> None:
        value = {"result":result,"exception_type":type(exc).__name__ if exc else None}
        _write_exclusive(path, _canonical_bytes(value))

    def _finish(self, case_id, factual_summary, candidate, stage_p, stage_c, final, reason):
        draft = StagedGateFReceiptV1(case_id=case_id,
            factual_summary_sha256=_sha_text(factual_summary),candidate_sha256=_sha_text(candidate),
            stage_p=stage_p,stage_c=stage_c,calls_consumed=int(stage_p.called)+int(stage_c.called),
            unused_call_budget=2-int(stage_p.called)-int(stage_c.called),final_decision=final,
            precedence_reason=reason,receipt_identity="sha256:"+"0"*64)
        receipt = draft.model_copy(update={"receipt_identity":canonical_identity(draft.model_dump(mode="json"))})
        _write_exclusive(self._root / case_id / "aggregate-receipt.json",
                         _canonical_bytes(receipt.model_dump(mode="json")))
        return receipt


def _not_called(stage: str) -> StageEvidenceReceiptV1:
    return StageEvidenceReceiptV1(stage_id=stage,evaluator_identity="NOT_CALLED",prompt_identity="NOT_CALLED",
        grammar_identity="NOT_CALLED",model_identity="NOT_CALLED",called=False,request_sha256=None,raw_path=None,
        raw_sha256=None,raw_bytes=0,validation_result="NOT_CALLED",error_code=None,elapsed_ms=0.0)


def _write_exclusive(path: Path, data: bytes) -> None:
    with path.open("xb") as handle:
        handle.write(data)
        handle.flush()


def _canonical_bytes(value: object) -> bytes:
    return json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(",",":"),allow_nan=False).encode("utf-8")


def _sha_text(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


__all__=("StageIdentityBindingV1","StagedGateFCoordinatorV1","StagedGateFReceiptV1","StagedFinalDecisionV1")
