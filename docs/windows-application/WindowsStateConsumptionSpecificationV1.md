# Windows State Consumption Specification V1

## 1. Authority, milestone, and closed scope

`CONSUME-001` This document is the Phase 5.4C authority at
`docs/windows-application/WindowsStateConsumptionSpecificationV1.md`. Its prerequisite
is the composite authority formed by immutable original
`phase-5.4b-windows-state-r1-verified` plus verified additive overlay
`phase-5.4b-windows-state-receipt-recovery-applicability-maintenance-r1-verified`.
V12's literal roadmap prerequisite remains the original tag; the later maintenance does
not rewrite V12 or original history. The readiness verdict, future commit subject, and
output tag are `PHASE_5_4C_WINDOWS_STATE_CONSUMPTION_SPECIFICATION_V1_READY_FOR_FREEZE`,
`Specify Windows state consumption V1`, and
`phase-5.4c-windows-state-consumption-spec-v1-ready`.

`CONSUME-002` Phase 5.4D changes exactly these production paths:

- `src/pastila_scout/desktop_v1/state_composition.py`;
- `src/pastila_scout/desktop_v1/settings.py`;
- `src/pastila_scout/desktop_v1/entrypoint.py`;
- `src/pastila_scout/desktop_v1/views.py`;
- `src/pastila_scout/desktop_v1/resources.py`;
- `src/pastila_scout/desktop_editor_v1/composition.py`;
- `src/pastila_scout/desktop_scout_v1/service.py`;
- `src/pastila_scout/poller.py`.

Its exact tests are `tests/test_windows_state_consumption_v1.py`,
`tests/test_desktop_startup_integration_v1.py`, `tests/test_desktop_shell_v1.py`,
`tests/test_desktop_editor_v1.py`, `tests/test_desktop_scout_v1.py`, and
`tests/test_poller.py`. API impact is private state-bound desktop startup/composition
only. Packaging, updater, source-bundle implementation, Scout semantics, CLI, global
state, service locators, GUI redesign, and a settings editor are forbidden. Its verdict,
subject, and tag are `PHASE_5_4D_WINDOWS_STATE_CONSUMPTION_REVISION_1_VERIFIED`,
`Add verified Windows state consumption`, and
`phase-5.4d-windows-state-consumption-r1-verified`.

`CONSUME-003` Phase 5.5A consumes
`phase-5.4d-windows-state-consumption-r1-verified`. Phase 5.4C and 5.4D implement no
trust, packaging, installer, updater, signed-source activation, restart, handoff, or
release behavior.

## 2. Frozen grounding and ownership

`CONSUME-004` Original Phase 5.4B supplies the sole path resolver, immutable path value,
directory creator, settings/default loader and saver, development migration inspector
and executor, receipt/journal recovery, and database migration gate. Its verified
maintenance overlay adds `DevelopmentMigrationApplicabilityV1` and
`_inspect_development_state_migration_applicability_v1` in the same lower owner without
rewriting the original tag. Phase 5.4D calls those composite APIs and duplicates none of
their validation, recovery, status, eligibility, freshness, or persistence rules.

`CONSUME-005` `config.py` remains sole owner of `ApplicationConfig`, `SourcesConfig`,
YAML parsing, category/source validation, and `load_sources_config`. `database.py`
retains normal schema, connection, transaction, integrity, and `user_version` behavior.
`desktop_report_v1` retains report generation, catalog identity, and opening. The facade
remains filesystem-neutral. `pyproject.toml` remains the sole application-version source.

`CONSUME-006` Frozen 5.3D startup creates one Tk root, withdraws it, composes one facade,
creates one controller and one view, binds the same facade to Scout, Editor, and report
operations, starts the controller, deiconifies, and then enters mainloop. It owns two
executors and one Tk queue/drain path; workers never access widgets. Phase 5.4D preserves
these cardinalities and ordering constraints.

## 3. State-bound composition contract

`CONSUME-007` `desktop_v1/state_composition.py` defines exactly this first-owned surface:

```python
class _DesktopStateCompositionV1: ...

def _compose_state_bound_desktop_application_v1(
    *,
    frozen: bool,
    environment: Mapping[str, str],
    development_root: Path | None,
    migration_consent: Callable[
        [WindowsApplicationPathsV1], DevelopmentMigrationPlanV1 | None
    ],
) -> _DesktopStateCompositionV1: ...
```

