"""Deterministic composition root for Controlled Revision runtime."""

from .gateway import ControlledRevisionGateway
from .runtime import (
    ControlledRevisionExecutionService,
    ControlledRevisionResultFactory,
    RevisedDraftValidator,
    RevisionLifecycleFactory,
    RevisionOutputContractValidator,
    RevisionPreservationValidator,
)
from .validation import (
    validate_controlled_revision_invocation,
    validate_controlled_revision_result,
    validate_revision_gateway_result,
)


def compose_controlled_revision_execution_service(
    gateway: ControlledRevisionGateway,
) -> ControlledRevisionExecutionService:
    """Compose one service with explicit canonical dependency instances."""

    lifecycle_factory = RevisionLifecycleFactory()
    result_factory = ControlledRevisionResultFactory(lifecycle_factory)
    return ControlledRevisionExecutionService(
        gateway=gateway,
        invocation_validator=validate_controlled_revision_invocation,
        gateway_result_validator=validate_revision_gateway_result,
        revised_draft_validator=RevisedDraftValidator(),
        output_contract_validator=RevisionOutputContractValidator(),
        preservation_validator=RevisionPreservationValidator(),
        result_factory=result_factory,
        result_validator=validate_controlled_revision_result,
    )
