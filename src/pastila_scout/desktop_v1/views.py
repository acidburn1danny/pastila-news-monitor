"""Tkinter/ttk structural views for the private desktop shell."""

# ruff: noqa: BLE001

from __future__ import annotations

import hashlib
import inspect
import re
import threading
import tkinter
import types
from datetime import UTC, datetime
from importlib import resources
from tkinter import messagebox, simpledialog, ttk

from pastila_scout.editor_core_identities_v1 import (
    CORE_V1_1_DISPLAY_NAME,
    CORE_V1_1_MODEL_ID,
    CORE_V1_2_DISPLAY_NAME,
    CORE_V1_2_MODEL_ID,
)

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
_EPISODE_DRAFT_INSPECTION_ACTION_WIDTH = 24
_INITIAL_WINDOW_BASE_WIDTH = 900
_INITIAL_WINDOW_BASE_HEIGHT = 600
_INITIAL_WINDOW_WIDTH = 1320
_INITIAL_WINDOW_HEIGHT = 850
_INITIAL_WINDOW_SCREEN_MARGIN_X = 40
_INITIAL_WINDOW_SCREEN_MARGIN_Y = 80
_NAVIGATION_BADGE_WIDTH = 18
_NAVIGATION_BADGE_HEIGHT = 1
_NAVIGATION_BADGE_PADX = 6
_NAVIGATION_BADGE_PADY = 2
_NAVIGATION_FONT_SIZE = 10
_NAVIGATION_FONT_STYLE = "bold italic"
_NAVIGATION_NORMAL_BORDER = 1
_NAVIGATION_ACTIVE_BORDER = 3
_NAVIGATION_STYLES = {
    _DesktopPageV1.SCOUT: ("#d71920", "#ffffff"),
    _DesktopPageV1.EDITOR: ("#f4c430", "#000000"),
    _DesktopPageV1.CHIEF_EDITOR: ("#1565c0", "#ffffff"),
}
_NAVIGATION_MASCOT_PACKAGE = "pastila_scout.resources.branding"
_NAVIGATION_MASCOT_RESOURCE = "pastila-scout-investigator-sidebar.png"
_NAVIGATION_MASCOT_SOURCE_SIZE = (1024, 1536)
_NAVIGATION_MASCOT_DISPLAY_SIZE = (118, 177)
_NAVIGATION_MASCOT_TOP_SPACING = 22


