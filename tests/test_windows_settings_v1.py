from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from pastila_scout.windows_state_v1.errors import _WindowsStateSettingsError
from pastila_scout.windows_state_v1.settings import (
    WindowsSettingsV1,
    _default_windows_settings_v1,
    _load_windows_settings_v1,
    _reconstruct_windows_settings_v1,
    _save_windows_settings_v1,
)

DEFAULTS = Path("src/pastila_scout/desktop_v1/default-settings-v1.json").resolve()


def test_resource_is_the_defaults_authority() -> None:
    settings = _default_windows_settings_v1(defaults_path=DEFAULTS)
    assert settings.schema == "pastila-scout-settings"
    assert settings.scout_period_days == 7
    assert settings.editor_timeout_seconds == 120.0


def test_absent_mutable_settings_load_defaults(tmp_path: Path) -> None:
    assert _load_windows_settings_v1(
        path=tmp_path / "missing.json", defaults_path=DEFAULTS
    ) == _default_windows_settings_v1(defaults_path=DEFAULTS)


def test_save_is_canonical_and_round_trips(tmp_path: Path) -> None:
    path = (tmp_path / "settings.json").resolve()
    settings = _default_windows_settings_v1(defaults_path=DEFAULTS)
    _save_windows_settings_v1(path=path, settings=settings)
    assert path.read_bytes() == DEFAULTS.read_bytes()
    assert _load_windows_settings_v1(path=path, defaults_path=DEFAULTS) == settings


def test_save_retains_one_backup(tmp_path: Path) -> None:
    path = (tmp_path / "settings.json").resolve()
    path.write_bytes(DEFAULTS.read_bytes())
    _save_windows_settings_v1(
        path=path, settings=_default_windows_settings_v1(defaults_path=DEFAULTS)
    )
    assert (tmp_path / "settings.json.bak").read_bytes() == DEFAULTS.read_bytes()
    assert not tuple(tmp_path.glob(".settings.json.*.tmp"))


@pytest.mark.parametrize(
    "payload",
    [
        b"",
        b"{",
        b"\xef\xbb\xbf{}",
        b'{"schema":"pastila-scout-settings"}',
        b'{"x":NaN}',
    ],
)
def test_malformed_settings_fail_safely(tmp_path: Path, payload: bytes) -> None:
    path = tmp_path / "settings.json"
    path.write_bytes(payload)
    with pytest.raises(_WindowsStateSettingsError) as raised:
        _load_windows_settings_v1(path=path, defaults_path=DEFAULTS)
    assert str(raised.value) == "Windows application settings are invalid."
    assert raised.value.__cause__ is None
    assert raised.value.__context__ is None


def test_unknown_missing_wrong_type_and_key_order_are_rejected(tmp_path: Path) -> None:
    value = json.loads(DEFAULTS.read_text(encoding="utf-8"))
    cases = []
    cases.append({**value, "unknown": 1})
    cases.append({name: item for name, item in value.items() if name != "log_level"})
    cases.append({**value, "updates_enabled": 1})
    cases.append(dict(reversed(tuple(value.items()))))
    for index, case in enumerate(cases):
        path = tmp_path / f"bad-{index}.json"
        path.write_text(json.dumps(case), encoding="utf-8")
        with pytest.raises(_WindowsStateSettingsError):
            _load_windows_settings_v1(path=path, defaults_path=DEFAULTS)


def test_settings_object_safety() -> None:
    settings = _default_windows_settings_v1(defaults_path=DEFAULTS)
    assert copy.copy(settings) == settings
    assert copy.deepcopy(settings) == settings
    assert _reconstruct_windows_settings_v1(settings) == settings
    assert "gpt-4.1-mini" not in repr(settings)
    with pytest.raises(TypeError):

        class Invalid(WindowsSettingsV1):
            pass
