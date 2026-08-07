# Desktop Application Facade Specification V1

Status: maintained implementation-ready specification. Report-opener reachability
maintenance adds one narrow GUI-neutral delegation while preserving the Phase 5.1B
value and execution contracts. It does not authorize GUI, report implementation, path,
configuration, or runtime composition.

## 1. Authority and scope

The normative prerequisite is
`phase-5-windows-desktop-productization-spec-v10-roadmap-baseline-ready` at
`eb1e915cd1ae694a969afe7f19eda41c31df8dbe`. The frozen Productization specification
owns the desktop architecture and roadmap. Windows Update Protocol V6 and Windows
Update Persistence Format V6 remain unchanged and are not facade dependencies.

Phase 5.1B is limited to:

- `src/pastila_scout/desktop_application_v1/__init__.py`;
- `src/pastila_scout/desktop_application_v1/models.py`;
- `src/pastila_scout/desktop_application_v1/services.py`;
- `src/pastila_scout/desktop_application_v1/errors.py`;
- `tests/test_desktop_application_v1.py`.

The facade exposes immutable contracts, two execution operations, and one synchronous
opaque-report opening delegation. It
does not supply production Scout or Editor adapters. Those private adapters belong to
Phases 5.2B and 5.3B. It does not create a GUI, executor, provider, database, report,
path authority, or composition root.

## 2. Repository grounding

The current repository establishes these authorities:

| Area | Existing authority | Relevant behavior |
| --- | --- | --- |
| Scout polling | `pastila_scout.poller.poll_once(config_path, database_path, timeout=20.0, *, now=None, max_article_age_hours_override=None, category="all") -> PollResult` | Loads source configuration, performs one bounded concurrent poll, owns HTTP cleanup, opens and initializes SQLite, persists the run/articles/events, and returns counters plus source failures. |
| Scout desktop orchestration | none | `poll_once()` is not a complete desktop result and has no facade-safe error or report projection. Phase 5.2B must adapt it without changing it. |
| Scout periods | `pastila_scout.cli.POLL_DAY_CHOICES` | Closed values are `1`, `3`, `7`, `14`, and `30`; the CLI's interactive/default selection is not an application API. |
| Scout categories | `pastila_scout.config.SourceCategory` plus CLI `all` | Closed serialized values are `Politica`, `Social`, `Conspiratii`, `Economie`, `CanCan`, `Externe`, `Diverse`, and `all`. |
| Editor application | `pastila_scout.editor_application_v1.EditorApplicationCoordinatorV1.execute(*, request: EditorApplicationRequestV1) -> EditorApplicationResultV1` | Owns validation, preparation, provider-neutral operational execution, serialization, atomic no-replace export, cancellation projection, and finite application outcomes. |
| Editor composition | package-private `pastila_scout.editor_application_v1.runtime_composition._compose_editor_application_runtime_v1()` | Creates one fresh coordinator and owns provider/runtime composition. Facade and GUI code must not import it. Phase 5.3B owns the private desktop adapter/composition. |
| Editor CLI | `pastila_scout.editor_cli_run_v1.run_editor_command(...) -> int` | Thin CLI adapter that loads files, constructs the application request, invokes the private composition root, and renders process output. It is not reusable as an in-process application boundary. |
| Configuration | `pastila_scout.config` loaders and Editor configuration authorities | Existing owners load and validate YAML/contracts. The facade neither reads nor mutates configuration. |
| Database | `pastila_scout.database` and `poll_once()` | Connections, cursors, transactions, schema initialization, and persistence remain lower-owned. |
| Reports | `pastila_scout.reporting` and Editor application serialization/export | Existing Scout writers produce JSON/text. No public HTML-report service exists. Phase 5.2B owns the additive HTML report and catalog boundary. |
| CLI | `pastila_scout.cli` and command packages | Parser, console rendering, and exit codes remain CLI-owned. |
| Logging | module loggers plus `pastila_scout.logging_config.configure_logging()` | Application startup configures logging. The facade introduces no logging subsystem. |

## 3. Purpose and dependency direction

`DesktopApplicationFacadeV1` is the only public in-process boundary through which the
future desktop shell submits Scout and Editor application work. It shields the shell
from CLI adapters and private provider, runtime, persistence, serialization, and export
owners.

