from __future__ import annotations

import copy
import importlib
from pathlib import Path

import pytest

from pastila_scout.windows_state_v1.errors import _WindowsStatePathError
from pastila_scout.windows_state_v1.paths import (
    WindowsApplicationPathsV1,
    _create_windows_application_directories_v1,
    _reconstruct_windows_application_paths_v1,
    _resolve_windows_application_paths_v1,
)


def test_development_paths_are_exact_and_ignore_environment(tmp_path: Path) -> None:
    root = tmp_path.resolve()
    paths = _resolve_windows_application_paths_v1(
        frozen=False,
        environment={"LOCALAPPDATA": "ignored", "APPDATA": "ignored"},
        bundled_application_root=None,
        development_root=root,
    )
    assert paths.mode == "development"
    assert paths.scout_application_config_path == root / "config" / "config.yaml"
    assert paths.bundled_source_path == root / "config" / "sources.yaml"
    assert paths.database_path == root / "data" / "news_monitor.db"
    assert paths.cache_directory == root / "data" / "ai_cache"
    assert paths.settings_path == root / "config" / "settings.json"
    assert "ignored" not in repr(paths)


def test_installed_paths_separate_immutable_and_mutable_roots(tmp_path: Path) -> None:
    local = (tmp_path / "local").resolve()
    roaming = (tmp_path / "roaming").resolve()
    local.mkdir()
    roaming.mkdir()
    app = _installed_app(local)
    paths = _resolve_windows_application_paths_v1(
        frozen=True,
        environment={"LOCALAPPDATA": str(local), "APPDATA": str(roaming)},
        bundled_application_root=app,
        development_root=None,
    )
    assert paths.settings_defaults_path.is_relative_to(app)
    assert paths.database_path.is_relative_to(local / "PastilaScout")
    assert paths.settings_path.is_relative_to(roaming / "PastilaScout")
    assert not paths.database_path.is_relative_to(app)


def test_directory_creation_is_explicit_and_idempotent(tmp_path: Path) -> None:
    root = tmp_path.resolve()
    paths = _resolve_windows_application_paths_v1(
        frozen=False,
        environment={},
        bundled_application_root=None,
        development_root=root,
    )
    _create_windows_application_directories_v1(paths=paths)
    _create_windows_application_directories_v1(paths=paths)
    for directory in (
        paths.database_backup_directory,
        paths.report_directory,
        paths.cache_directory,
        paths.log_directory,
    ):
        assert directory.is_dir()
    assert not paths.database_path.exists()


@pytest.mark.parametrize("root", [Path("relative"), Path("."), Path("..")])
def test_relative_development_roots_fail(root: Path) -> None:
    with pytest.raises(
        _WindowsStatePathError, match="Windows application paths are unavailable\\."
    ) as raised:
        _resolve_windows_application_paths_v1(
            frozen=False,
            environment={},
            bundled_application_root=None,
            development_root=root,
        )
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None


def test_installed_mode_requires_environment_and_markers(tmp_path: Path) -> None:
    with pytest.raises(_WindowsStatePathError):
        _resolve_windows_application_paths_v1(
            frozen=True,
            environment={},
            bundled_application_root=tmp_path.resolve(),
            development_root=None,
        )


def test_values_copy_reconstruct_and_reject_subclass(tmp_path: Path) -> None:
    paths = _resolve_windows_application_paths_v1(
        frozen=False,
        environment={},
        bundled_application_root=None,
        development_root=tmp_path.resolve(),
    )
    assert copy.copy(paths) == paths
    assert copy.deepcopy(paths) == paths
    assert _reconstruct_windows_application_paths_v1(paths) == paths
    with pytest.raises(TypeError):

        class Invalid(WindowsApplicationPathsV1):
            pass


def test_import_is_passive(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(Path, "mkdir", lambda *args, **kwargs: pytest.fail("mkdir"))
    import pastila_scout.windows_state_v1.paths as module

    importlib.reload(module)


def _installed_app(local_root: Path) -> Path:
    app = (local_root / "Programs" / "PastilaScout" / "app").resolve()
    (app / "config").mkdir(parents=True)
    (app / "desktop_v1").mkdir()
    (app / "config" / "config.yaml").write_text("polling: {}\n", encoding="utf-8")
    (app / "config" / "sources.yaml").write_text("sources: []\n", encoding="utf-8")
    (app / "desktop_v1" / "default-settings-v1.json").write_text(
        "{}\n", encoding="utf-8"
    )
    return app
