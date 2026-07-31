"""Deterministic draft-regeneration precondition evaluation."""

from typing import Any

from pydantic import model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.models import fingerprint

from .enums import (
    DraftRegenerationDiagnosticCode,
    DraftRegenerationPreconditionCode,
    DraftRegenerationPreconditionStatus,
)
from .generation_boundary import ControlledGenerationRequest
from .models import DraftRegenerationDiagnostic, DraftRegenerationRequest

EVALUATION_VERSION = "1"


class DraftRegenerationPreconditionResult(FrozenModel):
    precondition: DraftRegenerationPreconditionCode
    status: DraftRegenerationPreconditionStatus
    diagnostic_code: DraftRegenerationDiagnosticCode | None = None
    result_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values["result_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        expected = fingerprint(
            self.model_dump(exclude={"result_fingerprint"}, mode="python")
        )
        if self.result_fingerprint != expected:
            raise ValueError("precondition-result fingerprint is inconsistent")
        if (self.status is DraftRegenerationPreconditionStatus.SATISFIED) != (
            self.diagnostic_code is None
        ):
            raise ValueError("precondition-result shape is inconsistent")
        return self


class DraftRegenerationPreconditionEvaluation(FrozenModel):
    evaluation_version: str = EVALUATION_VERSION
    request: DraftRegenerationRequest
    evaluations: tuple[DraftRegenerationPreconditionResult, ...]
    overall_status: DraftRegenerationPreconditionStatus
    diagnostic: DraftRegenerationDiagnostic | None
    evaluation_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("evaluation_version", EVALUATION_VERSION)
        values["evaluations"] = tuple(values["evaluations"])
        values["evaluation_fingerprint"] = fingerprint(_identity(values))
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        if self.evaluation_version != EVALUATION_VERSION:
            raise ValueError("unsupported precondition-evaluation version")
        order = tuple(DraftRegenerationPreconditionCode).index
        if (
            tuple(sorted(self.evaluations, key=lambda item: order(item.precondition)))
            != self.evaluations
        ):
            raise ValueError("precondition evaluations are not canonical")
        statuses = {item.status for item in self.evaluations}
        expected_status = (
            DraftRegenerationPreconditionStatus.INVALID
            if DraftRegenerationPreconditionStatus.INVALID in statuses
            else (
                DraftRegenerationPreconditionStatus.NOT_SATISFIED
                if DraftRegenerationPreconditionStatus.NOT_SATISFIED in statuses
                else DraftRegenerationPreconditionStatus.SATISFIED
            )
        )
        if self.overall_status is not expected_status:
            raise ValueError("precondition aggregate is inconsistent")
        if (expected_status is DraftRegenerationPreconditionStatus.SATISFIED) != (
            self.diagnostic is None
        ):
            raise ValueError("precondition-evaluation diagnostic is inconsistent")
        if self.evaluation_fingerprint != fingerprint(
            _identity(self.model_dump(mode="python"))
        ):
            raise ValueError("precondition-evaluation fingerprint is inconsistent")
        return self


class DraftRegenerationPreconditionEvaluator:
    """Evaluate only requirements represented by frozen upstream contracts."""

    def evaluate(
        self,
        request: DraftRegenerationRequest,
        generation_request: ControlledGenerationRequest,
    ):
        checks = {
            DraftRegenerationPreconditionCode.SOURCE_INPUT_AVAILABLE: generation_request
            is request.regeneration_input.generation_invocation,
            DraftRegenerationPreconditionCode.GENERATION_POLICY_AVAILABLE: request.regeneration_input.generation_policy
            is not None,
            DraftRegenerationPreconditionCode.CONTROLLED_GENERATION_CONTRACT_SUPPORTED: bool(
                generation_request.invocation_fingerprint
            ),
            DraftRegenerationPreconditionCode.EXECUTOR_REQUEST_INTEGRITY_VALID: bool(
                request.executor_request.request_fingerprint
            ),
            DraftRegenerationPreconditionCode.PLAN_LINEAGE_VALID: request.executor_request.planning_result.plan
            is request.executor_request.plan,
            DraftRegenerationPreconditionCode.AUTHORIZATION_VALID: True,
        }
        results = tuple(
            DraftRegenerationPreconditionResult.build(
                precondition=code,
                status=(
                    DraftRegenerationPreconditionStatus.SATISFIED
                    if checks[code]
                    else DraftRegenerationPreconditionStatus.NOT_SATISFIED
                ),
                diagnostic_code=(
                    None
                    if checks[code]
                    else DraftRegenerationDiagnosticCode.PRECONDITION_NOT_SATISFIED
                ),
            )
            for code in DraftRegenerationPreconditionCode
        )
        satisfied = all(checks.values())
        diagnostic = (
            None
            if satisfied
            else DraftRegenerationDiagnostic.build(
                code=DraftRegenerationDiagnosticCode.PRECONDITION_NOT_SATISFIED,
                category="precondition",
                safe_message="A regeneration precondition was not satisfied.",
            )
        )
        return DraftRegenerationPreconditionEvaluation.build(
            request=request,
            evaluations=results,
            overall_status=(
                DraftRegenerationPreconditionStatus.SATISFIED
                if satisfied
                else DraftRegenerationPreconditionStatus.NOT_SATISFIED
            ),
            diagnostic=diagnostic,
        )


def _identity(values):
    return {
        "evaluation_version": values["evaluation_version"],
        "request_fingerprint": getattr(
            values["request"],
            "request_fingerprint",
            (
                values["request"].get("request_fingerprint")
                if isinstance(values["request"], dict)
                else None
            ),
        ),
        "result_fingerprints": tuple(
            (
                item["result_fingerprint"]
                if isinstance(item, dict)
                else item.result_fingerprint
            )
            for item in values["evaluations"]
        ),
        "overall_status": values["overall_status"],
        "diagnostic_code": getattr(values.get("diagnostic"), "code", None),
    }
