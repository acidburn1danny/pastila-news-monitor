"""Strict, frozen models for evaluation-only Semantic Admission V2."""

from __future__ import annotations

import hashlib
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, model_validator

REASON_CODES_V2 = frozenset({
    "FSEM_UNSUPPORTED_BIOGRAPHY_OR_HISTORY", "FSEM_UNSUPPORTED_MOTIVE_OR_INTENT",
    "FSEM_UNSUPPORTED_CAUSALITY", "FSEM_UNSUPPORTED_OUTCOME_OR_STATUS",
    "FSEM_UNSUPPORTED_EMOTION_OR_REACTION", "FSEM_UNSUPPORTED_CAPACITY",
    "FSEM_CERTAINTY_MUTATION", "FSEM_TIMING_MUTATION", "FSEM_UNSUPPORTED_LIFE_STAKES",
    "FSEM_INVENTED_SPEECH_OR_ROLE_KNOWLEDGE", "FSEM_UNSUPPORTED_PREMISE_TO_DIRECTIVE",
    "FSEM_FICTION_RETURN_TO_FACT", "SPEC_GENERIC_PORTABLE", "SPEC_TEMPLATE_DOMINANT",
    "SPEC_WEAK_LOCAL_MAPPING", "ADMISSION_AUTHORITY_FAILURE",
    "ADMISSION_EVALUATOR_FAILURE", "ADMISSION_INDETERMINATE",
})


class _Frozen(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, strict=True)


class GateIdV2(StrEnum):
    FACTUAL_SEMANTIC = "FACTUAL_SEMANTIC"
    STORY_SPECIFICITY = "STORY_SPECIFICITY"


class GateDecisionV2(StrEnum):
    PASS = "PASS"
    FAIL = "FAIL"
    FAIL_GENERIC_PORTABLE = "FAIL_GENERIC_PORTABLE"
    FAIL_TEMPLATE_DOMINANT = "FAIL_TEMPLATE_DOMINANT"
    FAIL_WEAK_MAPPING = "FAIL_WEAK_MAPPING"
    INDETERMINATE = "INDETERMINATE"
    NOT_EVALUATED = "NOT_EVALUATED"


class ReasonStatusV2(StrEnum):
    DECISIVE = "DECISIVE"
    SUPPORTING = "SUPPORTING"
    DEFENSE_IN_DEPTH_ONLY = "DEFENSE_IN_DEPTH_ONLY"


class FinalAdmissionDecisionV2(StrEnum):
    ADMIT = "ADMIT"
    REJECT_FACTUAL_SEMANTIC = "REJECT_FACTUAL_SEMANTIC"
    REJECT_OWNER_QUALITY = "REJECT_OWNER_QUALITY"
    ADMISSION_ABSTAINED = "ADMISSION_ABSTAINED"


class AuthorityBindingV2(_Frozen):
    factual_summary: str = Field(min_length=20, max_length=2000)
    factual_summary_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    authority_identity: str = Field(min_length=1)
    byte_immutable: bool

    @model_validator(mode="after")
    def verify_bytes(self):
        if not self.byte_immutable or _sha(self.factual_summary) != self.factual_summary_sha256:
            raise ValueError("factual authority byte binding failed")
        return self


class CandidateBindingV2(_Frozen):
    commentary: str = Field(min_length=1, max_length=2000)
    candidate_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    raw_response_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")

    @model_validator(mode="after")
    def verify_bytes(self):
        if _sha(self.commentary) != self.candidate_sha256:
            raise ValueError("candidate byte binding failed")
        return self


class RuntimeBindingV2(_Frozen):
    application_identity: str
    core_identity: str
    voice_identity: str
    prompt_identity: str
    model_identity: str


class PortabilityControlV2(_Frozen):
    case_id: str
    factual_summary: str = Field(min_length=20, max_length=2000)
    factual_summary_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    authority_identity: str

    @model_validator(mode="after")
    def verify_bytes(self):
        if _sha(self.factual_summary) != self.factual_summary_sha256:
            raise ValueError("portability control byte binding failed")
        return self


