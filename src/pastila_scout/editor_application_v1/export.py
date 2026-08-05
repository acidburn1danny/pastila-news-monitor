"""Race-safe, no-replace publication of canonical Editor payload bytes."""

from __future__ import annotations

import ctypes
import errno
import os
import stat
import sys
import tempfile
from enum import Enum, auto
from pathlib import Path
from typing import NoReturn

from .errors import EditorApplicationExportError
from .models import (
    EditorOutputDestinationV1,
    EditorOverwritePolicyV1,
    reconstruct_output_destination,
)

_PATH_TYPE = type(Path())
_FILE_ATTRIBUTE_REPARSE_POINT = 0x400
_MOVEFILE_WRITE_THROUGH = 0x8
_AT_FDCWD = -100
_RENAME_NOREPLACE = 1
_RENAME_EXCL = 0x4


class _ExportStatusV1(Enum):
    INVALID_PAYLOAD = auto()
    INVALID_DESTINATION = auto()
    UNSUPPORTED_PLATFORM = auto()
    UNSUPPORTED_NATIVE_PRIMITIVE = auto()
    UNSUPPORTED_FILESYSTEM = auto()
    INVALID_PARENT = auto()
    DESTINATION_EXISTS = auto()
    DESTINATION_INVALID = auto()
    TEMP_NAME_EXHAUSTED = auto()
    TEMP_CREATION_FAILED = auto()
    TEMP_IDENTITY_FAILED = auto()
    WRITE_FAILED = auto()
    SHORT_WRITE = auto()
    FLUSH_FAILED = auto()
    SYNC_FAILED = auto()
    CLOSE_FAILED = auto()
    PREPUBLICATION_FAILED = auto()
    DESTINATION_RACE = auto()
    NATIVE_PUBLICATION_FAILED = auto()
    CLEANUP_FAILED = auto()
    EXPORT_CORRUPTION = auto()


class _NoReplaceAtomicPublisherV1:
    """Package-private native no-replace publication adapter."""

    __slots__ = ()

    @staticmethod
    def supported() -> bool:
        try:
            if sys.platform == "win32":
                return bool(ctypes.WinDLL("kernel32", use_last_error=True).MoveFileExW)
            if sys.platform == "linux":
                return bool(ctypes.CDLL(None, use_errno=True).renameat2)
            if sys.platform == "darwin":
                return bool(ctypes.CDLL(None, use_errno=True).renamex_np)
            return False
        except Exception:  # noqa: BLE001 - capability probing fails closed
            return False

    @staticmethod
    def publish_existing(source: Path, destination: Path) -> _ExportStatusV1 | None:
        if sys.platform == "win32":
            return _publish_windows(source, destination)
        if sys.platform == "linux":
            return _publish_linux(source, destination)
        if sys.platform == "darwin":
            return _publish_macos(source, destination)
        return _ExportStatusV1.UNSUPPORTED_PLATFORM


class EditorAtomicExporterV1:
    """Publish one opaque canonical payload without replacing a destination."""

    __slots__ = ()

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Editor atomic exporters cannot be subclassed")

    def __repr__(self) -> str:
        return "EditorAtomicExporterV1()"

    def __eq__(self, other: object) -> bool:
        return type(other) is type(self)

    def __copy__(self) -> EditorAtomicExporterV1:
        return type(self)()

    def __deepcopy__(self, memo: dict[int, object]) -> EditorAtomicExporterV1:
        del memo
        return type(self)()

    def __reduce_ex__(self, protocol: int) -> NoReturn:
        del self, protocol
        raise TypeError("EditorAtomicExporterV1 does not support pickle")

    def publish(
        self,
        *,
        payload: bytes,
        destination: EditorOutputDestinationV1,
    ) -> Path:
        status, published = _publish_neutral(payload, destination)
        del self, payload, destination
        if status is not None:
            del status, published
            _raise_export_error()
        return published


