# Editor Desktop Integration Specification V1

Status: **implementation-ready and ready for freeze**. This Phase 5.3A specification is
grounded in frozen Productization V11, the report-opener-maintained desktop facade, the
verified Editor application/runtime, verified Scout Phase 5.2B, and the frozen Desktop
Shell.

## 1. Authority, roadmap identity, and scope

`EDITOR-001` Phase 5.3B implements only
`src/pastila_scout/desktop_editor_v1/{__init__.py,models.py,service.py,composition.py}`
and `tests/test_desktop_editor_v1.py`. Its prerequisite is
`phase-5.3a-editor-desktop-spec-v1-ready`; verdict is
`PHASE_5_3B_EDITOR_DESKTOP_REVISION_1_VERIFIED`; commit subject is
`Add verified Editor desktop integration`; output tag is
`phase-5.3b-editor-desktop-r1-verified`. It adds one private Editor adapter and the sole
private production `DesktopApplicationFacadeV1` composer. It owns no Tk, executor,
Scout behavior, update, provider change, CLI subprocess, or global state.

`EDITOR-002` Phase 5.3A's sole path is
`docs/windows-application/EditorDesktopIntegrationSpecificationV1.md`, its prerequisite
is `phase-5.2b-scout-desktop-r1-verified`, and its output identity is
`PHASE_5_3A_EDITOR_DESKTOP_SPECIFICATION_V1_READY_FOR_FREEZE`, commit subject
`Specify Editor desktop integration V1`, and tag
`phase-5.3a-editor-desktop-spec-v1-ready`. Neither 5.3A nor 5.3B changes a public API.

`EDITOR-003` Phase 5.3C specifies startup integration at
`docs/windows-application/DesktopStartupIntegrationSpecificationV1.md` after
`phase-5.3b-editor-desktop-r1-verified`; its verdict/tag are
`PHASE_5_3C_DESKTOP_STARTUP_INTEGRATION_SPECIFICATION_V1_READY_FOR_FREEZE` and
`phase-5.3c-desktop-startup-integration-spec-v1-ready`. Phase 5.3D then modifies only
`desktop_v1/{entrypoint.py,resources.py}` and
`tests/{test_desktop_startup_integration_v1.py,test_desktop_shell_v1.py}`, with verdict
`PHASE_5_3D_DESKTOP_STARTUP_INTEGRATION_REVISION_1_VERIFIED` and tag
`phase-5.3d-desktop-startup-integration-r1-verified`. It cannot redefine composition,
backend/provider/path/update semantics, packaging, CLI subprocesses, singletons,
service locators, or Shell controller/view/model behavior.

## 2. Existing authorities

`EDITOR-004` `EditorApplicationCoordinatorV1.execute(*, request:
EditorApplicationRequestV1) -> EditorApplicationResultV1` is the sole Editor application
execution authority. Its immutable request already owns the exact Scout input,
selection profile, episode context, generation configuration, output destination,
timezone-aware request time, operation reference, and immutable `CancellationTokenV2`.
Its immutable result owns status, lifecycle, operational result, output path, payload
checksum, export/handoff flags, failure, and exit code. Phase 5.3B does not reinterpret,
serialize, export, or duplicate any of those contracts.

`EDITOR-005` The private, passive, fresh-per-call
`_compose_editor_application_runtime_v1() -> EditorApplicationCoordinatorV1` remains the
singular provider/runtime composition authority. Desktop code calls it once per desktop
facade composition and contains no OpenAI, Ollama, selector, credential, client,
provider branch, model routing, or runtime-session construction.

`EDITOR-006` `editor_cli_run_v1` remains a thin console adapter. Desktop code neither
imports its command/composition modules nor invokes `pastila-scout`, argparse, a shell,
or a subprocess. CLI request-building and terminal projection confer no desktop
composition authority.

