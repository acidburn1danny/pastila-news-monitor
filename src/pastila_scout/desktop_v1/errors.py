"""Safe private errors for the structural desktop shell."""


class _DesktopShellConfigurationError(Exception):
    __slots__ = ()

    def __init__(self) -> None:
        super().__init__("")

    def __init_subclass__(cls, **kwargs: object) -> None:
        del cls, kwargs
        raise TypeError("Desktop shell errors are final")


class _DesktopShellExecutionError(Exception):
    __slots__ = ()

    def __init__(self) -> None:
        super().__init__("")

    def __init_subclass__(cls, **kwargs: object) -> None:
        del cls, kwargs
        raise TypeError("Desktop shell errors are final")
