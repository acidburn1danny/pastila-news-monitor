# Desktop Shell Specification V1

Status: implementation-ready specification for Phase 5.1C. This document specifies
the private Tkinter/ttk shell implemented in Phase 5.1D. It does not authorize
production code, backend adapters, packaging, paths, updates, or version consumption.

## 1. Authority and scope

The normative prerequisite is
`phase-5.1b-desktop-application-facade-r1-verified` at
`64ae9c9ddf26797e3fe887b28d86c1352bd411f6`. The frozen Windows Desktop
Productization Specification V11 at
`4727a480ad95da82dd6a982bfdde53ae0e73d0a6` owns the desktop architecture and
roadmap. The frozen
Desktop Application Facade Specification V1 and its verified implementation own the
GUI-neutral request, progress, result, and synchronous service boundary.

Phase 5.1D is limited to these production paths:

- `src/pastila_scout/desktop_v1/__init__.py`;
- `src/pastila_scout/desktop_v1/entrypoint.py`;
- `src/pastila_scout/desktop_v1/controller.py`;
- `src/pastila_scout/desktop_v1/models.py`;
- `src/pastila_scout/desktop_v1/views.py`;
- `src/pastila_scout/desktop_v1/resources.py`;
- `src/pastila_scout/desktop_v1/errors.py`;
- `pyproject.toml`.

Its only test path is `tests/test_desktop_shell_v1.py`. No other path is necessary.
The implementation adds the private desktop shell and the `pastila-scout-gui` console
entry point. The package exports no Python API. Backend execution, paths, updater
behavior, version consumption, packaging, Scout integration, Editor integration,
report generation, persistence, provider selection, and provider execution are
forbidden.

## 2. Repository grounding

The repository at the prerequisite establishes these facts:

| Area | Existing authority | Shell consequence |
| --- | --- | --- |
| Console application | `pastila_scout.cli:main`, registered as `pastila-scout` | The GUI is an additional entry point; the existing CLI is unchanged and is never imported by the shell. |
| Desktop application boundary | `pastila_scout.desktop_application_v1` | Its synchronous facade and immutable values remain frozen. The shell neither composes nor invokes the facade in Phase 5.1D. |
| Scout desktop adapter | none | Phase 5.2A specifies it and Phase 5.2B implements it. Scout controls in the initial shell are presentational and disabled. |
| Editor desktop adapter | none | Phase 5.3A specifies it and Phase 5.3B implements it. Editor controls in the initial shell are presentational and disabled. |
| Windows paths/settings | none | Phase 5.4 owns them. The shell reads no environment variable, configuration file, current-working-directory path, database, or credential. |
| Version projection | none | Phase 5.5D owns it. About contains no version label, placeholder, import, lookup, or `pyproject.toml` parsing. |
| Updater | none | Phase 5.7 owns update behavior and Phase 5.8 owns Update Center widgets. Check for Updates is disabled and performs no action in Phase 5.1D. |
| GUI | none | There is no existing Tk, Qt, window, widget, GUI entry point, executor controller, or desktop resource module. |

The shell depends only on the Python standard library. `tkinter` and `ttk` are the
sole GUI framework. No runtime dependency is added to `project.dependencies`.

## 3. Ownership boundary

Phase 5.1C owns this specification only. Phase 5.1D owns:

- one Tk root and one main window;
- private shell state and finite shell failures;
- immutable Romanian resource data;
- navigation and widget-state projection;
- one application executor and one update executor;
- worker-to-Tk publication through one queue and `root.after(50, ...)`;
- deterministic close and executor shutdown;
- the `pastila-scout-gui` entry point.

Already frozen Phase 5.1B owns all facade values, validation, progress events, and
synchronous Scout/Editor delegation. Phase 5.2 owns the Scout adapter, failed-source
projection, HTML report, and report catalog. Phase 5.3 owns Editor adapter and facade
composition. Phase 5.4 owns paths and settings. Phase 5.5D owns version projection.
Phases 5.7 and 5.8 own update execution and Update Center behavior. None is duplicated
here.

## 4. Dependency direction and passivity

The exact Phase 5.1D dependency graph is:

```text
pyproject.toml console entry
  -> pastila_scout.desktop_v1.entrypoint
     -> pastila_scout.desktop_v1.controller
     -> pastila_scout.desktop_v1.views
     -> pastila_scout.desktop_v1.models
     -> pastila_scout.desktop_v1.resources
     -> pastila_scout.desktop_v1.errors
```

`models`, `resources`, and `errors` import no Tk modules. `views` imports `tkinter`,
`tkinter.ttk`, and the private shell modules. `controller` imports concurrency and queue
stdlib modules plus private shell modules; it does not import `views` or Tk widget
classes. `entrypoint` is the sole module that creates a Tk root and wires controller to
views. `desktop_v1.__init__` imports nothing and sets `__all__ = ()`.

