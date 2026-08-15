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
from collections.abc import Mapping
from datetime import UTC, datetime
from pathlib import Path
from tkinter import filedialog, messagebox, ttk
from typing import NoReturn

import httpx

from pastila_scout.active_project_v1 import ActiveProjectStoreV1, ChiefEditorItemV1
from pastila_scout.ai.provider import resolve_openai_api_key
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
from .editor_batch import _run_editor_batch_v1
from .episode_draft import (
    _approve_episode_draft_v1,
    _handoff_episode_draft_for_approval_v1,
    _publish_episode_draft_v1,
    _recover_episode_draft_v1,
)
from .episode_draft_export import (
    _episode_draft_default_filename_v1,
    _export_current_episode_draft_v1,
)
from .errors import _DesktopShellConfigurationError, _DesktopShellExecutionError
from .first_run import _complete_desktop_setup_v1, _inspect_desktop_readiness_v1
from .integrated_editor import _integrated_editor_request_v1
from .models import (
    _DesktopPageV1,
    _DesktopTaskStateV1,
    _reconstruct_desktop_editor_action_input_v1,
    _reconstruct_desktop_scout_action_input_v1,
)
from .resources import _text_v1
from .settings import _project_desktop_settings_v1
from .source_settings import (
    _add_scout_source_v1,
    _rebase_scout_sources_override_v1,
)
from .state_composition import (
    _compose_state_bound_desktop_application_v1,
    _DesktopStateConsumptionError,
)
from .views import _PRIMARY_LABEL_STYLE, _configure_desktop_styles, _DesktopMainWindowV1


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

        environment = dict(os.environ)
        state = _compose_state_bound_desktop_application_v1(
            frozen=frozen,
            environment=environment,
            development_root=development_root,
            migration_consent=migration_consent,
        )
        facade = state.facade
        project_store = ActiveProjectStoreV1(
            database_path=state.database_path,
            project_path=state.active_project_path,
        )
        source_override = state.settings_path.parent / "sources.override.yaml"
        canonical_sources = _canonical_scout_sources_path_v1(
            frozen=frozen,
            development_root=development_root,
            environment=environment,
        )
        sources_path = _rebase_scout_sources_override_v1(
            canonical_path=canonical_sources,
            override_path=source_override,
        )
        settings = state.settings
        if sources_path.is_file() and hasattr(state.settings, "scout_provider"):
            readiness = _inspect_desktop_readiness_v1(
                settings=state.settings,
                settings_path=state.settings_path,
                sources_path=sources_path,
                default_output_directory=state.database_path.parent.parent / "reports",
                project_store=project_store,
            )
            if readiness.setup_required:
                settings = _show_first_run_setup(root, state, readiness)
                if settings is None:
                    return 0
            active_project = readiness.active_project
            if readiness.project_warning:
                messagebox.showwarning(
                    title=_text_v1(key="setup.title"),
                    message=readiness.project_warning,
                    parent=root,
                )
        else:  # compatibility for injected startup test compositions
            active_project = project_store.load()
        cells: dict[str, object] = {
            "facade": facade,
            "project": active_project,
            "settings": settings,
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
            if snapshot.application_state is _DesktopTaskStateV1.FAILED:
                cells["editor_batch_polling"] = False
                failed_project = project_store.load_runtime_state()
                if failed_project is not None:
                    cells["project"] = failed_project
                    _publish_editor_worklist(view, failed_project)

        controller = _DesktopTaskControllerV1(
            schedule_after=root.after,
            cancel_after=root.after_cancel,
            publish_snapshot=publish_snapshot,
        )
        view = _DesktopMainWindowV1(
            root=root,
            on_select_page=select_page,
            on_close=close,
            settings=settings,
        )
        cells.update(controller=controller, view=view)

        def run_scout(*, input) -> None:
            request = _scout_request(input)

            def task():
                return facade.run_scout(
                    request=request, progress_sink=_DesktopStartupProgressSinkV1()
                )

            def on_completed(*, result) -> None:
                _publish_scout_completion(view, project_store, result)

            controller.submit_application(task=task, on_completed=on_completed)

        def run_editor(*, input) -> None:
            selected = _reconstruct_desktop_editor_action_input_v1(input)
            event_ids = selected.event_ids
            project = cells.get("project")
            if project is None:
                raise _DesktopShellConfigurationError() from None
            event_order = {
                event_id: index for index, event_id in enumerate(event_ids, 1)
            }
            event_titles = {
                event.event_id: event.canonical_title
                for event in project.scout_input.ranked_events
            }
            cells["editor_batch_polling"] = True

            def poll_editor_batch() -> None:
                if not cells.get("editor_batch_polling") or closed:
                    return
                current = project_store.load_runtime_state()
                if current is not None:
                    cells["project"] = current
                    _publish_editor_worklist(view, current)
                    running = tuple(
                        item.event_id
                        for item in current.editor_worklist
                        if item.status.value == "running"
                        and item.event_id in event_order
                    )
                    if running:
                        event_id = running[0]
                        view.publish_editor_result(
                            status=(
                                f"Se proceseaza {event_order[event_id]} din "
                                f"{len(event_ids)}: {event_titles[event_id]}"
                            )
                        )
                root.after(100, poll_editor_batch)

            root.after(0, poll_editor_batch)

            def task():
                def execute(event_id: int) -> tuple[Path, str]:
                    request = _integrated_editor_request_v1(
                        project=project,
                        settings=cells["settings"],
                        event_id=event_id,
                    )
                    result = facade.run_editor(
                        request=EditorDesktopRequestV1(application_request=request),
                        progress_sink=_DesktopStartupProgressSinkV1(),
                    )
                    application_result = reconstruct_editor_desktop_result(
                        result
                    ).application_result
                    if not (
                        application_result.handoff_permitted
                        and application_result.output_path == request.destination.path
                        and application_result.payload_sha256 is not None
                    ):
                        raise _DesktopShellExecutionError() from None
                    return (
                        application_result.output_path,
                        application_result.payload_sha256,
                    )

                return _run_editor_batch_v1(
                    store=project_store, event_ids=event_ids, execute=execute
                )

            def on_completed(*, result) -> None:
                cells["editor_batch_polling"] = False
                cells["project"] = project_store.load_runtime_state()
                _publish_editor_worklist(view, cells["project"])
                _publish_chief_editor(view, cells["project"])
                if hasattr(view, "publish_episode_draft"):
                    _publish_episode_draft_projection(
                        view, _recover_episode_draft_v1(store=project_store)
                    )
                view.publish_editor_result(
                    status=(
                        f"{len(result.attempted_event_ids)} procesate: "
                        f"{len(result.completed_event_ids)} generate, "
                        f"{len(result.failed_event_ids)} erori"
                    )
                )

            controller.submit_application(task=task, on_completed=on_completed)

        def open_report(*, reference: str) -> None:
            facade.open_report(reference=reference)

        def retry_editor(*, input: tuple[int, ...]) -> None:
            event_ids = input
            current = project_store.load_runtime_state()
            selected = set(event_ids)
            ordered = tuple(
                item.event_id
                for item in current.editor_worklist
                if item.event_id in selected
            )
            failed = {
                item.event_id
                for item in current.editor_worklist
                if item.status.value == "failed"
            }
            if (
                type(event_ids) is not tuple
                or not event_ids
                or len(ordered) != len(event_ids)
                or not selected.issubset(failed)
            ):
                raise _DesktopShellConfigurationError() from None
            project = project_store.retry_editor_items(event_ids=ordered)
            cells["project"] = project
            _publish_editor_worklist(view, project)

        def handoff(*, input) -> None:
            _complete_handoff(
                store=project_store,
                event_ids=input,
                cells=cells,
                view=view,
                controller=controller,
            )

        def save_chief_editor(*, input) -> None:
            project = _save_chief_editor(project_store, input)
            cells["project"] = project
            _publish_chief_editor(view, project, _text_v1(key="chief_editor.saved"))
            _publish_episode_draft_projection(
                view, _recover_episode_draft_v1(store=project_store)
            )

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
            _publish_episode_draft_projection(
                view, _recover_episode_draft_v1(store=project_store)
            )

        def publish_episode_draft(*, input) -> None:
            _queue_episode_draft_publication_v1(
                store=project_store,
                view=view,
                controller=controller,
                cells=cells,
                input=input,
                revision_root=state.database_path.parent / "episode-drafts",
            )

        def export_episode_draft(*, input) -> None:
            del input
            projection = _recover_episode_draft_v1(store=project_store)
            if not projection.current:
                view.publish_episode_draft_export_status(status=projection.status)
                return
            selected = filedialog.asksaveasfilename(
                parent=root,
                defaultextension=".md",
                filetypes=(("Markdown", "*.md"),),
                initialfile=_episode_draft_default_filename_v1(projection.revision_id),
                confirmoverwrite=False,
            )
            if not selected:
                view.publish_episode_draft_export_status(status="Export anulat.")
                return
            result = _export_current_episode_draft_v1(
                store=project_store, destination=Path(selected)
            )
            view.publish_episode_draft_export_status(status=result.status)

        def approve_episode_draft(*, input) -> None:
            del input
            result = _handoff_episode_draft_for_approval_v1(store=project_store)
            current = project_store.load_runtime_state()
            if current is not None:
                cells["project"] = current
            _publish_episode_draft_projection(view, result)

        def finalize_episode_draft(*, input) -> None:
            del input
            result = _approve_episode_draft_v1(store=project_store)
            current = project_store.load_runtime_state()
            if current is not None:
                cells["project"] = current
            _publish_episode_draft_projection(view, result)

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
                        ollama = OllamaHttpClientV1(client)
                        models = ollama.list_models(
                            base_url=values[1],
                            timeout=state.settings.scout_ai_timeout_seconds,
                        )
                        view.publish_scout_models(models=models)
                        ollama.check_model(
                            model=values[2],
                            base_url=values[1],
                            timeout=state.settings.scout_ai_timeout_seconds,
                        )
                status = _text_v1(key="scout.ollama_ready")
            except Exception:
                status = _text_v1(key="scout.ollama_unavailable")
            view.publish_scout_provider_status(status=status)

        def save_scout_source(*, input) -> None:
            selected_sources = (
                source_override if source_override.is_file() else sources_path
            )
            result = _add_scout_source_v1(
                url=input, current_path=selected_sources, override_path=source_override
            )
            if result == "saved":
                scout_operation = object.__getattribute__(facade, "_scout_operation")
                object.__setattr__(scout_operation, "_sources_path", source_override)
            view.publish_source_status(
                status=_text_v1(key=f"scout.source_{result}"),
                clear=result == "saved",
            )

        view.bind_scout_action(callback=run_scout)
        view.bind_editor_action(callback=run_editor)
        view.bind_editor_retry_action(callback=retry_editor)
        view.bind_report_action(callback=open_report)
        view.bind_handoff_action(callback=handoff)
        view.bind_chief_editor_actions(
            save_callback=save_chief_editor, export_callback=export_chief_editor
        )
        if hasattr(view, "bind_episode_draft_action"):
            view.bind_episode_draft_action(callback=publish_episode_draft)
        if hasattr(view, "bind_episode_draft_export_action"):
            view.bind_episode_draft_export_action(callback=export_episode_draft)
        if hasattr(view, "bind_episode_draft_approval_action"):
            view.bind_episode_draft_approval_action(callback=approve_episode_draft)
        if hasattr(view, "bind_episode_draft_final_action"):
            view.bind_episode_draft_final_action(callback=finalize_episode_draft)
        view.bind_scout_provider_actions(
            save_callback=save_scout_provider, test_callback=test_scout_provider
        )
        if hasattr(view, "bind_scout_source_action"):
            view.bind_scout_source_action(callback=save_scout_source)
        _publish_candidates(
            view, project_store, getattr(settings, "scout_category", None)
        )
        if active_project is not None:
            view.publish_active_project(
                title=active_project.title,
                message=_text_v1(key="scout.handoff_success"),
            )
            _publish_editor_worklist(view, active_project)
            _publish_chief_editor(view, active_project)
            if hasattr(view, "publish_episode_draft"):
                _publish_episode_draft_projection(
                    view, _recover_episode_draft_v1(store=project_store)
                )
            controller.select_page(
                page=(
                    _DesktopPageV1.CHIEF_EDITOR
                    if active_project.editor_materials
                    else _DesktopPageV1.EDITOR
                )
            )
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


def _canonical_scout_sources_path_v1(
    *,
    frozen: bool,
    development_root: Path | None,
    environment: Mapping[str, str],
) -> Path:
    if frozen:
        return (
            Path(environment["LOCALAPPDATA"])
            / "Programs"
            / "PastilaScout"
            / "app"
            / "config"
            / "sources.yaml"
        )
    if development_root is None:
        raise TypeError("Development root is required")
    return development_root / "config" / "sources.yaml"


def _scout_request(value: object) -> ScoutDesktopRequestV1:
    try:
        valid = _reconstruct_desktop_scout_action_input_v1(value)
        period = int(valid.period, 10)
        if str(period) != valid.period:
            raise ValueError
        category = ScoutDesktopCategoryV1(valid.category)
        targeted_query = valid.targeted_query.strip() or None
        return ScoutDesktopRequestV1(
            operation_reference=f"scout-desktop-v1:{uuid.uuid4().hex}",
            period_days=period,
            category=category,
            targeted_query=targeted_query,
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


def _publish_candidates(
    view: object, store: ActiveProjectStoreV1, category: str | None = None
) -> None:
    if category is None or category in {"all", "Toate"}:
        useful_loader = getattr(store, "list_useful_candidates_v1_2", None)
        candidates = (
            useful_loader()
            if useful_loader is not None
            else store.list_candidates(category=category)
        )
    else:
        candidates = store.list_candidates(category=category)
    view.publish_candidates(  # type: ignore[attr-defined]
        candidates=tuple(
            (item.event_id, item.title, item.category, item.source_count)
            for item in candidates
        )
    )


def _publish_scout_completion(
    view: object, store: ActiveProjectStoreV1, value: object
) -> None:
    result = reconstruct_scout_desktop_result(value)
    _publish_scout_result(view, result)
    scoped_ids = result.targeted_candidate_ids
    if scoped_ids is None:
        _publish_candidates(
            view,
            store,
            None
            if result.executed_category is ScoutDesktopCategoryV1.ALL
            else result.executed_category.value,
        )
    else:
        _publish_scoped_candidates(view, store, scoped_ids)


def _publish_scoped_candidates(
    view: object, store: ActiveProjectStoreV1, event_ids: tuple[int, ...]
) -> None:
    candidates = store.list_candidates_by_ids(event_ids=event_ids)
    view.publish_candidates(  # type: ignore[attr-defined]
        candidates=tuple(
            (item.event_id, item.title, item.category, item.source_count)
            for item in candidates
        )
    )


def _complete_handoff(
    *,
    store,
    event_ids: tuple[int, ...] | None = None,
    event_id: int | None = None,
    cells,
    view,
    controller,
) -> bool:
    try:
        if event_ids is None:
            event_ids = (event_id,) if type(event_id) is int else ()
        project, skipped = store.handoff_many(event_ids=event_ids)
    except Exception:
        view.publish_active_project(
            title="—", message=_text_v1(key="scout.handoff_failure")
        )
        return False
    cells["project"] = project
    added = len(event_ids) - skipped
    message = (
        _text_v1(key="scout.handoff_success")
        if added == 1
        else _text_v1(key="scout.handoff_many").format(count=added)
    )
    if skipped:
        message += _text_v1(key="scout.handoff_duplicates").format(count=skipped)
    view.publish_active_project(title=project.title, message=message)
    _publish_editor_worklist(view, project)
    if hasattr(view, "publish_episode_draft"):
        _publish_episode_draft_projection(view, _recover_episode_draft_v1(store=store))
    controller.select_page(page=_DesktopPageV1.EDITOR)
    return True


def _publish_editor_worklist(view: object, project: object) -> None:
    events = {item.event_id: item for item in project.scout_input.ranked_events}
    view.publish_editor_worklist(  # type: ignore[attr-defined]
        items=tuple(
            (
                item.event_id,
                events[item.event_id].canonical_title,
                item.status.value,
            )
            for item in project.editor_worklist
        ),
    )


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
        available=tuple(
            (item.reference, item.title) for item in project.editor_materials
        ),
        items=tuple(
            (
                item.material_reference,
                materials[item.material_reference].title,
                item.section,
                item.note,
            )
            for item in project.chief_editor_items
            if item.material_reference in materials
        ),
        status=status,
        can_publish_episode_draft=(
            sum(item.status.value == "completed" for item in project.editor_worklist)
            >= 5
        ),
    )


def _publish_episode_draft_projection(view: object, projection: object) -> None:
    view.publish_episode_draft(  # type: ignore[attr-defined]
        status=projection.status,
        current=projection.current,
        revision_id=projection.revision_id,
        parent_revision_id=projection.parent_revision_id,
        included=projection.included,
        excluded=projection.excluded,
        assembled_text=projection.assembled_text,
        approval_pending=projection.approval_pending,
        can_submit_approval=projection.can_submit_approval,
        approval_approved=projection.approval_approved,
        can_approve=projection.can_approve,
    )


def _queue_episode_draft_publication_v1(
    *, store, view, controller, cells: dict[str, object], input, revision_root: Path
) -> None:
    project = _save_chief_editor(store, input)
    cells["project"] = project
    _publish_chief_editor(view, project)

    def task():
        return _publish_episode_draft_v1(
            store=store,
            revision_root=revision_root,
        )

    def on_completed(*, result) -> None:
        current = store.load_runtime_state()
        if current is not None:
            cells["project"] = current
            _publish_chief_editor(view, current)
        _publish_episode_draft_projection(view, result)

    controller.submit_application(task=task, on_completed=on_completed)


def _scout_provider_values(value: object) -> tuple[str, str, str]:
    if type(value) is not dict or set(value) != {"provider", "base_url", "model"}:
        raise _DesktopShellConfigurationError() from None
    provider, base_url, model = (
        value["provider"],
        value["base_url"],
        value["model"],
    )
    if provider not in {"openai", "ollama"} or not all(
        _safe_input(item) for item in (base_url, model)
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
        editor_provider=provider,
        editor_model=model,
    )
    settings = WindowsSettingsV1(**values)
    _save_windows_settings_v1(path=path, settings=settings)
    return settings


def _publish_scout_result(view: object, value: object) -> None:
    result = reconstruct_scout_desktop_result(value)
    report = result.report_reference
    view.publish_scout_result(  # type: ignore[attr-defined]
        summary=(
            f"{result.articles_found} articole - {result.articles_inserted} noi - "
            f"duplicate: {result.duplicates_skipped}"
        ),
        sources_available=result.sources_checked,
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


def _show_first_run_setup(root: object, state: object, readiness: object):
    """Show compact setup without performing provider calls."""
    window = tkinter.Toplevel(root)
    _configure_desktop_styles(root)
    window.title(_text_v1(key="setup.title"))
    window.resizable(False, False)
    provider = tkinter.StringVar(value=state.settings.scout_provider)
    base_url = "http://localhost:11434"
    model = tkinter.StringVar(value=state.settings.ollama_model)
    result: list[object] = []
    ttk.Label(window, text=_text_v1(key="setup.intro"), wraplength=520).grid(
        row=0, column=0, columnspan=2, padx=16, pady=10, sticky="w"
    )
    for row, (label, variable) in enumerate(
        (("AI Engine", provider), ("Model", model)), start=1
    ):
        ttk.Label(window, text=label, style=_PRIMARY_LABEL_STYLE).grid(
            row=row, column=0, padx=16, sticky="w"
        )
        if row == 1:
            ttk.Combobox(
                window,
                textvariable=variable,
                values=("openai", "ollama"),
                state="readonly",
            ).grid(row=row, column=1, padx=16, sticky="ew")
        else:
            model_widget = ttk.Combobox(
                window, textvariable=variable, state="readonly", width=36
            )
            model_widget.grid(row=row, column=1, padx=16)
    names = (
        ", ".join(
            f"{item.name} ({'activa' if item.enabled else 'inactiva'})"
            for item in readiness.sources
        )
        or "Nicio sursa configurata"
    )
    ttk.Label(window, text=f"Surse active: {names}", wraplength=520).grid(
        row=4, column=0, columnspan=2, padx=16, pady=8, sticky="w"
    )
    ttk.Label(
        window, text=f"Iesire: {readiness.output_directory}", wraplength=520
    ).grid(row=5, column=0, columnspan=2, padx=16, sticky="w")
    status = tkinter.StringVar(value="")
    ollama_verified = [False]
    ttk.Label(window, textvariable=status).grid(row=6, column=0, columnspan=2, padx=16)

    def test_ollama() -> None:
        if provider.get() != "ollama":
            status.set(_text_v1(key="setup.openai_local"))
            return
        try:
            with httpx.Client() as client:
                ollama = OllamaHttpClientV1(client)
                models = ollama.list_models(
                    base_url=base_url,
                    timeout=state.settings.scout_ai_timeout_seconds,
                )
                model_widget.configure(values=models)
                if not models:
                    status.set(_text_v1(key="setup.ollama_no_models"))
                    return
                if model.get() not in models:
                    model.set(models[0])
                ollama.check_model(
                    model=model.get(),
                    base_url=base_url,
                    timeout=state.settings.scout_ai_timeout_seconds,
                )
            status.set(_text_v1(key="scout.ollama_ready"))
            ollama_verified[0] = True
        except Exception:
            status.set(_text_v1(key="scout.ollama_unavailable"))

    def finish() -> None:
        if not readiness.enabled_sources:
            status.set(_text_v1(key="setup.no_sources"))
            return
        if provider.get() == "openai" and not resolve_openai_api_key():
            status.set(_text_v1(key="setup.openai_missing"))
            return
        if provider.get() == "ollama" and not ollama_verified[0]:
            status.set(_text_v1(key="setup.ollama_test_required"))
            return
        try:
            completed = _complete_desktop_setup_v1(
                settings=state.settings,
                settings_path=state.settings_path,
                provider=provider.get(),
                base_url=base_url,
                model=model.get(),
                output_directory=readiness.output_directory,
            )
        except Exception:
            status.set(_text_v1(key="setup.invalid"))
            return
        result.append(_desktop_setup_settings_v1(completed))
        window.destroy()

    buttons = ttk.Frame(window)
    buttons.grid(row=7, column=0, columnspan=2, pady=12)
    ttk.Button(
        buttons, text=_text_v1(key="scout.provider_test"), command=test_ollama
    ).pack(side="left")
    ttk.Button(buttons, text=_text_v1(key="setup.continue"), command=finish).pack(
        side="left"
    )
    _present_first_run_window(root=root, window=window)
    return result[0] if result else None


def _present_first_run_window(*, root: object, window: object) -> None:
    """Present setup independently of the intentionally withdrawn shell root."""
    window.protocol("WM_DELETE_WINDOW", window.destroy)
    window.deiconify()
    window.lift()
    window.grab_set()
    root.wait_window(window)


def _desktop_setup_settings_v1(settings: WindowsSettingsV1):
    """Project newly persisted Windows settings into the desktop shell type."""
    return _project_desktop_settings_v1(settings=settings)
