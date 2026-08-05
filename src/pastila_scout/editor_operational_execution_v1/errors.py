"""Safe public errors for Editor operational execution composition."""


class EditorOperationalExecutionConfigurationError(Exception):
    """Raised when the operational coordinator cannot be configured safely."""


__all__ = ("EditorOperationalExecutionConfigurationError",)