def _initial_window_geometry(root: object) -> str:
    available_width = max(
        _INITIAL_WINDOW_BASE_WIDTH,
        int(root.winfo_screenwidth()) - _INITIAL_WINDOW_SCREEN_MARGIN_X,
    )
    available_height = max(
        _INITIAL_WINDOW_BASE_HEIGHT,
        int(root.winfo_screenheight()) - _INITIAL_WINDOW_SCREEN_MARGIN_Y,
    )
    width = min(_INITIAL_WINDOW_WIDTH, available_width)
    height = min(_INITIAL_WINDOW_HEIGHT, available_height)
    left = max(0, (int(root.winfo_screenwidth()) - width) // 2)
    top = max(0, (int(root.winfo_screenheight()) - height) // 2)
    return f"{width}x{height}+{left}+{top}"


def _load_navigation_mascot(parent: tkinter.Misc) -> tkinter.PhotoImage | None:
    try:
        source = resources.files(_NAVIGATION_MASCOT_PACKAGE).joinpath(
            _NAVIGATION_MASCOT_RESOURCE
        )
        return tkinter.PhotoImage(master=parent, file=str(source))
    except Exception:
        return None


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
    parent: tkinter.Misc,
    *,
    text: str,
    command: object,
    state: str = "normal",
    width: int = _PRIMARY_ACTION_BUTTON_OPTIONS["width"],
) -> tkinter.Button:
    border = tkinter.Frame(parent, background=_PRIMARY_ACTION_COLOR, padx=1, pady=1)
    button = tkinter.Button(
        border,
        text=text,
        state=state,
        command=command,
        **{**_PRIMARY_ACTION_BUTTON_OPTIONS, "width": width},
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


def _editor_default_selection(
    settings: _DesktopSettingsProjectionV1,
) -> tuple[str, str, str | None]:
    configured = settings.editor_default_model
    experimental = {
        CORE_V1_1_MODEL_ID: CORE_V1_1_DISPLAY_NAME,
        CORE_V1_2_MODEL_ID: CORE_V1_2_DISPLAY_NAME,
    }
    if configured in experimental:
        return experimental[configured], "ollama", None
    if configured == settings.ollama_model:
        return configured, "ollama", None
    if configured == settings.editor_model:
        return configured, settings.editor_provider, None
    fallback = _editor_display_model(settings)
    return (
        fallback,
        settings.editor_provider,
        (
            f"Modelul Editor implicit «{configured}» nu este disponibil; "
            f"s-a selectat în siguranță «{fallback}»."
        ),
    )


def _editor_model_catalog(
    settings: _DesktopSettingsProjectionV1,
) -> tuple[str, ...]:
    candidates = (
        settings.ollama_model,
        settings.editor_model,
        CORE_V1_1_DISPLAY_NAME,
        CORE_V1_2_DISPLAY_NAME,
    )
    return tuple(dict.fromkeys(candidates))


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
        root.geometry(_initial_window_geometry(root))
        root.minsize(_INITIAL_WINDOW_BASE_WIDTH, _INITIAL_WINDOW_BASE_HEIGHT)
        root.resizable(True, True)
        root.columnconfigure(0, weight=1)
        root.rowconfigure(0, weight=1)

        self._main = ttk.Frame(root)
        self._main.grid(row=0, column=0, sticky="nsew")
        self._main.columnconfigure(1, weight=1)
        self._main.rowconfigure(0, weight=1)
        self._navigation = tkinter.Frame(self._main)
        self._navigation_badges: dict[_DesktopPageV1, tkinter.Label] = {}
        for row, page in enumerate(_DesktopPageV1):
            background, foreground = _NAVIGATION_STYLES[page]
            badge = tkinter.Label(
                self._navigation,
                text=_text_v1(key=f"navigation.{page.value}").upper(),
                background=background,
                foreground=foreground,
                font=("TkDefaultFont", _NAVIGATION_FONT_SIZE, _NAVIGATION_FONT_STYLE),
                width=_NAVIGATION_BADGE_WIDTH,
                height=_NAVIGATION_BADGE_HEIGHT,
                padx=_NAVIGATION_BADGE_PADX,
                pady=_NAVIGATION_BADGE_PADY,
                highlightbackground="#000000",
                highlightcolor="#000000",
                highlightthickness=_NAVIGATION_NORMAL_BORDER,
            )
            badge.grid(row=row, column=0, pady=(0, 6), sticky="ew")
            badge.bind(
                "<Button-1>", lambda _event, selected=page: self._select(selected)
            )
            self._navigation_badges[page] = badge
        self._navigation_mascot_image = _load_navigation_mascot(self._navigation)
        self._navigation_mascot = None
        if self._navigation_mascot_image is not None:
            self._navigation_mascot = tkinter.Label(
                self._navigation,
                image=self._navigation_mascot_image,
                background=self._navigation.cget("background"),
                borderwidth=0,
                highlightthickness=0,
            )
            self._navigation_mascot.grid(
                row=len(_DesktopPageV1),
                column=0,
                pady=(_NAVIGATION_MASCOT_TOP_SPACING, 0),
            )
        self._navigation.grid(row=0, column=0, sticky="ns", padx=(8, 4), pady=8)
        self._set_navigation_page(_DesktopPageV1.SCOUT)
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
        editor_model, editor_provider, fallback_status = _editor_default_selection(
            settings
        )
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
            "model": editor_model,
            "timeout_seconds": settings.editor_timeout_seconds,
            "output_path": settings.editor_output_directory,
        }
        for name, value in projected.items():
            self._editor_values[name].set("" if value is None else str(value))
        self._editor_widgets[0].configure(values=_editor_model_catalog(settings))
        self._provider.set(editor_provider)
        if fallback_status is not None:
            self._editor_status.set(fallback_status)

    def _check(self) -> None:
        if threading.get_ident() != self._thread or self._closed:
            raise _DesktopShellConfigurationError() from None

    def _build_scout(self) -> None:
        page = ttk.Frame(self._content)
        page.grid(row=0, column=0, sticky="nsew")
        page.columnconfigure(1, weight=1)
        page.columnconfigure(2, weight=1)
        page.rowconfigure(13, weight=1)
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
            height=14,
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
        self._editor_material_presentations: dict[int, object] = {}
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
            widget = ttk.Combobox(
                page,
                textvariable=value,
                values=(
                    value.get(),
                    CORE_V1_1_DISPLAY_NAME,
                    CORE_V1_2_DISPLAY_NAME,
                ),
                state="disabled",
            )
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
        page.rowconfigure(row + 5, weight=1)
        page.rowconfigure(row + 6, weight=1)
        self._editor_material_text = tkinter.Text(
            page, height=12, wrap="word", state="disabled"
        )
        self._editor_material_text.grid(
            row=row + 5, column=0, columnspan=2, sticky="nsew", pady=(8, 0)
        )
        self._voice_v2_event_id: int | None = None
        voice = ttk.Frame(page)
        voice.grid(row=row + 6, column=0, columnspan=2, sticky="nsew", pady=(8, 0))
        voice.columnconfigure(0, weight=1)
        voice.rowconfigure(8, weight=1)
        voice_fields = ttk.Frame(voice)
        voice_fields.grid(row=0, column=0, sticky="ew")
        voice = voice_fields
        voice.columnconfigure(1, weight=1)
        self._voice_program = tkinter.StringVar(value="")
        self._voice_program_ids: dict[str, str | None] = {}
        ttk.Label(
            voice, text="Construcție", style=_PRIMARY_LABEL_STYLE
        ).grid(row=0, column=0, sticky="w")
        self._voice_program_widget = ttk.Combobox(
            voice, textvariable=self._voice_program, state="disabled"
        )
        self._voice_program_widget.grid(row=0, column=1, sticky="ew")
        self._voice_program_widget.bind(
            "<<ComboboxSelected>>", self._voice_program_selected
        )
        self._voice_expression = tkinter.StringVar(value="")
        self._voice_expression_ids: dict[str, str | None] = {}
        ttk.Label(
            voice, text="Expresie opțională", style=_PRIMARY_LABEL_STYLE
        ).grid(row=1, column=0, sticky="w")
        self._voice_expression_widget = ttk.Combobox(
            voice, textvariable=self._voice_expression, state="disabled"
        )
        self._voice_expression_widget.grid(row=1, column=1, sticky="ew")
        self._voice_expression_widget.bind(
            "<<ComboboxSelected>>", self._voice_expression_selected
        )
        self._voice_adjudication = None
        self._voice_fact_candidate = tkinter.StringVar(value="")
        self._voice_fact_candidate_ids: dict[str, str] = {}
        ttk.Label(
            voice, text="Candidat factual", style=_PRIMARY_LABEL_STYLE
        ).grid(row=2, column=0, sticky="w")
        self._voice_fact_candidate_widget = ttk.Combobox(
            voice, textvariable=self._voice_fact_candidate, state="disabled"
        )
        self._voice_fact_candidate_widget.grid(row=2, column=1, sticky="ew")
        fact_controls = ttk.Frame(voice)
        fact_controls.grid(row=3, column=0, columnspan=2, sticky="w")
        self._voice_fact_accept_button = ttk.Button(
            fact_controls, text="Acceptă fapt tipizat", command=self._voice_accept_fact
        )
        self._voice_fact_reject_button = ttk.Button(
            fact_controls, text="Respinge candidat", command=self._voice_reject_fact
        )
        self._voice_fact_qualify_button = ttk.Button(
            fact_controls,
            text="Necesită calificare",
            command=self._voice_qualify_fact,
        )
        self._voice_finalize_facts_button = ttk.Button(
            fact_controls,
            text="Finalizează faptele",
            command=self._voice_finalize_facts,
        )
        self._voice_no_claim_button = ttk.Button(
            fact_controls, text="Fără construcție", command=self._voice_choose_no_claim
        )
        for button in (
            self._voice_fact_accept_button,
            self._voice_fact_reject_button,
            self._voice_fact_qualify_button,
            self._voice_finalize_facts_button,
            self._voice_no_claim_button,
        ):
            button.pack(side="left", padx=(0, 4))
        self._voice_mechanic = tkinter.StringVar(value="")
        self._voice_mechanic_widget = ttk.Combobox(
            voice, textvariable=self._voice_mechanic, state="disabled"
        )
        ttk.Label(
            voice, text="Mecanică editorială", style=_PRIMARY_LABEL_STYLE
        ).grid(row=4, column=0, sticky="w")
        self._voice_mechanic_widget.grid(row=4, column=1, sticky="ew")
        mechanic_controls = ttk.Frame(voice)
        mechanic_controls.grid(row=5, column=0, columnspan=2, sticky="w")
        self._voice_confirm_mechanic_button = ttk.Button(
            mechanic_controls,
            text="Confirmă mecanica",
            command=self._voice_confirm_mechanic,
        )
        self._voice_finalize_claims_button = ttk.Button(
            mechanic_controls,
            text="Finalizează construcția",
            command=self._voice_finalize_claims,
        )
        self._voice_confirm_mechanic_button.pack(side="left", padx=(0, 4))
        self._voice_finalize_claims_button.pack(side="left", padx=(0, 4))
        controls = ttk.Frame(voice)
        controls.grid(row=6, column=0, columnspan=2, sticky="ew", pady=(4, 0))
        self._voice_preview_button = ttk.Button(
            controls,
            text="Previzualizează",
            command=lambda: self._voice_action("preview"),
        )
        self._voice_accept_button = ttk.Button(
            controls, text="Acceptă", command=lambda: self._voice_action("accept")
        )
        self._voice_reject_button = ttk.Button(
            controls, text="Respinge", command=lambda: self._voice_action("reject")
        )
        self._voice_refresh_button = tkinter.Button(
            controls,
            text="Generează Comentariu Acid",
            command=self._generate_acid_commentary,
            font=("TkDefaultFont", 11, "bold"),
            foreground="#d71920",
            background="#f4f4f4",
            activeforeground="#d71920",
            activebackground="#ffffff",
            highlightbackground="#000000",
            highlightcolor="#000000",
            highlightthickness=1,
            borderwidth=1,
            relief="solid",
            width=24,
            height=1,
        )
        for button in (
            self._voice_preview_button,
            self._voice_accept_button,
            self._voice_reject_button,
            self._voice_refresh_button,
        ):
            button.pack(side="left", padx=(0, 4))
        self._voice_status = tkinter.StringVar(value="")
        ttk.Label(
            voice,
            textvariable=self._voice_status,
            wraplength=700,
            font=("TkDefaultFont", 10, "bold italic"),
        ).grid(
            row=7, column=0, columnspan=2, sticky="w", pady=(4, 0)
        )
        self._voice_preview_text = tkinter.Text(
            voice, height=12, wrap="word", state="disabled"
        )
        self._voice_preview_text.grid(
            row=8, column=0, columnspan=2, sticky="nsew", pady=(4, 0)
        )
        self._voice_advanced_visible = tkinter.BooleanVar(value=False)
        self._voice_advanced_widgets = tuple(
            widget
            for advanced_row in range(6)
            for widget in voice.grid_slaves(row=advanced_row)
        )
        self._voice_advanced_buttons = (
            self._voice_preview_button,
            self._voice_accept_button,
            self._voice_reject_button,
        )
        self._set_voice_advanced_visibility()
        self._clear_voice_v2_presentation()

    def _build_chief_editor(self) -> None:
        page = ttk.Frame(self._content)
        page.grid(row=0, column=0, sticky="nsew")
        page.columnconfigure(1, weight=1)
        page.rowconfigure(1, weight=1, uniform="chief_material_lists")
        page.rowconfigure(2, weight=1, uniform="chief_material_lists")
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
        self._chief_available.grid(row=1, column=0, columnspan=2, sticky="nsew")
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
        self._chief_v2_presentations: dict[str, str] = {}
        self._chief_material_text = tkinter.Text(
            page, width=42, wrap="word", state="disabled"
        )
        self._chief_material_text.grid(
            row=2, column=2, rowspan=4, sticky="nsew", padx=(8, 0)
        )
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
        self._editorial_evidence_button = ttk.Button(
            page,
            text=_text_v1(key="editorial_evidence.open"),
            command=self._editorial_evidence_open_action,
        )
        self._editorial_evidence_button.grid(row=6, column=2)
        self._chief_status = tkinter.StringVar(value=_text_v1(key="chief_editor.empty"))
        ttk.Label(page, textvariable=self._chief_status).grid(
            row=7, column=0, columnspan=2, sticky="w"
        )
        self._episode_publish_available = False
        self._episode_draft_current = False
        self._episode_draft_export_running = False
        self._episode_draft_approval_running = False
        self._episode_draft_can_submit_approval = False
        self._episode_approval_button = None
        self._episode_draft_final_running = False
        self._episode_draft_can_approve = False
        self._episode_final_button = None
        self._episode_draft_details = ("", "", (), (), "")
        self._episode_draft_button = _primary_action_button(
            page,
            text=_text_v1(key="episode_draft.publish"),
            command=self._episode_draft_publish_action,
            state="disabled",
        )
        self._episode_draft_button.master.grid(row=8, column=0, pady=(8, 0))
        self._episode_inspect_button = ttk.Button(
            page,
            text=_text_v1(key="episode_draft.inspect"),
            command=self._episode_draft_inspect,
            state="disabled",
        )
        self._episode_inspect_button.grid(row=8, column=1, pady=(8, 0))
        self._episode_draft_status = tkinter.StringVar(
            value=_text_v1(key="episode_draft.none")
        )
        ttk.Label(page, textvariable=self._episode_draft_status).grid(
            row=9, column=0, columnspan=2, sticky="w"
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
        view_menu.add_separator()
        view_menu.add_checkbutton(
            label="Instrumente Voice avansate",
            variable=self._voice_advanced_visible,
            command=self._set_voice_advanced_visibility,
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

    def _set_voice_advanced_visibility(self) -> None:
        advanced = self._voice_advanced_visible.get()
        for widget in self._voice_advanced_widgets:
            if advanced:
                widget.grid()
            else:
                widget.grid_remove()
        for button in (*self._voice_advanced_buttons, self._voice_refresh_button):
            button.pack_forget()
        if advanced:
            for button in self._voice_advanced_buttons:
                button.pack(side="left", padx=(0, 4))
            self._voice_refresh_button.pack(side="left", padx=(0, 4))
        else:
            self._voice_refresh_button.pack(anchor="center", pady=(2, 4))
        self._voice_refresh_button.configure(
            text="Re-evaluează" if advanced else "Generează Comentariu Acid"
        )

    def _select(self, page: _DesktopPageV1) -> None:
        self._check()
        self._set_navigation_page(page)
        self._on_select_page(page=page)

    def _set_navigation_page(self, page: _DesktopPageV1) -> None:
        for candidate, badge in self._navigation_badges.items():
            active = candidate is page
            badge.configure(
                font=("TkDefaultFont", _NAVIGATION_FONT_SIZE, _NAVIGATION_FONT_STYLE),
                highlightthickness=(
                    _NAVIGATION_ACTIVE_BORDER if active else _NAVIGATION_NORMAL_BORDER
                ),
            )

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

    def bind_editorial_evidence_actions(
        self, *, inspect_callback, finalize_callback, classify_callback
    ) -> None:
        self._bind("editorial_evidence_inspect", inspect_callback)
        self._bind("editorial_evidence_finalize", finalize_callback)
        self._bind("editorial_evidence_classify", classify_callback)

    def bind_episode_draft_action(self, *, callback) -> None:
        self._bind("episode_draft_publish", callback)
        self._sync_episode_draft_actions()

    def bind_episode_draft_export_action(self, *, callback) -> None:
        self._bind("episode_draft_export", callback)
        self._sync_episode_draft_actions()

    def bind_episode_draft_approval_action(self, *, callback) -> None:
        self._bind("episode_draft_approval", callback)
        self._sync_episode_draft_actions()

    def bind_episode_draft_final_action(self, *, callback) -> None:
        self._bind("episode_draft_final", callback)
        self._sync_episode_draft_actions()

    def publish_episode_draft_export_status(self, *, status: str) -> None:
        self._check()
        self._episode_draft_status.set(status)
        self._episode_draft_export_running = False
        self._sync_episode_draft_actions()

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
        experimental_models = {
            CORE_V1_1_DISPLAY_NAME: CORE_V1_1_MODEL_ID,
            CORE_V1_2_DISPLAY_NAME: CORE_V1_2_MODEL_ID,
        }
        if values["model"] in experimental_models:
            values["model"] = experimental_models[values["model"]]
            self._provider.set("ollama")
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
        self._render_editor_material_presentation()
        if focused and "voice_v2" in self._bindings:
            self._voice_v2_event_id = int(focused)
            self._voice_action("load")
        else:
            self._clear_voice_v2_presentation()
        self._sync_editor_action()

    def _render_editor_material_presentation(self) -> None:
        from .editor_material_presentation_v2 import (
            render_editor_material_presentation_v2,
        )

        focused = self._editor_worklist.focus()
        presentation = (
            self._editor_material_presentations.get(int(focused)) if focused else None
        )
        text = (
            ""
            if presentation is None
            else render_editor_material_presentation_v2(presentation)
        )
        self._editor_material_text.configure(state="normal")
        self._editor_material_text.delete("1.0", "end")
        if text:
            self._editor_material_text.insert("1.0", text)
        self._editor_material_text.configure(state="disabled")

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

    def publish_editor_material_presentations(
        self, *, items: tuple[object, ...]
    ) -> None:
        self._check()
        from .editor_material_presentation_v2 import EditorMaterialPresentationV2

        if type(items) is not tuple or any(
            type(item) is not EditorMaterialPresentationV2 for item in items
        ):
            raise _DesktopShellConfigurationError() from None
        self._editor_material_presentations = {item.event_id: item for item in items}
        if len(self._editor_material_presentations) != len(items):
            raise _DesktopShellConfigurationError() from None
        self._render_editor_material_presentation()

    def bind_voice_v2_action(self, *, callback) -> None:
        self._bind("voice_v2", callback)

    def bind_acid_commentary_action(self, *, callback) -> None:
        self._bind("acid_commentary", callback)

    def publish_acid_commentary_status(self, *, status: str, running: bool) -> None:
        self._check()
        self._voice_status.set(status)
        self._voice_refresh_button.configure(state="disabled" if running else "normal")

    def publish_voice_v2(self, *, presentation: object) -> None:
        self._check()
        from .voice_v2_interaction import VoiceDesktopPresentationV2

        if type(presentation) is not VoiceDesktopPresentationV2:
            raise _DesktopShellConfigurationError() from None
        self._voice_v2_event_id = presentation.event_id
        self._voice_adjudication = presentation.adjudication
        self._set_voice_choices(
            widget=self._voice_program_widget,
            variable=self._voice_program,
            mapping=self._voice_program_ids,
            choices=presentation.program_choices,
            selected=presentation.selected_program_identity,
            selection_finalized=presentation.program_selection_finalized,
            none_label="Fără comentariu",
        )
        self._set_voice_choices(
            widget=self._voice_expression_widget,
            variable=self._voice_expression,
            mapping=self._voice_expression_ids,
            choices=presentation.expression_choices,
            selected=presentation.selected_expression_identity,
            selection_finalized=presentation.expression_selection_finalized,
            none_label="Fără expresie",
        )
        interaction = presentation.interaction
        status = f"{interaction.title}\n{interaction.message}"
        if interaction.diagnostic_code:
            status += f"\nCod diagnostic: {interaction.diagnostic_code}"
        self._voice_status.set(status)
        self._voice_preview_text.configure(state="normal")
        self._voice_preview_text.delete("1.0", "end")
        if presentation.preview_text:
            self._voice_preview_text.insert("1.0", presentation.preview_text)
        self._voice_preview_text.configure(state="disabled")
        bound = "voice_v2" in self._bindings
        self._voice_preview_button.configure(
            state="normal" if bound and presentation.preview_enabled else "disabled"
        )
        self._voice_accept_button.configure(
            state="normal" if bound and presentation.accept_enabled else "disabled"
        )
        self._voice_reject_button.configure(
            state="normal" if bound and presentation.reject_enabled else "disabled"
        )
        self._voice_refresh_button.configure(
            state="normal" if bound and presentation.refresh_enabled else "disabled"
        )
        adjudication = presentation.adjudication
        self._voice_fact_candidate_ids.clear()
        candidate_labels = []
        if adjudication is not None:
            for item in adjudication.candidates:
                if item.disposition != "undecided":
                    continue
                label = f"{item.exact_text} — {item.source_label}"
                self._voice_fact_candidate_ids[label] = item.candidate_identity
                candidate_labels.append(label)
        self._voice_fact_candidate_widget.configure(
            values=tuple(candidate_labels),
            state="readonly"
            if bound and adjudication is not None and adjudication.can_review_facts
            else "disabled",
        )
        self._voice_fact_candidate.set(candidate_labels[0] if candidate_labels else "")
        fact_review = bool(bound and adjudication and adjudication.can_review_facts)
        for button in (
            self._voice_fact_accept_button,
            self._voice_fact_reject_button,
            self._voice_fact_qualify_button,
        ):
            button.configure(state="normal" if fact_review else "disabled")
        self._voice_finalize_facts_button.configure(
            state="normal"
            if bound and adjudication and adjudication.fact_finalization_enabled
            else "disabled"
        )
        mechanic_review = bool(
            bound and adjudication and adjudication.can_review_mechanics
        )
        mechanics = () if adjudication is None else adjudication.mechanic_choices
        self._voice_mechanic_widget.configure(
            values=mechanics,
            state="readonly" if mechanic_review and mechanics else "disabled",
        )
        self._voice_mechanic.set(mechanics[0] if mechanics else "")
        self._voice_confirm_mechanic_button.configure(
            state="normal" if mechanic_review and mechanics else "disabled"
        )
        self._voice_finalize_claims_button.configure(
            state="normal"
            if bound and adjudication and adjudication.claim_finalization_enabled
            else "disabled"
        )
        self._voice_no_claim_button.configure(
            state="normal"
            if bound and adjudication and adjudication.can_choose_no_claim
            else "disabled"
        )
        material = self._editor_material_presentations.get(presentation.event_id)
        generated_component = next(
            (
                component
                for component in (() if material is None else material.components)
                if component.availability == "generated"
                and component.label == "Comentariu acid: generat de modelul local"
            ),
            None,
        )
        if generated_component is not None:
            self._voice_status.set(
                "Comentariu acid: generat de modelul local.\n"
                "Rezumatul factual guvernat a ramas neschimbat."
            )
            self._voice_preview_text.configure(state="normal")
            self._voice_preview_text.delete("1.0", "end")
            self._voice_preview_text.insert("1.0", generated_component.text)
            self._voice_preview_text.configure(state="disabled")

    def _set_voice_choices(
        self,
        *,
        widget,
        variable,
        mapping,
        choices,
        selected,
        selection_finalized,
        none_label,
    ) -> None:
        mapping.clear()
        labels = []
        for identity, label in choices:
            if label in mapping:
                raise _DesktopShellConfigurationError() from None
            mapping[label] = None if identity == "NONE" else identity
            labels.append(label)
        widget.configure(
            values=tuple(labels), state="readonly" if labels else "disabled"
        )
        selected_label = next(
            (label for label, identity in mapping.items() if identity == selected), ""
        )
        if selection_finalized and selected is None and none_label in mapping:
            selected_label = none_label
        variable.set(selected_label)

    def _clear_voice_v2_presentation(self) -> None:
        self._voice_v2_event_id = None
        self._voice_program_ids.clear()
        self._voice_expression_ids.clear()
        self._voice_program.set("")
        self._voice_expression.set("")
        self._voice_program_widget.configure(values=(), state="disabled")
        self._voice_expression_widget.configure(values=(), state="disabled")
        self._voice_adjudication = None
        self._voice_fact_candidate_ids.clear()
        self._voice_fact_candidate.set("")
        self._voice_fact_candidate_widget.configure(values=(), state="disabled")
        self._voice_mechanic.set("")
        self._voice_mechanic_widget.configure(values=(), state="disabled")
        self._voice_status.set(
            "Selectează o știre pentru a genera comentariul acid"
        )
        self._voice_preview_text.configure(state="normal")
        self._voice_preview_text.delete("1.0", "end")
        self._voice_preview_text.configure(state="disabled")
        for button in (
            self._voice_preview_button,
            self._voice_accept_button,
            self._voice_reject_button,
            self._voice_refresh_button,
            self._voice_fact_accept_button,
            self._voice_fact_reject_button,
            self._voice_fact_qualify_button,
            self._voice_finalize_facts_button,
            self._voice_no_claim_button,
            self._voice_confirm_mechanic_button,
            self._voice_finalize_claims_button,
        ):
            button.configure(state="disabled")

    def _selected_fact_candidate(self) -> str | None:
        return self._voice_fact_candidate_ids.get(self._voice_fact_candidate.get())

    @staticmethod
    def _voice_ids(value: str | None) -> tuple[str, ...]:
        return tuple(item.strip() for item in (value or "").split(",") if item.strip())

    def _voice_adjudication_action(self, **values) -> None:
        from .voice_adjudication_actions import VoiceDesktopAdjudicationActionV1

        if self._voice_v2_event_id is None:
            return
        self._invoke(
            "voice_v2",
            input=VoiceDesktopAdjudicationActionV1(
                event_id=self._voice_v2_event_id,
                owner_identity="desktop-owner",
                occurred_at=datetime.now(UTC),
                **values,
            ),
        )

    def _voice_reject_fact(self) -> None:
        from pastila_scout.voice_adjudication_v2 import CandidateOwnerDispositionV1

        candidate = self._selected_fact_candidate()
        if candidate:
            self._voice_adjudication_action(
                action="decide_fact",
                candidate_identity=candidate,
                disposition=CandidateOwnerDispositionV1.REJECT,
                decision_rationale=(
                    "Editorul a respins fragmentul ca fapt independent utilizabil."
                ),
                supersession_reason=self._voice_supersession_reason(candidate),
            )

    def _voice_qualify_fact(self) -> None:
        from pastila_scout.voice_adjudication_v2 import CandidateOwnerDispositionV1

        candidate = self._selected_fact_candidate()
        if candidate:
            rationale = simpledialog.askstring(
                "Motivare decizie",
                "De ce necesită acest candidat calificare?",
                parent=self._root,
            )
            if not rationale:
                return
            self._voice_adjudication_action(
                action="decide_fact",
                candidate_identity=candidate,
                disposition=CandidateOwnerDispositionV1.REQUIRES_QUALIFICATION,
                decision_rationale=rationale,
                governed_object_or_scope=simpledialog.askstring(
                    "Calificare factuală",
                    "Ce obiect sau domeniu trebuie calificat?",
                    parent=self._root,
                ),
                supersession_reason=self._voice_supersession_reason(candidate),
            )

    def _voice_accept_fact(self) -> None:
        """Confirm one extracted fact without exposing storage/schema fields."""
        from pastila_scout.voice_adjudication_v2 import CandidateOwnerDispositionV1
        from pastila_scout.voice_fact_atoms_v2.models import (
            AtomKind,
            CompleteQuantityV1,
        )

        from .voice_adjudication_actions import VoiceDesktopFactAtomInputV1

        candidate = self._selected_fact_candidate()
        item = next(
            (
                value
                for value in (
                    self._voice_adjudication.candidates
                    if self._voice_adjudication is not None
                    else ()
                )
                if value.candidate_identity == candidate
            ),
            None,
        )
        if candidate is None or item is None:
            return
        kind = {
            "exact_span": AtomKind.EVENT_PROPOSITION,
            "named_entity": AtomKind.ACTOR_ENTITY,
            "complete_quantity": AtomKind.COMPLETE_QUANTITY,
            "attribution_marker": AtomKind.ATTRIBUTION,
            "date_time": AtomKind.CHRONOLOGY,
        }.get(item.candidate_kind)
        if kind is None:
            messagebox.showinfo(
                "Necesită clarificare",
                "Acest fragment are nevoie de context. Folosește «Necesită clarificare».",
                parent=self._root,
            )
            return
        quantity = None
        governed_scope = item.exact_text
        if kind is AtomKind.COMPLETE_QUANTITY:
            governed_scope = (
                simpledialog.askstring(
                    "Confirmă valoarea",
                    f"La ce se referă «{item.exact_text}»?",
                    parent=self._root,
                )
                or ""
            ).strip()
            payload = self._daily_use_quantity(item.exact_text, governed_scope)
            if payload is None:
                return
            quantity = CompleteQuantityV1(**payload)
        atom_id = "editor-fact-" + hashlib.sha256(
            candidate.encode("utf-8")
        ).hexdigest()[:16]
        self._voice_adjudication_action(
            action="decide_fact",
            candidate_identity=candidate,
            disposition=CandidateOwnerDispositionV1.ACCEPT_TYPED_ATOM,
            decision_rationale="Editorul a confirmat fragmentul ca fapt utilizabil.",
            atom_input=VoiceDesktopFactAtomInputV1(
                atom_id=atom_id,
                atom_kind=kind,
                quantity=quantity,
            ),
            governed_object_or_scope=governed_scope,
            supersession_reason=self._voice_supersession_reason(candidate),
        )

    @staticmethod
    def _daily_use_quantity(text: str, scope: str | None) -> dict | None:
        scope = (scope or "").strip()
        number = re.search(r"\d[\d. ,]*", text)
        unit = re.search(
            r"(?i)(%|lei|euro|dolari|persoane|oameni|ani|luni|zile|ore)", text
        )
        if not scope or number is None or unit is None:
            return None
        marker_match = re.search(
            r"(?i)\b(aproximativ|circa|peste|cel puțin|maximum|minimum)\b", text
        )
        marker = None if marker_match is None else marker_match.group(1)
        semantics = (
            "lower_bound"
            if marker in {"peste", "cel puțin"}
            else "upper_bound"
            if marker == "maximum"
            else "approximate"
            if marker in {"aproximativ", "circa"}
            else "exact"
        )
        return {
            "exact_surface": text,
            "numeric_surface": number.group(0).strip(),
            "approximation": marker,
            "bound_semantics": semantics,
            "unit_or_currency": unit.group(1),
            "subject_scope": scope,
        }

    def _voice_accept_fact_advanced(self) -> None:
        """Retained governed form for tests/internal tooling; not bound in daily use."""
        from pastila_scout.voice_adjudication_v2 import CandidateOwnerDispositionV1
        from pastila_scout.voice_fact_atoms_v2.models import (
            AtomKind,
            CompleteQuantityV1,
        )

        from .voice_adjudication_actions import VoiceDesktopFactAtomInputV1

        candidate = self._selected_fact_candidate()
        atom_id = simpledialog.askstring(
            "Fapt tipizat", "ID unic atom:", parent=self._root
        )
        kind_value = simpledialog.askstring(
            "Fapt tipizat",
            "Tip atom (" + ", ".join(item.value for item in AtomKind) + "):",
            parent=self._root,
        )
        if not candidate or not atom_id or not kind_value:
            return
        rationale = simpledialog.askstring(
            "Motivare decizie",
            "De ce este acceptat acest atom factual?",
            parent=self._root,
        )
        if not rationale:
            return
        kind = AtomKind(kind_value)
        quantity = None
        if kind is AtomKind.COMPLETE_QUANTITY:
            exact = simpledialog.askstring(
                "Cantitate", "Suprafață cantitativă exactă:", parent=self._root
            )
            numeric = simpledialog.askstring(
                "Cantitate", "Suprafață numerică:", parent=self._root
            )
            semantics = simpledialog.askstring(
                "Cantitate",
                "Semantică (exact/approximate/lower_bound/upper_bound):",
                parent=self._root,
            )
            unit = simpledialog.askstring(
                "Cantitate", "Unitate sau monedă:", parent=self._root
            )
            scope = simpledialog.askstring(
                "Cantitate", "Domeniul cantității:", parent=self._root
            )
            if not all((exact, numeric, semantics, unit, scope)):
                return
            quantity = CompleteQuantityV1(
                exact_surface=exact,
                numeric_surface=numeric,
                approximation=simpledialog.askstring(
                    "Cantitate",
                    "Marcaj aproximare (gol dacă nu există):",
                    parent=self._root,
                )
                or None,
                bound_semantics=semantics,
                unit_or_currency=unit,
                denominator=simpledialog.askstring(
                    "Cantitate", "Numitor (opțional):", parent=self._root
                )
                or None,
                period=simpledialog.askstring(
                    "Cantitate", "Perioadă (opțional):", parent=self._root
                )
                or None,
                subject_scope=scope,
            )
        targets = self._voice_ids(
            simpledialog.askstring(
                "Fapt tipizat",
                "ID-uri țintă pentru calificare, separate prin virgulă:",
                parent=self._root,
            )
        )
        self._voice_adjudication_action(
            action="decide_fact",
            candidate_identity=candidate,
            disposition=CandidateOwnerDispositionV1.ACCEPT_TYPED_ATOM,
            decision_rationale=rationale,
            atom_input=VoiceDesktopFactAtomInputV1(
                atom_id=atom_id,
                atom_kind=kind,
                quantity=quantity,
                qualification_target_atom_ids=targets,
            ),
            governed_object_or_scope=simpledialog.askstring(
                "Fapt tipizat", "Obiect/domeniu guvernat:", parent=self._root
            ),
            actor_or_subject_atom_ids=self._voice_ids(
                simpledialog.askstring(
                    "Legături", "ID-uri actor/subiect:", parent=self._root
                )
            ),
            chronology_atom_ids=self._voice_ids(
                simpledialog.askstring(
                    "Legături", "ID-uri cronologie:", parent=self._root
                )
            ),
            uncertainty_target_atom_ids=self._voice_ids(
                simpledialog.askstring(
                    "Legături",
                    "ID-uri țintă incertitudine/acuzație:",
                    parent=self._root,
                )
            ),
            attribution_atom_ids=self._voice_ids(
                simpledialog.askstring(
                    "Legături", "ID-uri atribuire:", parent=self._root
                )
            ),
            supersession_reason=self._voice_supersession_reason(candidate),
        )

    def _voice_supersession_reason(self, candidate: str) -> str | None:
        if self._voice_adjudication is None:
            return None
        item = next(
            (
                item
                for item in self._voice_adjudication.candidates
                if item.candidate_identity == candidate
            ),
            None,
        )
        if item is None or item.disposition == "undecided":
            return None
        return simpledialog.askstring(
            "Revizuire", "Motivul înlocuirii deciziei anterioare:", parent=self._root
        )

    def _voice_finalize_facts(self) -> None:
        self._voice_adjudication_action(action="finalize_facts")

    def _voice_choose_no_claim(self) -> None:
        reason = simpledialog.askstring(
            "Fără construcție", "Motivul deciziei NO CLAIM:", parent=self._root
        )
        if reason:
            self._voice_adjudication_action(
                action="choose_no_claim", no_claim_reason=reason
            )

    def _voice_confirm_mechanic(self) -> None:
        from pastila_scout.voice_deterministic_v2.models import MechanicIdV1
        from pastila_scout.voice_eligibility_v2.models import AtomRoleBindingV1

        mechanic = self._voice_mechanic.get()
        if not mechanic:
            return
        count = simpledialog.askinteger(
            "Legături mecanică",
            "Număr de roluri (1-3):",
            minvalue=1,
            maxvalue=3,
            parent=self._root,
        )
        if count is None:
            return
        roles = []
        for index in range(1, count + 1):
            role = simpledialog.askstring(
                "Legături mecanică", f"Numele rolului {index}:", parent=self._root
            )
            atom_ids = self._voice_ids(
                simpledialog.askstring(
                    "Legături mecanică",
                    f"ID-uri atom pentru rolul {index}:",
                    parent=self._root,
                )
            )
            if not role or not atom_ids:
                return
            roles.append(AtomRoleBindingV1(role=role, atom_ids=atom_ids))
        boundaries = self._voice_ids(
            simpledialog.askstring(
                "Limite",
                "Coduri epistemice/limită, separate prin virgulă:",
                parent=self._root,
            )
        )
        supersession_reason = simpledialog.askstring(
            "Revizuire mecanică",
            "Motivul revizuirii (lăsați gol pentru o confirmare nouă):",
            parent=self._root,
        )
        self._voice_adjudication_action(
            action="confirm_mechanic_claim",
            mechanic_id=MechanicIdV1(mechanic),
            atom_roles=tuple(roles),
            satisfied_boundary_codes=boundaries,
            supersession_reason=supersession_reason or None,
        )

    def _voice_finalize_claims(self) -> None:
        self._voice_adjudication_action(action="finalize_claims")

    def _voice_action(self, action: str, candidate_identity: str | None = None) -> None:
        from .voice_v2_interaction import VoiceDesktopActionInputV2

        if self._voice_v2_event_id is None:
            return
        self._invoke(
            "voice_v2",
            input=VoiceDesktopActionInputV2(
                action=action,
                event_id=self._voice_v2_event_id,
                candidate_identity=candidate_identity,
            ),
        )

    def _generate_acid_commentary(self) -> None:
        if self._voice_v2_event_id is None:
            return
        self._voice_status.set("Cererea de generare locală a fost trimisă…")
        self._invoke("acid_commentary", input=self._voice_v2_event_id)

    def _voice_program_selected(self, event: object) -> None:
        del event
        label = self._voice_program.get()
        if label in self._voice_program_ids:
            self._voice_action("select_program", self._voice_program_ids[label])

    def _voice_expression_selected(self, event: object) -> None:
        del event
        label = self._voice_expression.get()
        if label in self._voice_expression_ids:
            self._voice_action("select_expression", self._voice_expression_ids[label])

    def publish_chief_editor(
        self,
        *,
        title: str,
        available: tuple[tuple[str, str], ...],
        items: tuple[tuple[str, str, str, str], ...],
        status: str = "",
        can_publish_episode_draft: bool = False,
        v2_presentations: tuple[tuple[str, str], ...] = (),
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
        self._chief_v2_presentations = dict(v2_presentations)
        self._render_chief_editor_material()
        self._chief_status.set(
            status or (_text_v1(key="chief_editor.empty") if not items else "")
        )
        self._episode_publish_available = can_publish_episode_draft
        self._sync_episode_draft_actions()

    def publish_episode_draft(
        self,
        *,
        status: str,
        current: bool,
        revision_id: str,
        parent_revision_id: str,
        included: tuple[tuple[int, str, str], ...],
        excluded: tuple[tuple[int, str, str], ...],
        assembled_text: str,
        approval_pending: bool = False,
        can_submit_approval: bool = False,
        approval_approved: bool = False,
        can_approve: bool = False,
    ) -> None:
        self._check()
        self._episode_draft_status.set(status)
        self._episode_draft_current = current
        self._episode_draft_details = (
            revision_id,
            parent_revision_id,
            included,
            excluded,
            assembled_text,
        )
        self._episode_draft_can_submit_approval = (
            can_submit_approval and not approval_pending
        )
        self._episode_draft_approval_running = False
        self._episode_draft_can_approve = can_approve and not approval_approved
        self._episode_draft_final_running = False
        self._sync_episode_draft_actions()

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
        self._render_chief_editor_material()

    def _render_chief_editor_material(self) -> None:
        selected = self._chief_items.selection()
        text = self._chief_v2_presentations.get(selected[0], "") if selected else ""
        self._chief_material_text.configure(state="normal")
        self._chief_material_text.delete("1.0", "end")
        if text:
            self._chief_material_text.insert("1.0", text)
        self._chief_material_text.configure(state="disabled")

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

    def _editorial_evidence_open_action(self) -> None:
        selected = self._chief_items.selection()
        if selected:
            self._invoke("editorial_evidence_inspect", input=selected[0])

    def publish_editorial_evidence(
        self,
        *,
        capture_id: str,
        generated_text: str,
        final_text: str | None,
        diff_rows: tuple[tuple[int, str, str, str], ...],
        kpi_summary: str,
    ) -> None:
        self._check()
        child = tkinter.Toplevel(self._root)
        child.title(_text_v1(key="editorial_evidence.title"))
        child.transient(self._root)
        child.columnconfigure(0, weight=1)
        ttk.Label(child, text="Textul generat initial").grid(
            row=0, column=0, sticky="w", padx=8, pady=(8, 2)
        )
        baseline = tkinter.Text(child, height=8, wrap="word")
        baseline.insert("1.0", generated_text)
        baseline.configure(state="disabled")
        baseline.grid(row=1, column=0, columnspan=3, sticky="nsew", padx=8)
        ttk.Label(child, text="Versiunea finala a proprietarului").grid(
            row=2, column=0, sticky="w", padx=8, pady=(8, 2)
        )
        owner_final = tkinter.Text(child, height=8, wrap="word")
        owner_final.insert(
            "1.0", final_text if final_text is not None else generated_text
        )
        owner_final.configure(state="disabled" if final_text is not None else "normal")
        owner_final.grid(row=3, column=0, columnspan=3, sticky="nsew", padx=8)

        def finalize() -> None:
            self._invoke(
                "editorial_evidence_finalize",
                input={
                    "capture_id": capture_id,
                    "final_text": owner_final.get("1.0", "end-1c"),
                },
            )
            child.destroy()

        ttk.Button(
            child,
            text=_text_v1(key="editorial_evidence.finalize"),
            state="disabled" if final_text is not None else "normal",
            command=finalize,
        ).grid(row=4, column=0, sticky="w", padx=8, pady=8)
        ttk.Label(child, text=kpi_summary).grid(
            row=4, column=1, columnspan=2, sticky="w", padx=8
        )
        differences = ttk.Treeview(
            child,
            columns=("operation", "severity", "class"),
            show="headings",
            height=6,
        )
        for name, label in (
            ("operation", "Operatie"),
            ("severity", "Severitate"),
            ("class", "Clasa propusa"),
        ):
            differences.heading(name, text=label)
        for index, operation, severity, proposed in diff_rows:
            differences.insert(
                "", "end", iid=str(index), values=(operation, severity, proposed)
            )
        differences.grid(row=5, column=0, columnspan=3, sticky="nsew", padx=8)
        edit_class = tkinter.StringVar(value="UNKNOWN")
        learnability = tkinter.StringVar(value="UNKNOWN")
        ttk.Combobox(
            child,
            textvariable=edit_class,
            state="readonly",
            values=(
                "FACT_CORRECTION",
                "REMOVE_HALLUCINATION",
                "STYLE_OR_VOICE",
                "STRUCTURE",
                "EXPRESSION_OR_WORDING",
                "MECHANISM_OR_JOKE",
                "REDUNDANCY",
                "TRANSITION",
                "UNKNOWN",
            ),
        ).grid(row=6, column=0, padx=8, pady=8)
        ttk.Combobox(
            child,
            textvariable=learnability,
            state="readonly",
            values=("STYLE_CANDIDATE", "FACT_ONLY", "ONE_OFF", "UNKNOWN"),
        ).grid(row=6, column=1, padx=8, pady=8)

        def classify() -> None:
            selected = differences.selection()
            if selected:
                self._invoke(
                    "editorial_evidence_classify",
                    input={
                        "capture_id": capture_id,
                        "diff_index": int(selected[0]),
                        "edit_class": edit_class.get(),
                        "learnability": learnability.get(),
                    },
                )
                child.destroy()

        ttk.Button(
            child,
            text=_text_v1(key="editorial_evidence.classify"),
            state="normal" if final_text is not None else "disabled",
            command=classify,
        ).grid(row=6, column=2, padx=8, pady=8)

    def _episode_draft_publish_action(self) -> None:
        self._episode_draft_status.set("Publicare draft episod in curs...")
        self._invoke("episode_draft_publish", input=self._chief_editor_payload())

    def _sync_episode_draft_actions(self) -> None:
        idle = getattr(self, "_editor_idle", True)
        publish = (
            idle
            and self._episode_publish_available
            and "episode_draft_publish" in self._bindings
        )
        self._episode_draft_button.configure(state="normal" if publish else "disabled")
        self._episode_inspect_button.configure(
            state="normal" if self._episode_draft_current else "disabled"
        )
        approval_button = getattr(self, "_episode_approval_button", None)
        if approval_button is not None:
            try:
                approval_button.configure(
                    state=(
                        "normal"
                        if idle
                        and self._episode_draft_can_submit_approval
                        and not self._episode_draft_approval_running
                        and "episode_draft_approval" in self._bindings
                        else "disabled"
                    )
                )
            except tkinter.TclError:
                self._episode_approval_button = None
        final_button = getattr(self, "_episode_final_button", None)
        if final_button is not None:
            try:
                final_button.configure(
                    state=(
                        "normal"
                        if idle
                        and self._episode_draft_can_approve
                        and not self._episode_draft_final_running
                        and "episode_draft_final" in self._bindings
                        else "disabled"
                    )
                )
            except tkinter.TclError:
                self._episode_final_button = None

    def _episode_draft_inspect(self) -> None:
        if not self._episode_draft_current:
            return
        revision, parent, included, excluded, assembled = self._episode_draft_details
        child = tkinter.Toplevel(self._root)
        child.title(_text_v1(key="episode_draft.inspection"))
        child.transient(self._root)
        child.columnconfigure(0, weight=1)
        child.rowconfigure(7, weight=1)
        ttk.Label(
            child,
            text=f"{_text_v1(key='episode_draft.revision')}: {revision}",
        ).grid(row=0, column=0, sticky="w", padx=8, pady=(8, 2))
        ttk.Label(
            child,
            text=(f"{_text_v1(key='episode_draft.parent')}: {parent or '-'}"),
        ).grid(row=1, column=0, sticky="w", padx=8, pady=2)
        ttk.Label(child, text=_text_v1(key="episode_draft.included")).grid(
            row=2, column=0, sticky="w", padx=8
        )
        included_view = ttk.Treeview(
            child, columns=("story", "material"), show="headings", height=5
        )
        included_view.heading("story", text="Stire")
        included_view.heading("material", text="Material sursa")
        for event_id, title, material in included:
            included_view.insert(
                "", "end", iid=f"included:{event_id}", values=(title, material)
            )
        included_view.grid(row=3, column=0, sticky="ew", padx=8)
        ttk.Label(child, text=_text_v1(key="episode_draft.excluded")).grid(
            row=4, column=0, sticky="w", padx=8, pady=(6, 0)
        )
        excluded_view = ttk.Treeview(
            child, columns=("story", "reason"), show="headings", height=3
        )
        excluded_view.heading("story", text="Stire")
        excluded_view.heading("reason", text="Motiv")
        for event_id, title, reason in excluded:
            excluded_view.insert(
                "", "end", iid=f"excluded:{event_id}", values=(title, reason)
            )
        excluded_view.grid(row=5, column=0, sticky="nsew", padx=8)
        ttk.Label(child, text=_text_v1(key="episode_draft.preview")).grid(
            row=6, column=0, sticky="w", padx=8, pady=(6, 0)
        )
        preview = tkinter.Text(child, height=10, wrap="word")
        preview.insert("1.0", assembled)
        preview.configure(state="disabled")
        preview.grid(row=7, column=0, sticky="nsew", padx=8, pady=(0, 8))
        export_button = _primary_action_button(
            child,
            text=_text_v1(key="episode_draft.export"),
            command=lambda: self._episode_draft_export_action(revision),
            width=_EPISODE_DRAFT_INSPECTION_ACTION_WIDTH,
            state=(
                "normal"
                if "episode_draft_export" in self._bindings
                and not self._episode_draft_export_running
                else "disabled"
            ),
        )
        export_button.master.grid(row=8, column=0, pady=(0, 8))
        approval_button = _primary_action_button(
            child,
            text=_text_v1(key="episode_draft.approval"),
            command=lambda: self._episode_draft_approval_action(revision),
            width=_EPISODE_DRAFT_INSPECTION_ACTION_WIDTH,
            state=(
                "normal"
                if self._episode_draft_can_submit_approval
                and "episode_draft_approval" in self._bindings
                and not self._episode_draft_approval_running
                and getattr(self, "_editor_idle", True)
                else "disabled"
            ),
        )
        self._episode_approval_button = approval_button
        approval_button.master.grid(row=9, column=0, pady=(0, 8))
        final_button = _primary_action_button(
            child,
            text=_text_v1(key="episode_draft.final_approve"),
            command=lambda: self._episode_draft_final_action(revision),
            width=_EPISODE_DRAFT_INSPECTION_ACTION_WIDTH,
            state=(
                "normal"
                if self._episode_draft_can_approve
                and "episode_draft_final" in self._bindings
                and not self._episode_draft_final_running
                and getattr(self, "_editor_idle", True)
                else "disabled"
            ),
        )
        self._episode_final_button = final_button
        final_button.master.grid(row=10, column=0, pady=(0, 8))
        ttk.Label(child, textvariable=self._episode_draft_status).grid(
            row=11, column=0, sticky="w", padx=8, pady=(0, 8)
        )

    def _episode_draft_export_action(self, revision_id: str) -> None:
        if self._episode_draft_export_running:
            return
        self._episode_draft_export_running = True
        self._episode_draft_status.set("Export draft in curs...")
        try:
            self._invoke("episode_draft_export", input=revision_id)
        finally:
            if self._episode_draft_export_running:
                self._episode_draft_status.set(
                    "Draftul nu a putut fi exportat la destinatia aleasa."
                )
            self._episode_draft_export_running = False
            self._sync_episode_draft_actions()

    def _episode_draft_final_action(self, revision_id: str) -> None:
        if self._episode_draft_final_running:
            return
        self._episode_draft_final_running = True
        self._episode_draft_status.set("Aprobare draft in curs...")
        self._sync_episode_draft_actions()
        try:
            self._invoke("episode_draft_final", input=revision_id)
        finally:
            if self._episode_draft_final_running:
                self._episode_draft_status.set("Draftul nu a putut fi aprobat.")
            self._episode_draft_final_running = False
            self._sync_episode_draft_actions()

    def _episode_draft_approval_action(self, revision_id: str) -> None:
        if self._episode_draft_approval_running:
            return
        self._episode_draft_approval_running = True
        self._episode_draft_status.set("Trimitere pentru aprobare in curs...")
        self._sync_episode_draft_actions()
        try:
            self._invoke("episode_draft_approval", input=revision_id)
        finally:
            if self._episode_draft_approval_running:
                self._episode_draft_status.set(
                    "Draftul nu a putut fi trimis pentru aprobare."
                )
            self._episode_draft_approval_running = False
            self._sync_episode_draft_actions()

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
        self._set_navigation_page(snapshot.selected_page)
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
        self._sync_episode_draft_actions()
        if not idle:
            self._handoff_button.configure(state="disabled")
        else:
            self._sync_handoff()
        if snapshot.is_closed:
            for badge in self._navigation_badges.values():
                badge.unbind("<Button-1>")
            self._scout_button.configure(state="disabled")
            self._editor_button.configure(state="disabled")
            self._editor_retry_button.configure(state="disabled")
            self._handoff_button.configure(state="disabled")
            self._report_button.configure(state="disabled")
            self._episode_draft_button.configure(state="disabled")
            self._episode_inspect_button.configure(state="disabled")
            for button in (
                self._voice_preview_button,
                self._voice_accept_button,
                self._voice_reject_button,
                self._voice_refresh_button,
            ):
                button.configure(state="disabled")
            self._voice_program_widget.configure(state="disabled")
            self._voice_expression_widget.configure(state="disabled")

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
