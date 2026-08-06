from __future__ import annotations

import copy
import hashlib
import inspect
import os
import pickle
import subprocess
import sys
from pathlib import Path

import pytest

import pastila_scout.editor_application_v1 as public
import pastila_scout.editor_application_v1.export as implementation
from pastila_scout.editor_application_v1 import (
    EditorApplicationExportError,
    EditorAtomicExporterV1,
    EditorOutputDestinationV1,
    EditorOverwritePolicyV1,
)


def destination(path: Path) -> EditorOutputDestinationV1:
    return EditorOutputDestinationV1(path, EditorOverwritePolicyV1.FAIL_IF_EXISTS)


def install_local_no_replace(monkeypatch: pytest.MonkeyPatch, calls: list[str]) -> None:
    def publish(source: Path, target: Path):
        calls.append("publish")
        try:
            os.link(source, target)
        except FileExistsError:
            return implementation._ExportStatusV1.DESTINATION_RACE
        os.unlink(source)
        return None

    monkeypatch.setattr(
        implementation._NoReplaceAtomicPublisherV1,
        "publish_existing",
        staticmethod(publish),
    )
    monkeypatch.setattr(
        implementation._NoReplaceAtomicPublisherV1,
        "supported",
        staticmethod(lambda: True),
    )


def test_exact_public_api_position_identity_and_signature() -> None:
    assert public.__all__[12:18] == (
        "EditorApplicationStatusV1",
        "EditorAtomicExporterV1",
        "EditorEpisodeContextAuthorityV1",
        "EditorOperationalResultSerializerV1",
        "EditorSerializedOperationalResultV1",
        "EditorOutputDestinationV1",
    )
    assert public.EditorAtomicExporterV1 is EditorAtomicExporterV1
    assert implementation.__all__ == ("EditorAtomicExporterV1",)
    signature = inspect.signature(EditorAtomicExporterV1.publish)
    assert tuple(signature.parameters) == ("self", "payload", "destination")
    assert signature.parameters["payload"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["destination"].kind is inspect.Parameter.KEYWORD_ONLY
    assert signature.parameters["payload"].annotation == "bytes"
    assert signature.parameters["destination"].annotation == (
        "EditorOutputDestinationV1"
    )
    assert signature.return_annotation == "Path"


def test_object_contract_is_stateless_safe_and_unpickleable() -> None:
    value = EditorAtomicExporterV1()
    assert not hasattr(value, "__dict__")
    assert repr(value) == "EditorAtomicExporterV1()"
    assert value == EditorAtomicExporterV1()
    assert copy.copy(value) == value
    assert copy.deepcopy(value) == value
    with pytest.raises(TypeError, match="does not support pickle"):
        pickle.dumps(value)
    with pytest.raises(TypeError, match="cannot be subclassed"):
        type("InvalidExporter", (EditorAtomicExporterV1,), {})


@pytest.mark.parametrize(
    "payload",
    [None, "{}\n", bytearray(b"{}\n"), memoryview(b"{}\n"), b"", b"{}"],
)
def test_invalid_payload_fails_before_temp_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, payload: object
) -> None:
    calls = 0

    def forbidden(*args, **kwargs):
        nonlocal calls
        del args, kwargs
        calls += 1
        raise AssertionError

    monkeypatch.setattr(implementation.tempfile, "mkstemp", forbidden)
    with pytest.raises(EditorApplicationExportError) as captured:
        EditorAtomicExporterV1().publish(
            payload=payload, destination=destination(tmp_path / "result.json")
        )
    assert calls == 0
    assert str(captured.value) == "Editor output export failed."
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None
    assert captured.value.__suppress_context__ is True


def test_bytes_subclass_is_rejected(tmp_path: Path) -> None:
    class BytesSubclass(bytes):
        pass

    with pytest.raises(EditorApplicationExportError):
        EditorAtomicExporterV1().publish(
            payload=BytesSubclass(b"{}\n"),
            destination=destination(tmp_path / "result.json"),
        )