```text
future desktop shell
  -> pastila_scout.desktop_application_v1
     -> private Scout adapter (Phase 5.2B)
        -> existing Scout polling/persistence and new private report service
     -> private Editor adapter/composition (Phase 5.3B)
        -> EditorApplicationCoordinatorV1
           -> existing lower Editor/provider/runtime/export owners
```

No production package below the facade imports `desktop_application_v1`. The package
must not import `cli`, `editor_cli_run_v1`, provider-specific packages, private runtime
composition modules, `sqlite3`, `tkinter`, reporting implementations, or Windows update
packages.

## 4. Closed operation inventory after report-opener maintenance

The public facade has exactly three operations and three injected operation protocols:

```python
class ScoutDesktopOperationV1(Protocol):
    def run_scout(
        self,
        *,
        request: ScoutDesktopRequestV1,
    ) -> ScoutDesktopResultV1: ...

class EditorDesktopOperationV1(Protocol):
    def run_editor(
        self,
        *,
        request: EditorDesktopRequestV1,
    ) -> EditorDesktopResultV1: ...

class DesktopReportOperationV1(Protocol):
    def open_report(self, *, reference: str) -> None: ...

class DesktopApplicationFacadeV1:
    def __init__(
        self,
        *,
        scout_operation: ScoutDesktopOperationV1,
        editor_operation: EditorDesktopOperationV1,
        report_operation: DesktopReportOperationV1,
    ) -> None: ...

    def run_scout(
        self,
        *,
        request: ScoutDesktopRequestV1,
        progress_sink: DesktopProgressSinkV1,
    ) -> ScoutDesktopResultV1: ...

    def run_editor(
        self,
        *,
        request: EditorDesktopRequestV1,
        progress_sink: DesktopProgressSinkV1,
    ) -> EditorDesktopResultV1: ...

    def open_report(self, *, reference: str) -> None: ...
```

There is no generic command execution operation. Report catalog resolution and opening
remain solely implemented by the injected Phase 5.2B report operation; the facade only
validates the opaque scalar and delegates once. Report reveal,
configuration/source projection, capabilities, status queries, updates, and source
updates are not V1 operations. The first three belong to Phase 5.2; configuration and
installed-path ownership begin in Phase 5.4; update behavior begins in Phase 5.7.

`DesktopApplicationFacadeV1` is a final concrete delegator, not a composition root. Its
constructor accepts exactly the three injected operations shown above and performs no
lower construction. Phase 5.3B's private composition is the first phase allowed to
assemble the already-implemented private Scout and Editor adapters and inject them into
this constructor. No global registry, singleton, service locator, hidden cache, or
zero-argument public composer exists.

The concrete class has exact slots `_scout_operation`, `_editor_operation`,
`_report_operation`, and `_identity`, rejects subclassing, and exposes no public
dependency property. `_identity` is the ordered triple of injected object identities
captured after validation. No other instance state is legal.

## 5. Shared vocabularies

All enums are exact `StrEnum` classes. Their member names and values are:

| Type | Member | Serialized value |
| --- | --- | --- |
| `DesktopOperationKindV1` | `SCOUT` | `scout` |
|  | `EDITOR` | `editor` |
| `DesktopOperationStatusV1` | `COMPLETED` | `completed` |
|  | `PARTIAL` | `partial` |
|  | `FAILED` | `failed` |
|  | `CANCELLED` | `cancelled` |
| `DesktopProgressStageV1` | `ACCEPTED` | `accepted` |
|  | `RUNNING` | `running` |
|  | `COMPLETED` | `completed` |
|  | `PARTIAL` | `partial` |
|  | `FAILED` | `failed` |
|  | `CANCELLED` | `cancelled` |
| `ScoutDesktopCategoryV1` | `POLITICA` | `Politica` |
|  | `SOCIAL` | `Social` |
|  | `CONSPIRATII` | `Conspiratii` |
|  | `ECONOMIE` | `Economie` |
|  | `CANCAN` | `CanCan` |
|  | `EXTERNE` | `Externe` |
|  | `DIVERSE` | `Diverse` |
|  | `ALL` | `all` |
| `DesktopApplicationFailureCodeV1` | `SCOUT_EXECUTION_FAILED` | `scout_execution_failed` |

