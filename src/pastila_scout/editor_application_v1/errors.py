"""Fixed, content-free Editor application errors."""

from __future__ import annotations

from typing import NoReturn


class _EditorApplicationError(Exception):
    __slots__ = ()
    _message = ""

    def __init__(self) -> None:
        Exception.__init__(self, self._message)
        self.__suppress_context__ = True

    def __getattribute__(self, name: str):
        if name == "__dict__":
            raise AttributeError(name)
        return Exception.__getattribute__(self, name)

    def __setattr__(self, name: str, value: object) -> None:
        if name == "__suppress_context__":
            Exception.__setattr__(self, name, value)
            return
        raise AttributeError("Editor application errors are immutable")

    def __repr__(self) -> str:
        return f"{type(self).__name__}()"

    def __copy__(self):
        return type(self)()

    def __deepcopy__(self, memo: dict[int, object]):
        del memo
        return type(self)()

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("Editor application errors do not support pickle")


class EditorApplicationConfigurationError(_EditorApplicationError):
    """Raised when application-owned configuration is invalid."""

    __slots__ = ()
    _message = "Editor application configuration is invalid."


class EditorApplicationCoordinatorError(_EditorApplicationError):
    """Raised for an unenumerated application coordinator defect."""

    __slots__ = ()
    _message = "Editor application coordinator failed."


class EditorApplicationSerializationError(_EditorApplicationError):
    """Raised when an operational result cannot be serialized."""

    __slots__ = ()
    _message = "Editor operational result serialization failed."


class EditorApplicationExportError(_EditorApplicationError):
    """Raised when application output cannot be exported."""

    __slots__ = ()
    _message = "Editor output export failed."


def raise_configuration_error() -> NoReturn:
    error = EditorApplicationConfigurationError()
    try:
        raise error from None
    except EditorApplicationConfigurationError as published:
        Exception.__setattr__(published, "__context__", None)
        raise


__all__ = (
    "EditorApplicationConfigurationError",
    "EditorApplicationCoordinatorError",
    "EditorApplicationExportError",
    "EditorApplicationSerializationError",
)