Importing any shell module performs zero root creation, widget creation, executor
construction, task submission, timer registration, environment access, credential
access, file access, networking, provider selection, provider construction, facade
composition, logging configuration, or process exit. Only calling `main()` activates
the shell.

## 5. Exact private module contract

All names in this section are package-private. They are not re-exported by
`pastila_scout.desktop_v1`.

### 5.1 `models.py`

```python
class _DesktopPageV1(StrEnum):
    SCOUT = "scout"
    EDITOR = "editor"

class _DesktopLaneV1(StrEnum):
    APPLICATION = "application"
    UPDATE = "update"

class _DesktopTaskStateV1(StrEnum):
    IDLE = "idle"
    SUBMITTED = "submitted"
    RUNNING = "running"
    CANCELLING = "cancelling"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    CLOSED = "closed"

@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class _DesktopQueueEventV1:
    lane: _DesktopLaneV1
    state: _DesktopTaskStateV1
    completion: _DesktopTaskCompletionV1 | None

@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class _DesktopTaskCompletionV1:
    value: object

@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class _DesktopScoutActionInputV1:
    period: str
    category: str

@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class _DesktopEditorActionInputV1:
    scout_input_path: str
    selection_profile_path: str
    episode_context_path: str
    generation_config_path: str
    provider: str
    model: str
    timeout_seconds: str
    output_path: str
    no_replace: bool

@dataclass(frozen=True, slots=True, init=False, repr=False, eq=False)
class _DesktopShellSnapshotV1:
    selected_page: _DesktopPageV1
    application_state: _DesktopTaskStateV1
    update_state: _DesktopTaskStateV1
    is_closed: bool
```

`_DesktopShellSnapshotV1` accepts exact enum instances and exact `bool`. `CLOSED` is
valid for both lane states if and only if `is_closed` is true; when `is_closed` is
false neither lane is `CLOSED`. Construction otherwise raises
`_DesktopShellConfigurationError` from no cause. These shell-only values contain no
request, result, provider, path, version, or backend object.

`_DesktopQueueEventV1` accepts exact enum instances and either an exact
`_DesktopTaskCompletionV1` or `None`. Its state must be one of `RUNNING`, `COMPLETED`,
`FAILED`, or `CANCELLED`; `IDLE`, `SUBMITTED`, `CANCELLING`, and `CLOSED` are rejected.
`COMPLETED` requires a completion and every other state requires `None`. It is the only
queue item type. `_DesktopTaskCompletionV1` is a transient opaque transport: it never
calls, compares, copies, formats, serializes, or inspects `value`, and its fixed repr
contains no value detail. The controller removes its sole reference immediately after
Tk-thread delivery. Snapshots contain no request, result, or backend object.

The module also owns exactly
`_reconstruct_desktop_queue_event_v1(value: object) -> _DesktopQueueEventV1` and
`_reconstruct_desktop_task_completion_v1(value: object) -> _DesktopTaskCompletionV1`,
`_reconstruct_desktop_scout_action_input_v1(value: object) -> _DesktopScoutActionInputV1`,
`_reconstruct_desktop_editor_action_input_v1(value: object) -> _DesktopEditorActionInputV1`,
and
`_reconstruct_desktop_shell_snapshot_v1(value: object) -> _DesktopShellSnapshotV1`.
Constructors and reconstructors apply the stated exact-type and cross-field rules.
Equality compares reconstructed field tuples. Repr contains only the enum serialized
values and closed flag. Copy and deepcopy call the reconstructor. No additional model
or generic state dictionary is permitted.

The two action-input values accept only exact `str` fields and, for Editor, exact `bool`.
They preserve GUI text without normalization or interpretation, use fully redacted repr,
compare reconstructed field tuples, and reconstruct on copy/deepcopy through the two
exactly named reconstructors above. They are GUI-local snapshots,
not facade requests; later adapter/startup specifications exclusively own parsing,
validation, path loading, provider selection, and facade-request construction.

### 5.2 `errors.py`

```python
class _DesktopShellConfigurationError(Exception): ...
class _DesktopShellExecutionError(Exception): ...
```

Both are final, have no custom state, use a fixed empty message, and suppress chained
causes. Configuration errors identify invalid shell construction or calls. Execution
errors identify only failure of a submitted injected test task or executor lifecycle.
No raw exception, traceback, path, credential, request, result, callable repr, or memory
address reaches a view.

### 5.3 `resources.py`

The module owns exact immutable tuples of `(key, Romanian text)` pairs and one private
lookup function `_text_v1(*, key: str) -> str`. Duplicate keys and unknown keys fail
with `_DesktopShellConfigurationError`. Widget code contains no user-visible literal.