The immutable, slotted, final result contains exactly `facade` and `settings`. `facade`
is one `DesktopApplicationFacadeV1`; `settings` is one reconstructed
`_DesktopSettingsProjectionV1`. Resolved paths remain local to this one composition and
are injected before return; neither the result nor the entrypoint retains them. The
function performs one state initialization attempt and calls the underlying facade
composer exactly once after every preceding gate succeeds. It has no cache, singleton,
service locator, import effect, retry, lazy second composition, or fallback composer.

`CONSUME-008` `entrypoint.py` determines `frozen` as `bool(getattr(sys, "frozen", False))`,
passes an explicit copy of `os.environ`, and passes `development_root=None` when frozen.
The state composer derives the installed bundled application root exactly as
`Path(environment["LOCALAPPDATA"]) / "Programs" / "PastilaScout" / "app"`; the frozen
5.4B resolver validates its absoluteness, exact identity, and required immutable files,
including `desktop_v1/default-settings-v1.json`. For development, the entrypoint passes
exactly `Path(__file__).resolve().parents[3]` after validating the repository layout.
No current-directory, home, username, registry, executable-directory, or
installed-to-development fallback exists.

`CONSUME-009` The state composer calls `_resolve_windows_application_paths_v1` once. In
installed mode it passes `frozen=True`, the explicit environment, the deterministically
derived bundled root, and `development_root=None`; in development it passes
`frozen=False`, the explicit environment, `bundled_application_root=None`, and the
entrypoint-supplied development root. Every subsequent config, source, database, report,
settings, defaults, and migration location comes from that one reconstructed
`WindowsApplicationPathsV1`.

`CONSUME-010` After resolution and before settings or migration I/O, the composer calls
`_create_windows_application_directories_v1(paths=paths)` exactly once. Failure prevents
migration, source selection, and facade composition. No directory is created at import
or beneath the immutable installation root.

## 4. Settings projection and GUI defaults

`CONSUME-011` The composer calls `_load_windows_settings_v1` exactly once with
`path=paths.settings_path` and `defaults_path=paths.settings_defaults_path`. Absent
mutable settings use the immutable defaults resource. Malformed, inaccessible, or
unsupported settings terminate startup through the safe state-consumption failure;
5.4D performs no JSON parsing, repair, quarantine, or save.

`CONSUME-012` `desktop_v1/settings.py` owns exactly:

```python
class _DesktopSettingsProjectionV1: ...

def _project_desktop_settings_v1(
    *, settings: WindowsSettingsV1
) -> _DesktopSettingsProjectionV1: ...

def _select_scout_sources_path_v1(
    *, paths: WindowsApplicationPathsV1
) -> Path: ...
```

The projection is immutable, slotted, final, reconstructed on consumption, redacts user
paths/model in `repr`, rejects pickle/subclassing, and contains all thirteen settings
fields without becoming a second persistence authority. The module performs no I/O on
import and defines no mutable current-settings value.

`CONSUME-013` `_DesktopMainWindowV1.__init__` adds the keyword-only
`settings: _DesktopSettingsProjectionV1`. It initializes existing widgets exactly as
follows: `scout_period_days` as its base-10 string; `scout_category` unchanged;
`editor_profile_path`, `editor_context_path`, `editor_generation_path`, and
`editor_output_directory` as empty string for null or `str(path)` otherwise;
`editor_provider` and `editor_model` unchanged; `editor_timeout_seconds` with Python's
canonical `str(float)`; the existing no-replace control remains true. `schema`,
`schema_version`, `log_level`, and `updates_enabled` are retained in the projection but
have no visible 5.4D widget effect. No settings editor, new preference control, or save
action is added.

## 5. Installed development-state migration

`CONSUME-014` Development mode never calls the applicability gate,
migration-consent callback, inspector, or executor. In installed mode the state composer
first calls
`_inspect_development_state_migration_applicability_v1(destination=paths)` exactly once.
When a pending journal exists, the maintained lower boundary performs lower-owned
recovery before validating any receipt; it is not a filesystem-free query. Its behavior
is exact:

| Applicability status/outcome | Chooser | Confirmation/execution | Startup |
| --- | --- | --- | --- |
| `already_migrated` | no | neither | continue with initially loaded settings |
| `development_root_required` | exactly one chooser is permitted | determined only by the later full plan | continue through full inspection or cancel |
| safe applicability failure | no | neither | terminate with `migration.error` |

