"""Immutable M6C.5F Part 1 corrective-action decision contracts."""

from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator, model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.integration import EditorialReviewIntegrationResult
from pastila_scout.editor.qa.models import fingerprint

ENGINE_ID = "m6c5f.corrective_action_decision"
CONTRACT_VERSION = "1"
SUPPORTED_INPUT = "m6c5e.editorial_review_integration_result@1.0.0"


class CorrectiveAction(StrEnum):
    CONTINUE_WORKFLOW = "continue_workflow"
    REQUEST_REVISION = "request_revision"
    REQUEST_REGENERATION = "request_regeneration"
    REQUEST_MANUAL_REVIEW = "request_manual_review"
    HALT_WORKFLOW = "halt_workflow"
    NO_ACTION = "no_action"


class CorrectiveActionDecisionOutcome(StrEnum):
    COMPLETED = "completed"
    FAILED_INVALID_INPUT = "failed_invalid_input"
    FAILED_DURING_DECISION = "failed_during_decision"
    FAILED_DURING_FINALIZATION = "failed_during_finalization"


class CorrectiveActionDecisionReason(StrEnum):
    EDITORIAL_APPROVED = "editorial_approved"
    EDITORIAL_REVISION_REQUIRED = "editorial_revision_required"
    EDITORIAL_REGENERATION_REQUIRED = "editorial_regeneration_required"
    EDITORIAL_HUMAN_REVIEW_REQUIRED = "editorial_human_review_required"
    EDITORIAL_REJECTED = "editorial_rejected"
    EDITORIAL_OUTCOME_ABSENT = "editorial_outcome_absent"
    REVIEW_DISABLED = "review_disabled"
    UPSTREAM_GENERATION_FAILED = "upstream_generation_failed"
    UPSTREAM_DRAFT_INVALID = "upstream_draft_invalid"
    UPSTREAM_REVIEW_FAILED = "upstream_review_failed"
    UPSTREAM_INCOMPLETE = "upstream_incomplete"


class CorrectiveActionDecisionLifecycle(StrEnum):
    PREPARED = "prepared"
    VALIDATING = "validating"
    DECIDING = "deciding"
    DECIDED = "decided"
    FINALIZED = "finalized"
    FAILED = "failed"


class CorrectiveActionDecisionPhase(StrEnum):
    REQUEST_VALIDATION = "request_validation"
    UPSTREAM_RESULT_VALIDATION = "upstream_result_validation"
    POLICY_VALIDATION = "policy_validation"
    DECISION_EVALUATION = "decision_evaluation"
    DECISION_CONSTRUCTION = "decision_construction"
    REPORTING = "reporting"
    FINALIZATION = "finalization"


class CorrectiveActionDecisionDiagnosticCode(StrEnum):
    INVALID_DECISION_REQUEST = "invalid_decision_request"
    INVALID_INTEGRATION_RESULT = "invalid_integration_result"
    INVALID_DECISION_POLICY = "invalid_decision_policy"
    UNSUPPORTED_INTEGRATION_STATUS = "unsupported_integration_status"
    INCONSISTENT_UPSTREAM_STATE = "inconsistent_upstream_state"
    DECISION_CONSTRUCTION_FAILED = "decision_construction_failed"
    FINALIZATION_FAILED = "finalization_failed"


class CorrectiveActionDecisionDiagnosticSeverity(StrEnum):
    ERROR = "error"


class CorrectiveActionDecisionTraceType(StrEnum):
    REQUEST_RECEIVED = "request_received"
    REQUEST_VALIDATED = "request_validated"
    UPSTREAM_RESULT_VALIDATED = "upstream_result_validated"
    POLICY_RESOLVED = "policy_resolved"
    DECISION_EVALUATED = "decision_evaluated"
    DECISION_CONSTRUCTED = "decision_constructed"
    REPORT_CONSTRUCTED = "report_constructed"
    FINALIZED = "finalized"
    FAILED = "failed"


class CorrectiveActionDecisionDescriptor(FrozenModel):
    engine_id: str = ENGINE_ID
    contract_version: str = CONTRACT_VERSION
    supported_input: str = SUPPORTED_INPUT
    descriptor_fingerprint: str

    @classmethod
    def build(cls) -> CorrectiveActionDecisionDescriptor:
        values = {
            "engine_id": ENGINE_ID,
            "contract_version": CONTRACT_VERSION,
            "supported_input": SUPPORTED_INPUT,
        }
        return cls(**values, descriptor_fingerprint=fingerprint(values))

    @model_validator(mode="after")
    def identity_valid(self):
        if (
            self.engine_id != ENGINE_ID
            or self.contract_version != CONTRACT_VERSION
            or self.supported_input != SUPPORTED_INPUT
        ):
            raise ValueError("unsupported corrective-action descriptor")
        return _validate_fingerprint(self, "descriptor_fingerprint")


