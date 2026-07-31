"""Stable M6C.6B Part 1 dispatch contract taxonomies."""

from enum import StrEnum


class CorrectiveActionExecutionDispatchStatus(StrEnum):
    """Dispatch progress/terminal meaning, separate from operation outcome."""

    NOT_ATTEMPTED = "not_attempted"
    NOT_DISPATCHABLE = "not_dispatchable"
    AWAITING_AUTHORIZATION = "awaiting_authorization"
    DISPATCHED = "dispatched"
    EXECUTOR_COMPLETED = "executor_completed"
    EXECUTOR_FAILED = "executor_failed"
    DISPATCH_FAILED = "dispatch_failed"


class CorrectiveActionExecutionDispatchOutcome(StrEnum):
    """Operational outcome of the dispatch layer."""

    COMPLETED = "completed"
    FAILED_INVALID_INPUT = "failed_invalid_input"
    FAILED_UNSUPPORTED_CONTRACT = "failed_unsupported_contract"
    FAILED_INTEGRITY_VALIDATION = "failed_integrity_validation"
    FAILED_POLICY_VALIDATION = "failed_policy_validation"
    FAILED_NOT_DISPATCHABLE = "failed_not_dispatchable"
    FAILED_CAPABILITY_RESOLUTION = "failed_capability_resolution"
    FAILED_EXECUTOR_CONTRACT = "failed_executor_contract"
    FAILED_INTERNAL = "failed_internal"


class CorrectiveActionAuthorizationState(StrEnum):
    """Explicit human authorization state supplied by dispatch context."""

    NOT_REQUIRED = "not_required"
    REQUIRED_NOT_GRANTED = "required_not_granted"
    GRANTED = "granted"
    DENIED = "denied"
    UNKNOWN = "unknown"


class CorrectiveActionExecutorOutcome(StrEnum):
    """Capability-neutral executor operational outcomes."""

    COMPLETED = "completed"
    FAILED_INVALID_REQUEST = "failed_invalid_request"
    FAILED_UNSUPPORTED_PLAN = "failed_unsupported_plan"
    FAILED_PRECONDITION = "failed_precondition"
    FAILED_AUTHORIZATION = "failed_authorization"
    FAILED_INTERNAL = "failed_internal"


class CorrectiveActionExecutionStatus(StrEnum):
    """Small synchronous executor-result status taxonomy."""

    NOT_STARTED = "not_started"
    COMPLETED = "completed"
    FAILED = "failed"


class CorrectiveActionExecutionDispatchDiagnosticCode(StrEnum):
    """Stable dispatch and generic executor diagnostic codes."""

    INVALID_DISPATCH_REQUEST = "invalid_dispatch_request"
    INVALID_DISPATCH_POLICY = "invalid_dispatch_policy"
    UNSUPPORTED_DISPATCH_CONTRACT_VERSION = "unsupported_dispatch_contract_version"
    INVALID_PLANNING_RESULT = "invalid_planning_result"
    UNSUPPORTED_PLANNING_RESULT_VERSION = "unsupported_planning_result_version"
    PLANNING_RESULT_FINGERPRINT_MISMATCH = "planning_result_fingerprint_mismatch"
    PLAN_FINGERPRINT_MISMATCH = "plan_fingerprint_mismatch"
    PLAN_NOT_DISPATCHABLE = "plan_not_dispatchable"
    AUTOMATIC_DISPATCH_DISABLED = "automatic_dispatch_disabled"
    HUMAN_AUTHORIZATION_REQUIRED = "human_authorization_required"
    HUMAN_AUTHORIZATION_DENIED = "human_authorization_denied"
    REQUIRED_CAPABILITY_NONE = "required_capability_none"
    EXECUTOR_NOT_FOUND = "executor_not_found"
    AMBIGUOUS_EXECUTOR_MATCH = "ambiguous_executor_match"
    EXECUTOR_DESCRIPTOR_INVALID = "executor_descriptor_invalid"
    EXECUTOR_CONTRACT_VERSION_UNSUPPORTED = "executor_contract_version_unsupported"
    EXECUTOR_REQUEST_INVALID = "executor_request_invalid"
    EXECUTOR_RESULT_INVALID = "executor_result_invalid"
    EXECUTOR_INVOCATION_FAILED = "executor_invocation_failed"
    DISPATCH_INTERNAL_FAILURE = "dispatch_internal_failure"


class CorrectiveActionExecutionDispatchDiagnosticCategory(StrEnum):
    """Content-safe diagnostic classification."""

    VALIDATION = "validation"
    POLICY = "policy"
    ELIGIBILITY = "eligibility"
    AUTHORIZATION = "authorization"
    RESOLUTION = "resolution"
    EXECUTOR = "executor"
    INTERNAL = "internal"