Phase 5.4D never checks receipt existence, parses receipt JSON, inspects a journal,
derives applicability, discovers a development root, or infers recovery/completion.

`CONSUME-015` Only `development_root_required` invokes the sole `migration_consent`
callback, synchronously and at most once on the Tk-owning startup thread with the
withdrawn root captured by its entrypoint closure. Selection cancel returns `None`
without inspection. A selected root is passed once to
`_inspect_development_state_migration_v1(development_root=selected,
destination=paths)`. Full-plan behavior is exact:

| Full status | Chooser history | Confirmation | Execution | Startup/reload |
| --- | --- | --- | --- | --- |
| `ready` | already shown once | once, displaying source root, exact eligible destinations, and eligible artifact classes | affirmative only | decline/close continues unchanged; success reloads settings only when copied |
| `nothing_to_migrate` | already shown once | no | no | continue with initially loaded settings |
| `destination_occupied` | already shown once | no | no | continue with initially loaded settings |
| `already_migrated` | already shown once only when state changed after the pre-gate | no | no | continue with initially loaded settings |
| safe inspection failure | already shown once | no | no | terminate with `migration.error` |

Affirmative confirmation returns that same frozen `DevelopmentMigrationPlanV1`; decline
or dialog close returns `None`. The applicability result is never a plan and never enters
the executor.

`CONSUME-016` `resources.py` adds exactly these finite keys and Romanian values:

| Key | Value |
| --- | --- |
| `state.error` | `Starea aplicației Windows nu a putut fi inițializată.` |
| `migration.title` | `Importă starea de dezvoltare` |
| `migration.prompt` | `Selectați un proiect de dezvoltare pentru import. Fișierele sursă nu vor fi șterse.` |
| `migration.confirm` | `Importați starea validată în profilul Windows?` |
| `migration.error` | `Starea de dezvoltare nu a putut fi importată.` |
| `sources.override.error` | `Configurația surselor personalizate este invalidă.` |

No value interpolates a path, exception, configuration, model, or operating-system text.
Applicability reuses `migration.error`; Phase 5.4D adds no seventh resource or receipt-
specific presentation.

`CONSUME-017` The callback returns only `None` or the same fully inspected `ready` plan. The
composer requires an exact `DevelopmentMigrationPlanV1` with `status == "ready"` and
passes it once to `_execute_development_state_migration_v1(plan=plan)`, whose frozen
boundary performs authoritative reconstruction and freshness inspection. A `None` return
continues without execution. Inspection, invalid callback output, or execution failure
is terminal; facade composition has not occurred. Frozen per-artifact flags control
exactly what is copied, including partial eligibility. There is no retry, merge,
overwrite, automatic consent, desktop-owned eligibility rule, or source deletion.

`CONSUME-018` A completed import does not replace the immutable path authority. The
composer reuses its same local reconstructed `paths`, reloads settings once only when
`result.settings_copied` is true, and then selects sources. Pre-gate `already_migrated`,
chooser cancel, decline, close, and non-ready full statuses reuse initially loaded
settings. Receipt publication remains lower-owned. On later receipt-bearing launches the
maintained pre-presentation gate returns `already_migrated`, so no chooser, confirmation,
full inspection, or execution occurs.

## 6. Source selection and injection

`CONSUME-019` `_select_scout_sources_path_v1` implements Phase 5.4D precedence only:
if `paths.source_override_path` is absent, validate and return
`paths.bundled_source_path`; if the override is present, require a regular non-reparse
file, validate it through `load_sources_config`, and return it. A malformed or
inaccessible present override raises the safe source-selection failure and never falls
through. It copies, rewrites, merges, or parses no YAML itself.

`CONSUME-020` The selector's first ownership remains `desktop_v1/settings.py`, which is
also an exact Phase 5.9B authorized path. Phase 5.9B extends this selector between valid
override and bundled default with its separately verified active-bundle authority. Phase
5.4D creates no bundle path, placeholder, scan, trust check, network action, activation,
or fallback behavior.

`CONSUME-021` Installed application configuration is
`paths.scout_application_config_path` under immutable `app/config/config.yaml`;
development configuration is the same field resolved to repository
`config/config.yaml`. It is never migrated, transformed, parsed by the desktop settings
module, or treated as Windows settings.

`CONSUME-022` `_compose_desktop_application_facade_v1` changes to this exact signature:

```python
def _compose_desktop_application_facade_v1(
    *,
    config_path: Path,
    sources_path: Path,
    database_path: Path,
    report_directory: Path,
) -> DesktopApplicationFacadeV1: ...
```

It validates concrete paths, constructs one report facade with `report_directory`, one
Scout operation with `config_path`, `sources_path`, `database_path`, and that same report
facade, then constructs Editor and the public facade exactly once. It performs no file
discovery, state resolution, database open, or source selection. No parameter has a
default; all current production and tests change within the frozen 5.4D path set.

`CONSUME-023` `_ScoutDesktopOperationV1.__init__` adds required keyword-only
`sources_path: Path`, stores it immutably with config/database paths, includes it in
reconstruction identity, and forwards it unchanged on every `poll_once` call. It never
discovers, validates, or selects source files.

`CONSUME-024` `poll_once` changes additively to:

```python
def poll_once(
    config_path: Path,
    database_path: Path,
    timeout: float = 20.0,
    *,
    sources_path: Path | None = None,
    now: datetime | None = None,
    max_article_age_hours_override: float | None = None,
    category: str = "all",
) -> PollResult: ...
```

When `sources_path` is null it preserves every existing caller by invoking existing
`load_config(config_path)`. When non-null it requires the platform concrete absolute
path and invokes existing `load_configuration(config_path, sources_path=sources_path)`.
It contains no precedence, fallback, YAML schema, state resolution, or GUI behavior; all
other polling behavior and parameter semantics remain byte-equivalent in effect.

`CONSUME-025` The report facade constructed with the resolved report directory is the
same exact object supplied to Scout report generation and public facade report opening.
The resolved database path is passed only to Scout operation construction; composition
does not create or open the database. `DesktopApplicationFacadeV1` gains no path field,
constructor parameter, or filesystem behavior.

## 7. Startup integration and failure safety

`CONSUME-026` `entrypoint.main` replaces its one direct facade-composer call with one
`_compose_state_bound_desktop_application_v1` call after root withdrawal. It retains the
returned facade and settings only, supplies the facade to the existing closures, and
supplies settings to view construction. There is exactly one underlying facade
composition, one retained facade, no retained paths result, and no installed-mode call
to the old development-relative composer.

`CONSUME-027` All mode resolution, directory creation, settings load, applicability and
recovery, migration callback and execution, source validation/selection, and facade
composition run synchronously on the Tk-owning startup thread before controller/view
construction. Phase 5.4D adds no
executor, worker, thread, queue, drain, retry loop, or worker-owned modal action. Frozen
controller ownership of two executors and Tk dispatch remains unchanged.

`CONSUME-028` Mainloop is entered only after successful input establishment, mode and
installed-root determination, path resolution, directory creation, settings load,
installed applicability/recovery, any permitted chooser, full inspection/status,
eligible-plan consent and execution or a deterministic no-migration outcome, required settings reload, source selection,
state-bound facade composition, controller/view construction, bindings, controller
start, and deiconify, in that order. Root remains withdrawn until deiconify.

`CONSUME-029` `state_composition.py` defines one final private
`_DesktopStateConsumptionError` with fixed message
`Windows desktop state consumption failed.` Expected path, settings, migration, source
validation, and facade-composition failures are converted outside active handlers with
no cause, context, protected object, or raw text retained. `KeyboardInterrupt`,
`SystemExit`, `GeneratorExit`, and `MemoryError` propagate. `entrypoint.py` maps the safe
failure to finite resources and exit code `1`; it never interpolates lower details.

`CONSUME-030` Failure behavior is exact:

| Boundary | Root | Facade/controller | Cleanup | Presentation | Mainloop |
| --- | --- | --- | --- | --- | --- |
| inputs, mode, installed root, path, directories, settings | withdrawn | neither exists | destroy root | `state.error` | no |
| applicability `already_migrated` | withdrawn | created afterward | normal lifecycle | none | yes after all gates |
| applicability/recovery failure | withdrawn | neither exists | lower recovery; destroy root | `migration.error` | no |
| chooser cancel, non-ready full status, confirmation close/decline | withdrawn | created afterward | normal lifecycle | none | yes after all gates |
| chooser/inspection/confirmation/freshness/execution/reload failure | withdrawn | neither exists | lower recovery; destroy root | `migration.error` | no |
| override validation/selection | withdrawn | neither exists | destroy root | `sources.override.error` | no |
| facade composition | withdrawn | no retained facade/controller | destroy root | existing `startup.error` | no |
| controller/view/binding/start | withdrawn | close any controller once | destroy root | existing `startup.error` | no |

