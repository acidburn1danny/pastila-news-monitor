"""Closed provider-neutral vocabularies for Module 2.9 Phase 3."""

from enum import StrEnum


class GenerationOperation(StrEnum):
    INITIAL_GENERATION = "initial_generation"
    SCOPED_REGENERATION = "scoped_regeneration"
    REVISION_GENERATION = "revision_generation"
    VALIDATION_SUPPORT_GENERATION = "validation_support_generation"


class GenerationOutputScope(StrEnum):
    EPISODE = "episode"
    SEGMENT = "segment"
    BEAT = "beat"
    REVISION_TARGET = "revision_target"


class GenerationCapability(StrEnum):
    STRUCTURED_OUTPUT = "structured_output"
    LONG_CONTEXT = "long_context"
    INSTRUCTION_FOLLOWING = "instruction_following"
    CITATION_PRESERVATION = "citation_preservation"
    DETERMINISTIC_SEED_SUPPORT = "deterministic_seed_support"
    TOOL_FREE_GENERATION = "tool_free_generation"
    REVISION_SUPPORT = "revision_support"
    MULTILINGUAL_GENERATION = "multilingual_generation"
    CONSTRAINED_OUTPUT = "constrained_output"
    PARTIAL_REGENERATION = "partial_regeneration"
    CUSTOM = "custom"


class GenerationOutputBindingType(StrEnum):
    GENERATED_TEXT_UNIT = "generated_text_unit"
    GENERATED_SECTION = "generated_section"
    GENERATED_CLAIM_CANDIDATE = "generated_claim_candidate"
    GENERATED_REVISION_CANDIDATE = "generated_revision_candidate"
    STRUCTURED_GENERATION_PAYLOAD = "structured_generation_payload"


class OutputCardinality(StrEnum):
    ONE = "one"
    ONE_OR_MORE = "one_or_more"
    ZERO_OR_ONE = "zero_or_one"


class GenerationExecutionState(StrEnum):
    PLANNED = "planned"
    ELIGIBLE = "eligible"
    BLOCKED = "blocked"
    SUBMITTED = "submitted"
    ACCEPTED = "accepted"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    PARTIALLY_SUCCEEDED = "partially_succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"


class GenerationOutcomeStatus(StrEnum):
    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"


class GenerationExecutionFailureType(StrEnum):
    INVALID_REQUEST = "invalid_request"
    INCOMPATIBLE_INPUT = "incompatible_input"
    BLOCKED_BY_POLICY = "blocked_by_policy"
    BLOCKED_BY_AUTHORITY_CONFLICT = "blocked_by_authority_conflict"
    UNSUPPORTED_CAPABILITY = "unsupported_capability"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    EXECUTION_REJECTED = "execution_rejected"
    EXECUTION_TIMEOUT = "execution_timeout"
    MALFORMED_OUTPUT = "malformed_output"
    INCOMPLETE_OUTPUT = "incomplete_output"
    OUTPUT_BINDING_FAILURE = "output_binding_failure"
    CANCELLED = "cancelled"
    SUPERSEDED = "superseded"
    UNKNOWN_EXTERNAL_FAILURE = "unknown_external_failure"


class RetryScope(StrEnum):
    UNIT = "unit"
    FAILED_BINDINGS = "failed_bindings"
    PLAN = "plan"


class RetryBackoffClassification(StrEnum):
    IMMEDIATE = "immediate"
    DEFERRED = "deferred"
    EXTERNAL_SCHEDULER = "external_scheduler"


class FailurePropagationMode(StrEnum):
    FAIL_PLAN = "fail_plan"
    BLOCK_DEPENDENTS = "block_dependents"
    ALLOW_INDEPENDENT_UNITS = "allow_independent_units"
    RETAIN_PARTIAL_OUTPUTS = "retain_partial_outputs"


__all__ = (
    "FailurePropagationMode",
    "GenerationCapability",
    "GenerationExecutionFailureType",
    "GenerationExecutionState",
    "GenerationOperation",
    "GenerationOutcomeStatus",
    "GenerationOutputBindingType",
    "GenerationOutputScope",
    "OutputCardinality",
    "RetryBackoffClassification",
    "RetryScope",
)
