# Scout Desktop Integration Specification V1

Status: **implementation-ready and ready for freeze**. This Phase 5.2A specification is
grounded in the frozen roadmap, the maintained facade, the frozen Shell, and the
verified lower Scout structured-failure authority.

## 1. Authority and scope

`SCOUT-001` Phase 5.2B has one purpose: adapt the existing Scout polling authority to
`ScoutDesktopOperationV1` and create the structured result and opaque report reference
consumed by the frozen facade and shell. It owns no GUI, facade composition, Editor,
provider, CLI, updater, path persistence, packaging, installation, or release behavior.

`SCOUT-002` The authorized production paths are exactly
`desktop_scout_v1/{__init__.py,models.py,service.py}` and
`desktop_report_v1/{__init__.py,models.py,service.py,html.py}` beneath
`src/pastila_scout/`. The authorized focused tests are exactly
`tests/test_desktop_scout_v1.py` and `tests/test_desktop_report_v1.py`.

`SCOUT-003` Current `PollResult.failed_source_ids: tuple[str, ...]` is the sole structured
failed-source identity authority. It preserves the lower failure-occurrence order and
multiplicity. `source_failures` remains diagnostic text only. No consumer parses it,
narrows `SourceConfig.id`, sorts IDs, or deduplicates occurrences.

`SCOUT-004` The maintained `ScoutDesktopResultV1.failed_source_ids` accepts that tuple
unchanged and enforces occurrence cardinality with
`len(failed_source_ids) == sources_failed`. The exact projection is
`failed_source_ids=poll_result.failed_source_ids`; no adapter policy remains.

## 2. Existing contracts and ownership

`SCOUT-005` The operation implements the frozen protocol exactly:

```python
class _ScoutDesktopOperationV1:
    def __init__(
        self,
        *,
        config_path: Path,
        database_path: Path,
        report_facade: _DesktopReportFacadeV1,
    ) -> None: ...

    def run_scout(
        self, *, request: ScoutDesktopRequestV1
    ) -> ScoutDesktopResultV1: ...
```

It is final, private, synchronous, and passive on import and construction. Its three
dependencies are keyword-only and validated before storage. Paths are exact `Path`
instances. The report facade is validated by static class-level inspection of the exact
method contracts defined in `SCOUT-018`; instance substitution is rechecked before use.

`SCOUT-006` One call reconstructs the frozen request, invokes `poll_once()` exactly once
with the configured paths,
`max_article_age_hours_override=float(request.period_days * 24)`, and
`category=request.category.value`. It uses the lower default timeout and supplies no
`now`. There is no retry, fallback, repoll, cancellation, or generic options mapping.

`SCOUT-007` `poll_once()` exclusively owns configuration loading, source selection,
bounded source concurrency, HTTP client lifetime, SQLite connection/schema/transactions,
run/article/event persistence, and its lower exception behavior. The desktop adapter
does not import `cli`, `sqlite3`, GUI modules, Editor/provider/runtime composition, or
update modules.

`SCOUT-008` The request supplies only `operation_reference`, `period_days`, and
`category`. It supplies no paths, timeout, session, database object, report path,
progress sink, cancellation token, widget, CLI namespace, or provider value.

## 3. Result projection and invariants

`SCOUT-009` A returned `PollResult` must be an exact instance and satisfy:
all counters are exact nonnegative `int`; `sources_checked == sources_succeeded +
sources_failed`; `len(failed_source_ids) == sources_failed`; every failed ID satisfies
the maintained facade scalar rule; `articles_inserted <=
articles_found`; and `articles_inserted + duplicates_skipped <= articles_found`.
Malformed authority is an adapter integration failure and is never repaired.

`SCOUT-010` Projection is mechanical: operation reference, executed period, and executed
category come from the reconstructed request; `sources_checked`, `sources_succeeded`,
`sources_failed`, `articles_found`, `articles_inserted`, and `duplicates_skipped` come
directly from `PollResult`; `failed_source_ids` is the exact unchanged
`PollResult.failed_source_ids` tuple. No event count, duration, run ID, filtered
counter, or fabricated value crosses the facade result.

`SCOUT-011` Lower status `success` maps to maintained `COMPLETED` only with zero failures.
Lower status `partial` maps to `PARTIAL` only with at least one success and one failure.
Lower status `failed` maps to `FAILED` only with zero successes and at least one failure.
All other combinations are invalid lower authority.