def test_destination_is_authoritatively_reconstructed_before_io(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    value = destination(tmp_path / "result.json")
    object.__setattr__(value, "path", tmp_path / "changed.json")
    calls = 0

    def forbidden(*args, **kwargs):
        nonlocal calls
        del args, kwargs
        calls += 1

    monkeypatch.setattr(implementation.tempfile, "mkstemp", forbidden)
    with pytest.raises(EditorApplicationExportError):
        EditorAtomicExporterV1().publish(payload=b"{}\n", destination=value)
    assert calls == 0


def test_wrong_destination_type_is_rejected_without_io(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        implementation.tempfile,
        "mkstemp",
        lambda *args, **kwargs: pytest.fail("temporary file was created"),
    )
    with pytest.raises(EditorApplicationExportError):
        EditorAtomicExporterV1().publish(  # type: ignore[arg-type]
            payload=b"{}\n", destination=tmp_path / "result.json"
        )


@pytest.mark.parametrize("parent_kind", ["missing", "file"])
def test_invalid_parent_creates_no_temp(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    parent_kind: str,
) -> None:
    parent = tmp_path / "parent"
    if parent_kind == "file":
        parent.write_bytes(b"sentinel")
    calls = 0

    def forbidden(*args, **kwargs):
        nonlocal calls
        del args, kwargs
        calls += 1
        raise AssertionError

    monkeypatch.setattr(implementation.tempfile, "mkstemp", forbidden)
    with pytest.raises(EditorApplicationExportError):
        EditorAtomicExporterV1().publish(
            payload=b"{}\n", destination=destination(parent / "result.json")
        )
    assert calls == 0


def test_existing_destination_is_never_changed_and_creates_no_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "result.json"
    target.write_bytes(b"sentinel")
    monkeypatch.setattr(
        implementation.tempfile,
        "mkstemp",
        lambda *args, **kwargs: pytest.fail("temporary file was created"),
    )
    with pytest.raises(EditorApplicationExportError):
        EditorAtomicExporterV1().publish(
            payload=b"replacement\n", destination=destination(target)
        )
    assert target.read_bytes() == b"sentinel"


def test_success_writes_exact_opaque_payload_and_removes_temp(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    install_local_no_replace(monkeypatch, calls)
    target = tmp_path / "rezultat-știri.json"
    payload = b'{"opaque":"value"}\n'
    result = EditorAtomicExporterV1().publish(
        payload=payload, destination=destination(target)
    )
    assert result == target
    assert target.read_bytes() == payload
    assert calls == ["publish"]
    assert list(tmp_path.glob(".pastila-editor-*.tmp")) == []


def test_partial_writes_complete_exact_payload_once_logically(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[str] = []
    install_local_no_replace(monkeypatch, calls)
    real_write = implementation.os.write
    chunks: list[bytes] = []

    def partial(fd: int, value) -> int:
        chunk = bytes(value[:2])
        chunks.append(chunk)
        return real_write(fd, chunk)

    monkeypatch.setattr(implementation.os, "write", partial)
    payload = b"abcdef\n"
    target = tmp_path / "result.json"
    EditorAtomicExporterV1().publish(payload=payload, destination=destination(target))
    assert b"".join(chunks) == payload
    assert target.read_bytes() == payload


@pytest.mark.parametrize("boundary", ["write", "fsync", "close"])
def test_write_sync_and_close_failures_cleanup_once_and_publish_nothing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, boundary: str
) -> None:
    target = tmp_path / "result.json"
    temp_paths: list[Path] = []
    real_mkstemp = implementation.tempfile.mkstemp
    real_close = implementation.os.close

    def create(*args, **kwargs):
        fd, path = real_mkstemp(*args, **kwargs)
        temp_paths.append(Path(path))
        return fd, path

    monkeypatch.setattr(implementation.tempfile, "mkstemp", create)
    if boundary == "write":
        monkeypatch.setattr(implementation.os, "write", lambda fd, data: 0)
    elif boundary == "fsync":
        monkeypatch.setattr(
            implementation.os,
            "fsync",
            lambda fd: (_ for _ in ()).throw(OSError()),
        )
    else:
        failed = False

        def close(fd: int):
            nonlocal failed
            if not failed:
                failed = True
                real_close(fd)
                raise OSError
            return real_close(fd)

        monkeypatch.setattr(implementation.os, "close", close)
    with pytest.raises(EditorApplicationExportError):
        EditorAtomicExporterV1().publish(
            payload=b"payload\n", destination=destination(target)
        )
    assert not target.exists()
    assert temp_paths and all(not path.exists() for path in temp_paths)


def test_native_failure_cleans_temp_once_and_preserves_absence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "result.json"
    created: list[Path] = []
    real_mkstemp = implementation.tempfile.mkstemp

    def create(*args, **kwargs):
        fd, name = real_mkstemp(*args, **kwargs)
        created.append(Path(name))
        return fd, name

    monkeypatch.setattr(implementation.tempfile, "mkstemp", create)
    monkeypatch.setattr(
        implementation._NoReplaceAtomicPublisherV1,
        "supported",
        staticmethod(lambda: True),
    )
    monkeypatch.setattr(
        implementation._NoReplaceAtomicPublisherV1,
        "publish_existing",
        staticmethod(
            lambda source, destination: implementation._ExportStatusV1.NATIVE_PUBLICATION_FAILED
        ),
    )
    with pytest.raises(EditorApplicationExportError):
        EditorAtomicExporterV1().publish(
            payload=b"payload\n", destination=destination(target)
        )
    assert not target.exists()
    assert created and all(not path.exists() for path in created)


def test_destination_race_cannot_replace_sentinel(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "result.json"

    def race(source: Path, destination_path: Path):
        del source
        destination_path.write_bytes(b"sentinel")
        return implementation._ExportStatusV1.DESTINATION_RACE

    monkeypatch.setattr(
        implementation._NoReplaceAtomicPublisherV1,
        "supported",
        staticmethod(lambda: True),
    )
    monkeypatch.setattr(
        implementation._NoReplaceAtomicPublisherV1,
        "publish_existing",
        staticmethod(race),
    )
    with pytest.raises(EditorApplicationExportError):
        EditorAtomicExporterV1().publish(
            payload=b"payload\n", destination=destination(target)
        )
    assert target.read_bytes() == b"sentinel"


def test_unsupported_platform_fails_before_temp_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(
        implementation._NoReplaceAtomicPublisherV1,
        "supported",
        staticmethod(lambda: False),
    )
    monkeypatch.setattr(
        implementation.tempfile,
        "mkstemp",
        lambda *args, **kwargs: pytest.fail("temporary file was created"),
    )
    with pytest.raises(EditorApplicationExportError):
        EditorAtomicExporterV1().publish(
            payload=b"payload\n",
            destination=destination(tmp_path / "result.json"),
        )


def test_native_constants_and_no_fallback_primitives() -> None:
    assert implementation._MOVEFILE_WRITE_THROUGH == 0x8
    assert implementation._RENAME_NOREPLACE == 1
    assert implementation._RENAME_EXCL == 0x4
    source = Path(implementation.__file__).read_text(encoding="utf-8")
    assert "MOVEFILE_REPLACE_EXISTING" not in source
    assert "os.replace" not in source
    assert "os.rename" not in source
    assert "Path.replace" not in source


class _NativeFunction:
    def __init__(self, result: int) -> None:
        self.result = result
        self.calls: list[tuple[object, ...]] = []
        self.argtypes = None
        self.restype = None

    def __call__(self, *arguments):
        self.calls.append(arguments)
        return self.result


def test_windows_native_call_uses_wide_paths_and_exact_flags(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    function = _NativeFunction(1)
    library = type("Library", (), {"MoveFileExW": function})()
    monkeypatch.setattr(implementation.ctypes, "WinDLL", lambda *a, **k: library)
    source = tmp_path / "sursă.tmp"
    target = tmp_path / "ieșire.json"
    assert implementation._publish_windows(source, target) is None
    assert function.calls == [
        (str(source), str(target), implementation._MOVEFILE_WRITE_THROUGH)
    ]
    assert function.argtypes == (
        implementation.ctypes.c_wchar_p,
        implementation.ctypes.c_wchar_p,
        implementation.ctypes.c_uint32,
    )


def test_windows_destination_race_maps_without_fallback(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    function = _NativeFunction(0)
    library = type("Library", (), {"MoveFileExW": function})()
    monkeypatch.setattr(implementation.ctypes, "WinDLL", lambda *a, **k: library)
    monkeypatch.setattr(implementation.ctypes, "get_last_error", lambda: 183)
    assert (
        implementation._publish_windows(tmp_path / "a", tmp_path / "b")
        is implementation._ExportStatusV1.DESTINATION_RACE
    )
    assert len(function.calls) == 1


@pytest.mark.parametrize(
    ("platform", "symbol", "flag", "function_name"),
    [
        ("linux", "renameat2", 1, "_publish_linux"),
        ("darwin", "renamex_np", 4, "_publish_macos"),
    ],
)
def test_posix_native_calls_use_exact_exclusive_flag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    platform: str,
    symbol: str,
    flag: int,
    function_name: str,
) -> None:
    function = _NativeFunction(0)
    library = type("Library", (), {symbol: function})()
    monkeypatch.setattr(implementation.ctypes, "CDLL", lambda *a, **k: library)
    source = tmp_path / "source.tmp"
    target = tmp_path / "target.json"
    assert getattr(implementation, function_name)(source, target) is None
    assert len(function.calls) == 1
    assert function.calls[0][-1] == flag
    if platform == "linux":
        assert function.calls[0][0] == implementation._AT_FDCWD
        assert function.calls[0][2] == implementation._AT_FDCWD


@pytest.mark.parametrize("platform", ["linux", "darwin", "unsupported"])
def test_missing_native_capability_suppresses_temp_creation(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    platform: str,
) -> None:
    monkeypatch.setattr(implementation.sys, "platform", platform)
    monkeypatch.setattr(implementation.ctypes, "CDLL", lambda *a, **k: object())
    monkeypatch.setattr(
        implementation.tempfile,
        "mkstemp",
        lambda *a, **k: pytest.fail("temporary file was created"),
    )
    with pytest.raises(EditorApplicationExportError):
        EditorAtomicExporterV1().publish(
            payload=b"payload\n",
            destination=destination(tmp_path / "result.json"),
        )


def test_parent_reparse_preflight_suppresses_temp_creation(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    real_lstat = implementation._safe_lstat
    parent_stat = real_lstat(tmp_path)
    monkeypatch.setattr(
        implementation,
        "_is_reparse",
        lambda value: value is parent_stat,
    )
    monkeypatch.setattr(
        implementation,
        "_safe_lstat",
        lambda path: parent_stat if path == tmp_path else real_lstat(path),
    )
    monkeypatch.setattr(
        implementation.tempfile,
        "mkstemp",
        lambda *a, **k: pytest.fail("temporary file was created"),
    )
    with pytest.raises(EditorApplicationExportError):
        EditorAtomicExporterV1().publish(
            payload=b"payload\n",
            destination=destination(tmp_path / "result.json"),
        )


@pytest.mark.parametrize(
    "race_status",
    [
        implementation._ExportStatusV1.PREPUBLICATION_FAILED,
        implementation._ExportStatusV1.DESTINATION_RACE,
        implementation._ExportStatusV1.TEMP_IDENTITY_FAILED,
    ],
)
def test_revalidation_races_cleanup_and_never_publish(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    race_status,
) -> None:
    target = tmp_path / "result.json"
    native_calls = 0

    def native(*args):
        nonlocal native_calls
        del args
        native_calls += 1

    monkeypatch.setattr(implementation, "_revalidate", lambda *a: race_status)
    monkeypatch.setattr(
        implementation._NoReplaceAtomicPublisherV1,
        "supported",
        staticmethod(lambda: True),
    )
    monkeypatch.setattr(
        implementation._NoReplaceAtomicPublisherV1,
        "publish_existing",
        staticmethod(native),
    )
    with pytest.raises(EditorApplicationExportError):
        EditorAtomicExporterV1().publish(
            payload=b"payload\n", destination=destination(target)
        )
    assert native_calls == 0
    assert not target.exists()
    assert list(tmp_path.glob(".pastila-editor-*.tmp")) == []


def test_cleanup_failure_has_private_precedence_and_one_attempt(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    attempts = 0

    def cleanup(*args):
        nonlocal attempts
        del args
        attempts += 1
        return False

    monkeypatch.setattr(implementation, "_cleanup_temp", cleanup)
    monkeypatch.setattr(implementation.os, "write", lambda fd, value: 0)
    monkeypatch.setattr(
        implementation._NoReplaceAtomicPublisherV1,
        "supported",
        staticmethod(lambda: True),
    )
    status, result = implementation._publish_neutral(
        b"payload\n", destination(tmp_path / "result.json")
    )
    assert status is implementation._ExportStatusV1.CLEANUP_FAILED
    assert result is None
    assert attempts == 1


@pytest.mark.parametrize(
    "failure_setup",
    [
        "invalid_payload",
        "invalid_destination",
        "unsupported",
        "write",
        "sync",
        "native",
        "cleanup",
    ],
)
def test_public_traceback_frames_contain_no_protected_authority(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    failure_setup: str,
) -> None:
    payload: object = b"protected-payload\n"
    authority: object = destination(tmp_path / "protected-destination.json")
    monkeypatch.setattr(
        implementation._NoReplaceAtomicPublisherV1,
        "supported",
        staticmethod(lambda: failure_setup != "unsupported"),
    )
    if failure_setup == "invalid_payload":
        payload = b"invalid"
    elif failure_setup == "invalid_destination":
        authority = object()
    elif failure_setup == "write":
        monkeypatch.setattr(implementation.os, "write", lambda fd, value: 0)
    elif failure_setup == "sync":
        monkeypatch.setattr(
            implementation.os,
            "fsync",
            lambda fd: (_ for _ in ()).throw(OSError("private")),
        )
    elif failure_setup in {"native", "cleanup"}:
        monkeypatch.setattr(
            implementation._NoReplaceAtomicPublisherV1,
            "publish_existing",
            staticmethod(
                lambda *a: implementation._ExportStatusV1.NATIVE_PUBLICATION_FAILED
            ),
        )
        if failure_setup == "cleanup":
            monkeypatch.setattr(implementation, "_cleanup_temp", lambda *a: False)
    with pytest.raises(EditorApplicationExportError) as captured:
        EditorAtomicExporterV1().publish(  # type: ignore[arg-type]
            payload=payload, destination=authority
        )
    current = captured.value.__traceback__
    while current is not None:
        if current.tb_frame.f_globals.get("__name__") == implementation.__name__:
            assert "payload" not in current.tb_frame.f_locals
            assert "destination" not in current.tb_frame.f_locals
            assert "temp_path" not in current.tb_frame.f_locals
            assert "fd" not in current.tb_frame.f_locals
        current = current.tb_next
    assert captured.value.__cause__ is None
    assert captured.value.__context__ is None


def test_import_and_construction_are_passive_in_fresh_process() -> None:
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            "from pastila_scout.editor_application_v1 import EditorAtomicExporterV1; assert repr(EditorAtomicExporterV1()) == 'EditorAtomicExporterV1()'",
        ],
        check=False,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_current_revision_scope_and_frozen_integrity() -> None:
    root = Path(__file__).resolve().parents[1]
    baseline = "phase-4.3-editor-application-composition-spec-v6-ready"
    exact_commit = "a62ea03d008f2b777a263ffd274a98c608e644e9"
    allowed = {
        "src/pastila_scout/editor_application_v1/__init__.py",
        "src/pastila_scout/editor_application_v1/serialization.py",
        "tests/test_editor_application_contracts_v1.py",
        "tests/test_editor_application_serialization_v1.py",
        "tests/test_editor_application_export_v1.py",
    }
    self_digest = "7EE6D8945DCB7C5B44B6D85EBAC4ECBD5613C85F8AE7C86E3C1E809F76A6BF9A"

    def names(*arguments: str) -> set[str]:
        return set(
            subprocess.run(
                ["git", *arguments],
                cwd=root,
                check=True,
                capture_output=True,
                text=True,
            ).stdout.splitlines()
        )

    resolved = subprocess.run(
        ["git", "rev-parse", f"{baseline}^{{}}"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert resolved == exact_commit
    assert names("diff", "--cached", "--name-only") == set()
    assert names("diff", "--name-only", baseline) == allowed
    assert names("ls-files", "--others", "--exclude-standard") == set()
    frozen = {
        "docs/editorial-application/EditorApplicationCompositionSpecificationV1.md",
        "src/pastila_scout/editor_application_v1/configuration.py",
        "src/pastila_scout/editor_application_v1/errors.py",
        "src/pastila_scout/editor_application_v1/models.py",
        "src/pastila_scout/editor_application_v1/export.py",
    }
    assert names("diff", "--name-only", baseline, "--", *frozen) == set()
    test_bytes = (root / "tests/test_editor_application_export_v1.py").read_bytes()
    normalized = test_bytes.replace(self_digest.encode(), b"0" * 64)
    assert normalized != test_bytes
    assert hashlib.sha256(normalized).hexdigest().upper() == self_digest
