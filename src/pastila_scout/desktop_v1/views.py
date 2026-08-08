"""Tkinter/ttk structural views for the private desktop shell."""

# ruff: noqa: BLE001

from __future__ import annotations

import inspect
import threading
import tkinter
import types
from tkinter import ttk

from .errors import _DesktopShellConfigurationError
from .models import (
    _DesktopEditorActionInputV1,
    _DesktopPageV1,
    _DesktopScoutActionInputV1,
    _DesktopShellSnapshotV1,
    _DesktopTaskStateV1,
)
from .resources import _text_v1
from .settings import (
    _DesktopSettingsProjectionV1,
    _reconstruct_desktop_settings_projection_v1,
)


def _validate_binding(value: object, parameter: str) -> None:
    target = value
    drop_self = False
    if type(value) is types.FunctionType:
        if (
            inspect.getattr_static(value, "__signature__", None) is not None
            or inspect.getattr_static(value, "__wrapped__", None) is not None
        ):
            raise _DesktopShellConfigurationError() from None
    elif type(value) is types.MethodType:
        target = value.__func__
        drop_self = True
    else:
        try:
            target = inspect.getattr_static(type(value), "__call__")
        except AttributeError:
            raise _DesktopShellConfigurationError() from None
        if isinstance(target, (property, staticmethod, classmethod)) or not callable(
            target
        ):
            raise _DesktopShellConfigurationError() from None
        drop_self = True
    try:
        parameters = tuple(
            inspect.signature(target, follow_wrapped=False).parameters.values()
        )
    except (TypeError, ValueError):
        raise _DesktopShellConfigurationError() from None
    if drop_self:
        parameters = parameters[1:]
    if (
        len(parameters) != 1
        or parameters[0].name != parameter
        or parameters[0].kind is not parameters[0].KEYWORD_ONLY
    ):
        raise _DesktopShellConfigurationError() from None


