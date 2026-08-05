"""Safe application-owned errors for deterministic Editor preparation."""

CONFIGURATION_ERROR_MESSAGE = "Editor operational configuration is invalid."


class EditorOperationalConfigurationError(Exception):
    """Reject an invalid operational composition without retaining authority."""

    def __init__(self) -> None:
        super().__init__(CONFIGURATION_ERROR_MESSAGE)


__all__ = ("EditorOperationalConfigurationError",)
