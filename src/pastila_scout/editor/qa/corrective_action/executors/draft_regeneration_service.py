"""M6C.6C production execution service and deterministic composition root."""

import json
from enum import StrEnum
from typing import Any

from pydantic import model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    CorrectiveActionExecutionDispatchDiagnostic,
    CorrectiveActionExecutionDispatchDiagnosticCategory,
    CorrectiveActionExecutionDispatchDiagnosticCode,
    CorrectiveActionExecutionStatus,
    CorrectiveActionExecutorOutcome,
    CorrectiveActionExecutorRequest,
    CorrectiveActionExecutorResult,
)
from pastila_scout.editor.qa.integration.models import INTEGRATION_VERSION
from pastila_scout.editor.qa.models import fingerprint

from .draft_regeneration import (
    ControlledGenerationGateway,
    ControlledGenerationRequestProjector,
    DraftRegenerationInput,
    DraftRegenerationInputResolver,
    DraftRegenerationPolicy,
    DraftRegenerationPreconditionEvaluator,
    DraftRegenerationRequestFactory,
    build_standard_draft_regeneration_policy,
)
from .draft_regeneration_execution import (
    ControlledGenerationResultValidator,
    DraftRegenerationExecutor,
    DraftRegenerationResultFactory,
)

SERVICE_CONTRACT_VERSION = "1"
SERVICE_ID = "draft-regeneration-execution-service.v1"


class DraftRegenerationExecutionServiceDiagnosticCode(StrEnum):
    EXECUTION_SERVICE_INTERNAL_FAILURE = "execution_service_internal_failure"
    INVALID_RUNTIME_GRAPH = "invalid_runtime_graph"
    EXECUTOR_NOT_AVAILABLE = "executor_not_available"


class DraftRegenerationExecutionServiceDescriptor(FrozenModel):
    service_id: str = SERVICE_ID
    contract_version: str = SERVICE_CONTRACT_VERSION
    executor_descriptor_fingerprint: str
    controlled_generation_contract_version: str = INTEGRATION_VERSION
    descriptor_fingerprint: str

    @classmethod
    def build(cls, executor: DraftRegenerationExecutor):
        values = {
            "service_id": SERVICE_ID,
            "contract_version": SERVICE_CONTRACT_VERSION,
            "executor_descriptor_fingerprint": executor.descriptor.descriptor_fingerprint,
            "controlled_generation_contract_version": INTEGRATION_VERSION,
        }
        return cls(**values, descriptor_fingerprint=fingerprint(values))

    @model_validator(mode="after")
    def identity_valid(self):
        if self.contract_version != SERVICE_CONTRACT_VERSION:
            raise ValueError("unsupported regeneration execution-service version")
        if self.controlled_generation_contract_version != INTEGRATION_VERSION:
            raise ValueError("unsupported Controlled Generation boundary version")
        expected = fingerprint(
            self.model_dump(exclude={"descriptor_fingerprint"}, mode="python")
        )
        if self.descriptor_fingerprint != expected:
            raise ValueError("execution-service descriptor fingerprint is inconsistent")
        return self