`EDITOR-007` The maintained `DesktopApplicationFacadeV1` remains synchronous,
GUI-neutral, injected, and not a composition root. Its exact constructor dependencies
are `scout_operation: ScoutDesktopOperationV1`, `editor_operation:
EditorDesktopOperationV1`, and `report_operation: DesktopReportOperationV1`. Its exact
operations are `run_scout`, `run_editor`, and `open_report(*, reference: str) -> None`.
The first two own progress publication and safe selected-operation delegation;
`open_report` reconstructs the opaque scalar and delegates exactly once. Phase 5.3B
implements the private Editor dependency and constructs the facade without changing
the maintained package. Verified `_ScoutDesktopOperationV1` remains the sole Scout
behavior authority, while `_DesktopReportFacadeV1` remains the sole catalog resolver
and opener invoker.

## 3. Private Editor desktop operation

`EDITOR-008` `desktop_editor_v1.service` defines exactly this final, passive operation:

```python
class _EditorDesktopOperationV1:
    def __init__(
        self,
        *,
        application: EditorApplicationCoordinatorV1,
    ) -> None: ...

    def run_editor(
        self,
        *,
        request: EditorDesktopRequestV1,
    ) -> EditorDesktopResultV1: ...
```

The constructor requires an exact `EditorApplicationCoordinatorV1`, validates before
storage, records its identity without equality or repr, and performs no execution or
I/O. The class rejects subclasses and retained-state substitution. The package
`__init__.py` has `__all__: tuple[str, ...] = ()` and exports nothing.

`EDITOR-009` `run_editor` first reconstructs the exact maintained
`EditorDesktopRequestV1`, obtains its already-reconstructed nested
`EditorApplicationRequestV1`, revalidates the stored coordinator identity, and calls
`application.execute(request=nested_request)` exactly once. It supplies no second
provider, model, timeout, cancellation, prompt, lineage, export, path, or option value.
It performs no retry, fallback, duplicate generation, CLI execution, or cancellation
polling.

`EDITOR-010` The returned value must be an exact reconstructible
`EditorApplicationResultV1` with the same operation reference as the nested request.
The operation returns exactly `EditorDesktopResultV1(application_result=result)`.
`COMPLETED`, `CANCELLED`, and every valid failed result retain the lower status,
lifecycle, exit code, failure, output, checksum, export flag, handoff flag, and lineage
unchanged. No desktop status reclassification or fabricated result is permitted.

`EDITOR-011` An already-requested immutable `CancellationTokenV2` reaches the Editor
application unchanged and the application owns its existing before-execution cancelled
result. Once execution begins, the same immutable snapshot remains authoritative; the
adapter creates no mutable token, cancellation thread, future cancellation, callback,
or polling loop. Shell cancellation remains lane presentation until a later bounded
authority explicitly connects a backend cancellation contract.

`EDITOR-012` Invalid constructor/request/returned-value state raises the maintained
fixed `DesktopApplicationConfigurationError` before a further lower effect. An ordinary
exception escaping the one Editor execution is reduced outside the active `except`
suite to `DesktopApplicationExecutionError` from no cause. `KeyboardInterrupt`,
`SystemExit`, and `GeneratorExit` propagate unchanged. No outward exception, traceback
local, repr, log, stdout, or stderr retains or discloses a request, result, coordinator,
provider body, credential, prompt, path, runtime object, raw exception, cause, or
context.

## 4. Sole private desktop facade composer

`EDITOR-013` `desktop_editor_v1.models` defines only final private
`_DesktopApplicationCompositionErrorV1(RuntimeError)`. It has `__slots__ = ()`, rejects
subclasses, copy, deepcopy, and pickle, and its sole exact message is
`Desktop application composition failed.` Its repr contains only its private type and
fixed message. Phase 5.3C consumes this error and does not redefine it.

`EDITOR-014` `desktop_editor_v1.composition` defines the sole production boundary:

```python
def _compose_desktop_application_facade_v1() -> DesktopApplicationFacadeV1: ...
```

It is private and absent from every `__all__`. Import is passive. Each explicit call
returns one fresh facade; there is no module cache, singleton, registry, service locator,
lazy first-button construction, or per-operation reconstruction.

`EDITOR-015` One call constructs dependencies exactly once in this order:

1. `_DesktopReportFacadeV1(report_directory=Path("reports"), opener=_open_desktop_report_v1)`;
2. `_ScoutDesktopOperationV1(config_path=Path("config/config.yaml"),
   database_path=Path("data/news_monitor.db"), report_facade=report_facade)`;