No failure displays partially operational UI, retries composition, or falls back to a
different mode/source/config/database/report path.

## 8. Exact path responsibilities

`CONSUME-031` Production ownership is non-overlapping:

| Path | Sole load-bearing 5.4D responsibility |
| --- | --- |
| `desktop_v1/state_composition.py` | installed-root derivation, applicability invocation, lifecycle orchestration, two-field result, safe boundary |
| `desktop_v1/settings.py` | safe GUI projection and first-owned source selector |
| `desktop_v1/entrypoint.py` | explicit mode inputs, modal callback, one state-composer call |
| `desktop_v1/views.py` | initialize existing widgets from projection |
| `desktop_v1/resources.py` | finite Romanian state/migration/source text |
| `desktop_editor_v1/composition.py` | inject four resolved paths into existing facade graph |
| `desktop_scout_v1/service.py` | retain and forward selected sources path |
| `poller.py` | additive lower configuration loading with explicit sources path |

`CONSUME-032` Test ownership is non-overlapping:

| Test | Sole primary verification responsibility |
| --- | --- |
| `test_windows_state_consumption_v1.py` | modes, applicability/no-UI gate, lifecycle, migration, selector, failure boundary |
| `test_desktop_startup_integration_v1.py` | withdrawn-root ordering, one facade, cleanup/mainloop |
| `test_desktop_shell_v1.py` | projection/view defaults, resources, executor invariants |
| `test_desktop_editor_v1.py` | exact four-path facade-composer injection and facade neutrality |
| `test_desktop_scout_v1.py` | sources-path retention/forwarding and shared report identity |
| `test_poller.py` | explicit nullable sources-path loading and old-caller compatibility |

## 9. Verification matrix

Each row is one material test obligation rather than a grouped placeholder.

| Verification | Requirement | Material proof |
| --- | --- | --- |
| `CONSUME-V001` | `CONSUME-001` | Assert original prerequisite plus maintenance overlay, path, verdict, subject, and tag literals. |
| `CONSUME-V002` | `CONSUME-002` | Derive exact eight-production/six-test delta from immutable tags. |
| `CONSUME-V003` | `CONSUME-003` | Assert 5.5A dependency and trust/packaging exclusions. |
| `CONSUME-V004` | `CONSUME-004` | Verify composite identities, exact maintained API, and reject duplicated recovery/receipt logic. |
| `CONSUME-V005` | `CONSUME-005` | Static lower-owner and public-facade neutrality audit. |
| `CONSUME-V006` | `CONSUME-006` | Assert frozen root/facade/controller/executor cardinalities. |
| `CONSUME-V007` | `CONSUME-007` | Exclusive input signature, exact two result fields, one-call, passivity, and no-global tests. |
| `CONSUME-V008` | `CONSUME-008` | Environment-derived installed root, frozen marker, development-root matrix, and no-fallback spies. |
| `CONSUME-V009` | `CONSUME-009` | One resolver and one immutable authority identity test. |
| `CONSUME-V010` | `CONSUME-010` | Call-order and directory-failure short-circuit test. |
| `CONSUME-V011` | `CONSUME-011` | Absent/valid/malformed/access settings branches and no parser audit. |
| `CONSUME-V012` | `CONSUME-012` | Projection/selector signatures, object safety, redaction, passivity. |
| `CONSUME-V013` | `CONSUME-013` | Assert every exact existing-widget initial value and excluded fields. |
| `CONSUME-V014` | `CONSUME-014` | Receipt returns `already_migrated` with zero callback/chooser/confirmation/execution; root-required and applicability-failure call-order/no-parser spies. |
| `CONSUME-V015` | `CONSUME-015` | One chooser only when required, selected-root inspector identity, every full status, eligible display, accept/decline/cancel tests. |
| `CONSUME-V016` | `CONSUME-016` | Exact resource key/value and zero-interpolation assertions. |
| `CONSUME-V017` | `CONSUME-017` | Applicability-not-plan rejection, ready-plan identity, partial execution, stale-plan failure, and no-retry matrix. |
| `CONSUME-V018` | `CONSUME-018` | Receipt-bearing zero-UI/full-inspector proof, settings-copied reload, no-reload branches, and same local-path identity. |
| `CONSUME-V019` | `CONSUME-019` | Override/default/malformed/reparse/delegation/no-fallback matrix. |
| `CONSUME-V020` | `CONSUME-020` | Static absence of bundle behavior and 5.9B path-seam proof. |
| `CONSUME-V021` | `CONSUME-021` | Installed/development config mapping and no-migration audit. |
| `CONSUME-V022` | `CONSUME-022` | Exact composer signature, four arguments, one object graph test. |
| `CONSUME-V023` | `CONSUME-023` | Scout construction, reconstruction, and forwarding identity test. |
| `CONSUME-V024` | `CONSUME-024` | Old/new poller caller matrix and exact loader delegation. |
| `CONSUME-V025` | `CONSUME-025` | Same report facade, database no-open, facade field audit. |
| `CONSUME-V026` | `CONSUME-026` | Entry-point call replacement, two retained values, and absence of retained paths test. |
| `CONSUME-V027` | `CONSUME-027` | Thread/executor/queue/modal ownership spies. |
| `CONSUME-V028` | `CONSUME-028` | Total startup event-order and mainloop gate assertion. |
| `CONSUME-V029` | `CONSUME-029` | Error finality/message, process-control, context and traceback audit. |
| `CONSUME-V030` | `CONSUME-030` | Failure injection at every matrix boundary. |
| `CONSUME-V031` | `CONSUME-031` | One responsibility per exact production path. |
| `CONSUME-V032` | `CONSUME-032` | One primary owner per exact test and no seventh test. |

