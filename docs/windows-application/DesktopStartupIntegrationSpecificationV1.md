# Desktop Startup Integration Specification V1

Status: **implementation-ready and ready for freeze**. This Phase 5.3C specification
is grounded in frozen Productization V11, the frozen Desktop Shell, the maintained
desktop facade, and verified Phase 5.3B Editor desktop composition.

## 1. Authority, roadmap identity, and exact scope

`STARTUP-001` Phase 5.3C has prerequisite
`phase-5.3b-editor-desktop-r1-verified`, modifies only
`docs/windows-application/DesktopStartupIntegrationSpecificationV1.md`, has no test
path or public API impact, and specifies entrypoint invocation, finite failure
presentation, facade handoff and lifetime, and unchanged Shell executor ownership. Its
verdict is
`PHASE_5_3C_DESKTOP_STARTUP_INTEGRATION_SPECIFICATION_V1_READY_FOR_FREEZE`, commit
subject is `Specify desktop startup integration V1`, and output tag is
`phase-5.3c-desktop-startup-integration-spec-v1-ready`.

`STARTUP-002` Phase 5.3D has prerequisite
`phase-5.3c-desktop-startup-integration-spec-v1-ready`; modifies only
`src/pastila_scout/desktop_v1/entrypoint.py`,
`src/pastila_scout/desktop_v1/resources.py`,
`tests/test_desktop_startup_integration_v1.py`, and
`tests/test_desktop_shell_v1.py`; adds private startup wiring and one finite Romanian
startup-failure resource without a public Python API; and forbids
backend/provider/path/update semantics, packaging, CLI subprocesses, singletons,
service locators, and controller/view/model redesign. Its verdict, commit subject, and
tag are `PHASE_5_3D_DESKTOP_STARTUP_INTEGRATION_REVISION_1_VERIFIED`,
`Add verified desktop startup integration`, and
`phase-5.3d-desktop-startup-integration-r1-verified`.

`STARTUP-003` The immediate consumer is Phase 5.4A Windows state specification. Its
prerequisite is `phase-5.3d-desktop-startup-integration-r1-verified`, its sole path is
`docs/windows-application/WindowsStateSpecificationV1.md`, its API impact is private
path/settings/migration specification, and packaging/updater work is forbidden. Its
verdict, commit subject, and tag are
`PHASE_5_4A_WINDOWS_STATE_SPECIFICATION_V1_READY_FOR_FREEZE`,
`Specify Windows application state V1`, and
`phase-5.4a-windows-state-spec-v1-ready`. Phase 5.3D retains the current project-relative
paths and does not implement Windows state.

## 2. Existing Shell and composition authorities

`STARTUP-004` `pastila_scout.desktop_v1.entrypoint.main() -> int` remains the sole GUI
process entrypoint. It owns DPI best effort, one `tkinter.Tk` root, callback cells,
structural construction, startup visibility gating, the close protocol, one `mainloop`,
final controller close, root destruction, and exit codes. Import remains passive. A normal close returns `0`;
every startup or Tk failure returns `1` without stdout, stderr, or protected logging.

`STARTUP-005` `_DesktopTaskControllerV1` remains unchanged and solely owns exactly one
application executor, one update executor, one queue, the 50 ms Tk-thread drain, lane
state, result delivery, and idempotent shutdown. `submit_application(*, task,
on_completed)` remains the only Scout and Editor transport. Startup creates no executor,
thread, queue, future, cancellation mechanism, or second drain.

`STARTUP-006` `_DesktopMainWindowV1` and the GUI-local action snapshots remain
unchanged. The one-time bindings are exactly `bind_scout_action(*, callback)`,
`bind_editor_action(*, callback)`, and `bind_report_action(*, callback)`. Scout supplies
one `_DesktopScoutActionInputV1(period, category)`; Editor supplies one
`_DesktopEditorActionInputV1` containing its eight exact strings plus `no_replace`;
report supplies only `reference: str`. Result presentation remains
`publish_scout_result(...)` and `publish_editor_result(*, status: str)` on the Tk thread.