The exact keys and values are:

| Key | UTF-8 value |
| --- | --- |
| `app.title` | `Pastila Scout` |
| `menu.file` | `Fișier` |
| `menu.file.exit` | `Ieșire` |
| `menu.view` | `Vizualizare` |
| `menu.view.scout` | `Scout` |
| `menu.view.editor` | `Editor` |
| `menu.help` | `Ajutor` |
| `menu.help.about` | `Despre` |
| `menu.help.check_updates` | `Caută actualizări` |
| `navigation.scout` | `Scout` |
| `navigation.editor` | `Editor` |
| `scout.period` | `PERIOADA` |
| `scout.category` | `CATEGORIA` |
| `scout.run` | `CAUTĂ` |
| `scout.results` | `REZULTATE` |
| `scout.intro` | `Selectați perioada și categoria, apoi apăsați „CAUTĂ”.` |
| `scout.progress.reading` | `Pastila citește ziarele…` |
| `scout.progress.verifying` | `verifică și compară…` |
| `scout.progress.writing` | `scrie raportul pentru șefu’…` |
| `scout.progress.ready` | `Gata, șefu’! Raportul este pregătit.` |
| `scout.failed_sources` | `Surse nereușite` |
| `scout.report` | `Deschide raportul` |
| `editor.title` | `Editor` |
| `editor.unavailable` | `Editorul va fi disponibil într-o etapă ulterioară.` |
| `editor.scout_input` | `Intrare Scout` |
| `editor.selection_profile` | `Profil de selecție` |
| `editor.episode_context` | `Context episod` |
| `editor.generation_config` | `Configurație generare` |
| `editor.provider` | `Furnizor` |
| `editor.model` | `Model` |
| `editor.timeout` | `Timp-limită (secunde)` |
| `editor.output` | `Fișier de ieșire` |
| `editor.no_replace` | `Nu înlocui fișierul existent` |
| `editor.run` | `GENEREAZĂ` |
| `about.title` | `Despre Pastila Scout` |
| `about.body` | `Pastila Scout` |
| `close.running` | `Închidere în curs…` |
| `error.internal` | `Aplicația a întâmpinat o eroare internă.` |

The About body is exactly the product name. It contains no version value or version
placeholder. The resource module is UTF-8 source and values are NFC.

### 5.4 `controller.py`

`_DesktopTaskControllerV1` is final and has this exact constructor:

```python
class _DesktopTaskControllerV1:
    def __init__(
        self,
        *,
        schedule_after: Callable[[int, Callable[[], None]], object],
        cancel_after: Callable[[object], None],
        publish_snapshot: Callable[[_DesktopShellSnapshotV1], None],
        application_executor: Executor | None = None,
        update_executor: Executor | None = None,
    ) -> None: ...
```

`publish_snapshot` must accept exactly one keyword-only `snapshot` parameter. The
controller always invokes it as `publish_snapshot(snapshot=value)`. Both injected
executors must provide callable keyword-compatible `submit(fn)` and
`shutdown(wait=..., cancel_futures=...)`. `None` creates exactly one
`ThreadPoolExecutor(max_workers=1, thread_name_prefix="pastila-application")` for the
application lane or one with prefix `pastila-update` for the update lane. The controller
owns injected and constructed executors alike and shuts each down exactly once.

The remaining exact methods are:

```python
def start(self) -> None: ...
def select_page(self, *, page: _DesktopPageV1) -> None: ...
def submit_application(
    self,
    *,
    task: Callable[[], object],
    on_completed: Callable[[object], None],
) -> None: ...
def submit_update(
    self,
    *,
    task: Callable[[], object],
    on_completed: Callable[[object], None],
) -> None: ...
def request_cancel(self, *, lane: _DesktopLaneV1) -> None: ...
def close(self) -> None: ...
def snapshot(self) -> _DesktopShellSnapshotV1: ...
```

These methods are private infrastructure, not backend integration. In production
Phase 5.1D no view or entry point calls either submit method and no backend callable is
constructed. The methods exist so the shell's frozen single-owner executor and queue
behavior is materially testable without pulling later adapters forward.

Construction validates callable shape without executing descriptors, bodies, repr,
equality, or user hooks. It captures `threading.get_ident()` as the sole controller
thread, constructs one unbounded `queue.SimpleQueue[_DesktopQueueEventV1]`, and stores
no scheduled callback yet. Every method except the worker wrapper verifies the captured
thread identity before reading or changing controller state; mismatch raises the fixed
configuration error without invoking a dependency.

Calling `start()` is legal exactly once; it publishes the initial snapshot synchronously
and registers exactly one `schedule_after(50, drain)` callback. The opaque returned
token is stored as the one pending drain token. Returning `None` or raising is an
execution error and closes the controller through the same close transition. Only the
captured controller thread calls `publish_snapshot`, `schedule_after`, or
`cancel_after`. Workers enqueue exact `_DesktopQueueEventV1` values and never call
publication or Tk.

`on_completed` must be an exact callable with one keyword-only `result: object`
parameter and a `None` return annotation. Validation uses the same static, hook-free
rules as the constructor dependencies. The controller retains it only while its lane is
active. Submission is accepted only when started, open, and the selected lane is `IDLE`.
On the controller thread it changes `IDLE -> SUBMITTED`, publishes that snapshot
synchronously, and submits one wrapper. The wrapper enqueues `RUNNING`, invokes the
task exactly once, wraps its return value without inspection in one
`_DesktopTaskCompletionV1`, then enqueues `COMPLETED`; any `BaseException` and partial
return value are discarded and enqueue `FAILED`. No exception details survive the
wrapper. A second submission while the lane
is non-idle raises `_DesktopShellExecutionError` and performs no submit.
The task must be an exact zero-argument callable shape. If `submit(wrapper)` raises or
returns an object without a callable zero-argument `cancel`, the detail is discarded,
the lane publishes `FAILED`, is marked pending-idle, and the fixed execution error is
raised. The returned future is retained only until its lane becomes terminal or the
controller closes; its result and exception methods are never called.

`request_cancel()` changes `SUBMITTED|RUNNING -> CANCELLING`. Because Phase 5.1D has no
backend cancellation authority, it does not cancel a future, token, or thread. A later
worker terminal record changes the lane to its actual terminal state. Calling it in any
other state raises `_DesktopShellConfigurationError`. Terminal states publish once and
return to `IDLE` on the following drain cycle so a terminal snapshot is observable.

The complete non-close transition table is:

| Current | Authority | Next |
| --- | --- | --- |
| `IDLE` | controller submission | `SUBMITTED` |
| `SUBMITTED` | worker event | `RUNNING`, `COMPLETED`, or `FAILED` |
| `SUBMITTED` | controller cancellation request | `CANCELLING` |
| `RUNNING` | worker event | `COMPLETED` or `FAILED` |
| `RUNNING` | controller cancellation request | `CANCELLING` |
| `CANCELLING` | worker event | `COMPLETED`, `FAILED`, or `CANCELLED` |
| `COMPLETED`, `FAILED`, or `CANCELLED` | next drain reset | `IDLE` |

If a queued `RUNNING` event is consumed after the controller has already changed that
lane to `CANCELLING`, the event is discarded without publication and the lane remains
`CANCELLING`; this is the sole accepted no-transition event. `close()` changes every
non-closed state directly to `CLOSED`. Every other transition not listed is invalid and
triggers safe controller closure.

Each scheduled drain first clears its stored token, consumes all records already present
in `SimpleQueue` FIFO order, publishes one snapshot per accepted transition, and—if
open—registers exactly one next `schedule_after(50, drain)` and stores its returned
token. After a terminal state was published, the controller records that lane in a
private pending-idle set. At the start of the next drain it changes each pending lane to
`IDLE` in application-then-update order and publishes each resulting snapshot before
consuming new queue events. An otherwise empty drain publishes nothing and still
schedules exactly one successor.
For `COMPLETED`, before publishing the terminal snapshot, the drain removes the retained
completion handler and opaque value, invokes `on_completed(result=value)` exactly once on
the captured Tk thread, and then discards both. If that handler raises any
`BaseException`, its detail and value are discarded and the lane publishes `FAILED`
instead of `COMPLETED`. No handler runs for `FAILED`, `CANCELLED`, an invalid event, or
after close.
An event whose state is illegal from the lane's current state, or any publication or
scheduling exception, is discarded and closes the controller; no raw detail survives.
It fabricates no progress and performs no blocking wait.

`close()` is idempotent. It marks the controller closed and rejects new submissions. If
a drain token is stored, it calls `cancel_after(token)` exactly once, clears the token,
and suppresses any cancellation exception. It then changes both lane states to
`CLOSED`, attempts one final snapshot publication while discarding any callback
exception, and invokes
`shutdown(wait=False, cancel_futures=True)` exactly once on the application executor and
exactly once on the update executor. It registers no further callback. It performs no
facade, provider, network, persistence, cleanup, or process operation.

### 5.5 `views.py`

`_DesktopMainWindowV1` is final and constructed only after a root exists:

```python
class _DesktopMainWindowV1:
    def __init__(
        self,
        *,
        root: tkinter.Tk,
        on_select_page: Callable[[_DesktopPageV1], None],
        on_close: Callable[[], None],
    ) -> None: ...

    def publish_snapshot(self, *, snapshot: _DesktopShellSnapshotV1) -> None: ...
    def bind_scout_action(
        self,
        *,
        callback: Callable[[_DesktopScoutActionInputV1], None],
    ) -> None: ...
    def bind_editor_action(
        self,
        *,
        callback: Callable[[_DesktopEditorActionInputV1], None],
    ) -> None: ...
    def bind_report_action(
        self,
        *,
        callback: Callable[[str], None],
    ) -> None: ...
    def publish_scout_result(
        self,
        *,
        summary: str,
        failed_sources: tuple[str, ...],
        footer: str,
        report_reference: str | None,
    ) -> None: ...
    def publish_editor_result(self, *, status: str) -> None: ...
```

It constructs one main `ttk.Frame`, one left `ttk.Treeview` navigation control with
exactly Scout and Editor items, and one content frame containing exactly two page
frames. Selection changes call `on_select_page` with the exact enum. It never executes
application work.

The native menu has File, View, and Help. File contains Exit, which calls `on_close`.
View contains Scout and Editor navigation. Help contains About and disabled Check for
Updates. About opens one modal child showing `about.body` and an OK button supplied by
Tk; it contains no version value. Repeated About activation raises the existing child
rather than creating another.

The Scout page contains the Productization-prescribed period/category labels, initially
disabled editable selectors, disabled `CAUTĂ`, determinate progress bar at zero, status text, results
heading, numeric summary initialized to zero, failed-source panel, disabled report
action, and an empty footer. The Editor page contains its title, unavailable text, and
initially disabled fields for Scout input, selection profile, episode context, generation
configuration, model, timeout, output, and no-replace, plus a disabled read-only provider
selector containing exactly `openai` then `ollama`. These are presentation
fields only; the Shell does not load, resolve, or validate a path, provider, model,
timeout, or request. All text fields and both Scout selectors initially contain the empty
string, provider initially selects `openai`, no-replace is initially true, and the
`editor.run` action is initially disabled.
No request is created, no result is interpreted, and no status rotation runs.

The two primary `bind_scout_action` and `bind_editor_action` methods are the sole facade
action extension points. Each
requires the exact annotated one-keyword-only-argument callback shape shown above and is
legal once on the root-owning thread. Binding enables its page's input widgets and named
primary action. Scout activation constructs one immutable `_DesktopScoutActionInputV1`
from the two current strings and calls `callback(input=value)` exactly once. Editor
activation constructs one immutable `_DesktopEditorActionInputV1` from its current
strings and exact no-replace boolean and calls `callback(input=value)` exactly once.
Those two GUI-local input values are defined in `models.py`, apply exact-type validation,
contain no loaded file, provider object, request, or backend value, and use redacted repr.
`bind_report_action` separately accepts an exact one-keyword-only-argument
`reference: str` callback and is legal once under the same thread and validation rules.
It never enables the report action by itself. A later successful Scout publication with
an exact nonempty report reference enables that action; activation calls
`callback(reference=value)` once without parsing, resolving, opening, or logging it.
Repeated binding, wrong-thread binding, or an invalid callable raises the fixed
configuration error without invoking the callable. Phase 5.1D calls none of the three
binding methods.
There is no generic callback registry, plugin lookup, service locator, or runtime
discovery. Later specifications own whether and when their private composition calls
these methods.

When an enabled action is invoked, the view calls its stored callback exactly once.
It disables the action immediately before calling the callback.
`_DesktopShellConfigurationError` and `_DesktopShellExecutionError` are collapsed to
`error.internal` on the status label; every other `BaseException` is likewise discarded
and collapsed. No traceback is rendered or retained. The action is disabled until a
subsequent `IDLE` snapshot. The callback return value is ignored. The two
`publish_*_result` methods are callable only on the root-owning thread after the relevant
binding and before close. They accept the exact scalar and tuple types shown, reject
subclasses and invalid call order, and perform presentation only. Scout publication
replaces the numeric summary, failed-source rows, footer, and current opaque report
reference. The report action is enabled only when both its callback and a nonempty exact
`str` reference are present; `None` clears and disables it. Editor publication replaces
its status text. Dynamic
strings are already-safe projections created by later entrypoint integration; the view
performs no domain classification.

The constructor captures the root-owning thread identity. Every method and every widget
callback verifies that identity before accessing a root, widget, or Tk variable.
`publish_snapshot()` validates an exact snapshot,
selects and raises the matching page, synchronizes navigation selection, and disables
unbound action widgets. A bound primary action remains enabled only while its lane is
`IDLE`; all non-idle snapshots disable it. It does not infer backend progress. A closed
snapshot disables navigation and every action. View callbacks catch no backend
exceptions because none can be invoked in Phase 5.1D.

Navigation item order is Scout then Editor; Scout is selected initially. Selecting the
active item is idempotent and preserves all page widget values. A valid switch raises
the existing page without reconstructing either page, so both pages retain state.
An unknown tree item is immediately reset to the prior valid selection and invokes no
controller callback.