3. `_compose_editor_application_runtime_v1()`;
4. `_EditorDesktopOperationV1(application=editor_application)`;
5. `DesktopApplicationFacadeV1(scout_operation=scout_operation,
   editor_operation=editor_operation, report_operation=report_facade)`.

These project-relative values are the current Productization-recorded mutable defaults,
not Windows installed-state semantics. The later Windows-state milestone remains their
only replacement authority. Construction evaluates no path, creates no directory, and
performs no configuration, database, report, provider, or network operation.

`EDITOR-016` `_open_desktop_report_v1(path: Path) -> None` is a private stored callback,
requires the platform's exact concrete `Path` type, and invokes Windows `os.startfile`
exactly once only when the verified report facade explicitly opens a catalog-resolved
path. It is never called by composition. It performs no path parsing, lookup, fallback,
subprocess, shell command, or retry; the verified report facade owns safe opening-error
reduction.

`EDITOR-017` The composer passes the exact constructed Scout and Editor operation
identities directly to one `DesktopApplicationFacadeV1`. It adds no wrapper and invokes
no `run_scout`, `run_editor`, `poll_once`, report generation/opening, provider execution,
Tk constructor, controller, queue, thread, executor, event loop, socket, database, or
update behavior.

`EDITOR-018` Any ordinary dependency or facade construction exception becomes one fresh
`_DesktopApplicationCompositionErrorV1` raised outside the active `except` suite from
no cause, after partial local references are discarded. Process-control exceptions
propagate. There is no retry, fallback, partial facade return, raw detail, credential,
provider/config/path disclosure, retained cause/context, or logging. Static validation
does not execute descriptors, `__getattr__`, custom `__getattribute__`, equality, or repr.

## 5. Ownership, imports, and lifecycle

`EDITOR-019` The acyclic dependency direction is
`desktop_v1.entrypoint` -> `desktop_editor_v1.composition` -> private Editor/Scout
operations -> maintained facade and lower Editor/Scout authorities. Lower Editor,
Scout, facade, CLI, provider, Shell controller/models/views, and update packages do not
import `desktop_editor_v1`. The 5.3B modules import no Tk, Shell view/controller/resource,
executor, CLI, argparse, subprocess, updater, SQLite, or provider-specific module.

`EDITOR-020` Phase 5.3D can use only its frozen paths without a 5.3B or Shell redesign.
At explicit startup `entrypoint.py` calls the composer once before constructing Tk, the
controller, or executors and retains the returned facade for the Shell lifetime. It
binds closures over `facade.run_scout` and `facade.run_editor` to the existing primary
surfaces and binds `facade.open_report` directly to the existing exact report surface.
Both synchronous execution closures submit through `submit_application`; completion
handlers publish only safe scalar result projections on the Tk thread. The report
binding passes only the opaque reference and reaches the same `_DesktopReportFacadeV1`
identity injected into Scout and the facade; no private-state traversal, path exposure,
second catalog, or duplicate opener exists. Phase 5.3C owns the later deterministic
translation of GUI-local scalar inputs into maintained facade requests and the finite
Romanian startup-failure presentation inside `entrypoint.py`/`resources.py`.
Composition failure creates no Shell object and terminates without retry or raw
disclosure.

`EDITOR-021` The 5.3B path set is sufficient and indivisible: `__init__.py` owns empty
exports; `models.py` owns only the private composition error; `service.py` owns only the
Editor operation and safe execution boundary; `composition.py` owns the report opener,
exact dependency construction, and sole facade composer; the one focused test owns all
5.3B verification. Hidden production and test paths equal zero.

## 6. Verification matrix

Each row is one material verification; no row is a grouped placeholder.