`STARTUP-007` The verified private boundary is
`pastila_scout.desktop_editor_v1.composition._compose_desktop_application_facade_v1()
-> DesktopApplicationFacadeV1`. Each explicit call returns one fresh facade and performs
no operation. Its sole expected failure is
`_DesktopApplicationCompositionErrorV1("Desktop application composition failed.")`
from no cause. Phase 5.3D imports and consumes these private symbols but does not change
or redefine them.

`STARTUP-008` The retained facade operations remain exactly
`run_scout(*, request: ScoutDesktopRequestV1, progress_sink:
DesktopProgressSinkV1) -> ScoutDesktopResultV1`,
`run_editor(*, request: EditorDesktopRequestV1, progress_sink:
DesktopProgressSinkV1) -> EditorDesktopResultV1`, and
`open_report(*, reference: str) -> None`. Startup neither traverses facade private state
nor wraps or substitutes its operation identities.

## 3. Deterministic startup sequence and lifetime

`STARTUP-009` One explicit `pastila-scout-gui` invocation performs exactly this order:

1. perform the existing Windows DPI best effort;
2. create one Tk root and apply the existing scaling call;
3. call `root.withdraw()` exactly once so no partial startup state can become visible;
4. call `_compose_desktop_application_facade_v1()` exactly once;
5. create the existing callback cells and close guard, retaining the facade in the
   closure cells for the Shell lifetime;
6. construct one controller, thereby constructing its existing two executors;
7. construct one main window;
8. populate the controller, view, and facade cells;
9. bind Scout, then Editor, then report, all to closures over that same facade;
10. register the existing close protocol;
11. call `controller.start()` exactly once;
12. call `root.deiconify()` exactly once;
13. enter `root.mainloop()` exactly once;
14. execute the existing `finally` cleanup.

No bound operation is invoked during these steps. Composition never occurs on import,
inside a binding, on first button activation, per operation, or during shutdown.

The startup lifecycle state machine is exact:

| State | Owner | Sole successful transition |
| --- | --- | --- |
| before root | entrypoint | DPI best effort then root construction |
| root created | entrypoint | scaling then withdrawal |
| scaling established and root hidden | entrypoint | one facade composition |
| facade composed | entrypoint | callback-cell and controller construction |
| controller/view constructed | entrypoint and frozen Shell constructors | install Scout binding |
| Scout binding only | entrypoint through view | install Editor binding |
| Scout and Editor bindings | entrypoint through view | install report binding |
| all bindings installed | entrypoint | register close protocol and start controller |
| controller started | entrypoint | deiconify root |
| root visible | entrypoint | enter mainloop |
| mainloop entered | Tk and frozen Shell | guarded close or loop completion |
| closing | controller and entrypoint | idempotent controller shutdown and root destruction |
| closed | entrypoint | return `0` after normal completion |
| startup failed | entrypoint | safe presentation where legal, cleanup, return `1` |

Every failed transition goes directly to `startup failed`; no transition returns to an
earlier state and no second composition or binding attempt occurs.

`STARTUP-010` The local cells hold the exact composed facade strongly until `main`
leaves its `try/finally`. A startup that fails before or during composition retains zero
facades. Every startup that completes composition invokes the composer exactly once and
retains exactly its one returned facade through all later success or failure states.
There is no retry, fallback, singleton, module global, registry, service locator, weak
reference, replacement, copy, second composition after binding failure, or invented
facade shutdown. All three bindings close over the same retained identity.

## 4. Private startup helpers and progress sink

`STARTUP-011` Phase 5.3D defines startup-only private helpers in `entrypoint.py`; none
is exported. The exact minimum responsibilities are request construction, safe scalar
result projection, and the callbacks passed to the three existing binding surfaces.
They do not form a new package, adapter module, public API, or composition root.

`STARTUP-012` `entrypoint.py` defines one private, final, stateless
`_DesktopStartupProgressSinkV1` with exact method
`publish(*, event: DesktopProgressEventV1) -> None`. It validates by reconstructing the
exact event and then discards it. Facade progress generation remains authoritative; the
sink performs no widget access, queue publication, logging, retention, callback,
threading, I/O, or result inference. One sink is constructed inside each Scout or Editor
worker task and never shared across operations.