The root title is `app.title`. The minimum logical client size is 900 by 600. Widgets
use `grid`, expand with the window, preserve visible keyboard focus, and support Tab and
Shift-Tab traversal. Menu accelerators and navigation keyboard selection work without a
mouse. Styling uses ttk/system colors only and remains legible under Tk scaling 2.0.

### 5.6 `entrypoint.py`

The console target is exactly:

```toml
[project.scripts]
pastila-scout = "pastila_scout.cli:main"
pastila-scout-gui = "pastila_scout.desktop_v1.entrypoint:main"
```

`main` has exact signature `main() -> int`. It performs these steps exactly once and in
order:

1. when `sys.platform == "win32"`, call
   `ctypes.windll.shcore.SetProcessDpiAwareness(2)` once before root creation; absence,
   nonzero result, or exception is discarded and non-fatal; on other platforms make no
   DPI call;
2. create one `tkinter.Tk` root;
3. create callbacks whose controller/view cells are assigned before invocation;
4. construct one `_DesktopTaskControllerV1` with `root.after`, `root.after_cancel`, and
   the view publication callback;
5. construct one `_DesktopMainWindowV1` with the root and controller callbacks;
6. register the window-close protocol to the same close callback;
7. call controller `start()` once;
8. enter `root.mainloop()` once;
9. in `finally`, call controller `close()` once and destroy the root once if it exists;
10. return `0` after normal main-loop completion.

The close callback is guarded by one local closed flag, calls controller `close()` and
then `root.quit()` exactly once, and is a no-op thereafter. Root construction,
shell construction, or main-loop failure is caught at this outer boundary, details are
discarded, created resources are closed, and `1` is returned. Normal GUI output writes
nothing to stdout or stderr. The function never configures logging, constructs a
facade, loads credentials/configuration, imports a backend adapter, touches paths, or
performs networking.

## 6. Executor and Tk ownership

The controller is the sole owner of exactly two executors. The application executor is
reserved for future Scout, Editor, and report tasks. The update executor is reserved
for future update checks and downloads. Phase 5.1D submits zero production tasks to
both. Facade methods remain synchronous and own no executor.

The entrypoint owns the root. The view owns widgets. The controller owns task state,
queue, and executors. Only the Tk event-loop thread creates or mutates widgets. Worker
code cannot import or receive a widget. Queue publication reaches widgets only through
the 50 ms scheduled drain.

## 7. State and failure invariants

The following invariants are normative:

1. There is one root, one main window, one controller, two executors, and one drain loop.
2. The application and update lanes are independent and each accepts at most one active
   or queued task.
3. The queue is the only worker-to-controller communication channel.
4. A worker exception is discarded before queue publication; a successful return value
   crosses the queue only inside one opaque completion and is delivered once on the Tk
   thread without controller or view interpretation.
5. No traceback or chained exception reaches a snapshot, view, stdout, or stderr.
6. Closing is idempotent and shuts both executors down once.
7. Phase 5.1D production executes zero facade, Scout, Editor, report, provider, update,
   persistence, configuration, credential, path, or version operation.
8. Disabled UI never simulates an unavailable operation.
9. About contains no version consumer.
10. Existing `pastila-scout` behavior and all frozen public APIs are unchanged.
11. Root, widget, navigation, publication, scheduling, cancellation, and controller
    state mutations occur only on the captured main thread.

## 8. Public API and object safety

`pastila_scout.desktop_v1.__all__` is exactly `()`. No name is imported into the package
namespace except `__all__`. The only externally callable boundary is the console target
to private module function `main`; it is not a supported Python API.

Private enums and snapshots are immutable, slotted, reject subclassing, and reject
pickle. Snapshot copy and deepcopy reconstruct and validate. Copied-invalid state is
rejected with the fixed configuration error. Controller and view reject copy, deepcopy,
pickle, and subclassing. Their repr is a fixed redacted class label; equality is
identity. Dependency validation and all failure paths isolate tracebacks recursively so
injected callables, executor objects, roots, widgets, task values, and exceptions do not
survive in public errors or queued records.

## 9. Test specification

`tests/test_desktop_shell_v1.py` is the sole focused test file. It must cover materially:

- `SH-V-001`: exact package layout, empty `__all__`, entry-point registration, and unchanged
  `pastila-scout` registration;
- `SH-V-002`: passive import of every module under denied root/widget, executor, environment,
  credential, filesystem, socket, facade, provider, and backend construction;
- `SH-V-003`: exact resource vocabulary, NFC Romanian values, duplicate/unknown rejection, and no
  user-visible literals in widget code;
- `SH-V-004`: snapshot and action-input valid/copy/deepcopy/equality/repr behavior plus wrong types, copied-invalid,
  mutation, subclass, and pickle rejection;