class SurfaceDefenseFindingV2(_Frozen):
    code: str
    role: ReasonStatusV2 = ReasonStatusV2.DEFENSE_IN_DEPTH_ONLY

    @model_validator(mode="after")
    def require_defense_role(self):
        if self.role is not ReasonStatusV2.DEFENSE_IN_DEPTH_ONLY:
            raise ValueError("surface findings are defense-in-depth only")
        return self


class AdmissionInputV2(_Frozen):
    case_id: str
    authority: AuthorityBindingV2
    candidate: CandidateBindingV2
    runtime: RuntimeBindingV2
    portability_controls: tuple[PortabilityControlV2, ...] = Field(min_length=2, max_length=3)
    surface_findings: tuple[SurfaceDefenseFindingV2, ...] = ()

    @model_validator(mode="after")
    def distinct_controls(self):
        ids = tuple(control.case_id for control in self.portability_controls)
        if self.case_id in ids or len(set(ids)) != len(ids):
            raise ValueError("portability controls must be distinct from source and each other")
        return self


class ReasonRecordV2(_Frozen):
    code: str = Field(pattern=r"^(FSEM|SPEC|ADMISSION)_[A-Z0-9_]+$")
    status: ReasonStatusV2
    candidate_span: str | None
    authority_support: str | None
    unsupported_proposition: str | None
    confidence: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def known_reason(self):
        if self.code not in REASON_CODES_V2:
            raise ValueError("unknown Semantic Admission V2 reason code")
        return self


class GateResponseV2(_Frozen):
    gate_id: GateIdV2
    decision: GateDecisionV2
    reason_records: tuple[ReasonRecordV2, ...]

    @model_validator(mode="after")
    def validate_gate_contract(self):
        f_allowed = {GateDecisionV2.PASS, GateDecisionV2.FAIL, GateDecisionV2.INDETERMINATE}
        s_allowed = {GateDecisionV2.PASS, GateDecisionV2.FAIL_GENERIC_PORTABLE,
                     GateDecisionV2.FAIL_TEMPLATE_DOMINANT, GateDecisionV2.FAIL_WEAK_MAPPING,
                     GateDecisionV2.INDETERMINATE}
        if self.decision not in (f_allowed if self.gate_id is GateIdV2.FACTUAL_SEMANTIC else s_allowed):
            raise ValueError("decision is invalid for gate")
        if self.decision is GateDecisionV2.PASS and self.reason_records:
            raise ValueError("passing gate cannot carry failure reasons")
        if self.decision is not GateDecisionV2.PASS and not self.reason_records:
            raise ValueError("non-passing gate requires a reason")
        if self.decision is not GateDecisionV2.PASS and not any(
            reason.status is ReasonStatusV2.DECISIVE for reason in self.reason_records
        ):
            raise ValueError("non-passing gate requires a decisive reason")
        prefix = "FSEM_" if self.gate_id is GateIdV2.FACTUAL_SEMANTIC else "SPEC_"
        if any(not reason.code.startswith((prefix, "ADMISSION_")) for reason in self.reason_records):
            raise ValueError("reason namespace is invalid for gate")
        return self


class GateReceiptV2(_Frozen):
    gate_id: GateIdV2
    evaluator_identity: str
    prompt_identity: str
    request_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    raw_response_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    decision: GateDecisionV2
    reason_records: tuple[ReasonRecordV2, ...]
    elapsed_ms: float = Field(ge=0)
    error_code: str | None = None


class AdmissionReceiptV2(_Frozen):
    schema_name: str = "pastila-semantic-admission-v2-evaluation-receipt"
    schema_version: str = "2.0.0-evaluation.1"
    case_id: str
    authority: AuthorityBindingV2
    candidate: CandidateBindingV2
    runtime: RuntimeBindingV2
    surface_findings: tuple[SurfaceDefenseFindingV2, ...]
    gate_f: GateReceiptV2
    gate_s: GateReceiptV2
    final_decision: FinalAdmissionDecisionV2
    precedence_reason: str | None
    eligibility: str = "QUARANTINED_EVALUATION_ONLY"
    current_runtime_admission_affected: bool = False
    receipt_identity: str = Field(pattern=r"^sha256:[a-f0-9]{64}$")


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


__all__ = tuple(name for name in globals() if name.endswith("V2"))