def _publish_neutral(
    payload: object, destination: object
) -> tuple[_ExportStatusV1 | None, Path | None]:
    valid_destination = parent = target = temp_path = None
    parent_identity = temp_identity = None
    fd = None
    published = False
    status = None
    try:
        if type(payload) is not bytes or not payload or not payload.endswith(b"\n"):
            status = _ExportStatusV1.INVALID_PAYLOAD
        else:
            try:
                valid_destination = reconstruct_output_destination(destination)
            except Exception:  # noqa: BLE001 - frozen authority collapses here
                status = _ExportStatusV1.INVALID_DESTINATION
        if status is None:
            target = valid_destination.path
            if (
                type(target) is not _PATH_TYPE
                or valid_destination.overwrite_policy
                is not EditorOverwritePolicyV1.FAIL_IF_EXISTS
            ):
                status = _ExportStatusV1.INVALID_DESTINATION
        if status is None and not _NoReplaceAtomicPublisherV1.supported():
            status = _ExportStatusV1.UNSUPPORTED_PLATFORM
        if status is None:
            parent = target.parent
            parent_stat = _safe_lstat(parent)
            if (
                parent_stat is None
                or not stat.S_ISDIR(parent_stat.st_mode)
                or _is_reparse(parent_stat)
            ):
                status = _ExportStatusV1.INVALID_PARENT
            else:
                parent_identity = (parent_stat.st_dev, parent_stat.st_ino)
        if status is None:
            destination_stat = _safe_lstat(target)
            if destination_stat is not None:
                status = (
                    _ExportStatusV1.DESTINATION_INVALID
                    if stat.S_ISDIR(destination_stat.st_mode)
                    or stat.S_ISLNK(destination_stat.st_mode)
                    or _is_reparse(destination_stat)
                    else _ExportStatusV1.DESTINATION_EXISTS
                )
        if status is None:
            try:
                fd, raw_temp = tempfile.mkstemp(
                    prefix=".pastila-editor-", suffix=".tmp", dir=parent
                )
                temp_path = Path(raw_temp)
                os.set_inheritable(fd, False)
                opened = os.fstat(fd)
                named = os.lstat(temp_path)
                if (
                    not stat.S_ISREG(opened.st_mode)
                    or (opened.st_dev, opened.st_ino) != (named.st_dev, named.st_ino)
                    or temp_path.parent != parent
                ):
                    status = _ExportStatusV1.TEMP_IDENTITY_FAILED
                else:
                    temp_identity = (opened.st_dev, opened.st_ino)
            except Exception:  # noqa: BLE001 - reduced to a finite status
                status = _ExportStatusV1.TEMP_CREATION_FAILED
        if status is None:
            status = _write_and_sync(fd, payload)
        if fd is not None:
            try:
                os.close(fd)
            except Exception:  # noqa: BLE001 - reduced to a finite status
                if status is None:
                    status = _ExportStatusV1.CLOSE_FAILED
            fd = None
        if status is None:
            status = _revalidate(
                parent, target, temp_path, parent_identity, temp_identity
            )
        if status is None:
            status = _NoReplaceAtomicPublisherV1.publish_existing(temp_path, target)
            published = status is None
        if (
            status is not None
            and temp_path is not None
            and not published
            and not _cleanup_temp(temp_path, temp_identity)
        ):
            status = _ExportStatusV1.CLEANUP_FAILED
        result = target if published else None
    except Exception:  # noqa: BLE001 - unexpected defects fail closed
        if fd is not None:
            try:
                os.close(fd)
            except Exception:  # noqa: BLE001, S110 - best-effort close
                pass
            fd = None
        if temp_path is not None and not published:
            status = (
                status
                if _cleanup_temp(temp_path, temp_identity)
                else _ExportStatusV1.CLEANUP_FAILED
            )
        if status is None:
            status = _ExportStatusV1.PREPUBLICATION_FAILED
        result = None
    del payload, destination, valid_destination, parent, target, temp_path
    del parent_identity, temp_identity, fd, published
    return status, result


def _safe_lstat(path: Path):
    try:
        return os.lstat(path)
    except FileNotFoundError:
        return None


def _is_reparse(value: os.stat_result) -> bool:
    return bool(getattr(value, "st_file_attributes", 0) & _FILE_ATTRIBUTE_REPARSE_POINT)