class DraftRegenerationExecutionServiceReport(FrozenModel):
    report_version: str = "1"
    executor_outcome: CorrectiveActionExecutorOutcome
    execution_status: CorrectiveActionExecutionStatus
    executor_id: str
    service_descriptor_fingerprint: str
    executor_request_fingerprint: str
    executor_result_fingerprint: str
    output_reference_fingerprint: str | None
    diagnostic_code: CorrectiveActionExecutionDispatchDiagnosticCode | None
    report_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values.setdefault("report_version", "1")
        values["report_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def identity_valid(self):
        if self.report_version != "1":
            raise ValueError("unsupported execution-service report version")
        expected = fingerprint(
            self.model_dump(exclude={"report_fingerprint"}, mode="python")
        )
        if self.report_fingerprint != expected:
            raise ValueError("execution-service report fingerprint is inconsistent")
        return self


class DraftRegenerationExecutionService:
    """Invoke one injected executor and normalize only unexpected boundary faults."""

    def __init__(self, executor: DraftRegenerationExecutor):
        if not isinstance(executor, DraftRegenerationExecutor):
            raise TypeError("draft-regeneration executor is unavailable")
        self._executor = executor
        self._descriptor = DraftRegenerationExecutionServiceDescriptor.build(executor)

    @property
    def executor(self) -> DraftRegenerationExecutor:
        return self._executor

    @property
    def descriptor(self) -> DraftRegenerationExecutionServiceDescriptor:
        return self._descriptor

    def execute(
        self, executor_request: CorrectiveActionExecutorRequest
    ) -> CorrectiveActionExecutorResult:
        try:
            return self._executor.execute(executor_request)
        except Exception:  # noqa: BLE001 - outer runtime exception boundary
            diagnostic = CorrectiveActionExecutionDispatchDiagnostic.build(
                # Frozen M6C.6B exposes only capability-neutral executor failures.
                code=CorrectiveActionExecutionDispatchDiagnosticCode.EXECUTOR_INVOCATION_FAILED,
                category=CorrectiveActionExecutionDispatchDiagnosticCategory.INTERNAL,
                safe_message="Draft regeneration execution service failed.",
                fingerprint_references=(
                    ("executor_request", executor_request.request_fingerprint),
                ),
            )
            return CorrectiveActionExecutorResult.build(
                executor_descriptor=executor_request.executor_descriptor,
                request=executor_request,
                operational_outcome=CorrectiveActionExecutorOutcome.FAILED_INTERNAL,
                execution_status=CorrectiveActionExecutionStatus.FAILED,
                output_reference=None,
                diagnostic=diagnostic,
            )


def build_draft_regeneration_execution_service(
    generation_gateway: ControlledGenerationGateway,
    regeneration_input: DraftRegenerationInput,
    policy: DraftRegenerationPolicy | None = None,
) -> DraftRegenerationExecutionService:
    """Build one isolated runtime graph from explicit immutable dependencies."""

    if not isinstance(regeneration_input, DraftRegenerationInput):
        raise TypeError("invalid draft-regeneration composition input")
    if not isinstance(generation_gateway, ControlledGenerationGateway):
        raise TypeError("invalid Controlled Generation boundary")
    request_factory = DraftRegenerationRequestFactory(
        DraftRegenerationInputResolver(regeneration_input),
        projector=ControlledGenerationRequestProjector(),
        precondition_evaluator=DraftRegenerationPreconditionEvaluator(),
    )
    executor = DraftRegenerationExecutor(
        request_factory,
        generation_gateway,
        ControlledGenerationResultValidator(),
        DraftRegenerationResultFactory(),
        policy or build_standard_draft_regeneration_policy(),
    )
    return DraftRegenerationExecutionService(executor)


def build_draft_regeneration_execution_service_report(
    service: DraftRegenerationExecutionService,
    request: CorrectiveActionExecutorRequest,
    result: CorrectiveActionExecutorResult,
) -> DraftRegenerationExecutionServiceReport:
    """Project content-free execution lineage after execution."""

    output = result.output_reference
    return DraftRegenerationExecutionServiceReport.build(
        executor_outcome=result.operational_outcome,
        execution_status=result.execution_status,
        executor_id=result.executor_descriptor.executor_id,
        service_descriptor_fingerprint=service.descriptor.descriptor_fingerprint,
        executor_request_fingerprint=request.request_fingerprint,
        executor_result_fingerprint=result.result_fingerprint,
        output_reference_fingerprint=output.reference_fingerprint if output else None,
        diagnostic_code=result.diagnostic.code if result.diagnostic else None,
    )


def serialize_draft_regeneration_execution_service_report(
    report: DraftRegenerationExecutionServiceReport,
) -> str:
    """Serialize only the safe service projection deterministically."""

    return json.dumps(
        report.model_dump(mode="json"),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )
