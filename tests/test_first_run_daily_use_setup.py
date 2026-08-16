from pathlib import Path

from pastila_scout.desktop_v1 import entrypoint, first_run
from pastila_scout.desktop_v1.views import _editor_display_model
from pastila_scout.windows_state_v1.settings import _default_windows_settings_v1

ROOT = Path(__file__).resolve().parents[1]
DEFAULTS = ROOT / "src/pastila_scout/desktop_v1/default-settings-v1.json"
SOURCES = ROOT / "config/sources.yaml"


class _ProjectStore:
    def __init__(self, value=None, failure=None):
        self.value = value
        self.failure = failure

    def load(self):
        if self.failure:
            raise self.failure
        return self.value


def _inspect(tmp_path, monkeypatch, *, key=False, project=None, failure=None):
    monkeypatch.setattr(
        first_run, "resolve_openai_api_key", lambda: "key" if key else None
    )
    settings = _default_windows_settings_v1(defaults_path=DEFAULTS)
    return first_run._inspect_desktop_readiness_v1(
        settings=settings,
        settings_path=tmp_path / "settings.json",
        sources_path=SOURCES,
        default_output_directory=tmp_path / "reports",
        project_store=_ProjectStore(project, failure),
    )


def test_missing_settings_requires_setup_and_uses_practical_output(
    tmp_path, monkeypatch
):
    result = _inspect(tmp_path, monkeypatch)
    assert result.setup_required
    assert result.provider_ready
    assert result.enabled_sources
    assert result.output_directory == tmp_path / "reports"


def test_completion_persists_and_valid_settings_skip_setup(tmp_path, monkeypatch):
    settings = _default_windows_settings_v1(defaults_path=DEFAULTS)
    path = tmp_path / "settings.json"
    completed = first_run._complete_desktop_setup_v1(
        settings=settings,
        settings_path=path,
        provider="ollama",
        base_url="http://localhost:11434/",
        model="qwen3:14b",
        output_directory=tmp_path / "reports",
    )
    monkeypatch.setattr(first_run, "resolve_openai_api_key", lambda: None)
    result = first_run._inspect_desktop_readiness_v1(
        settings=completed,
        settings_path=path,
        sources_path=SOURCES,
        default_output_directory=tmp_path / "other",
        project_store=_ProjectStore(),
    )
    assert not result.setup_required
    assert completed.scout_provider == completed.editor_provider == "ollama"
    assert completed.editor_model == "qwen3:14b"
    assert completed.editor_output_directory.is_dir()


def test_unavailable_provider_does_not_reopen_completed_setup(tmp_path, monkeypatch):
    settings = _default_windows_settings_v1(defaults_path=DEFAULTS)
    completed = first_run._complete_desktop_setup_v1(
        settings=settings,
        settings_path=tmp_path / "settings.json",
        provider="openai",
        base_url=settings.ollama_base_url,
        model=settings.ollama_model,
        output_directory=tmp_path / "reports",
    )
    monkeypatch.setattr(first_run, "resolve_openai_api_key", lambda: None)
    result = first_run._inspect_desktop_readiness_v1(
        settings=completed,
        settings_path=tmp_path / "settings.json",
        sources_path=SOURCES,
        default_output_directory=tmp_path / "reports",
        project_store=_ProjectStore(),
    )
    assert not result.setup_required
    assert not result.provider_ready
    assert completed.scout_provider == completed.editor_provider == "openai"


def test_project_recovery_and_invalid_project_safe_warning(tmp_path, monkeypatch):
    project = object()
    assert _inspect(tmp_path, monkeypatch, project=project).active_project is project
    invalid = _inspect(tmp_path, monkeypatch, failure=ValueError("invalid"))
    assert invalid.active_project is None
    assert "pastrat" in invalid.project_warning


def test_setup_window_is_visible_before_modal_wait():
    calls = []

    class Window:
        def protocol(self, name, callback):
            calls.append(("protocol", name, callback))

        def destroy(self):
            calls.append(("destroy",))

        def deiconify(self):
            calls.append(("deiconify",))

        def lift(self):
            calls.append(("lift",))

        def grab_set(self):
            calls.append(("grab",))

    class Root:
        def wait_window(self, window):
            calls.append(("wait", window))

    window = Window()
    entrypoint._present_first_run_window(root=Root(), window=window)
    assert [call[0] for call in calls] == [
        "protocol",
        "deiconify",
        "lift",
        "grab",
        "wait",
    ]


def test_completed_setup_settings_are_projected_for_shell_construction(tmp_path):
    persisted = _default_windows_settings_v1(defaults_path=DEFAULTS)
    persisted = first_run._complete_desktop_setup_v1(
        settings=persisted,
        settings_path=tmp_path / "settings.json",
        provider="ollama",
        base_url=persisted.ollama_base_url,
        model=persisted.ollama_model,
        output_directory=tmp_path / "reports",
    )
    projected = entrypoint._desktop_setup_settings_v1(persisted)
    assert type(projected).__name__ == "_DesktopSettingsProjectionV1"
    assert projected.scout_provider == "ollama"
    assert projected.ollama_model == "qwen3:14b"
    assert _editor_display_model(projected) == "qwen3:14b"