| Verification | Requirement | Material assertion |
| --- | --- | --- |
| `EDITOR-V001` | `EDITOR-001` | Historical prerequisite tree plus exact four-module/one-test delta rejects every hidden 5.3B path. |
| `EDITOR-V002` | `EDITOR-002` | Frozen roadmap extraction proves the exact 5.3A identity and private API impact. |
| `EDITOR-V003` | `EDITOR-003` | Frozen 5.3C/5.3D rows and AST prove entrypoint/resources-only startup integration without composition redefinition. |
| `EDITOR-V004` | `EDITOR-004` | Completed, cancelled, and each failed application result reconstruct with every field unchanged. |
| `EDITOR-V005` | `EDITOR-005` | Patched authority records exactly one runtime-composer call and denies provider constructors in desktop modules. |
| `EDITOR-V006` | `EDITOR-006` | AST/import traps deny CLI, argparse, shell, and subprocess imports or calls. |
| `EDITOR-V007` | `EDITOR-007` | Maintained facade signatures prove exact Scout, Editor, and report injection plus safe three-operation delegation. |
| `EDITOR-V008` | `EDITOR-008` | Exact signatures, finality, empty exports, passive construction, identity sealing, and substitution attacks are checked. |
| `EDITOR-V009` | `EDITOR-009` | One nested request produces one identity-exact execute call and zero retry/fallback/extra arguments. |
| `EDITOR-V010` | `EDITOR-010` | Full result matrix proves direct nested projection and rejects wrong reference, subclass, and copied-invalid results. |
| `EDITOR-V011` | `EDITOR-011` | Already-cancelled and non-cancelled tokens remain exact; denied mutable/future/thread probes prove no second owner. |
| `EDITOR-V012` | `EDITOR-012` | Constructor/request/lower/return defects, process-control propagation, and recursive traceback-local isolation are asserted. |
| `EDITOR-V013` | `EDITOR-013` | Exact error type/message, finality, repr, copy/deepcopy, pickle, and subclass behavior are checked. |
| `EDITOR-V014` | `EDITOR-014` | Passive import plus two calls prove explicit-only construction and distinct facade/dependency identities. |
| `EDITOR-V015` | `EDITOR-015` | Constructor fakes prove exact order, cardinality, arguments, defaults, same report identity injected into Scout/facade, and zero path/I/O evaluation. |
| `EDITOR-V016` | `EDITOR-016` | Exact path/open signature, one `os.startfile` call, invalid path, and opener exception behavior are checked offline. |
| `EDITOR-V017` | `EDITOR-017` | Identity assertions and denied operation/Tk/executor/network/DB probes prove composition-only behavior. |
| `EDITOR-V018` | `EDITOR-018` | Every construction stage failure and process-control case proves one safe error, no partial return, retry, cause, context, or leaked local. |
| `EDITOR-V019` | `EDITOR-019` | AST import graph proves the exact acyclic direction and all forbidden imports absent. |
| `EDITOR-V020` | `EDITOR-020` | Structural startup harness proves one composer call, retained facade, three bindings including `facade.open_report`, application-lane submission, and Tk-thread publication using only 5.3D paths. |
| `EDITOR-V021` | `EDITOR-021` | Responsibility and phase-local historical audits prove every authorized path load-bearing and no hidden path. |

## 7. Integrity and freeze assessment

`EDITOR-022` The focused test uses offline fakes only and checks immutable prerequisite
baseline plus exact phase delta, not equality with a future complete worktree. It pins
historically maintained dependency bytes at the relevant commit and separately checks
current frozen Productization, facade, Shell, Scout, Editor, Protocol, and Persistence
authorities. Future unrelated paths remain generically permitted while unauthorized
expansion inside `desktop_editor_v1` is rejected.

The requirement set is `EDITOR-001` through `EDITOR-022`; the verification set is
`EDITOR-V001` through `EDITOR-V022`. There are 22 unique requirements and 22 unique
material verifications, with zero missing, orphan, duplicate, placeholder, or grouped
pseudo-test entries. Two independent implementers derive the same four modules, private
symbols, signatures, request/result projection, cancellation ownership, construction
order, shared report identity, defaults, error boundary, one focused test, and 5.3D
handoff. The exact Phase 5.3B paths implement the Editor adapter and exact facade
composer; the maintained facade supplies the third Shell binding through
`facade.open_report` without moving report semantics. The exact scope is sufficient and
this specification is ready for freeze.

| Verification | Requirement | Material assertion |
| --- | --- | --- |
| `EDITOR-V022` | `EDITOR-022` | Immutable-baseline, maintained-history, current-authority, and future-worktree-compatible integrity checks all pass independently. |
