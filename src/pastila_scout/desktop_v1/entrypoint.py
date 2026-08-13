"""Explicit production startup wiring for the private desktop application."""

# ruff: noqa: BLE001, S110

from __future__ import annotations

import ctypes
import math
import os
import sys
import tkinter
import unicodedata
import uuid
from datetime import UTC, datetime
from pathlib import Path
from tkinter import filedialog, messagebox
from typing import NoReturn

import httpx

from pastila_scout.active_project_v1 import ActiveProjectStoreV1, ChiefEditorItemV1
from pastila_scout.contracts.identity import verify_scout_input_identity
from pastila_scout.contracts.io import load_contract
from pastila_scout.contracts.scout_editor import ScoutEditorInputV1
from pastila_scout.desktop_application_v1 import (
    DesktopApplicationFacadeV1,
    DesktopProgressEventV1,
    EditorDesktopRequestV1,
    EditorDesktopResultV1,
    ScoutDesktopCategoryV1,
    ScoutDesktopRequestV1,
    reconstruct_desktop_progress_event,
    reconstruct_editor_desktop_result,
    reconstruct_scout_desktop_result,
)
from pastila_scout.editor_application_v1 import (
    EditorApplicationGenerationConfigurationAuthorityV1,
    EditorApplicationRequestV1,
    EditorEpisodeContextAuthorityV1,
    EditorOutputDestinationV1,
    EditorOverwritePolicyV1,
    EditorSelectionProfileAuthorityV1,
)
from pastila_scout.provider_execution_ollama_v1 import OllamaHttpClientV1
from pastila_scout.provider_execution_v2 import CancellationTokenV2
from pastila_scout.windows_state_v1.migrations import (
    _inspect_development_state_migration_v1,
)
from pastila_scout.windows_state_v1.settings import (
    WindowsSettingsV1,
    _save_windows_settings_v1,
)

from .controller import _DesktopTaskControllerV1
from .errors import _DesktopShellConfigurationError
from .models import (
    _DesktopPageV1,
    _reconstruct_desktop_editor_action_input_v1,
    _reconstruct_desktop_scout_action_input_v1,
)
from .resources import _text_v1
from .state_composition import (
    _compose_state_bound_desktop_application_v1,
    _DesktopStateConsumptionError,
)
from .views import _DesktopMainWindowV1


class _DesktopStartupProgressSinkV1:
    __slots__ = ()

    def __init_subclass__(cls, **kwargs) -> NoReturn:
        del cls, kwargs
        raise TypeError("Desktop startup progress sinks cannot be subclassed")

    def publish(self, *, event: DesktopProgressEventV1) -> None:
        reconstruct_desktop_progress_event(event)


def main() -> int:
    root = None
    controller = None
    present_failure = False
    try:
        if sys.platform == "win32":
            try:
                ctypes.windll.shcore.SetProcessDpiAwareness(2)
            except BaseException:
                pass
        root = tkinter.Tk()
        root.tk.call("tk", "scaling", 2.0)
        root.withdraw()
        present_failure = True
        frozen = bool(getattr(sys, "frozen", False))
        development_root = None if frozen else Path(__file__).resolve().parents[3]

        def migration_consent(paths):
            messagebox.showinfo(
                title=_text_v1(key="migration.title"),
                message=_text_v1(key="migration.prompt"),
                parent=root,
            )
            selected = filedialog.askdirectory(parent=root, mustexist=True)
            if not selected:
                return None
            plan = _inspect_development_state_migration_v1(
                development_root=Path(selected), destination=paths
            )
            if plan.status != "ready":
                return None
            accepted = messagebox.askyesno(
                title=_text_v1(key="migration.title"),
                message=_text_v1(key="migration.confirm"),
                parent=root,
            )
            return plan if accepted else None

        state = _compose_state_bound_desktop_application_v1(
            frozen=frozen,
            environment=dict(os.environ),
            development_root=development_root,
            migration_consent=migration_consent,
        )
        facade = state.facade
        project_store = ActiveProjectStoreV1(
            database_path=state.database_path,
            project_path=state.active_project_path,
        )
        active_project = project_store.load()
        cells: dict[str, object] = {
            "facade": facade,
            "project": active_project,
            "settings": state.settings,
        }
        closed = False

        def select_page(*, page) -> None:
            cells["controller"].select_page(page=page)  # type: ignore[attr-defined]

        def close() -> None:
            nonlocal closed
            if closed:
                return
            closed = True
            cells["controller"].close()  # type: ignore[attr-defined]
            root.quit()

        def publish_snapshot(*, snapshot) -> None:
            cells["view"].publish_snapshot(snapshot=snapshot)  # type: ignore[attr-defined]

        controller = _DesktopTaskControllerV1(
            schedule_after=root.after,
            cancel_after=root.after_cancel,
            publish_snapshot=publish_snapshot,
        )
        view = _DesktopMainWindowV1(
            root=root,
            on_select_page=select_page,
            on_close=close,
            settings=state.settings,
        )
        cells.update(controller=controller, view=view)

        def run_scout(*, input) -> None:
            request = _scout_request(input)

            def task():
                return facade.run_scout(
                    request=request, progress_sink=_DesktopStartupProgressSinkV1()
                )

            def on_completed(*, result) -> None:
                _publish_scout_result(view, result)
                _publish_candidates(view, project_store)

            controller.submit_application(task=task, on_completed=on_completed)

        def run_editor(*, input) -> None:
            values = _editor_values(input)

            def task():
                project = cells.get("project")
                source = None if project is None else project.scout_input  # type: ignore[attr-defined]
                return _run_editor(facade, values, source=source)

            def on_completed(*, result) -> None:
                _publish_editor_result(view, result)
                application_result = reconstruct_editor_desktop_result(result).application_result
                if (
                    application_result.handoff_permitted
                    and application_result.output_path is not None
                    and application_result.payload_sha256 is not None
                ):
                    cells["project"] = project_store.record_editor_output(
                        output_path=application_result.output_path,
                        payload_sha256=application_result.payload_sha256,
                    )
                    _publish_chief_editor(view, cells["project"])

            controller.submit_application(task=task, on_completed=on_completed)

        def open_report(*, reference: str) -> None:
            facade.open_report(reference=reference)

        def handoff(*, input) -> None:
            _complete_handoff(
                store=project_store,
                event_id=input,
                cells=cells,
                view=view,
                controller=controller,
            )

        def save_chief_editor(*, input) -> None:
            project = _save_chief_editor(project_store, input)
            cells["project"] = project
            _publish_chief_editor(view, project, _text_v1(key="chief_editor.saved"))

        def export_chief_editor(*, input) -> None:
            project = _save_chief_editor(project_store, input)
            selected = filedialog.asksaveasfilename(
                parent=root,
                defaultextension=".md",
                filetypes=(("Markdown", "*.md"), ("Text", "*.txt")),
                initialfile="structura-episod.md",
            )
            if selected:
                project_store.export_chief_editor(destination=Path(selected))
            cells["project"] = project
            _publish_chief_editor(view, project, _text_v1(key="chief_editor.saved"))

        def save_scout_provider(*, input) -> None:
            settings = _save_scout_provider_settings(
                path=state.settings_path,
                current=cells["settings"],
                value=input,
            )
            cells["settings"] = settings
            view.publish_scout_provider_status(
                status=_text_v1(key="scout.provider_saved")
            )

        def test_scout_provider(*, input) -> None:
            try:
                values = _scout_provider_values(input)
                if values[0] == "ollama":
                    with httpx.Client() as client:
                        OllamaHttpClientV1(client).check_model(
                            model=values[2],
                            base_url=values[1],
                            timeout=state.settings.scout_ai_timeout_seconds,
                        )
                status = _text_v1(key="scout.ollama_ready")
            except Exception:
                status = _text_v1(key="scout.ollama_unavailable")
            view.publish_scout_provider_status(status=status)

        view.bind_scout_action(callback=run_scout)
        view.bind_editor_action(callback=run_editor)
        view.bind_report_action(callback=open_report)
        view.bind_handoff_action(callback=handoff)
        view.bind_chief_editor_actions(
            save_callback=save_chief_editor, export_callback=export_chief_editor
        )
        view.bind_scout_provider_actions(
            save_callback=save_scout_provider, test_callback=test_scout_provider
        )
        _publish_candidates(view, project_store)
        if active_project is not None:
            view.publish_active_project(
                title=active_project.title,
                message=_text_v1(key="scout.handoff_success"),
            )
            _publish_chief_editor(view, active_project)
        root.protocol("WM_DELETE_WINDOW", close)
        controller.start()
        root.deiconify()
        present_failure = False
        root.mainloop()
        return 0
    except _DesktopStateConsumptionError as exc:
        if present_failure and root is not None:
            _present_startup_failure(root, key=exc.presentation_key)
        return 1
    except Exception:
        if present_failure and root is not None:
            _present_startup_failure(root, key="startup.error")
        return 1
    finally:
        if controller is not None:
            try:
                controller.close()
            except BaseException:
                pass
        if root is not None:
            try:
                root.destroy()
            except BaseException:
                pass


def _scout_request(value: object) -> ScoutDesktopRequestV1:
    try:
        valid = _reconstruct_desktop_scout_action_input_v1(value)
        period = int(valid.period, 10)
        if str(period) != valid.period:
            raise ValueError
        category = ScoutDesktopCategoryV1(valid.category)
        return ScoutDesktopRequestV1(
            operation_reference=f"scout-desktop-v1:{uuid.uuid4().hex}",
            period_days=period,
            category=category,
        )
    except BaseException:
        raise _DesktopShellConfigurationError() from None


def _editor_values(value: object) -> tuple[object, ...]:
    try:
        valid = _reconstruct_desktop_editor_action_input_v1(value)
        strings = tuple(
            getattr(valid, name)
            for name in (
                "scout_input_path",
                "selection_profile_path",
                "episode_context_path",
                "generation_config_path",
                "provider",
                "model",
                "timeout_seconds",
                "output_path",
            )
        )
        if (
            not valid.no_replace
            or not all(_safe_input(item) for item in strings[1:])
            or (strings[0] and not _safe_input(strings[0]))
        ):
            raise ValueError
        timeout = float(valid.timeout_seconds)
        if not math.isfinite(timeout) or timeout <= 0:
            raise ValueError
        output = Path(valid.output_path)
        if not output.is_absolute():
            output = Path.cwd() / output
        return (
            *(Path(item) for item in strings[:4]),
            strings[4],
            strings[5],
            timeout,
            output,
            f"editor-desktop-v1:{uuid.uuid4().hex}",
        )
    except BaseException:
        raise _DesktopShellConfigurationError() from None


def _run_editor(
    facade: DesktopApplicationFacadeV1,
    values: tuple[object, ...],
    *,
    source: ScoutEditorInputV1 | None = None,
) -> EditorDesktopResultV1:
    (
        scout_path,
        profile_path,
        context_path,
        generation_path,
        provider,
        model,
        timeout,
        output,
        reference,
    ) = values
    source = load_contract(scout_path) if source is None else source
    if type(source) is not ScoutEditorInputV1:
        raise _DesktopShellConfigurationError() from None
    source = ScoutEditorInputV1.model_validate(
        source.model_dump(mode="python", warnings=False), strict=True
    )
    verify_scout_input_identity(source)
    profile = EditorSelectionProfileAuthorityV1().load(path=profile_path)
    context = EditorEpisodeContextAuthorityV1().load(path=context_path)
    generation = EditorApplicationGenerationConfigurationAuthorityV1().load(
        path=generation_path
    )
    if not (
        generation.provider.value == provider
        and generation.model_identifier == model
        and generation.timeout_seconds == timeout
    ):
        raise _DesktopShellConfigurationError() from None
    nested = EditorApplicationRequestV1(
        source,
        profile,
        context,
        generation,
        EditorOutputDestinationV1(output, EditorOverwritePolicyV1.FAIL_IF_EXISTS),
        datetime.now(UTC),
        reference,
        CancellationTokenV2(cancellation_requested=False),
    )
    return facade.run_editor(
        request=EditorDesktopRequestV1(application_request=nested),
        progress_sink=_DesktopStartupProgressSinkV1(),
    )


def _publish_candidates(view: object, store: ActiveProjectStoreV1) -> None:
    candidates = store.list_candidates()
    view.publish_candidates(  # type: ignore[attr-defined]
        candidates=tuple(
            (item.event_id, item.title, item.category, item.source_count)
            for item in candidates
        )
    )


def _complete_handoff(*, store, event_id: int, cells, view, controller) -> bool:
    try:
        project = store.handoff(event_id=event_id)
    except Exception:
        view.publish_active_project(
            title="—", message=_text_v1(key="scout.handoff_failure")
        )
        return False
    cells["project"] = project
    view.publish_active_project(
        title=project.title, message=_text_v1(key="scout.handoff_success")
    )
    controller.select_page(page=_DesktopPageV1.EDITOR)
    return True


def _save_chief_editor(store: ActiveProjectStoreV1, value: object):
    if type(value) is not dict or set(value) != {"title", "items"}:
        raise _DesktopShellConfigurationError() from None
    raw_items = value["items"]
    if type(value["title"]) is not str or type(raw_items) is not tuple:
        raise _DesktopShellConfigurationError() from None
    try:
        items = tuple(
            ChiefEditorItemV1(reference, section.strip(), note.strip())
            for reference, section, note in raw_items
        )
        return store.save_chief_editor(title=value["title"], items=items)
    except Exception:
        raise _DesktopShellConfigurationError() from None


def _publish_chief_editor(view: object, project: object, status: str = "") -> None:
    materials = {item.reference: item for item in project.editor_materials}
    view.publish_chief_editor(  # type: ignore[attr-defined]
        title=project.chief_editor_title or project.title,
        available=tuple((item.reference, item.title) for item in project.editor_materials),
        items=tuple(
            (item.material_reference, materials[item.material_reference].title, item.section, item.note)
            for item in project.chief_editor_items
            if item.material_reference in materials
        ),
        status=status,
    )


def _scout_provider_values(value: object) -> tuple[str, str, str]:
    if type(value) is not dict or set(value) != {"provider", "base_url", "model"}:
        raise _DesktopShellConfigurationError() from None
    provider, base_url, model = (
        value["provider"],
        value["base_url"],
        value["model"],
    )
    if (
        provider not in {"openai", "ollama"}
        or not all(_safe_input(item) for item in (base_url, model))
    ):
        raise _DesktopShellConfigurationError() from None
    return provider, base_url.rstrip("/"), model


def _save_scout_provider_settings(*, path: Path, current: object, value: object):
    provider, base_url, model = _scout_provider_values(value)
    names = tuple(WindowsSettingsV1.__dataclass_fields__)
    values = {name: getattr(current, name) for name in names}
    values.update(
        scout_provider=provider,
        ollama_base_url=base_url,
        ollama_model=model,
    )
    settings = WindowsSettingsV1(**values)
    _save_windows_settings_v1(path=path, settings=settings)
    return settings


def _publish_scout_result(view: object, value: object) -> None:
    result = reconstruct_scout_desktop_result(value)
    report = result.report_reference
    view.publish_scout_result(  # type: ignore[attr-defined]
        summary=(
            f"Surse: {result.sources_checked}; reușite: {result.sources_succeeded}; "
            f"nereușite: {result.sources_failed}; articole: {result.articles_found}; "
            f"noi: {result.articles_inserted}; duplicate: {result.duplicates_skipped}."
        ),
        failed_sources=result.failed_source_ids,
        footer=result.status.value,
        report_reference=None if report is None else report.report_reference,
    )


def _publish_editor_result(view: object, value: object) -> None:
    result = reconstruct_editor_desktop_result(value)
    view.publish_editor_result(  # type: ignore[attr-defined]
        status=result.application_result.status.value
    )


def _present_startup_failure(root: object, *, key: str = "startup.error") -> None:
    try:
        messagebox.showerror(
            title=_text_v1(key="app.title"),
            message=_text_v1(key=key),
            parent=root,
        )
    except BaseException:
        pass


def _safe_input(value: object) -> bool:
    return (
        type(value) is str
        and bool(value)
        and value == value.strip()
        and unicodedata.is_normalized("NFC", value)
        and all(
            ord(character) >= 32
            and not 127 <= ord(character) <= 159
            and not 0xD800 <= ord(character) <= 0xDFFF
            for character in value
        )
    )
