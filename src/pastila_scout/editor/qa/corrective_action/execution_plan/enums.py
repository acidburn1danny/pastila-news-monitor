"""Stable M6C.6A execution-planning taxonomies."""

from enum import StrEnum


class CorrectiveActionExecutionPlanType(StrEnum):
    """The corrective work a future authorized executor may perform."""

    NO_CORRECTIVE_EXECUTION = "no_corrective_execution"
    REVISE_DRAFT = "revise_draft"
    REGENERATE_DRAFT = "regenerate_draft"
    CREATE_MANUAL_REVIEW_REQUEST = "create_manual_review_request"
    BLOCK_AUTOMATIC_CONTINUATION = "block_automatic_continuation"


class CorrectiveActionExecutionMode(StrEnum):
    """The authorization mode attached to an execution plan."""

    AUTOMATIC = "automatic"
    HUMAN_GATED = "human_gated"
    NON_EXECUTABLE = "non_executable"


class CorrectiveActionExecutionCapability(StrEnum):
    """A declared executor capability, never an executor identity."""

    NONE = "none"
    DRAFT_REVISION = "draft_revision"
    DRAFT_REGENERATION = "draft_regeneration"
    MANUAL_REVIEW_ROUTING = "manual_review_routing"
    WORKFLOW_CONTINUATION_BLOCK = "workflow_continuation_block"


class CorrectiveActionExecutionPlanOutcome(StrEnum):
    """Operational outcome of planning, separate from plan semantics."""

    COMPLETED = "completed"
    FAILED_INVALID_INPUT = "failed_invalid_input"
    FAILED_UNSUPPORTED_CONTRACT = "failed_unsupported_contract"
    FAILED_INTEGRITY_VALIDATION = "failed_integrity_validation"
    FAILED_POLICY_VALIDATION = "failed_policy_validation"
    FAILED_INTERNAL = "failed_internal"


class CorrectiveActionExecutionPlanDiagnosticCode(StrEnum):
    """Stable, content-safe planning diagnostic codes."""

    INVALID_REQUEST = "invalid_request"
    INVALID_POLICY = "invalid_policy"
    UNSUPPORTED_POLICY_VERSION = "unsupported_policy_version"
    INVALID_DECISION_RESULT = "invalid_decision_result"
    UNSUPPORTED_DECISION_CONTRACT_VERSION = "unsupported_decision_contract_version"
    DECISION_FINGERPRINT_MISMATCH = "decision_fingerprint_mismatch"
    POLICY_FINGERPRINT_MISMATCH = "policy_fingerprint_mismatch"
    REQUEST_FINGERPRINT_MISMATCH = "request_fingerprint_mismatch"
    UNSUPPORTED_ACTION = "unsupported_action"
    SEMANTIC_POLICY_CONFLICT = "semantic_policy_conflict"
    INVALID_EXECUTION_MODE = "invalid_execution_mode"
    INVALID_REQUIRED_CAPABILITY = "invalid_required_capability"
    INVALID_PRECONDITIONS = "invalid_preconditions"
    PLAN_FINGERPRINT_MISMATCH = "plan_fingerprint_mismatch"
    INVALID_LIFECYCLE_TRANSITION = "invalid_lifecycle_transition"
    INTERNAL_PLANNING_FAILURE = "internal_planning_failure"


class CorrectiveActionExecutionPlanStage(StrEnum):
    """Safe diagnostic stages available before Part 2 lifecycle work."""

    REQUEST_VALIDATION = "request_validation"
    POLICY_VALIDATION = "policy_validation"
    UPSTREAM_VALIDATION = "upstream_validation"
    PLAN_VALIDATION = "plan_validation"
    RESULT_VALIDATION = "result_validation"
    REPORTING = "reporting"


class CorrectiveActionExecutionPlanningLifecycle(StrEnum):
    """Immutable planning runtime phases."""

    PREPARED = "prepared"
    VALIDATING = "validating"
    PLANNING = "planning"
    PLANNED = "planned"
    FINALIZED = "finalized"
    FAILED = "failed"


class CorrectiveActionExecutionPlanningEventCode(StrEnum):
    """Stable codes for accepted lifecycle transitions."""

    VALIDATION_STARTED = "validation_started"
    PLANNING_STARTED = "planning_started"
    PLAN_CONSTRUCTED = "plan_constructed"
    PLANNING_FINALIZED = "planning_finalized"
    PLANNING_FAILED = "planning_failed"