class CorrectiveActionDecisionPolicy(FrozenModel):
    rejected_action: CorrectiveAction = CorrectiveAction.HALT_WORKFLOW
    missing_editorial_action: CorrectiveAction = CorrectiveAction.REQUEST_MANUAL_REVIEW
    review_disabled_action: CorrectiveAction = CorrectiveAction.REQUEST_MANUAL_REVIEW
    policy_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionDecisionPolicy:
        unknown = set(values) - {
            "rejected_action",
            "missing_editorial_action",
            "review_disabled_action",
        }
        if unknown:
            raise ValueError("unsupported corrective-action policy option")
        payload = {
            "rejected_action": values.get(
                "rejected_action", CorrectiveAction.HALT_WORKFLOW
            ),
            "missing_editorial_action": values.get(
                "missing_editorial_action", CorrectiveAction.REQUEST_MANUAL_REVIEW
            ),
            "review_disabled_action": values.get(
                "review_disabled_action", CorrectiveAction.REQUEST_MANUAL_REVIEW
            ),
        }
        return cls(**payload, policy_fingerprint=fingerprint(payload))

    @field_validator("rejected_action")
    @classmethod
    def valid_rejected_action(cls, value):
        if value not in {
            CorrectiveAction.HALT_WORKFLOW,
            CorrectiveAction.REQUEST_MANUAL_REVIEW,
        }:
            raise ValueError("rejected action must halt or request manual review")
        return value

    @field_validator("missing_editorial_action")
    @classmethod
    def valid_missing_editorial_action(cls, value):
        if value not in {
            CorrectiveAction.HALT_WORKFLOW,
            CorrectiveAction.REQUEST_MANUAL_REVIEW,
        }:
            raise ValueError(
                "missing-editorial action must halt or request manual review"
            )
        return value

    @field_validator("review_disabled_action")
    @classmethod
    def valid_review_disabled_action(cls, value):
        if value not in {
            CorrectiveAction.HALT_WORKFLOW,
            CorrectiveAction.REQUEST_MANUAL_REVIEW,
            CorrectiveAction.NO_ACTION,
        }:
            raise ValueError(
                "absent-outcome action must be halt, manual review, or none"
            )
        return value

    @model_validator(mode="after")
    def identity_valid(self):
        return _validate_fingerprint(self, "policy_fingerprint")


class CorrectiveActionDecisionRequest(FrozenModel):
    integration_result: EditorialReviewIntegrationResult
    policy: CorrectiveActionDecisionPolicy
    contract_version: str = CONTRACT_VERSION
    request_fingerprint: str

    @classmethod
    def build(
        cls,
        integration_result: EditorialReviewIntegrationResult,
        policy: CorrectiveActionDecisionPolicy,
    ) -> CorrectiveActionDecisionRequest:
        payload = _request_identity(integration_result, policy, CONTRACT_VERSION)
        return cls(
            integration_result=integration_result,
            policy=policy,
            request_fingerprint=fingerprint(payload),
        )

    @field_validator("contract_version")
    @classmethod
    def supported_version(cls, value):
        if value != CONTRACT_VERSION:
            raise ValueError("unsupported corrective-action contract version")
        return value

    @model_validator(mode="after")
    def identity_valid(self):
        expected = fingerprint(
            _request_identity(
                self.integration_result, self.policy, self.contract_version
            )
        )
        if self.request_fingerprint != expected:
            raise ValueError("request fingerprint is inconsistent")
        return self