The sink is mandatory because both maintained facade execution methods reject a missing
or structurally invalid sink. Discarding reconstructed events is legal because the
facade contract requires synchronous receipt, not persistence or presentation; the
frozen Shell exposes no progress-event publication method; forwarding from the worker
would require a forbidden view/controller change or a second queue; and the existing
application-lane snapshots plus terminal result publication provide the authorized
visible lifecycle. Tests require every accepted/running/terminal event to reach the sink
exactly once, require reconstruction to succeed, and prove zero retained event and zero
widget, queue, executor, callback, or logging effect.

## 5. Scout request, execution, and result binding

`STARTUP-013` The Scout callback first reconstructs the exact
`_DesktopScoutActionInputV1` on the Tk thread. It accepts `period` only when base-10
`int(period)` round-trips exactly through `str()` and is one of `1, 3, 7, 14, 30`;
leading/trailing whitespace, signs, leading zeroes, decimal notation, and subclasses
are rejected. It accepts `category` only as one exact serialized
`ScoutDesktopCategoryV1` value: `Politica`, `Social`, `Conspiratii`, `Economie`,
`CanCan`, `Externe`, `Diverse`, or `all`. Before submission it constructs one
`ScoutDesktopRequestV1` with those exact values and operation reference
`scout-desktop-v1:` followed by one fresh lowercase 32-hex UUID4 value.

`STARTUP-014` After successful construction, the callback calls
`controller.submit_application` exactly once. Its zero-argument worker closure calls
`facade.run_scout(request=request, progress_sink=_DesktopStartupProgressSinkV1())`
exactly once. Its one-keyword-only-argument completion closure requires an exact
reconstructed `ScoutDesktopResultV1` and calls `view.publish_scout_result` once with:

- `summary`: `Surse: {sources_checked}; reușite: {sources_succeeded}; nereușite:
  {sources_failed}; articole: {articles_found}; noi: {articles_inserted}; duplicate:
  {duplicates_skipped}.`;
- `failed_sources`: the unchanged exact `failed_source_ids` tuple;
- `footer`: the unchanged exact serialized `result.status.value`;
- `report_reference`: `None` or the unchanged opaque nested reference string.

The completion executes only through the controller drain on the Tk thread. Startup
does not call `poll_once`, generate HTML, access the report catalog, reinterpret
counters, or synthesize success.

`STARTUP-015` A malformed Scout snapshot or request raises only a safe existing
configuration error before submission; the view converts the callback failure to its
existing `error.internal` presentation. A worker/facade failure is discarded by the
controller's existing worker boundary and produces its existing failed lane state. No
raw input, reference, path, exception, traceback, or lower detail crosses the queue.

## 6. Editor request, execution, and result binding

`STARTUP-016` The Editor callback reconstructs the exact
`_DesktopEditorActionInputV1` on the Tk thread and rejects an empty, non-NFC,
non-stripped, NUL/control/surrogate-bearing path, provider, model, or timeout string. It
requires `no_replace is True`, parses timeout as a finite positive exact `float`, and
creates one lowercase UUID4 reference prefixed `editor-desktop-v1:`. It captures only
these safe copied scalars in one zero-argument worker closure and submits that closure
once through `controller.submit_application`. A relative output path is converted
lexically to `Path.cwd() / path`; an absolute output path is retained. No call to
`resolve`, filesystem probe, or file load occurs on the Tk thread.

`STARTUP-017` Inside the application worker, and nowhere on import or during
composition, the closure performs this exact provider-neutral request construction:

1. convert the four input strings and the already-absolute output value to the platform
   concrete `Path`;
2. load the Scout input through `load_contract`, require exact `ScoutEditorInputV1`,
   strict-copy it, and verify its maintained identity;
3. load selection profile through `EditorSelectionProfileAuthorityV1`;
4. load episode context through `EditorEpisodeContextAuthorityV1`;
5. load generation configuration through
   `EditorApplicationGenerationConfigurationAuthorityV1`;
6. require its provider serialized value, model identifier, and exact float timeout to
   equal the three GUI scalars;
7. construct `EditorOutputDestinationV1` from the absolute output path and exact
   `EditorOverwritePolicyV1.FAIL_IF_EXISTS`;
8. capture one `datetime.now(UTC)` and one fresh
   `CancellationTokenV2(cancellation_requested=False)`;
9. construct one `EditorApplicationRequestV1` with those exact values and captured
   operation reference;
