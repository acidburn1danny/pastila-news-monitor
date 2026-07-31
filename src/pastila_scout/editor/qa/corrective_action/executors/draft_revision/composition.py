"""Object-only composition for the Draft Revision v2 execution lane."""

from pastila_scout.editor.qa.corrective_action.execution_dispatch.v2_runtime import (
    CorrectiveActionExecutionDispatcherV2,
    CorrectiveActionV2Binding,
)
from pastila_scout.editor.qa.corrective_action.execution_plan import (
    CorrectiveActionExecutionCapability,
)
from pastila_scout.editor.qa.corrective_action.models import CorrectiveAction

from .integration import DraftRevisionCorrectiveActionExecutor


def compose_draft_revision_execution_dispatcher(
    *, preparation_service, draft_revision_executor
) -> CorrectiveActionExecutionDispatcherV2:
    """Bind injected frozen services explicitly without provider knowledge."""

    integration = DraftRevisionCorrectiveActionExecutor(
        preparation_service=preparation_service, executor=draft_revision_executor
    )
    return CorrectiveActionExecutionDispatcherV2(
        (
            CorrectiveActionV2Binding(
                capability=CorrectiveActionExecutionCapability.DRAFT_REVISION,
                action=CorrectiveAction.REQUEST_REVISION,
                integration=integration,
            ),
        )
    )