Enums reject subclassing and pickling and return themselves from `copy.copy()` and
`copy.deepcopy()`.

## 6. Scalar rules and validation order

Operation references, source IDs, and report references use the same scalar rule:
exact `str`, NFC, already stripped, non-empty, no NUL, no C0/C1 control or surrogate,
UTF-8 length 1 through 120 bytes. The facade never trims or normalizes input.

Nonnegative counters are exact `int` values in `0..2**63-1`; `bool` is rejected.
`period_days` is an exact `int` member of `(1, 3, 7, 14, 30)`. Tuples must be exact
`tuple` instances. Enum fields require the exact enum type; raw strings are rejected.

Every constructor validates in this order:

1. exact outer type and enum membership;
2. scalar grammar and bounds;
3. nested authoritative reconstruction;
4. tuple member type, uniqueness, and deterministic ordering;
5. cross-field invariants;
6. private integrity seal construction.

Validation failure raises `DesktopApplicationConfigurationError` with no chained
context, cause, protected local, or input-dependent message.

## 7. Request contracts

### 7.1 `ScoutDesktopRequestV1`

```python
ScoutDesktopRequestV1(
    *,
    operation_reference: str,
    period_days: int,
    category: ScoutDesktopCategoryV1,
)
```

All fields are required and non-null. `period_days` maps exactly to
`max_article_age_hours_override = float(period_days * 24)` in the Phase 5.2 adapter.
`category.value` maps exactly to the existing `poll_once(..., category=...)` input.
The request contains no configuration path, database path, timeout, report path,
provider, or cancellation token. Phase 5.2 composition owns installed paths and Scout
configuration. Current Scout execution has no compatible live cancellation authority;
Scout cancellation remains disabled rather than simulated.

### 7.2 `EditorDesktopRequestV1`

```python
EditorDesktopRequestV1(*, application_request: EditorApplicationRequestV1)
```

Construction requires exact type `EditorApplicationRequestV1`, calls its supported
`copy.copy()` reconstruction boundary, requires the copy to have that exact type, and
stores the copy. The nested request already owns the four validated
inputs, generation configuration, provider/model/timeout, absolute no-replace output
destination, aware request time, operation reference, and `CancellationTokenV2`.
The facade adds no duplicate field and does not rebuild or reinterpret this authority.

The GUI creates a fresh `CancellationTokenV2` while building the application request.
The token is immutable and is sampled by the existing Editor application execution.
V1 therefore supports cancellation requested before execution; it defines no mutable
mid-execution cancellation handle or cancellation registry.

The facade does not inspect or resample the token. An already-cancelled request still
follows facade progress `ACCEPTED -> RUNNING`, receives the unchanged cancelled
`EditorApplicationResultV1` from the one downstream invocation, and emits `CANCELLED`.
A non-cancelled immutable token cannot change after downstream invocation begins, so V1
defines no after-start cancellation transition or facade exception for that case.

## 8. Result contracts

### 8.1 `DesktopReportReferenceV1`

```python
DesktopReportReferenceV1(*, report_reference: str)
```

This is an opaque immutable identifier only. It is not a path and grants no filesystem
authority. Phase 5.2's report catalog resolves it to private report metadata.

### 8.2 `DesktopApplicationFailureV1`

```python
DesktopApplicationFailureV1(*, code: DesktopApplicationFailureCodeV1)
```

`safe_message` is a derived read-only property and is never accepted from callers:

| Code | Exact safe message |
| --- | --- |
| `SCOUT_EXECUTION_FAILED` | `Scout execution failed.` |

Messages are safe for display but remain English application codes/messages; Romanian
presentation resources belong to the future shell.

### 8.3 `ScoutDesktopResultV1`

```python
ScoutDesktopResultV1(
    *,
    operation_reference: str,
    status: DesktopOperationStatusV1,
    sources_checked: int,
    sources_succeeded: int,
    sources_failed: int,
    articles_found: int,
    articles_inserted: int,
    duplicates_skipped: int,
    failed_source_ids: tuple[str, ...],
    executed_period_days: int,
    executed_category: ScoutDesktopCategoryV1,
    report_reference: DesktopReportReferenceV1 | None,
    failure: DesktopApplicationFailureV1 | None,
)
```

