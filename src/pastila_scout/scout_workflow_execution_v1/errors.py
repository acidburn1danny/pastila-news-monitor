"""Application-owned errors for the Scout workflow execution boundary."""


class ScoutWorkflowExecutionError(RuntimeError):
    """Reject an invalid workflow composition or execution dependency."""


__all__ = ("ScoutWorkflowExecutionError",)
