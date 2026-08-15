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

_SCOUT_PERIOD_CHOICES = ("1", "3", "7", "14", "30")
_OPENAI_MODEL_CHOICES = ("gpt-4.1-mini",)
_SCOUT_CATEGORY_CHOICES = (
    "Toate",
    "Politica",
    "Social",
    "CanCan",
    "Diverse",
    "Externe",
)
_EDITOR_REQUIRED_CONFIGURATION = ("model", "timeout_seconds", "output_path")
_BUTTON_STYLE = "TButton"
_PRIMARY_LABEL_STYLE = "PastilaPrimary.TLabel"
_PRIMARY_ACTION_COLOR = "#e31919"
_LATEST_LABEL_STYLE = "PastilaLatest.TLabel"
_SOURCE_LABEL_STYLE = "PastilaSource.TLabel"
_SCOUT_STATUS_STYLE = "PastilaScoutStatus.TLabel"
_SCOUT_PROGRESS_STYLE = "PastilaScout.Horizontal.TProgressbar"
_SCOUT_PROGRESS_COLOR = "#17843b"
_SOURCE_LABEL_COLOR = "#2563b8"
_SEARCH_LABEL_COLUMN = 0
_SEARCH_ENTRY_COLUMN = 1
_SEARCH_ACTION_COLUMN = 2
_PRIMARY_ACTION_BUTTON_OPTIONS = {
    "activebackground": "#ffffff",
    "activeforeground": _PRIMARY_ACTION_COLOR,
    "background": "#ffffff",
    "borderwidth": 0,
    "disabledforeground": "#777777",
    "font": ("TkDefaultFont", 11, "bold"),
    "foreground": _PRIMARY_ACTION_COLOR,
    "height": 1,
    "highlightthickness": 0,
    "padx": 4,
    "pady": 2,
    "relief": "flat",
    "width": 16,
}


def _configure_desktop_styles(root: object) -> None:
    style = ttk.Style(root)
    style.configure(
        _BUTTON_STYLE,
        anchor="center",
        justify="center",
        borderwidth=1,
        relief="solid",
        bordercolor="#000000",
        lightcolor="#000000",
        darkcolor="#000000",
    )
    style.map(
        _BUTTON_STYLE,
        foreground=(("disabled", "#777777"), ("!disabled", "#000000")),
    )
    style.configure(_PRIMARY_LABEL_STYLE, font=("TkDefaultFont", 9, "bold"))
    style.configure(
        _LATEST_LABEL_STYLE,
        font=("TkDefaultFont", 9, "bold"),
        foreground=_PRIMARY_ACTION_COLOR,
    )
    style.configure(
        _SOURCE_LABEL_STYLE,
        font=("TkDefaultFont", 9, "bold"),
        foreground=_SOURCE_LABEL_COLOR,
    )
    style.configure(
        _SCOUT_STATUS_STYLE,
        foreground=_PRIMARY_ACTION_COLOR,
        font=("TkDefaultFont", 9, "bold"),
    )
    style.configure(
        _SCOUT_PROGRESS_STYLE,
        background=_SCOUT_PROGRESS_COLOR,
        troughcolor="#e5e7eb",
        borderwidth=0,
        lightcolor=_SCOUT_PROGRESS_COLOR,
        darkcolor=_SCOUT_PROGRESS_COLOR,
    )


def _primary_action_button(
    parent: tkinter.Misc, *, text: str, command: object, state: str = "normal"
) -> tkinter.Button:
    border = tkinter.Frame(parent, background=_PRIMARY_ACTION_COLOR, padx=1, pady=1)
    button = tkinter.Button(
        border,
        text=text,
        state=state,
        command=command,
        **_PRIMARY_ACTION_BUTTON_OPTIONS,
    )
    button.pack()
    return button


def _editor_configuration_ready(
    values: dict[str, tkinter.StringVar], *, provider: str
) -> bool:
    return provider in {"openai", "ollama"} and all(
        values[name].get().strip() for name in _EDITOR_REQUIRED_CONFIGURATION
    )


def _editor_selection_supported(
    *, selected_event_ids: tuple[int, ...], eligible_event_ids: frozenset[int]
) -> bool:
    return bool(selected_event_ids) and set(selected_event_ids).issubset(
        eligible_event_ids
    )