`failed_source_ids` preserves the authoritative lower failure-occurrence order and
multiplicity. It is not sorted or deduplicated. It exposes identifiers, not lower
exception messages. Counter invariants are:

- `sources_succeeded + sources_failed == sources_checked`;
- `len(failed_source_ids) == sources_failed`;
- `articles_inserted <= articles_found`;
- `articles_inserted + duplicates_skipped <= articles_found`;
- `COMPLETED` requires `sources_failed == 0`, no failure, and permits a report;
- `PARTIAL` requires both succeeded and failed sources, no facade failure, and permits a
  report;
- `FAILED` requires no succeeded sources, at least one failed source,
  `SCOUT_EXECUTION_FAILED`, and no report;
- `CANCELLED` is illegal for Scout V1 because no compatible cancellation authority
  exists.

Field authority is closed:

| Facade field | Authority |
| --- | --- |
| `operation_reference` | reconstructed `ScoutDesktopRequestV1` |
| source and article counters | identically named `PollResult` fields |
| `failed_source_ids` | structured Phase 5.2 adapter output required below; never CLI text or message splitting |
| executed period/category | reconstructed request, checked against the adapter invocation |
| status | exact `PollResult.status` mapping below |
| report reference | zero-or-one Phase 5.2 report-service output |
| failure | status matrix in this section |

`PollResult` contains no event count or duration. Neither is a V1 facade field, and no
implementer derives or fabricates either. Filtered-article counters and `run_id` also
remain lower Scout details because frozen Productization does not require them in this
public facade result.

The later Phase 5.2 adapter maps the existing `PollResult.status` values `success`,
`partial`, and `failed` to `COMPLETED`, `PARTIAL`, and `FAILED`. The current
`PollResult.source_failures` members are human-readable `<source-id>: <message>` strings,
while current `SourceConfig.id` accepts arbitrary strings. Splitting those strings is
therefore not a safe source-ID authority. Phase 5.1B neither parses that field nor
constructs production Scout results: its injected Scout operation supplies an already
validated `ScoutDesktopResultV1`.

Phase 5.2A must specify a structured, repository-grounded failed-source-ID projection
before Phase 5.2B implements the Scout adapter. It must not expose the human-readable
message, infer an ID by delimiter splitting, restrict an otherwise valid current Scout
configuration, or change this frozen public result model. This is an explicit later
adapter prerequisite already owned by the frozen 5.2A roadmap row, not a hidden 5.1B
implementation path. Report production likewise begins only in Phase 5.2B and supplies
the optional opaque reference.

### 8.4 `EditorDesktopResultV1`

```python
EditorDesktopResultV1(*, application_result: EditorApplicationResultV1)
```

Construction requires exact type `EditorApplicationResultV1`, calls its supported
`copy.copy()` reconstruction boundary, requires the copy to have that exact type, and
stores the copy. This is the unchanged public Editor projection; no facade
status, failure, lifecycle, exit-code, output, checksum, or lineage reinterpretation is
permitted. Its operation reference must equal the nested request reference in an actual
service invocation.

## 9. Progress contract

```python
DesktopProgressEventV1(
    *,
    operation_reference: str,
    operation: DesktopOperationKindV1,
    stage: DesktopProgressStageV1,
)

class DesktopProgressSinkV1(Protocol):
    def publish(self, *, event: DesktopProgressEventV1) -> None: ...
```

The event contains no free-form message, percentage, provider data, prompt, path, or
exception. The concrete facade emits exactly `ACCEPTED`, then `RUNNING`, then one
terminal event matching the returned result. Events for one operation preserve that
order and reference. No duplicate stage is legal. The sink is injected per invocation;
there is no event bus or global registry. Injected Scout and Editor operations neither
receive the sink nor emit facade progress.

`DesktopProgressEventV1` rejects `SCOUT` with `CANCELLED` and rejects `EDITOR` with
`PARTIAL`; all other operation/stage pairs in the closed enums are valid. Sequence
validity is enforced by the concrete facade, not stored as mutable event state.

