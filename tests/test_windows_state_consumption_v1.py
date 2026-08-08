from __future__ import annotations

import inspect
from pathlib import Path
from types import SimpleNamespace

import pytest

from pastila_scout.desktop_application_v1 import DesktopApplicationFacadeV1
from pastila_scout.desktop_v1 import settings as desktop_settings
from pastila_scout.desktop_v1 import state_composition
from pastila_scout.desktop_v1.settings import (
    _DesktopSettingsProjectionV1,
    _project_desktop_settings_v1,
    _select_scout_sources_path_v1,
)
from pastila_scout.desktop_v1.state_composition import (
    _compose_state_bound_desktop_application_v1,
    _DesktopStateCompositionV1,
    _DesktopStateConsumptionError,
)
from pastila_scout.windows_state_v1.migrations import (
    DevelopmentMigrationApplicabilityV1,
)
from pastila_scout.windows_state_v1.paths import (
    _resolve_windows_application_paths_v1,
)
from pastila_scout.windows_state_v1.settings import _default_windows_settings_v1

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = ROOT / "src/pastila_scout/desktop_v1/default-settings-v1.json"


def _projection() -> _DesktopSettingsProjectionV1:
    return _project_desktop_settings_v1(
        settings=_default_windows_settings_v1(defaults_path=DEFAULTS)
    )


def test_exact_private_contracts_and_projection() -> None:
    signature = inspect.signature(_compose_state_bound_desktop_application_v1)
    assert tuple(signature.parameters) == (
        "frozen",
        "environment",
        "development_root",
        "migration_consent",
    )
    assert all(
        value.kind is inspect.Parameter.KEYWORD_ONLY
        for value in signature.parameters.values()
    )
    assert tuple(inspect.signature(_select_scout_sources_path_v1).parameters) == (
        "paths",
    )
    projected = _projection()
    assert projected.scout_period_days == 7
    assert projected.scout_category == "all"
    assert "paths=<redacted>" in repr(projected)
    with pytest.raises(TypeError):

        class Invalid(_DesktopSettingsProjectionV1):
            pass


def test_real_development_composition_has_two_field_result() -> None:
    result = _compose_state_bound_desktop_application_v1(
        frozen=False,
        environment={},
        development_root=ROOT,
        migration_consent=lambda paths: pytest.fail(f"unexpected migration: {paths!r}"),
    )
    assert type(result) is _DesktopStateCompositionV1
    assert type(result.facade) is DesktopApplicationFacadeV1
    assert type(result.settings) is _DesktopSettingsProjectionV1
    assert set(result.__slots__) == {"facade", "settings"}


def test_source_selector_override_and_bundled_precedence(tmp_path: Path) -> None:
    root = tmp_path.resolve()
    (root / "config").mkdir()
    (root / "src/pastila_scout/desktop_v1").mkdir(parents=True)
    bundled = root / "config/sources.yaml"
    bundled.write_bytes((ROOT / "config/sources.yaml").read_bytes())
    (root / "config/config.yaml").write_bytes(
        (ROOT / "config/config.yaml").read_bytes()
    )
    (root / "src/pastila_scout/desktop_v1/default-settings-v1.json").write_bytes(
        DEFAULTS.read_bytes()
    )
    paths = _resolve_windows_application_paths_v1(
        frozen=False,
        environment={},
        bundled_application_root=None,
        development_root=root,
    )
    assert _select_scout_sources_path_v1(paths=paths) == bundled
    override = paths.source_override_path
    override.write_bytes(bundled.read_bytes())
    assert _select_scout_sources_path_v1(paths=paths) == override
    override.write_text("invalid: true\n", encoding="utf-8")
    with pytest.raises(ValueError):
        _select_scout_sources_path_v1(paths=paths)