class CorrectiveActionDecision(FrozenModel):
    action: CorrectiveAction
    reason: CorrectiveActionDecisionReason
    source_integration_fingerprint: str
    source_editorial_status: str | None = None
    policy_fingerprint: str
    policy_applied: bool
    decision_rule_id: str
    decision_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionDecision:
        values["decision_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @property
    def requires_human_attention(self) -> bool:
        return self.action in {
            CorrectiveAction.REQUEST_REVISION,
            CorrectiveAction.REQUEST_REGENERATION,
            CorrectiveAction.REQUEST_MANUAL_REVIEW,
            CorrectiveAction.HALT_WORKFLOW,
        }

    @property
    def allows_automatic_continuation(self) -> bool:
        return self.action is CorrectiveAction.CONTINUE_WORKFLOW

    @model_validator(mode="after")
    def identity_valid(self):
        _validate_fingerprint(self, "decision_fingerprint")
        allowed = {
            CorrectiveActionDecisionReason.EDITORIAL_APPROVED: {
                CorrectiveAction.CONTINUE_WORKFLOW
            },
            CorrectiveActionDecisionReason.EDITORIAL_REVISION_REQUIRED: {
                CorrectiveAction.REQUEST_REVISION
            },
            CorrectiveActionDecisionReason.EDITORIAL_REGENERATION_REQUIRED: {
                CorrectiveAction.REQUEST_REGENERATION
            },
            CorrectiveActionDecisionReason.EDITORIAL_HUMAN_REVIEW_REQUIRED: {
                CorrectiveAction.REQUEST_MANUAL_REVIEW
            },
            CorrectiveActionDecisionReason.EDITORIAL_REJECTED: {
                CorrectiveAction.HALT_WORKFLOW,
                CorrectiveAction.REQUEST_MANUAL_REVIEW,
            },
            CorrectiveActionDecisionReason.EDITORIAL_OUTCOME_ABSENT: {
                CorrectiveAction.HALT_WORKFLOW,
                CorrectiveAction.REQUEST_MANUAL_REVIEW,
            },
            CorrectiveActionDecisionReason.REVIEW_DISABLED: {
                CorrectiveAction.HALT_WORKFLOW,
                CorrectiveAction.REQUEST_MANUAL_REVIEW,
                CorrectiveAction.NO_ACTION,
            },
            CorrectiveActionDecisionReason.UPSTREAM_GENERATION_FAILED: {
                CorrectiveAction.HALT_WORKFLOW
            },
            CorrectiveActionDecisionReason.UPSTREAM_DRAFT_INVALID: {
                CorrectiveAction.HALT_WORKFLOW
            },
            CorrectiveActionDecisionReason.UPSTREAM_REVIEW_FAILED: {
                CorrectiveAction.HALT_WORKFLOW
            },
            CorrectiveActionDecisionReason.UPSTREAM_INCOMPLETE: {
                CorrectiveAction.HALT_WORKFLOW,
                CorrectiveAction.REQUEST_MANUAL_REVIEW,
            },
        }
        if self.action not in allowed[self.reason]:
            raise ValueError("decision action and reason are inconsistent")
        policy_reasons = {
            CorrectiveActionDecisionReason.EDITORIAL_REJECTED,
            CorrectiveActionDecisionReason.EDITORIAL_OUTCOME_ABSENT,
            CorrectiveActionDecisionReason.REVIEW_DISABLED,
            CorrectiveActionDecisionReason.UPSTREAM_INCOMPLETE,
        }
        if self.policy_applied != (self.reason in policy_reasons):
            raise ValueError("decision policy-applied metadata is inconsistent")
        if not self.decision_rule_id:
            raise ValueError("decision rule ID must be nonempty")
        return self


class CorrectiveActionDecisionDiagnostic(FrozenModel):
    code: CorrectiveActionDecisionDiagnosticCode
    severity: CorrectiveActionDecisionDiagnosticSeverity
    phase: CorrectiveActionDecisionPhase
    safe_context: tuple[tuple[str, str], ...] = ()
    diagnostic_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionDecisionDiagnostic:
        values["safe_context"] = tuple(sorted(values.get("safe_context", ())))
        values["diagnostic_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @field_validator("safe_context")
    @classmethod
    def safe_context_valid(cls, value):
        allowed = {
            "integration_fingerprint",
            "policy_fingerprint",
            "upstream_operational_status",
            "upstream_editorial_status",
            "contract_version",
        }
        keys = tuple(key for key, _ in value)
        if len(keys) != len(set(keys)) or not set(keys) <= allowed:
            raise ValueError("diagnostic context is not canonical or safe")
        return value

    @model_validator(mode="after")
    def identity_valid(self):
        return _validate_fingerprint(self, "diagnostic_fingerprint")


class CorrectiveActionDecisionTraceEvent(FrozenModel):
    sequence: int = Field(ge=0)
    event_type: CorrectiveActionDecisionTraceType
    phase: CorrectiveActionDecisionPhase
    code: str | None = None
    event_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionDecisionTraceEvent:
        values.setdefault("code", None)
        values["event_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def identity_valid(self):
        return _validate_fingerprint(self, "event_fingerprint")


class CorrectiveActionDecisionCompleteness(FrozenModel):
    input_present: bool
    input_validated: bool
    upstream_operational_status_observed: bool
    editorial_status_observed: bool
    policy_applied: bool
    decision_produced: bool
    report_produced: bool
    finalized: bool
    completeness_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionDecisionCompleteness:
        values["completeness_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def identity_valid(self):
        return _validate_fingerprint(self, "completeness_fingerprint")


class CorrectiveActionDecisionReport(FrozenModel):
    engine_id: str
    contract_version: str
    source_integration_fingerprint: str | None
    source_integration_status: str | None
    source_editorial_status: str | None
    operational_outcome: CorrectiveActionDecisionOutcome
    requested_action: CorrectiveAction | None
    decision_reason: CorrectiveActionDecisionReason | None
    policy_fingerprint: str | None
    decision_fingerprint: str | None
    diagnostic_codes: tuple[CorrectiveActionDecisionDiagnosticCode, ...]
    completeness: CorrectiveActionDecisionCompleteness
    report_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionDecisionReport:
        values["diagnostic_codes"] = tuple(sorted(values.get("diagnostic_codes", ())))
        values["report_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def identity_valid(self):
        return _validate_fingerprint(self, "report_fingerprint")


class CorrectiveActionDecisionResult(FrozenModel):
    descriptor: CorrectiveActionDecisionDescriptor
    request_fingerprint: str | None
    integration_result: EditorialReviewIntegrationResult | None
    operational_outcome: CorrectiveActionDecisionOutcome
    decision: CorrectiveActionDecision | None
    lifecycle: CorrectiveActionDecisionLifecycle
    diagnostics: tuple[CorrectiveActionDecisionDiagnostic, ...]
    trace: tuple[CorrectiveActionDecisionTraceEvent, ...]
    completeness: CorrectiveActionDecisionCompleteness
    report: CorrectiveActionDecisionReport
    result_fingerprint: str

    @classmethod
    def build(cls, **values: Any) -> CorrectiveActionDecisionResult:
        values["result_fingerprint"] = fingerprint(_result_identity(values))
        return cls.model_validate(values)

    @model_validator(mode="after")
    def invariants(self):
        completed = (
            self.operational_outcome is CorrectiveActionDecisionOutcome.COMPLETED
        )
        if completed != (self.decision is not None):
            raise ValueError("completed outcome requires exactly one decision")
        if self.decision is not None:
            if self.integration_result is None:
                raise ValueError(
                    "decision requires an authoritative integration result"
                )
            if (
                self.decision.source_integration_fingerprint
                != self.integration_result.result_fingerprint
            ):
                raise ValueError("decision source identity is inconsistent")
            if self.decision.policy_fingerprint != self.report.policy_fingerprint:
                raise ValueError("decision policy identity is inconsistent")
        if self.report.operational_outcome is not self.operational_outcome:
            raise ValueError("report operational outcome is inconsistent")
        if self.report.requested_action != (
            self.decision.action if self.decision else None
        ):
            raise ValueError("report action is inconsistent")
        if (
            completed
            and self.lifecycle is not CorrectiveActionDecisionLifecycle.FINALIZED
        ):
            raise ValueError("completed decision must be finalized")
        if (
            not completed
            and self.lifecycle is not CorrectiveActionDecisionLifecycle.FAILED
        ):
            raise ValueError("failed decision must use failed lifecycle")
        expected = fingerprint(_result_identity(self.model_dump(mode="python")))
        if self.result_fingerprint != expected:
            raise ValueError("result fingerprint is inconsistent")
        return self


def _request_identity(integration_result, policy, contract_version):
    return {
        "contract_version": contract_version,
        "integration_result_fingerprint": integration_result.result_fingerprint,
        "policy_fingerprint": policy.policy_fingerprint,
    }


def _result_identity(values):
    integration_result = values.get("integration_result")
    decision = values.get("decision")
    descriptor = values["descriptor"]
    completeness = values["completeness"]
    report = values["report"]
    return {
        "descriptor_fingerprint": _field(descriptor, "descriptor_fingerprint"),
        "request_fingerprint": values.get("request_fingerprint"),
        "source_integration_fingerprint": (
            _field(integration_result, "result_fingerprint")
            if integration_result
            else None
        ),
        "operational_outcome": values["operational_outcome"],
        "decision_fingerprint": (
            _field(decision, "decision_fingerprint") if decision else None
        ),
        "lifecycle": values["lifecycle"],
        "diagnostic_fingerprints": tuple(
            _field(item, "diagnostic_fingerprint") for item in values["diagnostics"]
        ),
        "trace_fingerprints": tuple(
            _field(item, "event_fingerprint") for item in values["trace"]
        ),
        "completeness_fingerprint": _field(completeness, "completeness_fingerprint"),
        "report_fingerprint": _field(report, "report_fingerprint"),
    }


def _field(value, name):
    return value[name] if isinstance(value, dict) else getattr(value, name)


def _validate_fingerprint(model: FrozenModel, field_name: str):
    expected = fingerprint(model.model_dump(exclude={field_name}, mode="python"))
    if getattr(model, field_name) != expected:
        raise ValueError(f"{field_name} is inconsistent")
    return model