The sink is a delivery boundary, not a scheduler. It must return `None`. A sink exception
is an integration defect and becomes the fixed safe `DesktopApplicationExecutionError`;
it never causes another lower invocation. Productization's rotating Romanian status text
remains presentation-only and is not a backend progress event.

Terminal mapping is closed: Scout `COMPLETED`, `PARTIAL`, and `FAILED` map to the
identically named progress stages; Editor application `COMPLETED`, `FAILED`, and
`CANCELLED` map to those stages. No Editor `PARTIAL` event exists. A lower exception,
invalid result, or reference mismatch maps to `FAILED`. The facade uses the reconstructed
request reference for every event and never trusts a lower result to choose event lineage.

## 10. Service semantics and cardinality

The concrete facade validates/reconstructs the request and validates the sink, emits
`ACCEPTED` and `RUNNING`, invokes one injected operation, reconstructs its result, and
emits the corresponding terminal event. The injected private operation owns only lower
adaptation. Execution is exactly:

```text
one run_scout call -> one Phase 5.2 Scout adapter call -> one poll_once call
                   -> zero or one report generation after success/partial

one run_editor call -> one Phase 5.3 Editor adapter call
                    -> one EditorApplicationCoordinatorV1.execute(request=...)
```

The facade calls the selected injected operation exactly once and never calls the
unselected operation. The returned result is authoritatively reconstructed before
crossing the facade. Wrong result type, copied-invalid state, or reference mismatch is a fixed
safe integration failure. There is no facade retry, fallback, alternate provider,
repoll, second export, second report write, or duplicate downstream invocation.

Constructor dependency validation uses `inspect.getattr_static(type(dependency),
method_name)` and the underlying function signature. It accepts only an instance method
with the exact name, parameter names/kinds, and synchronous return annotation shown in
Section 4; classmethod, staticmethod, property, forged `__signature__`, forged
`__wrapped__`, instance-level replacement, and missing/extra parameters are rejected
without invoking a descriptor, dependency body, `repr`, or equality hook. The sink is
validated the same way for `publish(*, event) -> None`. Validation failure raises
`DesktopApplicationConfigurationError` and construction invokes no dependency body.
Concretely, the static attribute must have exact type `types.FunctionType`; its
`__dict__` must contain neither `__signature__` nor `__wrapped__`; and
`inspect.signature(function, follow_wrapped=False)` must equal the specified parameter
shape. Instance `__dict__` must not contain the method name. Annotation equality is
checked against the exact public types after resolving only the facade module's own
static namespace; no dependency-controlled annotation evaluator runs.

The facade stores the three dependency identities and validates unchanged identity and
method ownership before every operation. Post-construction substitution and copied-invalid
facade state fail before either dependency executes. Facade `repr` is
`DesktopApplicationFacadeV1(dependencies=<injected>)`; equality is dependency identity
in constructor order; copy/deepcopy create a new facade with the same injected objects;
pickle is rejected. No dependency `repr`, equality, copy, or pickle hook is invoked.

Each operation reconstructs its request first, revalidates facade dependencies second,
validates the supplied sink third, emits the two initial events fourth, invokes the
selected dependency fifth, reconstructs/reference-checks the result sixth, and emits the
terminal event seventh. Request failure therefore touches no dependency or sink.
Dependency/sink validation failure invokes no body. An ordinary exception from the
selected dependency, sink publication, or result reconstruction is reduced to
`DesktopApplicationExecutionError`; process-control exceptions propagate. If lower
execution or result validation fails after `RUNNING`, the facade attempts one `FAILED`
event; failure of that terminal publication does not replace or chain the fixed facade
exception. Failure of `ACCEPTED` or `RUNNING` publication causes zero lower calls.

`open_report` first constructs and reconstructs an exact `DesktopReportReferenceV1`
from the supplied scalar, revalidates all three dependencies, and calls the injected
`report_operation.open_report(reference=validated.report_reference)` exactly once. It
requires a `None` return. Invalid scalar or dependency state raises the fixed
configuration error without an opening call. An ordinary opening exception or invalid
return becomes the fixed execution error raised outside the active exception handler
from no cause; process-control exceptions propagate. The facade owns no catalog, path,
opener, report implementation, retry, fallback, or second invocation.

