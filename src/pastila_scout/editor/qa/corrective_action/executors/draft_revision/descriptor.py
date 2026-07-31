"""Canonical M6C.6D draft-revision descriptor."""

from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    CorrectiveActionExecutorDescriptor,
)
from pastila_scout.editor.qa.corrective_action.execution_plan import (
    CorrectiveActionExecutionCapability,
    CorrectiveActionExecutionPlanType,
)

EXECUTOR_ID = "revise-draft.v1"


def build_draft_revision_executor_descriptor() -> CorrectiveActionExecutorDescriptor:
    return CorrectiveActionExecutorDescriptor.build(
        executor_id=EXECUTOR_ID,
        supported_capability=CorrectiveActionExecutionCapability.DRAFT_REVISION,
        supported_plan_types=(CorrectiveActionExecutionPlanType.REVISE_DRAFT,),
        supports_automatic_invocation=True,
        supports_human_gated_invocation=True,
    )