- `SH-V-005`: queue-event/completion exact type, state, payload-correlation, redaction, copied-invalid,
  subclass, pickle, and rejection of every excluded combination;
- `SH-V-006`: controller dependency signatures, forged signatures/wrapping, descriptors,
  instance substitution, and rejection without executing dependency hooks;
- `SH-V-007`: exactly two executor constructions with `max_workers=1` and exact thread prefixes;
- `SH-V-008`: initial publication, exact `SimpleQueue` ownership, exactly one 50 ms drain chain,
  opaque-token retention, empty drain, multiple-event FIFO transitions, terminal
  observability, return to idle, duplicate rejection, lane independence, callback
  failure closure, and no fabricated progress;
- `SH-V-009`: injected synchronous executors for success, `None` success, `Exception`, and
  `BaseException`, proving one task call, one Tk-thread completion call with exact result
  identity, safe handler/task failure collapse, zero retained result/exception after
  drain, and zero worker widget access;
- `SH-V-010`: cancellation state without future/thread/token cancellation;
- `SH-V-011`: close before start, close while queued/running, close during a pending drain, repeated
  close, exact `after_cancel` cardinality, final closed snapshot, no later scheduling,
  and each executor shutdown exactly once with exact arguments;
- `SH-V-012`: a withdrawn Tk root on Windows for exact menu/navigation/page/widget inventory,
  initial disabled actions and inputs, one-time binding, exact GUI-input snapshots,
  result publication, view switching, About singleton, absence of version text, keyboard
  traversal, system-color ttk use, and scaling 2.0;
- `SH-V-013`: entrypoint success and every construction/main-loop failure stage with fake Tk,
  deterministic exit codes, exact cleanup, no stdout/stderr traceback, and no backend
  or network work;
- `SH-V-014`: recursive traceback inspection of errors, contexts, causes, frames, locals, closures,
  and nested containers for protected objects;
- `SH-V-015`: frozen Phase 5.1B byte integrity and no public API drift;
- `SH-V-016`: scope integrity using the immediate frozen baseline plus the exact Phase 5.1D delta,
  never equality between the complete future worktree and a historical delta.

Tk-dependent assertions skip only when Tk itself is unavailable; controller, resource,
entrypoint-with-fakes, passivity, API, and scope tests never skip. Tests use no live
provider, network, credential, current-user path, database, report, or updater.

### 9.1 Mechanical requirement traceability

The following identifiers are the stable normative owners for every load-bearing clause
in the named scope. A clause in that scope refines its row and cannot create a separate
unverified requirement. Every verification identifier names one material bullet above;
none is a grouped placeholder, and every bullet is consumed at least once.

| Requirement | Exact normative scope | Verification |
| --- | --- | --- |
| `SH-R-001` | Sections 1 and 11: exact roadmap paths, prerequisite, handoff, and no hidden path | `SH-V-001`, `SH-V-015`, `SH-V-016` |
| `SH-R-002` | Sections 2 and 4: repository facts, dependency direction, and passive imports | `SH-V-002` |
| `SH-R-003` | Sections 3 and 6: one root, Tk thread, two executors, queue, and drain ownership | `SH-V-007`, `SH-V-008` |
| `SH-R-004` | Section 5.1: finite enums, snapshots, action inputs, completion, events, and reconstruction | `SH-V-004`, `SH-V-005` |
| `SH-R-005` | Section 5.2: exact finite errors and protected-detail isolation | `SH-V-014` |
| `SH-R-006` | Section 5.3: exact immutable Romanian resources and lookup | `SH-V-003` |
| `SH-R-007` | Section 5.4: controller dependency validation and callable shapes | `SH-V-006` |
| `SH-R-008` | Section 5.4: submission, opaque completion delivery, state transitions, and lane independence | `SH-V-008`, `SH-V-009`, `SH-V-010` |
| `SH-R-009` | Sections 5.4 and 7: close ordering, idempotence, and post-close exclusion | `SH-V-011` |
| `SH-R-010` | Section 5.5: exact widget/menu/layout/resource inventory | `SH-V-012` |
| `SH-R-011` | Section 5.5: one-time action binding, GUI-input capture, and result publication | `SH-V-012` |
| `SH-R-012` | Section 5.6: structural entrypoint order, cardinality, cleanup, and exit codes | `SH-V-013` |
| `SH-R-013` | Sections 7 and 8: public-API closure, object safety, and thread confinement | `SH-V-004`, `SH-V-014` |
| `SH-R-014` | Section 11: V11 5.3D entrypoint/resources-only compatibility and composition exclusion | `SH-V-001`, `SH-V-009`, `SH-V-012`, `SH-V-013` |
| `SH-R-015` | Section 12: nonconforming additions and two-implementer determinism | `SH-V-001`, `SH-V-016` |
| `SH-R-016` | Section 13: exact roadmap identities, verdicts, commits, and tags | `SH-V-016` |

