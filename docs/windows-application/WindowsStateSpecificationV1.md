# Windows Application State Specification V1

## 1. Authority, milestone, and scope

`STATE-001` This document is the Phase 5.4A authority at
`docs/windows-application/WindowsStateSpecificationV1.md`. Its prerequisite is
both `phase-5.3d-desktop-startup-integration-r1-verified` and
`phase-5-windows-desktop-productization-spec-v12-windows-state-consumption-roadmap-ready`.
The readiness verdict, future
commit subject, and tag are respectively
`PHASE_5_4A_WINDOWS_STATE_SPECIFICATION_V1_READY_FOR_FREEZE`,
`Specify Windows application state V1`, and
`phase-5.4a-windows-state-spec-v1-ready`.

`STATE-002` Phase 5.4B implements this specification only in:

- `src/pastila_scout/windows_state_v1/__init__.py`;
- `src/pastila_scout/windows_state_v1/paths.py`;
- `src/pastila_scout/windows_state_v1/settings.py`;
- `src/pastila_scout/windows_state_v1/migrations.py`;
- `src/pastila_scout/windows_state_v1/errors.py`;
- `src/pastila_scout/desktop_v1/default-settings-v1.json`;
- `tests/test_windows_paths_v1.py`;
- `tests/test_windows_settings_v1.py`;
- `tests/test_windows_migrations_v1.py`.

The implementation is private. Installer, updater, source-bundle, GUI, provider,
packaging, release, and trust behavior are excluded.

`STATE-003` Phase 5.4C consumes the verified 5.4B tag to specify installed/development
state injection, source selection, and migration presentation. Phase 5.4D then consumes
the verified 5.4B and 5.4C tags and is the sole roadmap milestone authorized to wire
state into its exact frozen production and test paths. Phase 5.5A depends on verified
5.4D. Later packaging, installer, updater, Update Center, and source-bundle phases
consume path values as compatibility inputs; they do not transfer their semantics to
5.4A or 5.4B.

## 2. Repository grounding and ownership

`STATE-004` `config/config.yaml` is the development-only Scout application YAML owned
and validated by `config.py`; it is never transformed into Windows settings or migrated.
`config/sources.yaml` is the development source-only YAML owned and validated by the
existing Scout source validator. Current development composition injects that application
configuration, `data/news_monitor.db`, and `reports/`; current CLI defaults remain
project-relative. Phase 5.4B is passive and changes none of those paths.

`STATE-005` `config.py` retains Scout configuration parsing and validation;
`database.py` retains connections, transactions, schema use, locking, and ordinary
database behavior; `desktop_report_v1` retains HTML generation, catalog identity, and
opening; Editor application contracts retain caller-selected output destinations.
The state layer supplies locations only.

`STATE-006` `project.version` in `pyproject.toml` remains the sole application-version
authority. Settings schema version and SQLite `PRAGMA user_version` are independent
integer authorities and never project an application version.

## 3. Closed state inventory

`STATE-007` The complete 5.4-owned inventory is:

| Class | Owner | Mutable | Exact persistence | Lifecycle and recovery |
| --- | --- | --- | --- | --- |
| Installed application-config reference | paths | no | installed `app/config/config.yaml` | development-config compatibility input; never migrated or transformed |
| Bundled source-default reference | paths | no | installed `app/config/sources.yaml` | immutable fallback input; never mutated by 5.4B |
| Installed settings-default reference | settings | no | installed `app/desktop_v1/default-settings-v1.json` | sole canonical settings-default bytes |
| SQLite location | paths | yes, by database owner | local `data/news_monitor.db` | parent explicitly created; migration backup retained |
| SQLite migration backups | migrations | append-only | local `data/backups/` | validated backup retained; user removes manually |
| Desktop HTML reports location | paths | yes, by report owner | local `reports/` | generated/disposable; no state-layer migration of contents after initial copy |
| Scout/AI cache location | paths | yes, by Scout owners | local `cache/` | generated/disposable; never migrated |
| Log location | paths | yes, by later logging consumer | local `logs/` | generated/disposable; no retention policy in 5.4 |
| Roaming settings | settings | yes, user-editable through later UI or file | roaming `settings.json` | atomic replace with one backup |
| User source override location | paths/migrations | yes, by later source owner | roaming `sources.override.yaml` | location; eligible explicit-consent byte-identical development seed only |
| Development import pending journal | migrations | yes during one attempt | local `data/development-migration-v1.pending.json` | removed after rollback or successful receipt publication |
| Development import receipt | migrations | append-only | local `data/development-migration-v1.json` | records one successful explicit import |

