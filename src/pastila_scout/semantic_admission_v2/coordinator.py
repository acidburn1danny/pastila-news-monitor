"""Isolated evaluation-only coordinator for Semantic Admission V2."""

from __future__ import annotations

import hashlib
import json
import time
from collections.abc import Callable

from .canonical_identity_v1 import canonical_identity

from .models import (
    AdmissionInputV2, AdmissionReceiptV2, FinalAdmissionDecisionV2,
    GateDecisionV2, GateIdV2, GateReceiptV2, GateResponseV2,
    ReasonRecordV2, ReasonStatusV2,
)

EvaluatorV2 = Callable[[dict[str, object]], str]


class SemanticAdmissionCoordinatorV2:
    """Evaluate without participating in production Voice admission."""

    def __init__(self, *, gate_f: EvaluatorV2, gate_s: EvaluatorV2,
                 gate_f_identity: str, gate_s_identity: str,
                 gate_f_prompt_identity: str, gate_s_prompt_identity: str) -> None:
        identities = (gate_f_identity, gate_s_identity, gate_f_prompt_identity, gate_s_prompt_identity)
        if any(type(value) is not str or not value for value in identities):
            raise ValueError("evaluator identities are required")
        self._gate_f, self._gate_s = gate_f, gate_s
        self._f_identity, self._s_identity = gate_f_identity, gate_s_identity
        self._f_prompt, self._s_prompt = gate_f_prompt_identity, gate_s_prompt_identity

    def evaluate(self, value: AdmissionInputV2) -> AdmissionReceiptV2:
        f_request = {"gate_id": GateIdV2.FACTUAL_SEMANTIC.value,
                     "factual_summary": value.authority.factual_summary,
                     "candidate": value.candidate.commentary}
        s_request = {"gate_id": GateIdV2.STORY_SPECIFICITY.value,
                     "factual_summary": value.authority.factual_summary,
                     "candidate": value.candidate.commentary,
                     "controls": [control.model_dump(mode="json") for control in value.portability_controls]}
        gate_f = self._invoke(self._gate_f, f_request, GateIdV2.FACTUAL_SEMANTIC,
                              self._f_identity, self._f_prompt)
        gate_s = self._invoke(self._gate_s, s_request, GateIdV2.STORY_SPECIFICITY,
                              self._s_identity, self._s_prompt)
        final, precedence = _final_decision(gate_f, gate_s)
        receipt = AdmissionReceiptV2(case_id=value.case_id, authority=value.authority,
            candidate=value.candidate, runtime=value.runtime,
            surface_findings=value.surface_findings, gate_f=gate_f, gate_s=gate_s,
            final_decision=final, precedence_reason=precedence,
            receipt_identity="sha256:" + "0" * 64)
        identity = canonical_identity(receipt.model_dump(mode="json"))
        return receipt.model_copy(update={"receipt_identity": identity})

    @staticmethod
    def _invoke(evaluator: EvaluatorV2, request: dict[str, object], gate_id: GateIdV2,
                evaluator_identity: str, prompt_identity: str) -> GateReceiptV2:
        request_bytes = json.dumps(request, ensure_ascii=False, sort_keys=True,
                                   separators=(",", ":"), allow_nan=False).encode("utf-8")
        tick = time.perf_counter(); raw = ""; error = None
        try:
            raw = evaluator(request)
            parsed = GateResponseV2.model_validate_json(raw, strict=True)
            if parsed.gate_id is not gate_id:
                raise ValueError("evaluator returned wrong gate")
        except Exception:  # evaluator failures always fail closed
            error = "ADMISSION_EVALUATOR_FAILURE"
            if type(raw) is not str:
                raw = ""
            parsed = GateResponseV2(
                gate_id=gate_id, decision=GateDecisionV2.INDETERMINATE,
                reason_records=(ReasonRecordV2(code=error, status=ReasonStatusV2.DECISIVE,
                    candidate_span=None, authority_support=None,
                    unsupported_proposition="Evaluator output unavailable or invalid.", confidence=0.0),))
        return GateReceiptV2(gate_id=gate_id, evaluator_identity=evaluator_identity,
            prompt_identity=prompt_identity, request_sha256=hashlib.sha256(request_bytes).hexdigest(),
            raw_response_sha256=hashlib.sha256(raw.encode("utf-8")).hexdigest(),
            decision=parsed.decision, reason_records=parsed.reason_records,
            elapsed_ms=round((time.perf_counter()-tick)*1000, 3), error_code=error)


def _final_decision(gate_f: GateReceiptV2, gate_s: GateReceiptV2):
    if gate_f.decision is GateDecisionV2.INDETERMINATE:
        return FinalAdmissionDecisionV2.ADMISSION_ABSTAINED, "ADMISSION_EVALUATOR_FAILURE"
    if gate_f.decision is GateDecisionV2.FAIL:
        decisive = next((r.code for r in gate_f.reason_records if r.status is ReasonStatusV2.DECISIVE), None)
        return FinalAdmissionDecisionV2.REJECT_FACTUAL_SEMANTIC, decisive
    if gate_s.decision is GateDecisionV2.INDETERMINATE:
        return FinalAdmissionDecisionV2.ADMISSION_ABSTAINED, "ADMISSION_EVALUATOR_FAILURE"
    if gate_s.decision is not GateDecisionV2.PASS:
        decisive = next((r.code for r in gate_s.reason_records if r.status is ReasonStatusV2.DECISIVE), None)
        return FinalAdmissionDecisionV2.REJECT_OWNER_QUALITY, decisive
    return FinalAdmissionDecisionV2.ADMIT, None


__all__ = ("SemanticAdmissionCoordinatorV2",)