`SCOUT-012` `COMPLETED` and `PARTIAL` have no facade failure and permit one report.
`FAILED` has `DesktopApplicationFailureV1(SCOUT_EXECUTION_FAILED)` and no report.
`CANCELLED` is never emitted.

`SCOUT-013` Invalid request or constructor input raises the fixed
`DesktopApplicationConfigurationError` before side effects. An ordinary exception that
escapes polling, report generation, catalog resolution, or opening is reduced to
`DesktopApplicationExecutionError` with `raise ... from None`; the adapter never
fabricates counters or failed IDs to manufacture a result. A valid lower `failed`
`PollResult` remains an operational value and maps as specified by `SCOUT-012`.

`SCOUT-014` `KeyboardInterrupt`, `SystemExit`, and `GeneratorExit` propagate unchanged.
Unexpected programming errors reduce only at the frozen safe boundary. No returned
value, exception, log, repr, stdout, or stderr contains a raw exception, traceback,
chained exception, source URL, path, credential, token, request object, or result object.

## 4. Report boundary

`SCOUT-015` Phase 5.2 owns an additive private HTML writer and private report facade/catalog.
Existing reporting files and formats remain unchanged. The facade and shell receive only
`DesktopReportReferenceV1`; the reference is not a path and grants no filesystem access.

`SCOUT-016` Exactly one report-generation attempt follows a valid `COMPLETED` or
`PARTIAL` poll. No attempt follows lower failure, invalid authority, or an escaped poll
exception. A report failure raises `DesktopApplicationExecutionError` from no cause;
the enclosing maintained facade emits its one failed terminal progress event. It never
retries, returns a Scout result, or returns a stale/missing reference.

`SCOUT-017` `desktop_report_v1.html` defines exactly
`_render_report_html_v1(*, report: _DesktopScoutReportInputV1) -> str`. It returns one
complete UTF-8 HTML5 document containing, in order, the escaped operation reference,
status value, period, category value, the six facade counters, and one escaped list item
per failed-source occurrence. Empty failures produce an empty list. Rendering is pure
and deterministic. The opaque reference is exactly
`"scout-report-v1:" + sha256(operation_reference.encode("utf-8")).hexdigest()`; its
private filename is the same lowercase digest plus `.html`. Collision or a second
generation for the same reference is rejected. References are never parsed as paths.

`SCOUT-018` The private concrete report facade contract is exact and synchronous:

```python
class _DesktopReportFacadeV1:
    def __init__(
        self,
        *,
        report_directory: Path,
        opener: Callable[[Path], None],
    ) -> None: ...

    def generate_report(
        self, *, result: _DesktopScoutReportInputV1
    ) -> DesktopReportReferenceV1: ...

    def open_report(self, *, reference: str) -> None: ...

class _DesktopScoutReportInputV1:
    def __init__(
        self,
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
    ) -> None: ...
```

The report input is final, frozen, slotted, non-pickleable, redacts its operation
reference and failed IDs in `repr`, rejects subclasses and copied-invalid state, and
reconstructs every maintained facade scalar/counter/status invariant except report and
failure fields. Generation occurs once and returns an exact reconstructible maintained
reference. The derived opaque reference is the catalog key. The facade atomically
writes one UTF-8 HTML file under its injected directory and records the private resolved
path. A pre-existing target, partial temporary write, or catalog collision fails without
replacement. `open_report`
reconstructs the scalar reference, resolves it only through that catalog, invokes the
injected opener exactly once, and returns `None`. Unknown references fail safely. Later
composition binds `open_report(reference=value)` to the Shell's already-frozen opaque
report callback. Neither the facade result nor Shell receives a path.

## 5. Concurrency, progress, passivity, and imports

`SCOUT-019` The adapter creates no thread, executor, event loop, process, socket, HTTP
session, SQLite connection, timer, GUI object, or cancellation mechanism. Lower Scout
owns its internal pool; the frozen facade owns progress events; the frozen shell
controller owns application-task submission and GUI-thread publication.

`SCOUT-020` Imports and constructors perform no I/O, environment lookup, credential
lookup, logging configuration, path resolution, directory creation, report generation,
poll, database access, network access, or background work.