## 11. Error reduction and exception boundary

Operational failures are values. The exact lower reductions required of later private
adapters are:

| Origin | Public projection |
| --- | --- |
| Invalid `ScoutDesktopRequestV1` before polling | raise `DesktopApplicationConfigurationError`; zero lower calls |
| `PollResult(status="success")` | `ScoutDesktopResultV1(COMPLETED, failure=None)` |
| `PollResult(status="partial")` | `ScoutDesktopResultV1(PARTIAL, failure=None)` |
| `PollResult(status="failed")` | `ScoutDesktopResultV1(FAILED, failure=SCOUT_EXECUTION_FAILED)` |
| Valid `EditorApplicationResultV1` | unchanged inside `EditorDesktopResultV1` |
| Invalid `EditorDesktopRequestV1` before coordinator execution | raise `DesktopApplicationConfigurationError`; zero lower calls |
| Wrong/copy-invalid lower result or reference mismatch | raise `DesktopApplicationExecutionError` with fixed message |
| Any other ordinary `Exception` escaping a lower dependency | raise `DesktopApplicationExecutionError` with fixed message |

Only a valid `PollResult` is an operational Scout outcome. Configuration, filesystem,
SQLite, HTTP-client construction, or other exceptions escaping `poll_once()` are not
converted into fabricated counters or a fabricated `PollResult`; they cross the injected
operation as an exception and the concrete facade reduces them to
`DesktopApplicationExecutionError`. Similarly, an exception escaping the already-valid
Editor request path is an execution-boundary defect, not a second request-validation
outcome.

`DesktopApplicationConfigurationError` has the fixed message
`Desktop application configuration is invalid.`.
`DesktopApplicationExecutionError` has the fixed message
`Desktop application execution failed.`. Both have empty `__slots__`, accept no message
argument, use `raise ... from None`, and expose no lower exception, traceback, input,
path, or dependency representation. `KeyboardInterrupt`, `SystemExit`, and
`GeneratorExit` are not caught.

Public exceptions are created and raised only after leaving the lower `except` block.
Before that raise, implementations delete protected request, result, dependency, sink,
and lower-exception locals. Recursive inspection of traceback frames, locals, closures,
nested containers, `__context__`, and `__cause__` must reveal none of those objects. The
public exception's context and cause are both `None`.

Editor operational failures and cancellation remain represented by the unchanged
`EditorApplicationResultV1`; the facade does not duplicate them in its own vocabulary.

## 12. Object safety

Every concrete facade value is an exact, final, frozen, slotted dataclass with
`init=False`, `repr=False`, and `eq=False`. Each defines a keyword-only constructor,
rejects subclassing, stores a private SHA-256 integrity seal, and has one public
`reconstruct_<type_snake_case>(value: object) -> ExactType` function.

Reconstruction reads fields with `object.__getattribute__`, invokes no value-provided
`repr`, equality, descriptor, iterator, or serialization hook, reconstructs nested
authorities, rebuilds the exact type, and compares the seal with constant-time
`hmac.compare_digest`. Copied-invalid, foreign subclass, missing-slot, added-state, and
post-construction mutation attempts fail with `DesktopApplicationConfigurationError`.

`repr()` exposes only type, operation/status/code, and redacts nested content and paths.
Equality reconstructs both operands and compares canonical field tuples. `copy.copy()`
and `copy.deepcopy()` return fresh authoritative reconstructions; deepcopy does not copy
dependencies or protected nested state through arbitrary hooks. Pickle is rejected by
`__reduce__`, `__reduce_ex__`, and `__getstate__` with a fixed `TypeError`. Exceptions
and protocols are not value models.

## 13. Side-effect and ownership table