def test_installed_applicability_already_migrated_has_zero_ui(monkeypatch) -> None:
    calls: list[str] = []
    paths = SimpleNamespace(
        settings_path=Path("C:/state/settings.json"),
        settings_defaults_path=DEFAULTS,
        scout_application_config_path=Path("C:/app/config/config.yaml"),
        database_path=Path("C:/state/news.db"),
        report_directory=Path("C:/state/reports"),
    )
    facade = object()
    monkeypatch.setattr(
        state_composition,
        "_resolve_windows_application_paths_v1",
        lambda **kwargs: paths,
    )
    monkeypatch.setattr(
        state_composition,
        "_create_windows_application_directories_v1",
        lambda **kwargs: calls.append("directories"),
    )
    monkeypatch.setattr(
        state_composition,
        "_load_windows_settings_v1",
        lambda **kwargs: (_default_windows_settings_v1(defaults_path=DEFAULTS)),
    )
    monkeypatch.setattr(
        state_composition,
        "_inspect_development_state_migration_applicability_v1",
        lambda **kwargs: DevelopmentMigrationApplicabilityV1("already_migrated"),
    )
    monkeypatch.setattr(
        state_composition,
        "_select_scout_sources_path_v1",
        lambda **kwargs: Path("C:/app/config/sources.yaml"),
    )
    monkeypatch.setattr(
        state_composition,
        "_compose_desktop_application_facade_v1",
        lambda **kwargs: facade,
    )
    monkeypatch.setattr(
        state_composition, "_DesktopStateCompositionV1", lambda **kwargs: kwargs
    )
    result = _compose_state_bound_desktop_application_v1(
        frozen=True,
        environment={"LOCALAPPDATA": "C:/Users/test/AppData/Local"},
        development_root=None,
        migration_consent=lambda paths: pytest.fail("chooser must not run"),
    )
    assert result["facade"] is facade
    assert calls == ["directories"]


@pytest.mark.parametrize(
    "boundary,key",
    [
        ("resolve", "state.error"),
        ("applicability", "migration.error"),
        ("sources", "sources.override.error"),
        ("facade", "startup.error"),
    ],
)
def test_safe_failure_taxonomy(monkeypatch, boundary: str, key: str) -> None:
    paths = SimpleNamespace(
        settings_path=Path("C:/state/settings.json"),
        settings_defaults_path=DEFAULTS,
        scout_application_config_path=Path("C:/app/config/config.yaml"),
        database_path=Path("C:/state/news.db"),
        report_directory=Path("C:/state/reports"),
    )

    def fail(**kwargs):
        del kwargs
        raise RuntimeError("secret")

    monkeypatch.setattr(
        state_composition,
        "_resolve_windows_application_paths_v1",
        fail if boundary == "resolve" else lambda **kwargs: paths,
    )
    monkeypatch.setattr(
        state_composition,
        "_create_windows_application_directories_v1",
        lambda **kwargs: None,
    )
    monkeypatch.setattr(
        state_composition,
        "_load_windows_settings_v1",
        lambda **kwargs: _default_windows_settings_v1(defaults_path=DEFAULTS),
    )
    monkeypatch.setattr(
        state_composition,
        "_inspect_development_state_migration_applicability_v1",
        (
            fail
            if boundary == "applicability"
            else lambda **kwargs: DevelopmentMigrationApplicabilityV1(
                "already_migrated"
            )
        ),
    )
    monkeypatch.setattr(
        state_composition,
        "_select_scout_sources_path_v1",
        fail if boundary == "sources" else lambda **kwargs: Path("C:/sources.yaml"),
    )
    monkeypatch.setattr(
        state_composition,
        "_compose_desktop_application_facade_v1",
        fail if boundary == "facade" else lambda **kwargs: object(),
    )
    with pytest.raises(_DesktopStateConsumptionError) as caught:
        _compose_state_bound_desktop_application_v1(
            frozen=True,
            environment={"LOCALAPPDATA": "C:/Users/test/AppData/Local"},
            development_root=None,
            migration_consent=lambda paths: None,
        )
    assert str(caught.value) == "Windows desktop state consumption failed."
    assert caught.value.presentation_key == key
    assert caught.value.__cause__ is None
    assert caught.value.__context__ is None


def test_modules_are_passive_and_have_no_current_state() -> None:
    assert desktop_settings.__all__ == ()
    assert state_composition.__all__ == ()
    forbidden = {"current_paths", "current_settings", "current_sources"}
    assert forbidden.isdisjoint(vars(desktop_settings))
    assert forbidden.isdisjoint(vars(state_composition))