class _DesktopMainWindowV1:
    def __init__(
        self,
        *,
        root: tkinter.Tk,
        on_select_page,
        on_close,
        settings: _DesktopSettingsProjectionV1,
    ) -> None:
        if not callable(on_select_page) or not callable(on_close):
            raise _DesktopShellConfigurationError() from None
        self._root = root
        self._thread = threading.get_ident()
        self._closed = False
        self._bindings: dict[str, object] = {}
        self._report_reference: str | None = None
        self._about: tkinter.Toplevel | None = None
        self._on_select_page = on_select_page
        self._on_close = on_close
        self._settings = _reconstruct_desktop_settings_projection_v1(settings)
        root.title(_text_v1(key="app.title"))
        root.minsize(900, 600)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        self._main = ttk.Frame(root)
        self._main.grid(row=0, column=0, sticky="nsew")
        self._main.columnconfigure(1, weight=1)
        self._main.rowconfigure(0, weight=1)
        self._navigation = ttk.Treeview(
            self._main, show="tree", selectmode="browse", height=2
        )
        self._navigation.insert(
            "", "end", iid="scout", text=_text_v1(key="navigation.scout")
        )
        self._navigation.insert(
            "", "end", iid="editor", text=_text_v1(key="navigation.editor")
        )
        self._navigation.selection_set("scout")
        self._navigation.grid(row=0, column=0, sticky="ns", padx=(8, 4), pady=8)
        self._navigation.bind("<<TreeviewSelect>>", self._navigation_changed)
        self._content = ttk.Frame(self._main)
        self._content.grid(row=0, column=1, sticky="nsew", padx=(4, 8), pady=8)
        self._content.columnconfigure(0, weight=1)
        self._content.rowconfigure(0, weight=1)
        self._pages: dict[_DesktopPageV1, ttk.Frame] = {}
        self._build_scout()
        self._build_editor()
        self._build_menu()
        self._apply_settings()
        self._raise_page(_DesktopPageV1.SCOUT)

    def _apply_settings(self) -> None:
        settings = self._settings
        self._period.set(str(settings.scout_period_days))
        self._category.set(settings.scout_category)
        projected = {
            "selection_profile_path": settings.editor_profile_path,
            "episode_context_path": settings.editor_context_path,
            "generation_config_path": settings.editor_generation_path,
            "model": settings.editor_model,
            "timeout_seconds": settings.editor_timeout_seconds,
            "output_path": settings.editor_output_directory,
        }
        for name, value in projected.items():
            self._editor_values[name].set("" if value is None else str(value))
        self._provider.set(settings.editor_provider)

    def _check(self) -> None:
        if threading.get_ident() != self._thread or self._closed:
            raise _DesktopShellConfigurationError() from None

    def _build_scout(self) -> None:
        page = ttk.Frame(self._content)
        page.grid(row=0, column=0, sticky="nsew")
        page.columnconfigure(1, weight=1)
        self._pages[_DesktopPageV1.SCOUT] = page
        ttk.Label(page, text=_text_v1(key="scout.period")).grid(
            row=0, column=0, sticky="w"
        )
        self._period = tkinter.StringVar(value="")
        self._period_widget = ttk.Combobox(
            page, textvariable=self._period, state="disabled"
        )
        self._period_widget.grid(row=0, column=1, sticky="ew")
        ttk.Label(page, text=_text_v1(key="scout.category")).grid(
            row=1, column=0, sticky="w"
        )
        self._category = tkinter.StringVar(value="")
        self._category_widget = ttk.Combobox(
            page, textvariable=self._category, state="disabled"
        )
        self._category_widget.grid(row=1, column=1, sticky="ew")
        self._scout_button = ttk.Button(
            page, text=_text_v1(key="scout.run"), state="disabled", command=self._scout
        )
        self._scout_button.grid(row=2, column=0, columnspan=2, pady=8)
        self._progress = ttk.Progressbar(page, mode="determinate", value=0)
        self._progress.grid(row=3, column=0, columnspan=2, sticky="ew")
        self._status = tkinter.StringVar(value=_text_v1(key="scout.intro"))
        ttk.Label(page, textvariable=self._status).grid(
            row=4, column=0, columnspan=2, sticky="w"
        )
        ttk.Label(page, text=_text_v1(key="scout.results")).grid(
            row=5, column=0, sticky="w"
        )
        self._summary = tkinter.StringVar(value="0")
        ttk.Label(page, textvariable=self._summary).grid(row=5, column=1, sticky="w")
        ttk.Label(page, text=_text_v1(key="scout.failed_sources")).grid(
            row=6, column=0, sticky="nw"
        )
        self._failed = tkinter.StringVar(value="")
        ttk.Label(page, textvariable=self._failed).grid(row=6, column=1, sticky="w")
        self._report_button = ttk.Button(
            page,
            text=_text_v1(key="scout.report"),
            state="disabled",
            command=self._report,
        )
        self._report_button.grid(row=7, column=0, columnspan=2)
        self._footer = tkinter.StringVar(value="")
        ttk.Label(page, textvariable=self._footer).grid(
            row=8, column=0, columnspan=2, sticky="w"
        )

    def _build_editor(self) -> None:
        page = ttk.Frame(self._content)
        page.grid(row=0, column=0, sticky="nsew")
        page.columnconfigure(1, weight=1)
        self._pages[_DesktopPageV1.EDITOR] = page
        ttk.Label(page, text=_text_v1(key="editor.title")).grid(
            row=0, column=0, columnspan=2
        )
        self._editor_status = tkinter.StringVar(
            value=_text_v1(key="editor.unavailable")
        )
        ttk.Label(page, textvariable=self._editor_status).grid(
            row=1, column=0, columnspan=2
        )
        fields = (
            ("scout_input_path", "editor.scout_input"),
            ("selection_profile_path", "editor.selection_profile"),
            ("episode_context_path", "editor.episode_context"),
            ("generation_config_path", "editor.generation_config"),
            ("model", "editor.model"),
            ("timeout_seconds", "editor.timeout"),
            ("output_path", "editor.output"),
        )
        self._editor_values: dict[str, tkinter.StringVar] = {}
        self._editor_widgets: list[ttk.Widget] = []
        for row, (name, key) in enumerate(fields, start=2):
            ttk.Label(page, text=_text_v1(key=key)).grid(row=row, column=0, sticky="w")
            value = tkinter.StringVar(value="")
            widget = ttk.Entry(page, textvariable=value, state="disabled")
            widget.grid(row=row, column=1, sticky="ew")
            self._editor_values[name] = value
            self._editor_widgets.append(widget)
        row = 2 + len(fields)
        ttk.Label(page, text=_text_v1(key="editor.provider")).grid(
            row=row, column=0, sticky="w"
        )
        self._provider = tkinter.StringVar(value="openai")
        provider = ttk.Combobox(
            page,
            textvariable=self._provider,
            values=("openai", "ollama"),
            state="disabled",
        )
        provider.grid(row=row, column=1, sticky="ew")
        self._editor_widgets.append(provider)
        self._no_replace = tkinter.BooleanVar(value=True)
        check = ttk.Checkbutton(
            page,
            text=_text_v1(key="editor.no_replace"),
            variable=self._no_replace,
            state="disabled",
        )
        check.grid(row=row + 1, column=0, columnspan=2)
        self._editor_widgets.append(check)
        self._editor_button = ttk.Button(
            page,
            text=_text_v1(key="editor.run"),
            state="disabled",
            command=self._editor,
        )
        self._editor_button.grid(row=row + 2, column=0, columnspan=2)

    def _build_menu(self) -> None:
        menu = tkinter.Menu(self._root)
        file_menu = tkinter.Menu(menu, tearoff=False)
        file_menu.add_command(
            label=_text_v1(key="menu.file.exit"), command=self._on_close
        )
        menu.add_cascade(label=_text_v1(key="menu.file"), menu=file_menu)
        view_menu = tkinter.Menu(menu, tearoff=False)
        view_menu.add_command(
            label=_text_v1(key="menu.view.scout"),
            command=lambda: self._select(_DesktopPageV1.SCOUT),
        )
        view_menu.add_command(
            label=_text_v1(key="menu.view.editor"),
            command=lambda: self._select(_DesktopPageV1.EDITOR),
        )
        menu.add_cascade(label=_text_v1(key="menu.view"), menu=view_menu)
        help_menu = tkinter.Menu(menu, tearoff=False)
        help_menu.add_command(
            label=_text_v1(key="menu.help.about"), command=self._show_about
        )
        help_menu.add_command(
            label=_text_v1(key="menu.help.check_updates"), state="disabled"
        )
        menu.add_cascade(label=_text_v1(key="menu.help"), menu=help_menu)
        self._root.configure(menu=menu)
        self._menu = menu

    def _select(self, page: _DesktopPageV1) -> None:
        self._check()
        self._navigation.selection_set(page.value)
        self._on_select_page(page=page)

    def _navigation_changed(self, event: object) -> None:
        del event
        self._check()
        selected = self._navigation.selection()
        if selected and selected[0] in {"scout", "editor"}:
            self._on_select_page(page=_DesktopPageV1(selected[0]))

    def _raise_page(self, page: _DesktopPageV1) -> None:
        self._pages[page].tkraise()

    def _show_about(self) -> None:
        self._check()
        if self._about is not None and self._about.winfo_exists():
            self._about.lift()
            return
        child = tkinter.Toplevel(self._root)
        child.title(_text_v1(key="about.title"))
        child.transient(self._root)
        ttk.Label(child, text=_text_v1(key="about.body")).grid(
            row=0, column=0, padx=20, pady=12
        )
        ttk.Label(child, text=_text_v1(key="about.version")).grid(
            row=1, column=0, padx=20, pady=4
        )
        ttk.Button(child, text="OK", command=child.destroy).grid(
            row=2, column=0, pady=8
        )
        child.grab_set()
        self._about = child

    def bind_scout_action(self, *, callback) -> None:
        self._bind("scout", callback)
        self._period_widget.configure(state="normal")
        self._category_widget.configure(state="normal")
        self._scout_button.configure(state="normal")

    def bind_editor_action(self, *, callback) -> None:
        self._bind("editor", callback)
        for widget in self._editor_widgets:
            widget.configure(
                state="normal" if not isinstance(widget, ttk.Combobox) else "readonly"
            )
        self._editor_button.configure(state="normal")

    def bind_report_action(self, *, callback) -> None:
        self._bind("report", callback)
        self._sync_report()

    def _bind(self, name: str, callback: object) -> None:
        self._check()
        _validate_binding(callback, "reference" if name == "report" else "input")
        if name in self._bindings:
            raise _DesktopShellConfigurationError() from None
        self._bindings[name] = callback

    def _scout(self) -> None:
        self._invoke(
            "scout",
            input=_DesktopScoutActionInputV1(self._period.get(), self._category.get()),
        )

    def _editor(self) -> None:
        values = {name: value.get() for name, value in self._editor_values.items()}
        values.update(
            provider=self._provider.get(), no_replace=bool(self._no_replace.get())
        )
        self._invoke("editor", input=_DesktopEditorActionInputV1(**values))

    def _report(self) -> None:
        self._invoke("report", reference=self._report_reference)

    def _invoke(self, name: str, **kwargs: object) -> None:
        self._check()
        callback = self._bindings.get(name)
        if callback is None:
            raise _DesktopShellConfigurationError() from None
        try:
            callback(**kwargs)  # type: ignore[operator]
        except BaseException:
            self._status.set(_text_v1(key="error.internal"))

    def publish_scout_result(
        self,
        *,
        summary: str,
        failed_sources: tuple[str, ...],
        footer: str,
        report_reference: str | None,
    ) -> None:
        self._check()
        if (
            type(summary) is not str
            or type(failed_sources) is not tuple
            or any(type(x) is not str for x in failed_sources)
            or type(footer) is not str
            or (
                report_reference is not None
                and (type(report_reference) is not str or not report_reference)
            )
        ):
            raise _DesktopShellConfigurationError() from None
        self._summary.set(summary)
        self._failed.set("\n".join(failed_sources))
        self._footer.set(footer)
        self._report_reference = report_reference
        self._sync_report()

    def publish_editor_result(self, *, status: str) -> None:
        self._check()
        if type(status) is not str:
            raise _DesktopShellConfigurationError() from None
        self._editor_status.set(status)

    def _sync_report(self) -> None:
        state = (
            "normal"
            if "report" in self._bindings and self._report_reference
            else "disabled"
        )
        self._report_button.configure(state=state)

    def publish_snapshot(self, *, snapshot: _DesktopShellSnapshotV1) -> None:
        self._check()
        if type(snapshot) is not _DesktopShellSnapshotV1:
            raise _DesktopShellConfigurationError() from None
        self._raise_page(snapshot.selected_page)
        self._navigation.selection_set(snapshot.selected_page.value)
        idle = snapshot.application_state is _DesktopTaskStateV1.IDLE
        self._scout_button.configure(
            state="normal" if idle and "scout" in self._bindings else "disabled"
        )
        self._editor_button.configure(
            state="normal" if idle and "editor" in self._bindings else "disabled"
        )
        if snapshot.is_closed:
            self._navigation.configure(selectmode="none")
            self._scout_button.configure(state="disabled")
            self._editor_button.configure(state="disabled")
            self._report_button.configure(state="disabled")

    def __repr__(self) -> str:
        return "_DesktopMainWindowV1(<redacted>)"

    def __init_subclass__(cls, **kwargs: object) -> None:
        del cls, kwargs
        raise TypeError("_DesktopMainWindowV1 is final")

    def __copy__(self):
        raise TypeError("_DesktopMainWindowV1 does not support copy")

    __deepcopy__ = __copy__

    def __reduce_ex__(self, protocol: int):
        del protocol
        raise TypeError("_DesktopMainWindowV1 does not support pickle")
