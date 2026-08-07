"""Private failures for desktop application composition."""

from __future__ import annotations

from typing import NoReturn


class _DesktopApplicationCompositionErrorV1(RuntimeError):
    __slots__ = ()

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Desktop application composition errors cannot be subclassed")

    def __init__(self) -> None:
        super().__init__("Desktop application composition failed.")

    def __copy__(self) -> NoReturn:
        raise TypeError("Desktop application composition errors cannot be copied")

    def __deepcopy__(self, memo: dict[int, object]) -> NoReturn:
        del memo
        raise TypeError("Desktop application composition errors cannot be copied")

    def __reduce__(self) -> NoReturn:
        raise TypeError("Desktop application composition errors do not support pickle")

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del protocol
        raise TypeError("Desktop application composition errors do not support pickle")


__all__: tuple[str, ...] = ()