`STATE-008` The application YAML is not Windows settings. An active signed source bundle
is not part of 5.4B, and 5.4B implements no source selector. Update downloads/state,
handoff/health state, mutable trust, source bundles,
installer artifacts, credentials, Editor exports, and temporary operating-system files
are closed exclusions from the 5.4-owned inventory. No catch-all state class exists.

## 4. Installation and Windows roots

`STATE-009` Installed immutable files are rooted at
`%LOCALAPPDATA%\Programs\PastilaScout\app`. Mutable local state is rooted at
`%LOCALAPPDATA%\PastilaScout`. Roaming state is rooted at
`%APPDATA%\PastilaScout`. No mutable state is written below the installed root.

`STATE-010` Installed mode requires `frozen=True`, an absolute concrete bundled
application root containing regular immutable `config/config.yaml`,
`config/sources.yaml`, and `desktop_v1/default-settings-v1.json` files, and an
environment mapping containing absolute `%LOCALAPPDATA%` and `%APPDATA%` values.
Development mode requires `frozen=False` and the explicit absolute repository root
derived by Phase 5.4D as `Path(__file__).resolve().parents[3]`; 5.4B never derives it and
never reads either environment variable in development mode. Tests inject all inputs.
No current-working-directory, registry, home-directory, or username inference is
permitted. Installed-mode detection (`sys.frozen`) and bundled-root derivation remain
Phase 5.4D composition responsibilities.

`STATE-011` Missing, empty, relative, malformed, inaccessible, or non-directory
environment roots fail with `_WindowsStatePathError`. Installed resolution never falls
back to the executable, current directory, roaming root, local root, or temporary root.

## 5. Canonical path model and layout