| Effect | Owner | Facade rule |
| --- | --- | --- |
| Desktop scheduling, Tk queue, widgets | future shell `DesktopTaskController` | facade owns none |
| Source HTTP and internal source pool | existing `poll_once()`/`HTTPClient` | initiated once through Phase 5.2 adapter |
| Scout configuration read | existing Scout loader under Phase 5.2 composition | no facade path or parser |
| SQLite open/schema/transactions/writes | existing Scout/database owners | no connection, cursor, or transaction exposure |
| Scout HTML report and catalog | Phase 5.2 private report service | facade exposes only opaque reference |
| Editor preparation/generation | `EditorApplicationCoordinatorV1` and lower owners | one coordinator invocation |
| Provider selection, clients, cleanup | existing Editor runtime composition | facade imports/owns none |
| Editor serialization/export | `EditorApplicationCoordinatorV1` | facade does not duplicate writes |
| Configuration/source mutation | later bounded phase | no V1 operation |
| Update/trust/installer work | frozen Protocol/Persistence and later Productization phases | no facade dependency |

Indirect persistence and export are documented side effects of the invoked application
operation; they do not transfer ownership to the facade.

## 14. Thread, passivity, CLI, and logging rules

Facade methods are ordinary synchronous in-process calls. They create no
`ThreadPoolExecutor`, thread, task queue, Tk object, event loop, timer, or `root.after`
callback. The future shell owns the one-worker application executor. Existing bounded
Scout source concurrency remains lower-owned.

The facade stores no per-call mutable state and owns no lock. It does not serialize
concurrent callers or promise dependency thread safety. Frozen Productization's single
application worker is the production serialization authority; tests call the facade
synchronously on their invoking thread.

Import and protocol/value construction perform zero networking, environment or
credential access, file reads/writes, database access, polling, provider selection,
client construction, execution, cleanup, thread creation, Tk creation, or subprocess.

The facade never invokes `pastila-scout`, `run_editor_command`, `argparse`, a shell, or a
subprocess and never parses console text. Existing CLI commands do not migrate in 5.1B.

The facade implementation emits no logs in 5.1B. Later private adapters are permitted
to log only
operation kind, opaque operation reference, terminal status, and numeric counters.
They must not log raw exceptions, prompts, credentials, tokens, provider bodies, source
URLs, report/output paths, or nested request/result representations.

## 15. Exact Phase 5.1B public API

`pastila_scout.desktop_application_v1.__all__` contains exactly, in this order:

```python
(
    "DesktopApplicationConfigurationError",
    "DesktopApplicationExecutionError",
    "DesktopApplicationFacadeV1",
    "DesktopApplicationFailureCodeV1",
    "DesktopApplicationFailureV1",
    "DesktopOperationKindV1",
    "DesktopOperationStatusV1",
    "DesktopProgressEventV1",
    "DesktopProgressSinkV1",
    "DesktopProgressStageV1",
    "DesktopReportOperationV1",
    "DesktopReportReferenceV1",
    "EditorDesktopOperationV1",
    "EditorDesktopRequestV1",
    "EditorDesktopResultV1",
    "ScoutDesktopCategoryV1",
    "ScoutDesktopOperationV1",
    "ScoutDesktopRequestV1",
    "ScoutDesktopResultV1",
    "reconstruct_desktop_application_failure",
    "reconstruct_desktop_progress_event",
    "reconstruct_desktop_report_reference",
    "reconstruct_editor_desktop_request",
    "reconstruct_editor_desktop_result",
    "reconstruct_scout_desktop_request",
    "reconstruct_scout_desktop_result",
)
```

Symbol ownership is exact:

| Module | Symbols |
| --- | --- |
| `errors.py` | the two public exceptions |
| `models.py` | enums, seven concrete values, and seven reconstruction functions |
| `services.py` | three operation protocols, progress-sink protocol, and concrete `DesktopApplicationFacadeV1` |
| `__init__.py` | imports and the exact `__all__` only |

No symbol is added to `pastila_scout.__init__`. No additional production module is
required. Protocol methods are synchronous and keyword-only exactly as shown in Sections
4 and 9. Protocols contain declarations only. The concrete facade contains only
validation, single-call delegation, result reconstruction, and fixed safe exception
reduction.

## 16. Phase 5.1B focused verification

`tests/test_desktop_application_v1.py` is the only focused test file. It materially
verifies:

1. exact module and package exports, symbol ownership, method signatures, annotations,
   keyword-only parameters, and closed enum values;
2. every valid request/result/event/failure construction and authoritative
   reconstruction;
