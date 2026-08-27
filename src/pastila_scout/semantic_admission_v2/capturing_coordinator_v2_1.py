"""Versioned raw-evidence capture wrapper for SAV2 evaluation-only runs."""

from __future__ import annotations

import hashlib
import json
from enum import StrEnum

from pydantic import BaseModel, ConfigDict

from .coordinator import SemanticAdmissionCoordinatorV2
from .models import AdmissionInputV2, AdmissionReceiptV2, GateIdV2, GateResponseV2


class ContractDiagnosticV21(StrEnum):
    VALID = "VALID"
    EMPTY = "EMPTY"
    NON_STRING = "NON_STRING"
    NON_JSON = "NON_JSON"
    JSON_NOT_OBJECT = "JSON_NOT_OBJECT"
    WRONG_KEY_SET = "WRONG_KEY_SET"
    STRICT_SCHEMA_INVALID = "STRICT_SCHEMA_INVALID"
    EVALUATOR_EXCEPTION = "EVALUATOR_EXCEPTION"


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class CapturedGateEvidenceV21(_Frozen):
    gate_id: GateIdV2
    raw_response: str | None
    raw_response_sha256: str
    diagnostic: ContractDiagnosticV21
    evaluator_exception_type: str | None


class CapturedAdmissionEvaluationV21(_Frozen):
    schema_name: str = "pastila-semantic-admission-v2-captured-evaluation"
    schema_version: str = "2.1.0-evaluation.1"
    receipt: AdmissionReceiptV2
    gate_f_evidence: CapturedGateEvidenceV21
    gate_s_evidence: CapturedGateEvidenceV21
    eligibility: str = "QUARANTINED_EVALUATION_ONLY"
    current_runtime_admission_affected: bool = False


class CapturingSemanticAdmissionCoordinatorV21:
    """Capture raw evaluator bytes without changing V2 admission semantics."""

    def __init__(self, *, gate_f, gate_s, gate_f_identity: str, gate_s_identity: str,
                 gate_f_prompt_identity: str, gate_s_prompt_identity: str) -> None:
        self._captured: dict[GateIdV2, tuple[object, str | None]] = {}
        def wrap(gate_id, evaluator):
            def call(request):
                try:
                    raw = evaluator(request)
                except Exception as exc:
                    self._captured[gate_id] = (None, type(exc).__name__)
                    raise
                self._captured[gate_id] = (raw, None)
                return raw
            return call
        self._inner = SemanticAdmissionCoordinatorV2(
            gate_f=wrap(GateIdV2.FACTUAL_SEMANTIC, gate_f),
            gate_s=wrap(GateIdV2.STORY_SPECIFICITY, gate_s),
            gate_f_identity=gate_f_identity, gate_s_identity=gate_s_identity,
            gate_f_prompt_identity=gate_f_prompt_identity,
            gate_s_prompt_identity=gate_s_prompt_identity)

    def evaluate(self, value: AdmissionInputV2) -> CapturedAdmissionEvaluationV21:
        self._captured.clear()
        receipt = self._inner.evaluate(value)
        f = _evidence(GateIdV2.FACTUAL_SEMANTIC, self._captured.get(GateIdV2.FACTUAL_SEMANTIC))
        s = _evidence(GateIdV2.STORY_SPECIFICITY, self._captured.get(GateIdV2.STORY_SPECIFICITY))
        if f.raw_response_sha256 != receipt.gate_f.raw_response_sha256 or s.raw_response_sha256 != receipt.gate_s.raw_response_sha256:
            raise RuntimeError("captured raw response hash does not match admission receipt")
        return CapturedAdmissionEvaluationV21(receipt=receipt,gate_f_evidence=f,gate_s_evidence=s)


def _evidence(gate_id: GateIdV2, captured: tuple[object, str | None] | None) -> CapturedGateEvidenceV21:
    if captured is None:
        raw, exception = None, "MissingCapture"
    else:
        raw, exception = captured
    diagnostic = _diagnose(raw, exception)
    text = raw if type(raw) is str else None
    return CapturedGateEvidenceV21(gate_id=gate_id,raw_response=text,
        raw_response_sha256=hashlib.sha256((text or "").encode()).hexdigest(),
        diagnostic=diagnostic,evaluator_exception_type=exception)


def _diagnose(raw: object, exception: str | None) -> ContractDiagnosticV21:
    if exception is not None: return ContractDiagnosticV21.EVALUATOR_EXCEPTION
    if type(raw) is not str: return ContractDiagnosticV21.NON_STRING
    if not raw: return ContractDiagnosticV21.EMPTY
    try: value=json.loads(raw)
    except (TypeError,ValueError): return ContractDiagnosticV21.NON_JSON
    if type(value) is not dict: return ContractDiagnosticV21.JSON_NOT_OBJECT
    if set(value)!={"gate_id","decision","reason_records"}: return ContractDiagnosticV21.WRONG_KEY_SET
    try: GateResponseV2.model_validate_json(raw,strict=True)
    except Exception: return ContractDiagnosticV21.STRICT_SCHEMA_INVALID
    return ContractDiagnosticV21.VALID


__all__=("CapturedAdmissionEvaluationV21","CapturedGateEvidenceV21",
         "CapturingSemanticAdmissionCoordinatorV21","ContractDiagnosticV21")
