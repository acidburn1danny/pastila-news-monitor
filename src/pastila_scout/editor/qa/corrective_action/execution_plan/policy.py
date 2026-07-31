"""Standard M6C.6A execution-planning policy construction."""

from .models import CorrectiveActionExecutionPlanPolicy


def build_standard_corrective_action_execution_plan_policy() -> (
    CorrectiveActionExecutionPlanPolicy
):
    """Return the deterministic standard planning policy."""

    return CorrectiveActionExecutionPlanPolicy.build()