3. wrong outer/nested types, bool-as-int, bounds, Unicode/control values, enum raw
   strings, tuple order/duplicates, and every cross-field invariant;
4. copied-invalid, missing/additional state, foreign subclasses, mutation attempts,
   copy/deepcopy, pickle rejection, deterministic equality, and redacted repr;
5. fake OpenAI and Ollama Editor application results remain unchanged through the
   wrapper; no live provider is used;
6. fake Scout completed/partial/failed results preserve counters, category, period,
   failed-source IDs, and opaque report reference;
7. exact error reduction tables, fixed safe exception messages, recursive traceback
   isolation, and non-catching of process-control exceptions;
8. cancellation-before-execution preservation for Editor and explicit absence of Scout
   cancellation or mutable cancellation APIs;
9. exact progress ordering and terminal/result equivalence through the concrete facade
   using deterministic injected operations;
10. one concrete facade call produces one selected fake-operation call and zero
    unselected calls, retry, fallback, alternate provider, duplicate export, or duplicate
    report;
11. dependency validation independently rejects wrong parameters, positional methods,
    classmethod/staticmethod/property, forged `__signature__`/`__wrapped__`, instance
    replacement, copied-invalid state, and post-construction substitution before any
    dependency or descriptor body executes;
12. passive imports/construction under denied socket, environment, credential, file,
    database, subprocess, thread, executor, and Tk probes;
13. AST/import graph denial for CLI, Tk, sqlite3, provider packages, private runtime
    composition, reporting implementations, and Windows update packages;
14. no public connection/cursor/runtime/client/serializer/exporter value exposure;
15. Productization, Protocol, Persistence, existing Editor, and existing CLI behavior
    remain unchanged.

The scope-cardinality test compares `git diff --name-only` from the exact frozen
5.1A output tag supplied to the future 5.1B task, not from an older cumulative baseline.
It permits exactly the four production paths and one test path named in Section 1. It
does not assert that later repository history must forever match the 5.1B delta.

Frozen integrity uses committed blob hashes or files read from the exact prerequisite
tag and compares only frozen files that 5.1B is forbidden to modify. It does not reject
authorized later-phase evolution merely because the current worktree contains later
commits.

All tests are offline. Focused and full suites run with `-p no:cacheprovider`.

## 17. Implementation and verification sequence

Two implementers must derive the same sequence:

1. create only the four authorized package files;
2. implement exact enums, values, reconstruction, and errors;
3. declare the four exact protocols and implement the injected delegator without
   composing lower services;
4. expose exactly Section 15's `__all__`;
5. add only `tests/test_desktop_application_v1.py`;
6. run the focused test, full offline suite, Ruff, Black, compileall, pip check, and
   `git diff --check`;
7. verify the authorized delta against the frozen 5.1A tag;
8. return `PHASE_5_1B_DESKTOP_APPLICATION_FACADE_REVISION_1_VERIFIED` only after
   independent verification.

The required 5.1B commit subject is `Add verified desktop application facade`; its tag
is `phase-5.1b-desktop-application-facade-r1-verified`.

## 18. Closed non-goals

The facade does not implement Scout or Editor adapters, composition, HTML, report
catalog/path resolution/reveal, configuration projection/mutation, installed paths, capabilities,
updates, GUI, localization, scheduling, database access, provider execution, retry,
fallback, routing, polling beyond a future adapter's single invocation, or CLI changes.

There is no alternative facade shape, generic extension point, optional operation,
provider-specific branch, or hidden implementation path in V1.

## 19. Report-opener reachability maintenance

The bounded maintenance repairs the Phase 5.3D reachability gap without transferring
report ownership. Future Phase 5.3B constructs one `_DesktopReportFacadeV1`, injects
that exact object into `_ScoutDesktopOperationV1.report_facade` and
`DesktopApplicationFacadeV1.report_operation`, and returns the facade. Future Phase
5.3D binds `facade.open_report` directly to the frozen Shell callback shape
`(*, reference: str) -> None`. The opaque reference remains the only crossing value;
the private report facade remains the only validator, catalog resolver, and opener
invoker. No startup or Shell code receives a path or report implementation object.
