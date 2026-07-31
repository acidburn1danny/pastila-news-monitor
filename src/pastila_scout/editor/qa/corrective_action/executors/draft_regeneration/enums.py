"""Stable M6C.6C draft-regeneration taxonomies."""

from enum import StrEnum


class DraftRegenerationOutcome(StrEnum):
    COMPLETED = "completed"
    FAILED_INVALID_EXECUTOR_REQUEST = "failed_invalid_executor_request"
    FAILED_UNSUPPORTED_CONTRACT = "failed_unsupported_contract"
    FAILED_PLAN_MISMATCH = "failed_plan_mismatch"
    FAILED_CAPABILITY_MISMATCH = "failed_capability_mismatch"
    FAILED_EXECUTION_MODE = "failed_execution_mode"
    FAILED_AUTHORIZATION = "failed_authorization"
    FAILED_PRECONDITION = "failed_precondition"
    FAILED_INPUT_VALIDATION = "failed_input_validation"
    FAILED_GENERATION_CONTRACT = "failed_generation_contract"
    FAILED_OUTPUT_VALIDATION = "failed_output_validation"
    FAILED_INTERNAL = "failed_internal"


class DraftRegenerationStatus(StrEnum):
    NOT_STARTED = "not_started"
    READY = "ready"
    COMPLETED = "completed"
    FAILED = "failed"


class DraftRegenerationPreconditionCode(StrEnum):
    SOURCE_INPUT_AVAILABLE = "source_input_available"
    GENERATION_POLICY_AVAILABLE = "generation_policy_available"
    CONTROLLED_GENERATION_CONTRACT_SUPPORTED = (
        "controlled_generation_contract_supported"
    )
    EXECUTOR_REQUEST_INTEGRITY_VALID = "executor_request_integrity_valid"
    PLAN_LINEAGE_VALID = "plan_lineage_valid"
    AUTHORIZATION_VALID = "authorization_valid"


class DraftRegenerationDiagnosticCategory(StrEnum):
    VALIDATION = "validation"
    PLAN = "plan"
    AUTHORIZATION = "authorization"
    INPUT = "input"
    PRECONDITION = "precondition"
    GENERATION = "generation"
    OUTPUT = "output"
    INTERNAL = "internal"


class DraftRegenerationDiagnosticCode(StrEnum):
    INVALID_REGENERATION_POLICY = "invalid_regeneration_policy"
    INVALID_REGENERATION_REQUEST = "invalid_regeneration_request"
    UNSUPPORTED_REGENERATION_CONTRACT_VERSION = (
        "unsupported_regeneration_contract_version"
    )
    INVALID_EXECUTOR_REQUEST = "invalid_executor_request"
    EXECUTOR_REQUEST_FINGERPRINT_MISMATCH = "executor_request_fingerprint_mismatch"
    PLANNING_RESULT_FINGERPRINT_MISMATCH = "planning_result_fingerprint_mismatch"
    PLAN_FINGERPRINT_MISMATCH = "plan_fingerprint_mismatch"
    PLAN_TYPE_NOT_REGENERATE_DRAFT = "plan_type_not_regenerate_draft"
    CAPABILITY_NOT_DRAFT_REGENERATION = "capability_not_draft_regeneration"
    EXECUTION_MODE_NOT_SUPPORTED = "execution_mode_not_supported"
    AUTHORIZATION_REQUIRED = "authorization_required"
    AUTHORIZATION_DENIED = "authorization_denied"
    SOURCE_INPUT_MISSING = "source_input_missing"
    GENERATION_INPUT_INVALID = "generation_input_invalid"
    GENERATION_POLICY_INVALID = "generation_policy_invalid"
    PRECONDITION_NOT_SATISFIED = "precondition_not_satisfied"
    CONTROLLED_GENERATION_RESULT_INVALID = "controlled_generation_result_invalid"
    REGENERATED_DRAFT_MISSING = "regenerated_draft_missing"
    REGENERATED_DRAFT_IDENTITY_REUSED = "regenerated_draft_identity_reused"
    REGENERATED_DRAFT_FINGERPRINT_MISMATCH = "regenerated_draft_fingerprint_mismatch"
    OUTPUT_REFERENCE_INVALID = "output_reference_invalid"
    REGENERATION_INTERNAL_FAILURE = "regeneration_internal_failure"
    REGENERATION_INPUT_RESOLUTION_FAILED = "regeneration_input_resolution_failed"
    CONTROLLED_GENERATION_REQUEST_PROJECTION_FAILED = (
        "controlled_generation_request_projection_failed"
    )
    PRECONDITION_EVALUATION_INVALID = "precondition_evaluation_invalid"
    PREPARATION_LIFECYCLE_INVALID = "preparation_lifecycle_invalid"


class DraftRegenerationPreparationOutcome(StrEnum):
    COMPLETED = "completed"
    FAILED_INVALID_EXECUTOR_REQUEST = "failed_invalid_executor_request"
    FAILED_PLAN_MISMATCH = "failed_plan_mismatch"
    FAILED_CAPABILITY_MISMATCH = "failed_capability_mismatch"
    FAILED_EXECUTION_MODE = "failed_execution_mode"
    FAILED_AUTHORIZATION = "failed_authorization"
    FAILED_POLICY_VALIDATION = "failed_policy_validation"
    FAILED_INPUT_RESOLUTION = "failed_input_resolution"
    FAILED_PRECONDITION = "failed_precondition"
    FAILED_CONTROLLED_GENERATION_REQUEST = "failed_controlled_generation_request"
    FAILED_INTEGRITY = "failed_integrity"
    FAILED_INTERNAL = "failed_internal"


class DraftRegenerationPreparationStatus(StrEnum):
    PREPARED = "prepared"
    FAILED = "failed"


class DraftRegenerationPreconditionStatus(StrEnum):
    SATISFIED = "satisfied"
    NOT_SATISFIED = "not_satisfied"
    INVALID = "invalid"


class DraftRegenerationPreparationPhase(StrEnum):
    RECEIVED = "received"
    VALIDATING_EXECUTOR_REQUEST = "validating_executor_request"
    RESOLVING_INPUT = "resolving_input"
    BUILDING_REGENERATION_REQUEST = "building_regeneration_request"
    PROJECTING_GENERATION_REQUEST = "projecting_generation_request"
    EVALUATING_PRECONDITIONS = "evaluating_preconditions"
    PREPARED = "prepared"
    FAILED = "failed"