## 10. Verification gates

Phase 5.1D must run:

```text
python -m pytest tests/test_desktop_shell_v1.py -p no:cacheprovider -q
python -m pytest tests/test_desktop_application_v1.py -p no:cacheprovider -q
python -m pytest -p no:cacheprovider -q
ruff check .
black --check .
python -m compileall -q src tests
python -m pip check
git diff --check
```

The repository's separately gated Ollama live test may remain skipped. No live OpenAI or Ollama execution is
permitted. The final diff must contain only the eight authorized production paths and
focused test relative to the frozen 5.1C baseline. Nothing is staged.

## 11. Compatibility and handoff

Phase 5.1C produces exactly
`phase-5.1c-desktop-shell-spec-v1-ready`, the sole prerequisite of Phase 5.1D. Phase
5.1D implements only Section 1's authorized paths and produces exactly
`phase-5.1d-desktop-shell-r1-verified`, the sole prerequisite of Phase 5.2A.

The shell's disabled Scout surface gives Phase 5.2A a presentation target without
defining the Scout adapter, failed-source mapping, or report service. The disabled
Editor surface similarly reserves layout without defining Editor composition. The two
private executor submission methods provide task transport without owning a backend.
The exact `bind_scout_action` and `bind_editor_action` methods are the only facade-action
enabling surfaces available to later composition; `bind_report_action` is the separate
opaque report-opening handoff. Their callers retain backend construction and
request-mapping ownership. This specification neither invents runtime discovery nor
authorizes a hidden import. Phase 5.1D therefore has no hidden path and does not pull
later work forward.

Frozen Productization V11 adds Phase 5.3C/5.3D after 5.3B. Phase 5.3D is authorized to
modify only `src/pastila_scout/desktop_v1/entrypoint.py` and
`src/pastila_scout/desktop_v1/resources.py`. Its entrypoint can therefore call the one
private 5.3B composer before shell construction, retain the returned facade in two local
action/task/completion closures for one shell lifetime, bind those closures through the
two exact view methods, submit synchronous facade work through the existing application
lane, and publish already-safe scalar projections through the exact result methods. A
composition failure occurs before controller, main-window, or executor construction and
uses only the finite Romanian resource added by 5.3D. Phase 5.3D needs no modification to
`controller.py`, `models.py`, or `views.py`; those modules import neither the facade nor
the composer. The entrypoint remains the sole caller and lifetime owner, while the
controller remains only the executor/queue/Tk-marshalling owner.

## 12. Contradiction and two-implementer gates

An implementation is nonconforming if it adds a public export, third-party GUI package,
second root/window/controller, second queue/drain owner, executor outside the controller,
facade composition, backend execution, dynamic adapter discovery, path/config/version
lookup, enabled unavailable action, update behavior, packaging, or an unlisted path.

Two implementers receive no material choice: the framework, module placement, private
symbols, signatures, resources, layout, states, transition rules, executor topology,
queue cadence, close behavior, entry point, exit codes, tests, and exclusions are exact.
The only implementation freedom is local helper naming and mechanically equivalent code
inside the listed modules; helpers remain private and cannot change observable behavior.

## 13. Roadmap identity

| Milestone | Prerequisite | Artifact | Verdict | Commit subject | Output tag |
| --- | --- | --- | --- | --- | --- |
| 5.1C Shell specification | `phase-5.1b-desktop-application-facade-r1-verified` | `docs/windows-application/DesktopShellSpecificationV1.md` | `PHASE_5_1C_DESKTOP_SHELL_SPECIFICATION_V1_READY_FOR_FREEZE` | `Specify Windows desktop shell V1` | `phase-5.1c-desktop-shell-spec-v1-ready` |
| 5.1D Shell implementation | `phase-5.1c-desktop-shell-spec-v1-ready` | frozen roadmap paths in Section 1 | `PHASE_5_1D_DESKTOP_SHELL_REVISION_1_VERIFIED` | `Add verified Windows desktop shell` | `phase-5.1d-desktop-shell-r1-verified` |
| 5.2A Scout GUI specification | `phase-5.1d-desktop-shell-r1-verified` | `docs/windows-application/ScoutDesktopIntegrationSpecificationV1.md` | `PHASE_5_2A_SCOUT_DESKTOP_SPECIFICATION_V1_READY_FOR_FREEZE` | `Specify Scout desktop integration V1` | `phase-5.2a-scout-desktop-spec-v1-ready` |

This proves the frozen dependency chain
`5.1B -> 5.1C -> 5.1D -> 5.2A` without changing any adjacent owner.
