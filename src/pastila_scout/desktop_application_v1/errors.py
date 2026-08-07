"""Safe public errors for the desktop application facade."""


class DesktopApplicationConfigurationError(ValueError):
    """Report an invalid facade value or injected dependency."""

    __slots__ = ()

    def __init__(self) -> None:
        super().__init__("Desktop application configuration is invalid.")


class DesktopApplicationExecutionError(RuntimeError):
    """Report a safely collapsed facade execution failure."""

    __slots__ = ()

    def __init__(self) -> None:
        super().__init__("Desktop application execution failed.")


__all__ = (
    "DesktopApplicationConfigurationError",
    "DesktopApplicationExecutionError",
)