10. wrap it once in `EditorDesktopRequestV1`;
11. call `facade.run_editor(request=request,
   progress_sink=_DesktopStartupProgressSinkV1())` exactly once.

The entrypoint imports no provider implementation, client, runtime composer, selector,
CLI command/composition module, argparse, shell, or subprocess. It does not reconstruct
provider execution or cancellation ownership.

`STARTUP-018` The Editor completion closure requires an exact reconstructed
`EditorDesktopResultV1`, reads only its authoritative application status, and calls
`view.publish_editor_result` once with the unchanged exact serialized application
`status.value` (`completed`, `cancelled`, or `failed`). It does not expose output paths,
payloads, checksums,
provider responses, failure messages, prompts, lineage, or exceptions. Completion runs
only on the Tk thread through the existing queue drain.

`STARTUP-019` Editor scalar or request-construction failure produces no facade call.
Pre-submission scalar failure uses the existing `error.internal` view presentation.
Worker loading, validation, facade, serialization, export, and execution failures are
discarded by the controller worker boundary and produce only its existing failed lane
state. There is no retry, fallback, CLI delegation, second request, or alternate
provider.

## 7. Report binding

`STARTUP-020` The report binding is the thinnest exact adapter:
`def open_report(*, reference: str) -> None: facade.open_report(reference=reference)`.
It passes the opaque exact string once and performs no parsing, path conversion,
catalog lookup, opener call, retry, fallback, task submission, or private-state
traversal. The view already catches an ordinary callback failure and presents
`error.internal`. This direct binding preserves the frozen 5.3A report identity and
does not create another executor owner.

## 8. Failure, mainloop, and shutdown

`STARTUP-021` `resources.py` adds exactly one finite immutable Romanian resource:

| Key | Exact text |
| --- | --- |
| `startup.error` | `Aplicația nu a putut fi configurată.` |

No resource includes an exception, path, provider, configuration, credential, prompt,
traceback, or variable interpolation.

`STARTUP-022` `tkinter.messagebox` is imported passively as `messagebox`. If the
composer raises exact `_DesktopApplicationCompositionErrorV1`, `main` calls
`messagebox.showerror(title=_text_v1(key="app.title"),
message=_text_v1(key="startup.error"), parent=root)` at most once, discards any
presentation failure, skips controller and view construction, skips all bindings and
`mainloop`, destroys the root in `finally`, and returns `1`. It does not retry, fall
back, log, print, or return a partial Shell. Process-control or unexpected composition
exceptions reach the existing outer safe boundary and receive the same cleanup and
exit code without raw presentation.

`STARTUP-023` Any controller, view, cell, binding, protocol, or `controller.start()`
failure is a binding/startup failure. The root remains withdrawn, so zero, one, two, or
three installed bindings never become an operational partial application. If the root
exists, `main` attempts the same finite startup-error presentation once unless it was
already attempted, then the existing `finally` attempts `controller.close()` when a
controller exists and attempts `root.destroy()` once. It never enters `mainloop`, never
invokes an operation, and returns `1`. Root construction failure has no usable parent,
performs no presentation or `mainloop`, and returns `1`.

`STARTUP-024` `mainloop` begins only when the exact predicate is true: the root exists,
scaling and withdrawal succeeded, one exact facade is retained, controller and view
exist, all three bindings succeeded over that facade, the close protocol is registered,
controller start succeeded, and root deiconification succeeded. Normal loop completion
returns `0`. The guarded close callback attempts controller close and root quit once;
the `finally` block can call close again, but controller idempotence permits only one
effective executor shutdown. Root destruction is attempted only by `finally` and only
once. A controller-start failure can call close internally and again from `finally`,
with the same one-effective-shutdown invariant. The facade receives no close, cancel,
or shutdown call.

The failure atomicity matrix is exact (`C` means constructed, `—` means absent):