def _editor_action_enabled(
    *,
    idle: bool,
    callback_bound: bool,
    configuration_ready: bool,
    selected_event_ids: tuple[int, ...],
    eligible_event_ids: frozenset[int],
) -> bool:
    return (
        idle
        and callback_bound
        and configuration_ready
        and _editor_selection_supported(
            selected_event_ids=selected_event_ids,
            eligible_event_ids=eligible_event_ids,
        )
    )


def _restored_candidate_summary(*, current: str, count: int) -> str:
    if type(current) is not str or type(count) is not int or count < 0:
        raise _DesktopShellConfigurationError() from None
    if current != "0":
        return current
    return f"{count} {'stire restaurata' if count == 1 else 'stiri restaurate'}"


def _failed_sources_summary(failed_sources: tuple[str, ...]) -> str:
    if type(failed_sources) is not tuple or any(
        type(value) is not str for value in failed_sources
    ):
        raise _DesktopShellConfigurationError() from None
    return str(len(failed_sources))


def _handoff_label(count: int) -> str:
    base = _text_v1(key="scout.send_editor")
    return f"{base} ({count})" if count > 1 else base


def _editor_display_model(settings: _DesktopSettingsProjectionV1) -> str:
    return (
        settings.ollama_model
        if settings.editor_provider == "ollama"
        else settings.editor_model
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
    except TypeError, ValueError:
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
        _configure_desktop_styles(root)
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
        self._navigation.insert(
            "", "end", iid="chief_editor", text=_text_v1(key="navigation.chief_editor")
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
        self._build_chief_editor()
        self._build_menu()
        self._apply_settings()
        self._raise_page(_DesktopPageV1.SCOUT)

    def _apply_settings(self) -> None:
        settings = self._settings
        self._period.set(str(settings.scout_period_days))
        self._category.set(
            "Toate" if settings.scout_category == "all" else settings.scout_category
        )
        self._scout_provider.set(settings.scout_provider)
        self._ollama_url.set(settings.ollama_base_url)
        self._ollama_model.set(settings.ollama_model)
        self._model_widget.configure(
            values=(
                (settings.ollama_model,)
                if settings.scout_provider == "ollama"
                else (settings.editor_model,)
            )
        )
        projected = {
            "selection_profile_path": settings.editor_profile_path,
            "episode_context_path": settings.editor_context_path,
            "generation_config_path": settings.editor_generation_path,
            "model": _editor_display_model(settings),
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
        ttk.Label(
            page, text=_text_v1(key="scout.period"), style=_PRIMARY_LABEL_STYLE
        ).grid(row=0, column=0, sticky="w")
        self._period = tkinter.StringVar(value="")
        self._period_widget = ttk.Combobox(
            page,
            textvariable=self._period,
            values=_SCOUT_PERIOD_CHOICES,
            state="disabled",
        )
        self._period_widget.grid(row=0, column=1, sticky="ew")
        ttk.Label(
            page, text=_text_v1(key="scout.category"), style=_PRIMARY_LABEL_STYLE
        ).grid(row=1, column=0, sticky="w")
        self._category = tkinter.StringVar(value="")
        self._category_widget = ttk.Combobox(
            page,
            textvariable=self._category,
            values=_SCOUT_CATEGORY_CHOICES,
            state="disabled",
        )
        self._category_widget.grid(row=1, column=1, sticky="ew")
        ttk.Label(
            page, text=_text_v1(key="scout.provider"), style=_PRIMARY_LABEL_STYLE
        ).grid(row=2, column=0, sticky="w")
        self._scout_provider = tkinter.StringVar(value="openai")
        self._scout_provider_widget = ttk.Combobox(
            page,
            textvariable=self._scout_provider,
            values=("openai", "ollama"),
            state="readonly",
        )
        self._scout_provider_widget.grid(row=2, column=1, sticky="ew")
        self._scout_provider_widget.bind("<<ComboboxSelected>>", self._provider_changed)
        self._ollama_url = tkinter.StringVar(value="")
        ttk.Label(
            page, text=_text_v1(key="scout.model"), style=_PRIMARY_LABEL_STYLE
        ).grid(row=3, column=0, sticky="w")
        self._ollama_model = tkinter.StringVar(value="")
        self._model_widget = ttk.Combobox(
            page, textvariable=self._ollama_model, state="readonly"
        )
        self._model_widget.grid(row=3, column=1, sticky="ew")
        provider_buttons = ttk.Frame(page)
        provider_buttons.grid(row=4, column=0, columnspan=2)
        ttk.Button(
            provider_buttons,
            text=_text_v1(key="scout.provider_save"),
            command=self._save_scout_provider,
        ).pack(side="left")
        ttk.Button(
            provider_buttons,
            text=_text_v1(key="scout.provider_test"),
            command=self._test_scout_provider,
        ).pack(side="left")
        search_section = ttk.Frame(page)
        search_section.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        search_section.columnconfigure(_SEARCH_ENTRY_COLUMN, weight=1)
        self._targeted_query_label = ttk.Label(
            search_section,
            text=_text_v1(key="scout.latest"),
            style=_LATEST_LABEL_STYLE,
        )
        self._targeted_query_label.grid(
            row=0, column=_SEARCH_LABEL_COLUMN, sticky="w", pady=(0, 4)
        )
        self._targeted_query = tkinter.StringVar(value="")
        self._targeted_query_widget = ttk.Entry(
            search_section, textvariable=self._targeted_query
        )
        self._targeted_query_widget.grid(
            row=0, column=_SEARCH_ENTRY_COLUMN, sticky="ew", pady=(0, 4)
        )
        self._source_label = ttk.Label(
            search_section,
            text=_text_v1(key="scout.source_add"),
            style=_SOURCE_LABEL_STYLE,
        )
        self._source_label.grid(
            row=1, column=_SEARCH_LABEL_COLUMN, sticky="w", pady=(4, 0)
        )
        self._source_url = tkinter.StringVar(value="")
        self._source_url_widget = ttk.Entry(
            search_section, textvariable=self._source_url
        )
        self._source_url_widget.grid(
            row=1, column=_SEARCH_ENTRY_COLUMN, sticky="ew", pady=(4, 0)
        )
        self._source_save_button = ttk.Button(
            search_section,
            text=_text_v1(key="scout.source_save"),
            command=self._save_source,
            width=16,
        )
        self._source_save_button.grid(
            row=1,
            column=_SEARCH_ACTION_COLUMN,
            padx=(8, 0),
            pady=(4, 0),
        )
        self._scout_button = _primary_action_button(
            page,
            text=_text_v1(key="scout.run"),
            state="disabled",
            command=self._scout,
        )
        self._scout_button.master.grid(row=7, column=0, columnspan=2, pady=8)
        self._progress_frame = ttk.Frame(page, width=340, height=22)
        self._progress_frame.grid(row=8, column=0, columnspan=2, pady=(0, 6))
        self._progress_frame.grid_propagate(False)
        self._progress = ttk.Progressbar(
            self._progress_frame,
            mode="determinate",
            maximum=100,
            value=0,
            length=320,
            style=_SCOUT_PROGRESS_STYLE,
        )
        self._progress.place(relx=0.5, rely=0.5, anchor="center", width=320, height=18)
        self._progress_completion = tkinter.Canvas(
            self._progress_frame,
            width=320,
            height=18,
            borderwidth=0,
            highlightthickness=0,
        )
        self._progress_completion_rectangle = (
            self._progress_completion.create_rectangle(
                0, 0, 320, 18, fill=_SCOUT_PROGRESS_COLOR, outline=_SCOUT_PROGRESS_COLOR
            )
        )
        self._progress_completion_text = self._progress_completion.create_text(
            160,
            9,
            text="Cautare finalizata",
            fill="#ffffff",
            font=("TkDefaultFont", 9, "bold"),
            anchor="center",
        )
        self._scout_progress_active = False
        self._status = tkinter.StringVar(value=_text_v1(key="scout.intro"))
        ttk.Label(page, textvariable=self._status).grid(
            row=9, column=0, columnspan=2, sticky="w"
        )
        statistics = ttk.Frame(page)
        statistics.grid(row=10, column=0, columnspan=2, sticky="ew", pady=(4, 2))
        statistics.columnconfigure(1, weight=1)
        statistics.columnconfigure(2, weight=1)
        source_statistics = ttk.Frame(statistics)
        source_statistics.grid(row=0, column=0, sticky="w")
        ttk.Label(
            source_statistics,
            text=f"{_text_v1(key='scout.sources_available')}:",
            style=_SCOUT_STATUS_STYLE,
        ).grid(row=0, column=0, sticky="w")
        self._available = tkinter.StringVar(value="0")
        ttk.Label(source_statistics, textvariable=self._available).grid(
            row=0, column=1, sticky="w", padx=(4, 0)
        )
        self._failed = tkinter.StringVar(value=_failed_sources_summary(()))
        ttk.Label(
            source_statistics,
            text=f"{_text_v1(key='scout.failed_sources')}:",
            style=_SCOUT_STATUS_STYLE,
        ).grid(row=1, column=0, sticky="w")
        ttk.Label(source_statistics, textvariable=self._failed).grid(
            row=1, column=1, sticky="w", padx=(4, 0)
        )
        result_statistics = ttk.Frame(statistics)
        result_statistics.grid(row=0, column=2, sticky="e")
        ttk.Label(
            result_statistics,
            text=f"{_text_v1(key='scout.results')}:",
            style=_SCOUT_STATUS_STYLE,
        ).pack(side="left")
        self._summary = tkinter.StringVar(value="0 articole - 0 noi - duplicate: 0")
        ttk.Label(result_statistics, textvariable=self._summary).pack(
            side="left", padx=(4, 0)
        )
        self._report_button = ttk.Button(
            page,
            text=_text_v1(key="scout.report"),
            state="disabled",
            command=self._report,
        )
        self._report_button.grid(row=12, column=0, columnspan=2)
        self._candidates = ttk.Treeview(
            page,
            columns=("title", "category", "sources"),
            show="headings",
            selectmode="extended",
            height=8,
        )
        self._candidates.heading("title", text="Titlu")
        self._candidates.heading("category", text="Categorie")
        self._candidates.heading("sources", text="Surse")
        self._candidates.column("title", width=520)
        self._candidates.column("category", width=110)
        self._candidates.column("sources", width=60)
        self._candidates.grid(row=13, column=0, columnspan=2, sticky="nsew", pady=8)
        self._candidates.bind("<<TreeviewSelect>>", self._candidate_changed)
        self._handoff_button = ttk.Button(
            page,
            text=_text_v1(key="scout.send_editor"),
            state="disabled",
            command=self._handoff,
        )
        self._handoff_button.grid(row=14, column=0, columnspan=2)
        self._footer = tkinter.StringVar(value="")

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
        self._editor_worklist = ttk.Treeview(
            page,
            columns=("story", "status"),
            show="headings",
            selectmode="extended",
            height=7,
        )
        self._editor_worklist.heading(
            "story", text=_text_v1(key="editor.worklist.story")
        )
        self._editor_worklist.heading(
            "status", text=_text_v1(key="editor.worklist.status")
        )
        self._editor_worklist.column("story", width=620)
        self._editor_worklist.column("status", width=130)
        self._editor_worklist.grid(row=2, column=0, columnspan=2, sticky="nsew", pady=8)
        self._editor_worklist.bind("<<TreeviewSelect>>", self._editor_worklist_changed)
        self._editor_eligible_event_ids: frozenset[int] = frozenset()
        self._editor_failed_event_ids: frozenset[int] = frozenset()
        self._editor_idle = True
        self._active_project = tkinter.StringVar(value="")
        ttk.Label(
            page, text=_text_v1(key="editor.active_project"), style=_PRIMARY_LABEL_STYLE
        ).grid(row=3, column=0, sticky="w")
        ttk.Label(page, textvariable=self._active_project).grid(
            row=3, column=1, sticky="w"
        )
        hidden_paths = (
            "scout_input_path",
            "selection_profile_path",
            "episode_context_path",
            "generation_config_path",
            "timeout_seconds",
            "output_path",
        )
        self._editor_values = {
            name: tkinter.StringVar(value="") for name in hidden_paths
        }
        fields = (("model", "editor.model"),)
        self._editor_widgets: list[ttk.Widget] = []
        for row, (name, key) in enumerate(fields, start=4):
            ttk.Label(page, text=_text_v1(key=key), style=_PRIMARY_LABEL_STYLE).grid(
                row=row, column=0, sticky="w"
            )
            value = tkinter.StringVar(value="")
            widget = ttk.Entry(page, textvariable=value, state="disabled")
            widget.grid(row=row, column=1, sticky="ew")
            self._editor_values[name] = value
            self._editor_widgets.append(widget)
        row = 4 + len(fields)
        ttk.Label(
            page, text=_text_v1(key="editor.provider"), style=_PRIMARY_LABEL_STYLE
        ).grid(row=row, column=0, sticky="w")
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
        self._editor_button = _primary_action_button(
            page,
            text=_text_v1(key="editor.run"),
            state="disabled",
            command=self._editor,
        )
        self._editor_button.master.grid(row=row + 2, column=0, columnspan=2)
        self._editor_retry_button = ttk.Button(
            page,
            text=_text_v1(key="editor.retry"),
            state="disabled",
            command=self._editor_retry,
            width=12,
        )
        self._editor_retry_button.grid(row=row + 4, column=0, columnspan=2)

    def _build_chief_editor(self) -> None:
        page = ttk.Frame(self._content)
        page.grid(row=0, column=0, sticky="nsew")
        page.columnconfigure(1, weight=1)
        page.rowconfigure(2, weight=1)
        self._pages[_DesktopPageV1.CHIEF_EDITOR] = page
        ttk.Label(page, text=_text_v1(key="chief_editor.title")).grid(
            row=0, column=0, sticky="w"
        )
        self._chief_title = tkinter.StringVar(value="")
        ttk.Entry(page, textvariable=self._chief_title).grid(
            row=0, column=1, sticky="ew"
        )
        self._chief_available = ttk.Treeview(
            page, columns=("title",), show="headings", selectmode="browse", height=4
        )
        self._chief_available.heading("title", text="Materiale disponibile")
        self._chief_available.grid(row=1, column=0, columnspan=2, sticky="ew")
        ttk.Button(
            page, text=_text_v1(key="chief_editor.add"), command=self._chief_editor_add
        ).grid(row=1, column=2)
        self._chief_items = ttk.Treeview(
            page,
            columns=("title", "section", "note"),
            show="headings",
            selectmode="browse",
        )
        for name, label in (
            ("title", "Material"),
            ("section", "Sectiune"),
            ("note", "Nota / tranzitie"),
        ):
            self._chief_items.heading(name, text=label)
        self._chief_items.grid(row=2, column=0, columnspan=2, sticky="nsew")
        self._chief_items.bind("<<TreeviewSelect>>", self._chief_editor_selected)
        controls = ttk.Frame(page)
        controls.grid(row=3, column=0, columnspan=2, sticky="ew")
        ttk.Button(
            controls,
            text=_text_v1(key="chief_editor.up"),
            command=lambda: self._chief_editor_move(-1),
        ).pack(side="left")
        ttk.Button(
            controls,
            text=_text_v1(key="chief_editor.down"),
            command=lambda: self._chief_editor_move(1),
        ).pack(side="left")
        ttk.Button(
            controls,
            text=_text_v1(key="chief_editor.remove"),
            command=self._chief_editor_remove_selected,
        ).pack(side="left")
        ttk.Label(
            page, text=_text_v1(key="chief_editor.section"), style=_PRIMARY_LABEL_STYLE
        ).grid(row=4, column=0, sticky="w")
        self._chief_section = tkinter.StringVar(value="")
        ttk.Entry(page, textvariable=self._chief_section).grid(
            row=4, column=1, sticky="ew"
        )
        ttk.Label(
            page, text=_text_v1(key="chief_editor.note"), style=_PRIMARY_LABEL_STYLE
        ).grid(row=5, column=0, sticky="w")
        self._chief_note = tkinter.StringVar(value="")
        ttk.Entry(page, textvariable=self._chief_note).grid(
            row=5, column=1, sticky="ew"
        )
        self._chief_save_button = _primary_action_button(
            page,
            text=_text_v1(key="chief_editor.save"),
            command=self._chief_editor_save_action,
        )
        self._chief_save_button.master.grid(row=6, column=0)
        self._chief_export_button = _primary_action_button(
            page,
            text=_text_v1(key="chief_editor.export"),
            command=self._chief_editor_export_action,
        )
        self._chief_export_button.master.grid(row=6, column=1)
        self._chief_status = tkinter.StringVar(value=_text_v1(key="chief_editor.empty"))
        ttk.Label(page, textvariable=self._chief_status).grid(
            row=7, column=0, columnspan=2, sticky="w"
        )

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
        view_menu.add_command(
            label=_text_v1(key="navigation.chief_editor"),
            command=lambda: self._select(_DesktopPageV1.CHIEF_EDITOR),
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
        if selected and selected[0] in {"scout", "editor", "chief_editor"}:
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
        self._period_widget.configure(state="readonly")
        self._category_widget.configure(state="readonly")
        self._scout_button.configure(state="normal")

    def bind_editor_action(self, *, callback) -> None:
        self._bind("editor", callback)
        for widget in self._editor_widgets:
            widget.configure(
                state="normal" if not isinstance(widget, ttk.Combobox) else "readonly"
            )
        self._sync_editor_action()

    def bind_editor_retry_action(self, *, callback) -> None:
        self._bind("editor_retry", callback)
        self._sync_editor_action()

    def bind_report_action(self, *, callback) -> None:
        self._bind("report", callback)
        self._sync_report()

    def bind_handoff_action(self, *, callback) -> None:
        self._bind("handoff", callback)
        self._sync_handoff()

    def bind_scout_provider_actions(self, *, save_callback, test_callback) -> None:
        self._bind("scout_provider_save", save_callback)
        self._bind("scout_provider_test", test_callback)

    def bind_scout_source_action(self, *, callback) -> None:
        self._bind("scout_source", callback)

    def _save_source(self) -> None:
        self._invoke("scout_source", input=self._source_url.get())

    def publish_source_status(self, *, status: str, clear: bool = False) -> None:
        self._check()
        self._status.set(status)
        if clear:
            self._source_url.set("")

    def _scout_provider_payload(self) -> dict[str, str]:
        return {
            "provider": self._scout_provider.get(),
            "base_url": self._ollama_url.get(),
            "model": self._ollama_model.get(),
        }

    def _provider_changed(self, event: object) -> None:
        del event
        if self._scout_provider.get() == "openai":
            self._model_widget.configure(values=_OPENAI_MODEL_CHOICES)
            self._ollama_model.set(_OPENAI_MODEL_CHOICES[0])
        else:
            configured = self._settings.ollama_model
            self._model_widget.configure(values=(configured,))
            self._ollama_model.set(configured)

    def _save_scout_provider(self) -> None:
        self._invoke("scout_provider_save", input=self._scout_provider_payload())

    def _test_scout_provider(self) -> None:
        self._invoke("scout_provider_test", input=self._scout_provider_payload())

    def publish_scout_provider_status(self, *, status: str) -> None:
        self._check()
        self._status.set(status)

    def publish_scout_models(self, *, models: tuple[str, ...]) -> None:
        self._check()
        self._model_widget.configure(values=models)
        if models and self._ollama_model.get() not in models:
            self._ollama_model.set(models[0])

    def bind_chief_editor_actions(self, *, save_callback, export_callback) -> None:
        self._bind("chief_editor_save", save_callback)
        self._bind("chief_editor_export", export_callback)

    def _bind(self, name: str, callback: object) -> None:
        self._check()
        _validate_binding(callback, "reference" if name == "report" else "input")
        if name in self._bindings:
            raise _DesktopShellConfigurationError() from None
        self._bindings[name] = callback

    def _scout(self) -> None:
        self._scout_progress_active = True
        self._set_scout_progress_running()
        self._invoke(
            "scout",
            input=_DesktopScoutActionInputV1(
                self._period.get(),
                "all" if self._category.get() == "Toate" else self._category.get(),
                self._targeted_query.get(),
            ),
        )

    def _candidate_changed(self, event: object) -> None:
        del event
        self._check()
        self._sync_handoff()

    def _handoff(self) -> None:
        selected = self._candidates.selection()
        if selected:
            selected_set = set(selected)
            ordered = tuple(
                int(item)
                for item in self._candidates.get_children("")
                if item in selected_set
            )
            self._invoke("handoff", input=ordered)

    def _editor(self) -> None:
        selected = set(self._editor_worklist.selection())
        ordered = tuple(
            int(iid)
            for iid in self._editor_worklist.get_children("")
            if iid in selected
        )
        if not ordered:
            raise _DesktopShellConfigurationError() from None
        values = {name: value.get() for name, value in self._editor_values.items()}
        values.update(
            event_ids=ordered,
            provider=self._provider.get(),
            no_replace=bool(self._no_replace.get()),
        )
        self._invoke("editor", input=_DesktopEditorActionInputV1(**values))

    def _editor_worklist_changed(self, event: object) -> None:
        del event
        self._check()
        selected = self._editor_worklist.selection()
        focused = self._editor_worklist.focus()
        if focused not in selected:
            focused = selected[-1] if selected else ""
        title = self._editor_worklist.set(focused, "story") if focused else ""
        self._active_project.set(title)
        self._sync_editor_action()

    def _editor_retry(self) -> None:
        selected = set(self._editor_worklist.selection())
        ordered = tuple(
            int(iid)
            for iid in self._editor_worklist.get_children("")
            if iid in selected
        )
        if not ordered:
            raise _DesktopShellConfigurationError() from None
        self._invoke("editor_retry", input=ordered)

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
            if name == "scout":
                self._scout_progress_active = False
                self._set_scout_progress_failed()

    def publish_scout_result(
        self,
        *,
        summary: str,
        sources_available: int,
        failed_sources: tuple[str, ...],
        footer: str,
        report_reference: str | None,
    ) -> None:
        self._check()
        if (
            type(summary) is not str
            or type(sources_available) is not int
            or sources_available < 0
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
        self._available.set(str(sources_available))
        self._failed.set(_failed_sources_summary(failed_sources))
        self._footer.set(footer)
        if footer in {"completed", "partial"}:
            self._set_scout_progress_completed()
        else:
            self._set_scout_progress_failed()
        self._scout_progress_active = False
        self._report_reference = report_reference
        self._sync_report()

    def publish_editor_result(self, *, status: str) -> None:
        self._check()
        if type(status) is not str:
            raise _DesktopShellConfigurationError() from None
        self._editor_status.set(status)

    def publish_candidates(
        self, *, candidates: tuple[tuple[int, str, str, int], ...]
    ) -> None:
        self._check()
        for item in self._candidates.get_children(""):
            self._candidates.delete(item)
        for event_id, title, category, sources in candidates:
            self._candidates.insert(
                "", "end", iid=str(event_id), values=(title, category, str(sources))
            )
        self._summary.set(
            _restored_candidate_summary(
                current=self._summary.get(), count=len(candidates)
            )
        )
        self._sync_handoff()

    def publish_active_project(self, *, title: str, message: str) -> None:
        self._check()
        if type(title) is not str or type(message) is not str:
            raise _DesktopShellConfigurationError() from None
        self._editor_status.set(message)
        self._sync_editor_action()

    def publish_editor_worklist(
        self,
        *,
        items: tuple[tuple[int, str, str], ...],
    ) -> None:
        self._check()
        statuses = {"pending", "running", "completed", "failed"}
        if (
            type(items) is not tuple
            or any(
                type(item) is not tuple
                or len(item) != 3
                or type(item[0]) is not int
                or type(item[1]) is not str
                or type(item[2]) is not str
                or item[2] not in statuses
                for item in items
            )
            or len({item[0] for item in items}) != len(items)
        ):
            raise _DesktopShellConfigurationError() from None
        selected = set(self._editor_worklist.selection())
        focused = self._editor_worklist.focus()
        for iid in self._editor_worklist.get_children(""):
            self._editor_worklist.delete(iid)
        for event_id, title, status in items:
            self._editor_worklist.insert(
                "",
                "end",
                iid=str(event_id),
                values=(title, _text_v1(key=f"editor.worklist.{status}")),
            )
        existing = set(self._editor_worklist.get_children(""))
        retained = tuple(
            iid for iid in self._editor_worklist.get_children("") if iid in selected
        )
        if retained:
            self._editor_worklist.selection_set(retained)
        if focused in existing:
            self._editor_worklist.focus(focused)
        self._editor_eligible_event_ids = frozenset(
            event_id for event_id, _, status in items if status == "pending"
        )
        self._editor_failed_event_ids = frozenset(
            event_id for event_id, _, status in items if status == "failed"
        )
        self._editor_worklist_changed(None)

    def publish_chief_editor(
        self,
        *,
        title: str,
        available: tuple[tuple[str, str], ...],
        items: tuple[tuple[str, str, str, str], ...],
        status: str = "",
    ) -> None:
        self._check()
        self._chief_title.set(title)
        for iid in self._chief_available.get_children(""):
            self._chief_available.delete(iid)
        for reference, item_title in available:
            self._chief_available.insert("", "end", iid=reference, values=(item_title,))
        for iid in self._chief_items.get_children(""):
            self._chief_items.delete(iid)
        for reference, item_title, section, note in items:
            self._chief_items.insert(
                "", "end", iid=reference, values=(item_title, section, note)
            )
        self._chief_status.set(
            status or (_text_v1(key="chief_editor.empty") if not items else "")
        )

    def _chief_editor_add(self) -> None:
        selected = self._chief_available.selection()
        if not selected:
            return
        reference = selected[0]
        if reference not in self._chief_items.get_children(""):
            title = self._chief_available.item(reference, "values")[0]
            self._chief_items.insert("", "end", iid=reference, values=(title, "", ""))

    def _chief_editor_selected(self, event: object) -> None:
        del event
        selected = self._chief_items.selection()
        if selected:
            values = self._chief_items.item(selected[0], "values")
            self._chief_section.set(values[1])
            self._chief_note.set(values[2])

    def _chief_editor_apply_fields(self) -> None:
        selected = self._chief_items.selection()
        if selected:
            values = list(self._chief_items.item(selected[0], "values"))
            values[1] = self._chief_section.get()
            values[2] = self._chief_note.get()
            self._chief_items.item(selected[0], values=values)

    def _chief_editor_move(self, offset: int) -> None:
        self._chief_editor_apply_fields()
        selected = self._chief_items.selection()
        if not selected:
            return
        iid = selected[0]
        target = self._chief_items.index(iid) + offset
        if 0 <= target < len(self._chief_items.get_children("")):
            self._chief_items.move(iid, "", target)

    def _chief_editor_remove_selected(self) -> None:
        selected = self._chief_items.selection()
        if selected:
            self._chief_items.delete(selected[0])

    def _chief_editor_payload(self) -> dict[str, object]:
        self._chief_editor_apply_fields()
        return {
            "title": self._chief_title.get(),
            "items": tuple(
                (iid, *self._chief_items.item(iid, "values")[1:])
                for iid in self._chief_items.get_children("")
            ),
        }

    def _chief_editor_save_action(self) -> None:
        self._invoke("chief_editor_save", input=self._chief_editor_payload())

    def _chief_editor_export_action(self) -> None:
        self._invoke("chief_editor_export", input=self._chief_editor_payload())

    def _sync_handoff(self) -> None:
        count = len(self._candidates.selection())
        state = "normal" if "handoff" in self._bindings and count else "disabled"
        self._handoff_button.configure(state=state, text=_handoff_label(count))

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
        if self._scout_progress_active and snapshot.application_state in {
            _DesktopTaskStateV1.SUBMITTED,
            _DesktopTaskStateV1.RUNNING,
        }:
            self._set_scout_progress_running()
        elif self._scout_progress_active and snapshot.application_state in {
            _DesktopTaskStateV1.FAILED,
            _DesktopTaskStateV1.CANCELLED,
        }:
            self._scout_progress_active = False
            self._set_scout_progress_failed()
        self._scout_button.configure(
            state="normal" if idle and "scout" in self._bindings else "disabled"
        )
        self._editor_idle = idle
        self._sync_editor_action()
        if not idle:
            self._handoff_button.configure(state="disabled")
        else:
            self._sync_handoff()
        if snapshot.is_closed:
            self._navigation.configure(selectmode="none")
            self._scout_button.configure(state="disabled")
            self._editor_button.configure(state="disabled")
            self._editor_retry_button.configure(state="disabled")
            self._handoff_button.configure(state="disabled")
            self._report_button.configure(state="disabled")

    def _set_scout_progress_running(self) -> None:
        self._progress.stop()
        self._progress.configure(mode="indeterminate", value=0)
        self._progress_completion.place_forget()
        self._progress.place(relx=0.5, rely=0.5, anchor="center", width=320, height=18)
        self._progress.start(12)

    def _set_scout_progress_completed(self) -> None:
        self._progress.stop()
        self._progress.configure(mode="determinate", value=100)
        self._progress.place_forget()
        self._progress_completion.place(
            relx=0.5, rely=0.5, anchor="center", width=320, height=18
        )

    def _set_scout_progress_failed(self) -> None:
        self._progress.stop()
        self._progress.configure(mode="determinate", value=0)
        self._progress_completion.place_forget()
        self._progress.place(relx=0.5, rely=0.5, anchor="center", width=320, height=18)

    def _sync_editor_action(self) -> None:
        try:
            selected = tuple(int(iid) for iid in self._editor_worklist.selection())
        except ValueError:
            selected = ()
        enabled = _editor_action_enabled(
            idle=self._editor_idle,
            callback_bound="editor" in self._bindings,
            configuration_ready=_editor_configuration_ready(
                self._editor_values, provider=self._provider.get()
            ),
            selected_event_ids=selected,
            eligible_event_ids=self._editor_eligible_event_ids,
        )
        self._editor_button.configure(state="normal" if enabled else "disabled")
        retry_enabled = (
            self._editor_idle
            and "editor_retry" in self._bindings
            and bool(selected)
            and set(selected).issubset(self._editor_failed_event_ids)
        )
        self._editor_retry_button.configure(
            state="normal" if retry_enabled else "disabled"
        )

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
