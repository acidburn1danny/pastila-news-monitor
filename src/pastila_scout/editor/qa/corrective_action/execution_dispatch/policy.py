"""Standard immutable M6C.6B dispatch policy construction."""

from .models import CorrectiveActionExecutionDispatchPolicy


def build_standard_corrective_action_execution_dispatch_policy() -> (
    CorrectiveActionExecutionDispatchPolicy
):
    """Return the deterministic standard dispatch-only policy."""

    return CorrectiveActionExecutionDispatchPolicy.build()