| Failure point | Root | Controller/view | Presentation | Cleanup | Exit | Mainloop | Retry |
| --- | --- | --- | --- | --- | --- | --- | --- |
| DPI best effort | — | — | none; failure discarded | none | continue startup | no | none |
| root construction | — | — | none | none | `1` | no | none |
| scaling | C, not withdrawn | — | none | destroy root once | `1` | no | none |
| withdrawal | C | — | none | destroy root once | `1` | no | none |
| composition | C, withdrawn | — | one startup message | destroy root once | `1` | no | none |
| controller construction | C, withdrawn | — | one startup message | destroy root once | `1` | no | none |
| view construction | C, withdrawn | controller C/view partial | one startup message | close controller; destroy root once | `1` | no | none |
| Scout binding | C, withdrawn | both C/zero bindings | one startup message | close controller; destroy root once | `1` | no | none |
| Editor binding | C, withdrawn | both C/Scout bound | one startup message | close controller; destroy root once | `1` | no | none |
| report binding | C, withdrawn | both C/Scout+Editor bound | one startup message | close controller; destroy root once | `1` | no | none |
| controller start | C, withdrawn | both C/all bound | one startup message | idempotent close; destroy root once | `1` | no | none |
| deiconification | C, withdrawn | both C/all bound, started | one startup message | close controller; destroy root once | `1` | no | none |
| mainloop call raises | C, visible | both C/all bound, started | none; existing outer boundary | close controller; destroy root once | `1` | call entered | none |

Presentation is attempted only while a live root exists and before destruction. No
callback touches a widget after destruction. No startup exception is re-raised across
the process entrypoint. Neither the resource, message box, return value, stdout, stderr,
nor logging receives an exception, cause, context, traceback, path, provider,
configuration, credential, prompt, or protected local. The existing
outer `BaseException` boundary continues to collapse `KeyboardInterrupt`, `SystemExit`,
and `GeneratorExit` at `main` to exit `1`; lower composer/facade process-control
propagation remains unchanged.

## 9. Ownership, passivity, and path sufficiency

`STARTUP-025` Imports remain passive: no facade composition, Tk/root/widget creation,
executor/thread/queue construction, timer, environment/configuration/credential/path
access, database/network/provider operation, request construction, report generation,
report opening, logging configuration, or process exit occurs before explicit `main`.

`STARTUP-026` The 5.3D production paths are sufficient and indivisible.
`entrypoint.py` owns the one composer call, local facade lifetime, provider-neutral
request mapping, progress sink, three binding closures, safe projection, ordering,
mainloop, and cleanup. `resources.py` owns only the single finite startup text specified
above. `controller.py`, `views.py`, `models.py`, `errors.py`, Shell exports,
5.3B composition, facade, Scout/report, Editor lower layers, CLI, provider/runtime,
Productization, and every specification remain byte-identical. Hidden production and
test paths equal zero. Existing output silence, logging non-ownership, labels, focus,
keyboard activation, disabled-state signaling, and other Shell accessibility behavior
remain unchanged.

`STARTUP-027` Phase 5.3D tests are only
`tests/test_desktop_startup_integration_v1.py` and the necessary additive assertions in
`tests/test_desktop_shell_v1.py`. They use offline fakes, no live provider/network/DB,
and derive historical scope from the immutable 5.3C prerequisite tree plus the exact
5.3D delta. They never require a later worktree to equal the historical delta.
Maintainable dependencies are pinned at their applicable historical commits and current
frozen authorities are checked separately.

`STARTUP-028` Phase 5.3B's five files and their behavior remain unchanged. Any need to
change the composer, facade, Shell controller/view/models, backend semantics, or an
unlisted path is a Major external blocker. Phase 5.3D's output mechanically satisfies
Phase 5.4A's prerequisite while retaining current project-relative paths for the later
Windows-state authority.

## 10. Phase 5.3D verification matrix

Each row is one material verification and maps to exactly one requirement.

