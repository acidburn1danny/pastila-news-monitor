"""Safe errors for immutable Editor generation execution requests."""


class EditorGenerationExecutionRequestError(Exception):
    """Raised when an execution request is invalid or copied-invalid."""


__all__ = ("EditorGenerationExecutionRequestError",)
