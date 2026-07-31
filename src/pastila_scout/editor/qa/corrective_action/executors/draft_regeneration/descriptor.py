"""The canonical future draft-regeneration executor descriptor."""

from pastila_scout.editor.qa.corrective_action.execution_dispatch import (
    CorrectiveActionExecutorDescriptor,
)
from pastila_scout.editor.qa.corrective_action.execution_plan import (
    CorrectiveActionExecutionCapability,
    CorrectiveActionExecutionPlanType,
)

EXECUTOR_ID = "draft-regeneration.v1"


def build_draft_regeneration_executor_descriptor() -> (
    CorrectiveActionExecutorDescriptor
):
    """Return the deterministic descriptor without constructing an executor."""

    return CorrectiveActionExecutorDescriptor.build(
        executor_id=EXECUTOR_ID,
        supported_capability=CorrectiveActionExecutionCapability.DRAFT_REGENERATION,
        supported_plan_types=(CorrectiveActionExecutionPlanType.REGENERATE_DRAFT,),
        supports_automatic_invocation=True,
        supports_human_gated_invocation=True,
    )