`SCOUT-021` The dependency direction is shell/composition -> frozen facade -> private
desktop Scout/report adapters -> existing Scout/reporting primitives. Neither private
package is imported by lower Scout, the facade package, shell package, CLI, Editor,
provider, or update code. Both package `__init__.py` files export no public API.

## 6. Authorized path responsibilities

`SCOUT-022` `desktop_scout_v1/models.py` owns only private reconstructed lower/result
projection values; `service.py` owns the operation, validation, one-call projection, and
safe boundary; `__init__.py` keeps the package private. `desktop_report_v1/models.py`
owns the private report input/catalog metadata; `html.py` owns pure escaped HTML;
`service.py` owns the report facade, one-write generation, catalog resolution, and
injected opening; `__init__.py` keeps the package private. No additional production or
test path is required.

## 7. Verification matrix

Each row is one material verification; none is a grouped placeholder.

| Verification | Requirement | Material assertion |
| --- | --- | --- |
| `SCOUT-V001` | `SCOUT-001` | AST denies GUI, facade composition, Editor, provider, CLI, updater, and release ownership. |
| `SCOUT-V002` | `SCOUT-002` | Historical baseline plus exact 5.2B delta contains only the frozen path set. |
| `SCOUT-V003` | `SCOUT-003` | Unsorted, duplicate, delimiter-like, slash, backslash, punctuation, and NFC Unicode occurrences remain exact without diagnostic parsing. |
| `SCOUT-V004` | `SCOUT-004` | Every legal lower tuple constructs and reconstructs unchanged through the maintained facade result. |
| `SCOUT-V005` | `SCOUT-005` | Exact constructor and `run_scout` signatures reject subclasses and forged dependencies. |
| `SCOUT-V006` | `SCOUT-006` | One request causes one exact fake poll call and no retry/fallback. |
| `SCOUT-V007` | `SCOUT-007` | Denied lower resources prove ownership stays in the injected fake poll boundary. |
| `SCOUT-V008` | `SCOUT-008` | Request projection contains exactly three frozen fields. |
| `SCOUT-V009` | `SCOUT-009` | Zero, all-success, one/many/all failures, duplicates, malformed records, duplicate IDs, and inconsistent counters are checked. |
| `SCOUT-V010` | `SCOUT-010` | Every result field equals its stated authority; absent counters cannot appear. |
| `SCOUT-V011` | `SCOUT-011` | Completed, partial, failed, and every inconsistent status/counter pairing are checked. |
| `SCOUT-V012` | `SCOUT-012` | Exact frozen failure/report matrix is reconstructed successfully. |
| `SCOUT-V013` | `SCOUT-013` | Expected config, filesystem, report, DB, and Scout failures never fabricate identity. |
| `SCOUT-V014` | `SCOUT-014` | Process-control propagation and recursive traceback-local isolation are asserted. |
| `SCOUT-V015` | `SCOUT-015` | Facade/shell observe one opaque reference and no path or catalog metadata. |
| `SCOUT-V016` | `SCOUT-016` | Generation raise, invalid return, duplicate attempt, and lower pre-report failure prove zero retry and no fabricated result. |
| `SCOUT-V017` | `SCOUT-017` | Golden HTML order, escaping, exact reference/filename derivation, atomic no-replace, collision, and path-like-reference attacks are checked. |
| `SCOUT-V018` | `SCOUT-018` | Exact constructor/method signatures, one write/open, catalog-only resolution, unknown reference, and opener failure are asserted. |
| `SCOUT-V019` | `SCOUT-019` | Denied thread/executor/process/socket/DB/Tk probes establish concurrency ownership and no cancellation. |
| `SCOUT-V020` | `SCOUT-020` | Passive import/construction succeeds under denied I/O, environment, credential, network, and DB probes. |
| `SCOUT-V021` | `SCOUT-021` | AST import graph and empty public exports are exact. |
| `SCOUT-V022` | `SCOUT-022` | Every authorized file has only its stated load-bearing responsibility. |

## 8. Freeze assessment

The requirement and verification ID sets are one-to-one: 22 requirements, 22 unique
verifications, zero missing rows, zero orphan rows, and zero grouped placeholders. Two
independent implementers derive the same paths, symbols, projections, report behavior,
failure boundary, ownership, and tests. The exact frozen 5.2B production/test path set
is sufficient, both prior identity blockers are closed, and this specification is ready
for freeze.