| Verification | Requirement | Material assertion |
| --- | --- | --- |
| `STARTUP-V001` | `STARTUP-001` | Frozen roadmap extraction proves exact 5.3C identity and sole specification path. |
| `STARTUP-V002` | `STARTUP-002` | Frozen roadmap extraction proves exact four-path 5.3D scope, ownership, verdict, commit, and tag. |
| `STARTUP-V003` | `STARTUP-003` | Frozen roadmap extraction proves exact Phase 5.4A consumer and prerequisite. |
| `STARTUP-V004` | `STARTUP-004` | Signature and failure fakes prove entrypoint ownership, exit codes, output silence, and cleanup. |
| `STARTUP-V005` | `STARTUP-005` | Executor fakes prove exactly two unchanged controller-owned lanes, queue/drain delivery, and shutdown. |
| `STARTUP-V006` | `STARTUP-006` | Exact snapshot, binding, and publication signatures prove unchanged Shell surfaces. |
| `STARTUP-V007` | `STARTUP-007` | Patched composer proves one exact private call and unchanged fixed failure. |
| `STARTUP-V008` | `STARTUP-008` | Facade fakes prove exact three-operation signatures and no private traversal. |
| `STARTUP-V009` | `STARTUP-009` | Ordered state/event ledger proves withdrawal, one composition, three bindings, start, deiconification, mainloop, and every single-owner transition. |
| `STARTUP-V010` | `STARTUP-010` | Every failure-stage probe proves zero facade before composition, exactly one retained identity afterward, and no retry or second call. |
| `STARTUP-V011` | `STARTUP-011` | AST and scope checks prove private helpers remain only in entrypoint. |
| `STARTUP-V012` | `STARTUP-012` | Sink tests prove mandatory facade compatibility, exact event cardinality/reconstruction, non-retention, and zero UI/queue side effect. |
| `STARTUP-V013` | `STARTUP-013` | Complete period/category boundary matrix and UUID probe prove exact Scout request construction. |
| `STARTUP-V014` | `STARTUP-014` | Executor and facade fakes prove one Scout call and exact safe Tk-thread result projection. |
| `STARTUP-V015` | `STARTUP-015` | Invalid snapshot/request and worker failures prove no lower call or protected leakage. |
| `STARTUP-V016` | `STARTUP-016` | Scalar grammar, timeout, no-replace, UUID, and submission tests prove Editor preflight. |
| `STARTUP-V017` | `STARTUP-017` | Authority fakes prove exact load/construction order, field identity, cancellation, and one facade call. |
| `STARTUP-V018` | `STARTUP-018` | Completed/cancelled/failed results prove exact serialized Tk-thread status projection only. |
| `STARTUP-V019` | `STARTUP-019` | Every construction/execution failure stage proves zero retry, fallback, and leakage. |
| `STARTUP-V020` | `STARTUP-020` | Opaque-reference fake proves one direct same-facade report call and no catalog/path logic. |
| `STARTUP-V021` | `STARTUP-021` | Resource equality and uniqueness checks prove the one exact finite Romanian startup text. |
| `STARTUP-V022` | `STARTUP-022` | Withdrawn-root composition-failure fake proves one safe presentation, no Shell/mainloop, cleanup, and exit `1`. |
| `STARTUP-V023` | `STARTUP-023` | Zero/partial/all-binding failure fakes prove the window stays hidden, no operation/mainloop occurs, and cleanup is exact. |
| `STARTUP-V024` | `STARTUP-024` | Every failure-matrix row plus normal close proves the exact mainloop predicate, root-destroy cardinality, and one effective executor shutdown. |
| `STARTUP-V025` | `STARTUP-025` | Fresh-process import traps prove complete passivity and output silence. |
| `STARTUP-V026` | `STARTUP-026` | AST/import and Git scope audits prove two load-bearing production paths and zero forbidden change. |
| `STARTUP-V027` | `STARTUP-027` | Immutable-baseline delta and current-authority checks prove exact maintainable historical scope. |
| `STARTUP-V028` | `STARTUP-028` | Frozen hashes and structural Phase 5.4A harness prove 5.3B non-regression and future compatibility. |

## 11. Readiness and ambiguity closure

There are 28 unique requirements, `STARTUP-001` through `STARTUP-028`, and 28 unique
material verifications, `STARTUP-V001` through `STARTUP-V028`. There are no missing,
orphan, duplicate, placeholder, grouped pseudo-test, or hidden-path obligations.

Two independent implementers derive the same root-before-composition ordering, one
composer call before controller/view/executors, one facade lifetime, Scout/Editor/report
binding order, request mapping, application-executor use, progress disposal, Tk-thread
publication, finite failures, mainloop gate, exit codes, cleanup, and tests. No
load-bearing choice remains.

The prescribed load-bearing ambiguity scan returns zero matches. The exact Phase 5.3D
path set is sufficient, Phase 5.3B requires zero change, and no Critical, Major, or
blocking Minor remains.