## 10. Integrity, exclusions, and readiness

`CONSUME-033` Phase 5.4D scope derives from maintained baseline commit
`1cd1bbefc28b78b08e2cd12bc30e03cc89b037b9`, the future immutable
`phase-5.4c-windows-state-consumption-spec-v1-ready`, and its future verified tag. Tests
verify original 5.4B tag/commit, maintenance tag/commit, the exact two-file overlay,
maintained hashes `E5AF7360648979CD00DE05D6A10650BD86D879894EF678348BDC96F9C9566B04`
and `3FED0F4843FD2F3C0B2F4A6B5725AE4722345F1EADF2C25E12E95437F9CDBB53`,
and the exact future 5.4D delta from the maintained baseline. Maintained files are not
required to equal original 5.4B hashes. Unrelated worktree paths never define historical
scope; staging is checked independently.

`CONSUME-034` Imports and object construction perform no path resolution, directory
creation, settings I/O, migration, database open, YAML load, GUI creation, network,
logging configuration, updater action, or thread creation. Effects occur only through
the explicit startup composition call.

`CONSUME-035` The implementation contains no global current paths/settings/source,
environment mutation, source scan, application-config migration, settings editor, third
executor, new queue, facade filesystem field, packaging, installer, registry, shortcut,
Authenticode, update check, Protocol/Persistence transition, trust operation, signed
bundle activation, source download, restart, handoff, or release behavior.

`CONSUME-036` Two independent implementations derive identical callable signatures,
mode inputs, settings mapping, applicability statuses, receipt-bearing zero-UI behavior,
chooser/full-inspector points, consent/freshness outcomes, selector precedence, injected paths,
poller forwarding, startup ordering, safe failures, eight production paths, and six
tests. Any material divergence is a specification defect.

`CONSUME-037` Phase 5.4D focused tests, relevant desktop/config/database/Scout/report
regressions, the full offline suite, Ruff, Black check, compileall, pip check,
`git diff --check`, import passivity, exact scope, frozen hashes, and zero live network
or provider activity are mandatory gates.

`CONSUME-038` This specification changes no production, test, Productization, 5.4A,
5.4B, maintenance, frozen desktop, facade, Scout/report, Editor/provider,
Protocol/Persistence, packaging, updater, trust, or source-bundle file.

| Verification | Requirement | Material proof |
| --- | --- | --- |
| `CONSUME-V033` | `CONSUME-033` | Original/maintenance tag chain, overlay hashes, maintained-baseline future delta, staging, and mutation tests. |
| `CONSUME-V034` | `CONSUME-034` | Fresh-process import and constructor effect traps. |
| `CONSUME-V035` | `CONSUME-035` | Static forbidden-symbol/path/ownership audit. |
| `CONSUME-V036` | `CONSUME-036` | Independent two-implementation comparison. |
| `CONSUME-V037` | `CONSUME-037` | Execute every focused, regression, full, and static gate. |
| `CONSUME-V038` | `CONSUME-038` | Exact candidate-only worktree and frozen-byte audit. |
