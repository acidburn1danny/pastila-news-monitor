"""Stable M6C.6D draft-revision taxonomies."""

from enum import StrEnum


class DraftRevisionTargetType(StrEnum):
    OPENING = "opening"
    STORY = "story"
    TRANSITION = "transition"
    CLOSING = "closing"
    CALL_TO_ACTION = "call_to_action"


class DraftRevisionOutcome(StrEnum):
    COMPLETED = "completed"
    FAILED_VALIDATION = "failed_validation"
    FAILED_CONTROLLED_REVISION = "failed_controlled_revision"
    FAILED_INVALID_RESULT = "failed_invalid_result"
    FAILED_INTERNAL = "failed_internal"


class DraftRevisionStatus(StrEnum):
    COMPLETED = "completed"
    FAILED = "failed"


class DraftRevisionDiagnosticCategory(StrEnum):
    VALIDATION = "validation"
    AUTHORIZATION = "authorization"
    REVISION = "revision"
    OUTPUT = "output"
    INTERNAL = "internal"


class DraftRevisionDiagnosticCode(StrEnum):
    INVALID_REVISION_REQUEST = "invalid_revision_request"
    INVALID_REVISION_POLICY = "invalid_revision_policy"
    INVALID_REVISION_SCOPE = "invalid_revision_scope"
    INVALID_REVISION_TARGET = "invalid_revision_target"
    INVALID_REVISION_INSTRUCTIONS = "invalid_revision_instructions"
    SOURCE_DRAFT_MISMATCH = "source_draft_mismatch"
    UNAUTHORIZED_REVISION = "unauthorized_revision"
    PROHIBITED_REVISION = "prohibited_revision"
    INVALID_REVISED_DRAFT = "invalid_revised_draft"
    SOURCE_DRAFT_REUSED = "source_draft_reused"
    REVISION_INTERNAL_FAILURE = "revision_internal_failure"