`STATE-012` Every accepted path is the platform concrete `Path`, absolute, lexically
normalized with `os.path.normpath`, and unchanged by Unicode normalization. A path
rejects NUL, C0/C1 controls, unpaired surrogates, `.` or `..` components in supplied
relative names, alternate data stream colons outside the drive designator, UNC roots,
extended/device namespaces (`\\?\`, `\\.\`), and Windows reserved components
`CON`, `PRN`, `AUX`, `NUL`, `COM1` through `COM9`, and `LPT1` through `LPT9`, including
those names followed by an extension. Existing ancestors used for creation reject
reparse points. Resolution performs no filesystem creation.

`STATE-013` Installed layout is exact:

```text
%LOCALAPPDATA%\Programs\PastilaScout\app\
|-- config\
|   |-- config.yaml
|   `-- sources.yaml
`-- desktop_v1\default-settings-v1.json
%LOCALAPPDATA%\PastilaScout\
|-- cache\
|-- data\
|   |-- backups\
|   |-- development-migration-v1.pending.json
|   |-- development-migration-v1.json
|   `-- news_monitor.db
|-- logs\
`-- reports\
%APPDATA%\PastilaScout\
|-- settings.json
|-- settings.json.bak
`-- sources.override.yaml
```

Development layout is exact: `<development_root>/config/config.yaml`,
`<development_root>/config/sources.yaml`,
`<development_root>/data/news_monitor.db`, `<development_root>/data/backups`,
`<development_root>/data/ai_cache`, `<development_root>/logs`, and
`<development_root>/reports`. The development settings path is
`<development_root>/config/settings.json`; its backup is `settings.json.bak`.

`STATE-014` `WindowsApplicationPathsV1` contains exactly `mode`, `installation_root`,
`scout_application_config_path`, `bundled_source_path`, `local_state_root`,
`roaming_state_root`, `database_path`, `database_backup_directory`, `report_directory`,
`cache_directory`, `log_directory`, `settings_defaults_path`, `settings_path`,
`settings_backup_path`, `source_override_path`, `migration_pending_path`, and
`migration_receipt_path`.
`mode` is exactly `"installed"` or `"development"`. Development
`installation_root` equals `development_root`; installed `migration_receipt_path` is
`local_state_root/data/development-migration-v1.json`; development receipt path is
`development_root/data/development-migration-v1.json`.

`STATE-015` `_create_windows_application_directories_v1(*, paths)` creates only local
and roaming roots plus `data`, `data/backups`, `reports`, `cache`, and `logs`, in that
order, with `parents=True` and `exist_ok=True`. It creates no file. It validates every
existing ancestor and final directory against reparse points before returning. Failure
is atomic only per directory operation, maps to `_WindowsStatePathError`, and never
removes a pre-existing directory.

## 6. Exact path APIs

`STATE-016` `paths.py` defines only these call surfaces:

```python
class WindowsApplicationPathsV1: ...

def _resolve_windows_application_paths_v1(
    *,
    frozen: bool,
    environment: Mapping[str, str],
    bundled_application_root: Path | None,
    development_root: Path | None,
) -> WindowsApplicationPathsV1: ...

def _reconstruct_windows_application_paths_v1(
    value: object,
) -> WindowsApplicationPathsV1: ...

def _create_windows_application_directories_v1(
    *, paths: WindowsApplicationPathsV1
) -> None: ...
```

There is no generic name-to-path dispatcher, global cached authority, implicit mode
detection, or module-import resolution.

## 7. Settings model and canonical format

`STATE-017` `desktop_v1/default-settings-v1.json` is UTF-8 without BOM, ends with one
LF, and contains the exact canonical JSON object below with keys in this order and
two-space indentation:

```json
{
  "schema": "pastila-scout-settings",
  "schema_version": 1,
  "scout_period_days": 7,
  "scout_category": "all",
  "log_level": "INFO",
  "editor_profile_path": null,
  "editor_context_path": null,
  "editor_generation_path": null,
  "editor_provider": "openai",
  "editor_model": "gpt-4.1-mini",
  "editor_timeout_seconds": 120.0,
  "editor_output_directory": null,
  "updates_enabled": true
}
```

`STATE-018` `WindowsSettingsV1` contains exactly those thirteen fields. Exact validation
order is: concrete object/type, exact field set/order, schema literals, scalar types,
scalar bounds/enums, text safety/NFC, then optional absolute path safety. Booleans never
pass as integers. `scout_period_days` is one of `1, 3, 7, 14, 30`;
`scout_category` is one of `Politica`, `Social`, `Conspiratii`, `Economie`, `CanCan`,
`Externe`, `Diverse`, `all`; `log_level` is one of `ERROR`, `WARNING`, `INFO`;
`editor_provider` is `openai` or `ollama`; model is 1..128 UTF-8 bytes;
timeout is a finite float in `0 < value <= 3600`; optional paths are null or absolute
safe paths under `STATE-012`. Every string is NFC, non-empty where non-null, stripped,
and free of NUL, C0/C1 controls, and unpaired surrogates. Credentials and endpoints are
not fields.

`STATE-019` Settings JSON is at most 65,536 bytes, strict UTF-8 without BOM, one JSON
object, and uses no `NaN`, `Infinity`, or `-Infinity`. Parsing rejects duplicate keys,
unknown keys, missing keys, wrong key order, wrong types, unsupported schema/version,
and trailing non-whitespace data. Empty input is malformed. No YAML or TOML settings
reader exists.

## 8. Settings read, write, and failures

`STATE-020` `settings.py` defines exactly:

```python
class WindowsSettingsV1: ...

def _default_windows_settings_v1(*, defaults_path: Path) -> WindowsSettingsV1: ...
def _reconstruct_windows_settings_v1(value: object) -> WindowsSettingsV1: ...
def _load_windows_settings_v1(
    *, path: Path, defaults_path: Path
) -> WindowsSettingsV1: ...
def _save_windows_settings_v1(*, path: Path, settings: WindowsSettingsV1) -> None: ...
```

`_default_windows_settings_v1` reads, strictly validates, and returns the model encoded
by the immutable `STATE-017` resource. That resource is the sole default-value authority;
code contains no second field-value table. Load returns that validated resource only
when the mutable path is absent. A missing or invalid defaults resource, or a directory,
empty file, malformed file, unsupported version, access failure, or invalid mutable
value raises the fixed settings error and is never repaired, renamed, quarantined, or
replaced by hard-coded defaults.

`STATE-021` Save reconstructs first, serializes the exact `STATE-017` key order with
`ensure_ascii=False`, `allow_nan=False`, two-space indentation, separators `(',', ': ')`,
and one LF, then encodes UTF-8 without BOM. The parent must already be an existing
non-reparse directory. Save creates a same-directory exclusive temporary regular file
named `.settings.json.<32-lowercase-hex>.tmp`, writes and flushes bytes, closes it, moves
an existing regular non-reparse `settings.json` to `settings.json.bak` with atomic
replace, then atomically replaces the destination with the temporary file. On failure
before publication it removes only its temporary file. On failure after backup
publication and before destination publication it atomically restores the backup.
Successful publication leaves one backup when a prior destination existed and no backup
when it did not. No `fsync`, ACL rewrite, retry, merge, or cross-volume fallback occurs.

`STATE-022` Converted settings failures expose `_WindowsStateSettingsError` with exact
message `Windows application settings are invalid.` Path/environment failures expose
`_WindowsStatePathError` with exact message
`Windows application paths are unavailable.` Neither failure contains a path, input,
JSON content, provider/model, credential, operating-system text, cause, or context.

## 9. Development-state migration

`STATE-023` Development-state migration means one explicit-consent import from one
explicit development root into unoccupied installed database, report, settings, and
roaming source-override destinations. It never migrates or transforms
`config/config.yaml`; that file remains development-only Scout application
configuration. It never means database schema migration, settings-schema migration,
report-format conversion, CLI behavior change, updater/signed-source-bundle migration,
or source deletion. There is no prior production Windows layout in this repository.

`STATE-024` `_inspect_development_state_migration_v1` receives one explicit absolute
development root and one installed `WindowsApplicationPathsV1`; a development-mode
destination is rejected. Legal sources are only
`<root>/data/news_monitor.db`, `<root>/reports`, `<root>/config/settings.json`, and
`<root>/config/sources.yaml`. The last is eligible only as a byte-identical seed of an
absent roaming `sources.override.yaml`, after validation by the existing Scout-owned
`load_sources_config`; 5.4B neither duplicates nor changes that validator. Inspection
validates a present source YAML and reports malformed input as the fixed migration
failure before offering a ready plan; execution revalidates the staged bytes to detect
mutation. The presence of the immutable installed source default does not occupy or
disable the roaming seed destination. Inspection
performs no parent, home, drive, registry, recursive,
or current-directory search. Its immutable plan privately retains the reconstructed
development root and destination authority and publicly reports `nothing_to_migrate`,
`ready`, or `destination_occupied`, plus booleans for the four source classes and exact
per-class eligibility/conflict outcomes. Its
`repr` and result projections contain no raw paths.

`STATE-025` Phase 5.4D is the sole production invoker and owns detection presentation,
the explicit consent action, and the call to execution. Phase 5.4B exposes inspection
and execution APIs but changes neither frozen 5.3D startup nor the Shell. Inspection
performs zero copies. Execution accepts only a freshly reconstructed `ready` plan; its
invocation is the consent boundary and 5.4B contains no GUI, prompt, implicit-consent
default, or policy inference.

`STATE-026` One plan authorizes zero or one execution attempt. A valid receipt makes the
whole import `already_migrated`. Otherwise each class is independently eligible only
when its source exists and its destination is absent/empty: database and settings files
must be absent; reports destination must contain no entry; source override must be
absent. Occupied classes are reported and never merged or overwritten; remaining
eligible classes form one plan. No eligible source returns `nothing_to_migrate` or
`destination_occupied` according to whether any source was blocked. Source mutation
after inspection, malformed/non-regular source files, reparse points, permission
failure, or an incomplete prior staging directory returns a fixed migration failure.

`STATE-027` Execution creates exclusive sibling staging directories in local and roaming
destination roots, each named `.development-migration-<operation-id>`. It copies present
regular sources without following reparse points, validates copied settings through the
settings loader, validates the copied database with SQLite `quick_check` and the bounded
rules in Section 10, validates a source seed by calling the existing Scout
`load_sources_config` on the staged bytes, and copies report files only when each is a
regular non-reparse
`.html` file directly below the reports source. Before the first publication it atomically
publishes `data/development-migration-v1.pending.json`, containing the operation ID and
SHA-256 of every staged file. The pending journal is canonical JSON with exact ordered
fields `schema`, `schema_version`, `operation_id`, and `artifacts`; literals are
`pastila-scout-development-migration-pending` and `1`; `artifacts` is ordered by
`destination_kind` then `relative_path` and each entry contains exactly those two fields
plus `sha256`. Destination kind is `local` or `roaming`; relative paths pass
the safety rules in `STATE-012`; SHA-256 is 64 lowercase hexadecimal characters. It publishes each artifact
by atomic rename within its own
destination volume and publishes the receipt last. The source is never changed or
deleted. Any caught pre-receipt failure removes only hash-identical files recorded by the
journal, both staging directories, and the journal. On the next invocation after process
interruption, a valid pending journal causes the same hash-checked cleanup before inspection;
a malformed journal or hash mismatch raises migration failure without deleting anything.
Partial destination is never success.

`STATE-028` The receipt is canonical JSON, UTF-8 without BOM and one LF, at
`data/development-migration-v1.json`, with exact fields `schema`, `schema_version`,
`operation_id`, `database_copied`, `reports_copied`, `settings_copied`,
`source_override_seeded`, and `completed_at`. Literals are
`pastila-scout-development-migration`, `1`; operation ID is
32 lowercase hexadecimal characters; database/settings/source-seed values are booleans;
`reports_copied` is a non-negative integer; timestamp is
UTC `YYYY-MM-DDTHH:MM:SSZ`. A valid receipt makes every later inspection and execution
return `already_migrated` without reading the source. A malformed receipt is failure,
not success. Cross-volume source copying is supported because publication occurs only
inside the destination volume.

## 10. SQLite schema migration

`STATE-029` State owns the database location and the startup-time schema migration gate,
not ordinary database behavior. `TARGET_SCHEMA_VERSION = 1` and
`MIGRATIONS = {0: _migrate_0_to_1}` exist only in `migrations.py`. Version 0 exact
recognition and version 1 target structure are the tables, columns, constraints, indexes,
foreign keys, and absence of triggers frozen in Productization V12. This specification
does not restate or redefine normal SQLite schema, connection, transaction, integrity,
or `user_version` authority. `_migrate_0_to_1`
changes only `PRAGMA user_version` inside the migration transaction.

`STATE-030` `_migrate_windows_database_v1` is the Productization-authorized startup
schema gate and receives one database path and backup directory. Its bounded exception
to ordinary database ownership is only the exact backup/version transition sequence
frozen in Productization V12: it acquires one process-local module mutex, obtains SQLite
exclusive locking, runs `quick_check`, validates current version/structure, requires free space
of twice database size plus 100 MiB, creates and validates
`news_monitor-v<source>-<YYYYMMDDTHHMMSSZ>-<sha256>.db` through SQLite backup, starts
`BEGIN EXCLUSIVE`, applies every contiguous registry step, validates
`foreign_key_check`, target structure, and `quick_check`, then commits. Any failure before
commit leaves the original unchanged; transaction failure rolls back. The validated
backup remains. Version 1 exact target returns `current` without backup; version greater
than 1 or malformed/unknown version 0 returns `unsupported` without mutation or backup.

`STATE-031` Repeated invocation after successful migration returns `current` and creates
no second backup. Missing registry steps, integrity, space, lock, access, or backup
validation failures raise `_WindowsStateMigrationError` with exact message
`Windows application state migration failed.` `KeyboardInterrupt`, `SystemExit`,
`GeneratorExit`, `MemoryError`, and programming errors propagate unchanged.

## 11. Exact migration APIs

`STATE-032` `migrations.py` defines only:

```python
class DevelopmentMigrationPlanV1: ...
class DevelopmentMigrationResultV1: ...
class DatabaseMigrationResultV1: ...

def _inspect_development_state_migration_v1(
    *, development_root: Path, destination: WindowsApplicationPathsV1
) -> DevelopmentMigrationPlanV1: ...

def _execute_development_state_migration_v1(
    *, plan: DevelopmentMigrationPlanV1
) -> DevelopmentMigrationResultV1: ...

def _migrate_windows_database_v1(
    *, database_path: Path, backup_directory: Path
) -> DatabaseMigrationResultV1: ...
```

Plan statuses are `nothing_to_migrate`, `ready`, `destination_occupied`,
`already_migrated`. Execution statuses add `completed`. Database statuses
are `current`, `migrated`, `unsupported`. Results contain status plus finite copied counts
and a source-seeded boolean, or source/target integer versions; they contain no paths,
connections, exceptions, or
input objects. There is no Boolean migration result.

## 12. Object and error safety

`STATE-033` Every new value type is exact-type, immutable, slotted, final by
`__init_subclass__` rejection, structurally sealed, and reconstructed field-by-field into
a fresh value. Construction and reconstruction use the normative validation order.
`copy.copy` and `copy.deepcopy` return independently reconstructed equal values. Equality
accepts only the exact type. `repr` exposes enums, booleans, counts, and versions but
redacts every path and user string. Pickling and subclassing raise `TypeError`. Mutation
or copied-invalid instances are rejected by every consumer.

`STATE-034` `errors.py` defines exact private hierarchy:

```text
_WindowsStateError
|-- _WindowsStatePathError
|-- _WindowsStateSettingsError
`-- _WindowsStateMigrationError
```

All are final, have no public fields, and accept no caller message. Expected converted
failures set `__cause__ is None`, `__context__ is None`, retain no protected input/path/
settings/source/connection object, and are raised outside active exception handlers after
protected locals are deleted. `__init__.py` exports nothing through `__all__`.

## 13. Passivity, concurrency, and exclusions

`STATE-035` Importing any 5.4B module performs no environment read, path resolution,
filesystem probe or creation, settings I/O, migration, SQLite connection, GUI action,
network access, logging configuration, global service composition, or thread creation.

`STATE-036` Settings have one in-process writer and no cross-process lock. Atomic replace
prevents torn files but concurrent processes are unsupported and produce the ordinary
fixed settings failure. Database migration has the one process-local mutex plus SQLite
exclusive locking; it never claims a distributed application lock. Development import
has one explicit UI invocation and exclusive destination creation. No new executor,
worker, queue, retry loop, or background migration exists.

`STATE-037` The state implementation contains no installer selection, file installation,
shortcut, uninstall, registry, elevation, Authenticode, PyInstaller, Inno Setup, update
check, download, Protocol transition, Persistence schema duplication, trust verification,
restart/handoff, source-bundle activation, or release behavior.

`STATE-038` Cache and logs receive deterministic locations only. Cache is disposable and
has no 5.4 retention API. Logs have no file-handler or retention API in 5.4. Operating-
system temporary storage is not application state and is not exposed by the path model.

## 14. Startup compatibility and implementation sufficiency

`STATE-039` Frozen 5.3D remains byte-identical. Phase 5.4B implements passive private
state APIs only. Frozen Productization V12 makes Phase 5.4D the later composition
milestone authorized to edit the exact startup, Shell, Editor, Scout, poller, resource,
and six test paths listed there. Phase 5.4C first specifies their injection, source
selection, and migration presentation. Until 5.4D, current development composition
remains unchanged. No hidden 5.4B production or test path is required.

`STATE-040` Responsibility is closed: `paths.py` owns path values/resolution/creation;
`settings.py` owns the settings value and JSON I/O; `migrations.py` owns development
copy and SQLite version migration; `errors.py` owns safe failures; `__init__.py` owns an
empty private package surface; `default-settings-v1.json` owns canonical defaults. The
three tests respectively own paths/passivity/scope, settings/object/error safety, and
migration/conflict/SQLite behavior.

## 15. Verification matrix

Each verification is one material test obligation. No row is a grouped placeholder.

| Verification | Requirement | Material proof |
| --- | --- | --- |
| `STATE-V001` | `STATE-001` | Assert prerequisite, path, verdict, subject, and tag literals. |
| `STATE-V002` | `STATE-002` | Derive exact 5.4B delta and reject any hidden path. |
| `STATE-V003` | `STATE-003` | Assert downstream prerequisite and ownership exclusions. |
| `STATE-V004` | `STATE-004` | Prove development paths and CLI bytes remain unchanged. |
| `STATE-V005` | `STATE-005` | Static ownership/import exclusion audit. |
| `STATE-V006` | `STATE-006` | Assert version authorities remain distinct. |
| `STATE-V007` | `STATE-007` | Assert every inventory path and lifecycle classification. |
| `STATE-V008` | `STATE-008` | Reject excluded classes in path/settings APIs. |
| `STATE-V009` | `STATE-009` | Exact installed-root mapping test. |
| `STATE-V010` | `STATE-010` | Installed/development input matrix; no cwd/home inference. |
| `STATE-V011` | `STATE-011` | Missing/malformed environment failure matrix. |
| `STATE-V012` | `STATE-012` | Traversal, device, UNC, ADS, reserved, Unicode, and reparse cases. |
| `STATE-V013` | `STATE-013` | Assert every exact installed and development path. |
| `STATE-V014` | `STATE-014` | Exact fields, modes, and receipt locations. |
| `STATE-V015` | `STATE-015` | Creation order, idempotence, no-file, and partial-failure proof. |
| `STATE-V016` | `STATE-016` | Signature and absence-of-dispatch/global-cache audit. |
| `STATE-V017` | `STATE-017` | Exact default bytes and round-trip equality. |
| `STATE-V018` | `STATE-018` | Field-order/type/range/enum/path adversarial matrix. |
| `STATE-V019` | `STATE-019` | Size, encoding, duplicate, unknown, missing, and non-finite rejection. |
| `STATE-V020` | `STATE-020` | Sole-resource defaults, absent/default, and every load failure branch. |
| `STATE-V021` | `STATE-021` | Atomic save, backup/restore, temporary cleanup, and no-fsync spies. |
| `STATE-V022` | `STATE-022` | Exact messages and zero sensitive projection. |
| `STATE-V023` | `STATE-023` | Prove migration exclusions and source preservation. |
| `STATE-V024` | `STATE-024` | Exact-source inspection and no-search spies. |
| `STATE-V025` | `STATE-025` | Inspection passivity, consent-boundary API, and frozen-startup hash. |
| `STATE-V026` | `STATE-026` | Full source/destination/conflict/mutation matrix. |
| `STATE-V027` | `STATE-027` | Failure injection at every copy/validation/publication boundary. |
| `STATE-V028` | `STATE-028` | Exact receipt bytes, malformed receipt, and repeated invocation. |
| `STATE-V029` | `STATE-029` | Exact registry and exhaustive version-0/target schema fixtures. |
| `STATE-V030` | `STATE-030` | Lock, integrity, space, backup, transaction, and rollback matrix. |
| `STATE-V031` | `STATE-031` | Idempotence, fixed failure, and process-control propagation. |
| `STATE-V032` | `STATE-032` | Exact signatures/statuses and result redaction. |
| `STATE-V033` | `STATE-033` | Mutation, copy, deepcopy, equality, repr, pickle, subclass tests. |
| `STATE-V034` | `STATE-034` | Hierarchy, finality, raise-outside-handler, traceback-object audit. |
| `STATE-V035` | `STATE-035` | Fresh-process import traps and output silence. |
| `STATE-V036` | `STATE-036` | Lock/thread/executor/queue ownership spies. |
| `STATE-V037` | `STATE-037` | Static packaging/updater/trust/source ownership exclusion audit. |
| `STATE-V038` | `STATE-038` | Assert no cache/log/temp mutation or retention API. |
| `STATE-V039` | `STATE-039` | Frozen 5.3D hashes and no consumer-path delta. |
| `STATE-V040` | `STATE-040` | One responsibility per exact implementation path. |
| `STATE-V041` | `STATE-041` | Prove tag-pair history allows unrelated future work. |
| `STATE-V042` | `STATE-042` | Execute the exact focused and repository-wide gates. |
| `STATE-V043` | `STATE-043` | Independent two-implementation comparison. |
| `STATE-V044` | `STATE-044` | Scope and frozen/read-only byte audit. |

`STATE-041` Implementation integrity uses both immutable prerequisite tags, including
the Productization V12 tag, and derives the exact phase delta from immutable tag
`phase-5.4a-windows-state-spec-v1-ready` to the future verified 5.4B tag. Before that tag
exists, it derives the exact worktree delta from the immutable prerequisite. Afterward it
uses the immutable tag pair and therefore permits unrelated future work. Frozen
authorities are checked by historical blobs; maintainable descendants are never pinned
to future-current worktree bytes.

`STATE-042` Phase 5.4B focused tests run only the three roadmap test files. Full offline
tests, Ruff, Black check, compileall, pip check, `git diff --check`, import passivity,
exact phase-local scope, frozen hashes, and zero live network/provider activity are
mandatory implementation gates.

## 16. Readiness finding

`STATE-043` Two independent implementations following this document derive identical
roots, layout, path APIs, settings bytes and I/O, migration sources and triggers,
conflict/atomicity/idempotence rules, SQLite boundary, failures, tests, and exact files.
Any material divergence is a specification defect.

`STATE-044` The specification changes no production, test, packaging, updater, trust,
release, Protocol, Persistence, Productization, or frozen desktop file.

## 17. Productization V12 compatibility closure

`STATE-045` The structural surface is sufficient for Phase 5.4C and the exact frozen
Phase 5.4D consumers without a 5.4B redesign: the path value exposes immutable Scout
application configuration, immutable bundled sources, mutable roaming override,
settings defaults/settings, database, reports, cache, logs, and migration metadata;
settings APIs accept the sole defaults resource; migration APIs expose passive detection
and explicit-consent execution. Phase 5.4D therefore injects installed or exact
module-relative development paths through `state_composition.py`. Its source selector
can enforce valid roaming override, then a later valid active signed bundle when that
authority exists, then immutable bundled default; a present malformed roaming override
blocks safely and never falls through. Phase 5.4B neither implements that selector nor
anticipates Phase 5.9B bundle activation.

| Verification | Requirement | Material proof |
| --- | --- | --- |
| `STATE-V045` | `STATE-045` | Two-implementer audit proves 5.4C/5.4D can consume every required surface without changing 5.4B or violating source precedence. |