def _write_and_sync(fd: int, payload: bytes) -> _ExportStatusV1 | None:
    view = memoryview(payload)
    offset = 0
    try:
        while offset < len(view):
            written = os.write(fd, view[offset:])
            if type(written) is not int or written <= 0 or written > len(view) - offset:
                return _ExportStatusV1.SHORT_WRITE
            offset += written
        os.fsync(fd)
        return None
    except OSError:
        return (
            _ExportStatusV1.WRITE_FAILED
            if offset < len(view)
            else _ExportStatusV1.SYNC_FAILED
        )
    finally:
        view.release()


def _revalidate(parent, target, temp_path, parent_identity, temp_identity):
    try:
        current_parent = os.lstat(parent)
        current_temp = os.lstat(temp_path)
        if (
            not stat.S_ISDIR(current_parent.st_mode)
            or _is_reparse(current_parent)
            or (current_parent.st_dev, current_parent.st_ino) != parent_identity
        ):
            return _ExportStatusV1.PREPUBLICATION_FAILED
        if _safe_lstat(target) is not None:
            return _ExportStatusV1.DESTINATION_RACE
        if (
            not stat.S_ISREG(current_temp.st_mode)
            or _is_reparse(current_temp)
            or (current_temp.st_dev, current_temp.st_ino) != temp_identity
            or current_temp.st_dev != current_parent.st_dev
        ):
            return _ExportStatusV1.TEMP_IDENTITY_FAILED
        return None
    except OSError:
        return _ExportStatusV1.PREPUBLICATION_FAILED


def _cleanup_temp(temp_path: Path, temp_identity) -> bool:
    try:
        current = os.lstat(temp_path)
        if (
            temp_identity is not None
            and (current.st_dev, current.st_ino) != temp_identity
        ):
            return False
        os.unlink(temp_path)
        return True
    except FileNotFoundError:
        return True
    except Exception:  # noqa: BLE001 - cleanup must be one finite attempt
        return False


def _publish_windows(source: Path, destination: Path) -> _ExportStatusV1 | None:
    try:
        function = ctypes.WinDLL("kernel32", use_last_error=True).MoveFileExW
        function.argtypes = (ctypes.c_wchar_p, ctypes.c_wchar_p, ctypes.c_uint32)
        function.restype = ctypes.c_int
        if function(str(source), str(destination), _MOVEFILE_WRITE_THROUGH):
            return None
        code = ctypes.get_last_error()
        if code in {80, 183}:
            return _ExportStatusV1.DESTINATION_RACE
        return _ExportStatusV1.NATIVE_PUBLICATION_FAILED
    except Exception:  # noqa: BLE001 - native details remain private
        return _ExportStatusV1.NATIVE_PUBLICATION_FAILED


def _publish_linux(source: Path, destination: Path) -> _ExportStatusV1 | None:
    try:
        library = ctypes.CDLL(None, use_errno=True)
        function = library.renameat2
        function.argtypes = (
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        )
        function.restype = ctypes.c_int
        result = function(
            _AT_FDCWD,
            os.fsencode(source),
            _AT_FDCWD,
            os.fsencode(destination),
            _RENAME_NOREPLACE,
        )
        if result == 0:
            return None
        if ctypes.get_errno() == errno.EEXIST:
            return _ExportStatusV1.DESTINATION_RACE
        return _ExportStatusV1.NATIVE_PUBLICATION_FAILED
    except Exception:  # noqa: BLE001 - absent syscall fails closed
        return _ExportStatusV1.NATIVE_PUBLICATION_FAILED


def _publish_macos(source: Path, destination: Path) -> _ExportStatusV1 | None:
    try:
        library = ctypes.CDLL(None, use_errno=True)
        function = library.renamex_np
        function.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint)
        function.restype = ctypes.c_int
        result = function(os.fsencode(source), os.fsencode(destination), _RENAME_EXCL)
        if result == 0:
            return None
        if ctypes.get_errno() == errno.EEXIST:
            return _ExportStatusV1.DESTINATION_RACE
        return _ExportStatusV1.NATIVE_PUBLICATION_FAILED
    except Exception:  # noqa: BLE001 - absent symbol fails closed
        return _ExportStatusV1.NATIVE_PUBLICATION_FAILED


def _raise_export_error() -> NoReturn:
    error = EditorApplicationExportError()
    try:
        raise error from None
    except EditorApplicationExportError as published:
        Exception.__setattr__(published, "__context__", None)
        raise


__all__ = ("EditorAtomicExporterV1",)
