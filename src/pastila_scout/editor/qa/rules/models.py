"""Immutable private contracts for deterministic editorial rules."""

from enum import StrEnum
from typing import Any

from pydantic import Field, field_validator, model_validator

from pastila_scout.editor.generation.models import FrozenModel
from pastila_scout.editor.qa.models import EditorialFinding, ReviewScope, fingerprint


class RuleCategory(StrEnum):
    STRUCTURE = "structure"
    RUNTIME = "runtime"
    CALLBACK = "callback"
    REPETITION = "repetition"
    LANGUAGE = "language"
    VOICE = "voice"


class RuleCapability(StrEnum):
    STRUCTURE = "structure"
    RUNTIME = "runtime"
    CALLBACK = "callback"
    REPETITION = "repetition"
    LANGUAGE = "language"
    VOICE = "voice"
    TRANSITION = "transition"


class RuleOperationalStatus(StrEnum):
    """Reachability classification without changing rule execution behavior."""

    OPERATIONALLY_REACHABLE = "implemented_operationally_reachable"
    DEFENSIVE = "implemented_defensive"


class RuleApplicabilityStatus(StrEnum):
    APPLICABLE = "applicable"
    SKIPPED = "skipped"
    UNSUPPORTED = "unsupported"


class RuleApplicabilityReason(StrEnum):
    NO_TARGET_COMPONENTS = "NO_TARGET_COMPONENTS"
    NO_CALLBACK_METADATA = "NO_CALLBACK_METADATA"
    NO_VOICE_CONSTRAINTS = "NO_VOICE_CONSTRAINTS"
    NO_REQUIRED_PHRASES = "NO_REQUIRED_PHRASES"
    NO_FORBIDDEN_PHRASES = "NO_FORBIDDEN_PHRASES"
    NO_PROFANITY_POLICY = "NO_PROFANITY_POLICY"
    NO_PROTECTED_NUMERIC_LITERALS = "NO_PROTECTED_NUMERIC_LITERALS"
    SCOPE_NOT_SUPPORTED = "SCOPE_NOT_SUPPORTED"
    UPSTREAM_CONTRACT_UNAVAILABLE = "UPSTREAM_CONTRACT_UNAVAILABLE"
    RULE_DISABLED_BY_POLICY = "RULE_DISABLED_BY_POLICY"


class RuleApplicability(FrozenModel):
    status: RuleApplicabilityStatus
    reason_code: RuleApplicabilityReason | None = None
    target_component_ids: tuple[str, ...] = ()

    @field_validator("target_component_ids")
    @classmethod
    def canonical_targets(cls, value):
        if len(value) != len(set(value)):
            raise ValueError("applicability targets must be unique")
        return tuple(sorted(value))


class RuleExecutionKey(FrozenModel):
    rule_id: str
    rule_version: str
    scope: ReviewScope
    target_component_ids: tuple[str, ...] = ()

    @property
    def value(self) -> str:
        targets = ",".join(self.target_component_ids) or "-"
        return f"{self.rule_id}@{self.rule_version}|scope={self.scope.value}|targets={targets}"


class RuleFailureCode(StrEnum):
    RULE_EXCEPTION = "RULE_EXCEPTION"
    INVALID_RULE_OUTPUT_TYPE = "INVALID_RULE_OUTPUT_TYPE"
    INVALID_FINDING = "INVALID_FINDING"
    DUPLICATE_FINDING_ID = "DUPLICATE_FINDING_ID"
    FINDING_RULE_ID_MISMATCH = "FINDING_RULE_ID_MISMATCH"


class CompletedRuleRecord(FrozenModel):
    execution_key: str
    finding_ids: tuple[str, ...]
    result_fingerprint: str


class SkippedRuleRecord(FrozenModel):
    execution_key: str
    reason_code: RuleApplicabilityReason


class FailedRuleRecord(FrozenModel):
    execution_key: str
    failure_code: RuleFailureCode
    message_code: str


class RuleTraceEventType(StrEnum):
    RULE_STARTED = "rule_started"
    RULE_COMPLETED = "rule_completed"
    RULE_FAILED = "rule_failed"
    RULE_SKIPPED = "rule_skipped"
    FINDING_EMITTED = "finding_emitted"


class RuleTraceRecord(FrozenModel):
    sequence_number: int = Field(gt=0)
    event_type: RuleTraceEventType
    execution_key: str
    finding_id: str | None = None
    message_code: str


class RuleExecutionState(FrozenModel):
    revision: int = Field(ge=0)
    context_fingerprint: str
    rule_set_fingerprint: str
    pending_rule_keys: tuple[str, ...]
    completed_rules: tuple[CompletedRuleRecord, ...] = ()
    skipped_rules: tuple[SkippedRuleRecord, ...] = ()
    failed_rules: tuple[FailedRuleRecord, ...] = ()
    accepted_findings: tuple[EditorialFinding, ...] = ()
    trace_records: tuple[RuleTraceRecord, ...] = ()

    @model_validator(mode="after")
    def partition_is_valid(self):
        terminal = (
            tuple(r.execution_key for r in self.completed_rules)
            + tuple(r.execution_key for r in self.skipped_rules)
            + tuple(r.execution_key for r in self.failed_rules)
        )
        if len(terminal) != len(set(terminal)):
            raise ValueError("rule executions must have one terminal state")
        if set(terminal) & set(self.pending_rule_keys):
            raise ValueError("terminal rule cannot remain pending")
        return self


class RuleExecutionResult(FrozenModel):
    context_fingerprint: str
    rule_set_fingerprint: str
    executed_rule_count: int = Field(ge=0)
    successful_rule_count: int = Field(ge=0)
    skipped_rule_count: int = Field(ge=0)
    failed_rule_count: int = Field(ge=0)
    findings: tuple[EditorialFinding, ...]
    completed_rules: tuple[CompletedRuleRecord, ...]
    skipped_rules: tuple[SkippedRuleRecord, ...]
    failed_rules: tuple[FailedRuleRecord, ...]
    trace: tuple[RuleTraceRecord, ...]
    result_fingerprint: str

    @classmethod
    def build(cls, **values: Any):
        values["result_fingerprint"] = fingerprint(values)
        return cls.model_validate(values)

    @model_validator(mode="after")
    def fingerprint_is_valid(self):
        expected = fingerprint(
            self.model_dump(exclude={"result_fingerprint"}, mode="python")
        )
        if self.result_fingerprint != expected:
            raise ValueError("rule execution fingerprint is inconsistent")
        return self
