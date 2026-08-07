"""Safe private Windows-state failures."""

from typing import NoReturn


class _WindowsStateError(Exception):
    """Base class for safe state failures."""

    _message = "Windows application state is unavailable."

    def __init__(self) -> None:
        super().__init__(self._message)

    def __init_subclass__(cls, **kwargs) -> None:
        if cls.__module__ == __name__ and cls.__name__ in {
            "_WindowsStatePathError",
            "_WindowsStateSettingsError",
            "_WindowsStateMigrationError",
        }:
            return super().__init_subclass__(**kwargs)
        del cls, kwargs
        raise TypeError("Windows state errors cannot be subclassed")


class _WindowsStatePathError(_WindowsStateError):
    _message = "Windows application paths are unavailable."

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Windows state path errors cannot be subclassed")


class _WindowsStateSettingsError(_WindowsStateError):
    _message = "Windows application settings are invalid."

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Windows state settings errors cannot be subclassed")


class _WindowsStateMigrationError(_WindowsStateError):
    _message = "Windows application state migration failed."

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Windows state migration errors cannot be subclassed")


__all__: tuple[str, ...] = ()
