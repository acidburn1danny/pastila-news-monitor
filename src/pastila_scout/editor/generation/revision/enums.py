"""Stable provider-neutral Controlled Revision taxonomies."""

from enum import StrEnum


class ControlledGenerationOperation(StrEnum):
    REVISION = "revision"


class RevisionTargetType(StrEnum):
    OPENING = "opening"
    STORY = "story"
    TRANSITION = "transition"
    CLOSING = "closing"
    CALL_TO_ACTION = "call_to_action"


class RevisionLifecyclePhase(StrEnum):
    CREATED = "created"
    VALIDATED = "validated"
    INVOKED = "invoked"
    GATEWAY_COMPLETED = "gateway_completed"
    OUTPUT_VALIDATED = "output_validated"
    COMPLETED = "completed"
    FAILED = "failed"


class RevisionResultStatus(StrEnum):
    SUCCESS = "success"
    REJECTED = "rejected"
    GATEWAY_FAILURE = "gateway_failure"
    CONTRACT_FAILURE = "contract_failure"


class RevisionGatewayStatus(StrEnum):
    SUCCESS = "success"
    FAILURE = "failure"
    UNSUPPORTED = "unsupported"


class RevisionDiagnosticCode(StrEnum):
    INVALID_REVISION_REQUEST = "invalid_revision_request"
    INVALID_SOURCE_DRAFT = "invalid_source_draft"
    INVALID_REVISION_TARGETS = "invalid_revision_targets"
    INVALID_REVISION_INSTRUCTIONS = "invalid_revision_instructions"
    INVALID_REVISION_POLICY = "invalid_revision_policy"
    INVALID_PRESERVATION_REQUIREMENTS = "invalid_preservation_requirements"
    INVALID_OUTPUT_CONTRACT = "invalid_output_contract"
    REVISION_OPERATION_UNSUPPORTED = "revision_operation_unsupported"
    REVISION_GATEWAY_FAILURE = "revision_gateway_failure"
    INVALID_REVISION_GATEWAY_RESULT = "invalid_revision_gateway_result"
    REVISION_LINEAGE_MISMATCH = "revision_lineage_mismatch"
    REVISION_OUTPUT_INVALID = "revision_output_invalid"
    REVISION_LIFECYCLE_INVALID = "revision_lifecycle_invalid"
