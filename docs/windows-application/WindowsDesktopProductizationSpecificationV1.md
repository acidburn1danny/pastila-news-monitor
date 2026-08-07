# Windows Desktop Productization Specification V1

Status: implementation-ready specification. This document is normative for Phase 5.
It defines architecture only; it does not authorize implementation.

Revision 12 is the roadmap authority for every unfrozen milestone beginning with Phase
5.4A. Its maintenance verdict, commit subject, and annotated tag are
`PHASE_5_WINDOWS_DESKTOP_PRODUCTIZATION_SPECIFICATION_V12_WINDOWS_STATE_CONSUMPTION_ROADMAP_READY_FOR_FREEZE`,
`Close Windows state consumption roadmap`, and
`phase-5-windows-desktop-productization-spec-v12-windows-state-consumption-roadmap-ready`.
Completed identities and prerequisites through Phase 5.3D remain unchanged.

## 1. Baseline and scope

The authority baseline is `phase-4.3-editor-cli-run-r6-verified` at
`cf36d0fcd87186a69c9c0cbca79fcb3011111420`. The Windows product is additive.
Every frozen Scout, Editor, provider-neutral, CLI, serialization, export, SQLite,
and report contract remains unchanged unless a later bounded specification explicitly
authorizes a new public facade.

Windows update implementation additionally consumes the frozen specifications at the
current freeze-review baseline: Windows Update Protocol V6, SHA-256
`9E4615576785062A5C902CA8BBA663EE1F9BF1112F98ED881F7620B0CAD568ED`, and Windows
Update Persistence Format V6, SHA-256
`05CF922678BD9DCD4C6837B00B8896CA7A014D839C84290A7B5D70F54158DFF6`.
Those documents exclusively own their declared runtime and wire/store semantics.

The product is **Pastila Scout Desktop**, initially Windows x64 only. It is one
installed, windowed desktop executable plus the existing `pastila-scout` console
entry point. The desktop contains a single main window with a persistent left
navigation sidebar and six pages: Scout, Editor, Reports, Settings, Help, and Update
Center. Modal dialogs are used only for confirmation, credential guidance, and
terminal errors. There are no provider-specific pages and no shell-command backend.

## 2. Repository grounding

Repository inspection establishes the following facts.

- There is no GUI module, GUI entry point, GUI dependency, frozen GUI executable,
  packaging recipe, installer, updater, release workflow, or Windows productization
  experiment. Searches found no Tkinter, Qt, PyInstaller, Nuitka, cx_Freeze,
  Briefcase, MSIX, WiX, Inno Setup, or NSIS ownership.
- `pyproject.toml` defines Python `>=3.14`, package version `0.1.0`, setuptools,
  and the only entry point, `pastila-scout = pastila_scout.cli:main`.
- `src/pastila_scout/cli.py` owns the root argparse tree. It exposes polling,
  validation, status, queue, events, reporting/export commands, provider-run, and the
  verified `editor-run`; existing CLI defaults are project-relative paths.
- `poll_once()` is an in-process Scout orchestration API and returns `PollResult`.
  It owns source polling and SQLite persistence. Configuration loading and validation
  are in `config.py`; SQLite ownership is in `database.py`.
- Scout reports are produced by the `reporting` package. Ranking and verification
  currently write JSON plus plain text, not HTML. No production HTML-report API was
  found. Phase 5.2 therefore requires an additive, separately specified HTML report
  application service; GUI code must not render domain reports itself.
- `editor-run` is a thin CLI adapter. The verified Editor application boundary is
  `EditorApplicationRequestV1` to `EditorApplicationCoordinatorV1.execute()` and its
  public `EditorApplicationResultV1`. Command-time composition is currently private
  (`_compose_editor_application_runtime_v1()` and the CLI composition adapter).
- `config/config.yaml` is development-only Scout application configuration owned by
  `config.py`; it owns polling, matching, AI, cache, scoring, and the reference to a
  source-definition file. `config/sources.yaml` is the development source-definition
  document whose YAML parsing, validation, categories, and source semantics are also
  owned by `config.py`. Neither file is the Windows application `settings.json` schema.
- Credentials are not configuration fields. OpenAI obtains `OPENAI_API_KEY` at
  command-time provider composition. Ollama owns a local HTTP client and configurable
  model. Credentials and clients never enter GUI models, logs, settings exports, or
  updater state.
- Logging currently has one stderr console handler and no file rotation. Mutable
  defaults include `data/news_monitor.db`, `data/ai_cache`, and `reports/`.
- `EditorAtomicExporterV1` has a Windows native, no-replace, write-through boundary.
  This does not make it a general report or updater exporter.
- Tests use pytest and offline fakes; live Ollama is environment-gated. No packaging
  or GUI tests exist.

No current component owns Windows paths, desktop lifecycle, settings, version
projection, packaging, installation, updates, or release signing. Those are the gaps
closed by this specification.

## 3. Recorded baseline hashes

These uppercase SHA-256 values were captured before this document was created.

| File | SHA-256 |
| --- | --- |
| `pyproject.toml` | `7306FDA085396F0A19C3B028840B4D49599AE2AE104727E6E2423CE01592B36F` |
| `src/pastila_scout/__init__.py` | `6D6E8661ED5D34D228E506FC44D563E650C7B17DB0C1627A7D9FCD94FF674937` |
| `src/pastila_scout/cli.py` | `B03CB952E45590B674DCE43B370D8FFB66388C3AA9F4528129AF36DCBC736A0C` |
| `src/pastila_scout/config.py` | `8DB3A5BEB616CCD403D93E8040A455C85601F009404467AC8E44FF2644BBD6D8` |
| `src/pastila_scout/database.py` | `BB77457369C07735AAB38F3FD32676C6F6624A797688FA6A0AD9293A555F7E64` |
| `src/pastila_scout/logging_config.py` | `589EF60903A6C108DA8F4623FC7B174101AC9AEC2C253C891F19524A073295A5` |
| `src/pastila_scout/poller.py` | `18447240C6D8F39AED735C18AEFAC7A2AFFD9E6F6F726B1CB1C6E9F82D5A3743` |
| `src/pastila_scout/editor_cli_run_v1/command.py` | `31E5032BC8BB97C778A400DA759E47BEC415E6F8C9B58CE5025CA18BF8CA8940` |
| `src/pastila_scout/editor_cli_run_v1/composition.py` | `2604618EE99A0B8A5628E4CA3FF4F18A41C0B9FED100FACD1A5AC43C569FD1C4` |
| `src/pastila_scout/editor_application_v1/application.py` | `B49056A11E5834FB18C70679D6B4970C0BDBCB5DFC516E87EA31AD0F16CA409C` |
| `src/pastila_scout/editor_application_v1/runtime_composition.py` | `DBD580E5188E227D13F280FA8F37888ADE4E2ED0E447A4A61CF67B1A4564B92C` |
| `src/pastila_scout/editor_application_v1/serialization.py` | `8D9A56A74D02CA3CF751D717C2AAD55922C0B8D62582A58A4D57D0025DCEDB06` |
| `src/pastila_scout/editor_application_v1/export.py` | `93C099F78C5F46117F02F1BA205091B226B5F09C901216B20BF45D76ED70CA2C` |
| `config/config.yaml` | `A2FFBB2F310F3489329F22C8482CC2810469AA7A70F1018D9FEE0BB0FE7CA25B` |
| `config/sources.yaml` | `C57900E1567A39C03228E5FF783FA5AE7959A247D65ABADF1451B2A9BFB9A4DF` |
| `tests/test_cli.py` | `A37E43A8021115454FF346DC68D135D65586AB1CEE7E6A7DD7A682FD0ABE6161` |
| `tests/test_config.py` | `5DB136CD1FA3B3CFB1768453C8BBF424C3304D391EB9721126FB6EB193BD6F01` |
| `tests/test_editor_cli_run_v1.py` | `611782835ACA57850350D3FEF801BBBB7412CEEDDF6893BB315CE1949C40F868` |
| `tests/test_editor_application_v1.py` | `997460CA53A9607E89081BE926C4579924E652D7B165434E126F4CCA7B0B5265` |

There are no existing GUI files, version module, build files, installer scripts, or
packaging tests to hash.

## 4. GUI framework and window architecture

The only framework is Python's stdlib **Tkinter with ttk**. PySide6/PyQt add a large
Qt runtime, licensing/distribution review, and a second event ecosystem; WinUI bridges
add native integration complexity; CustomTkinter adds a third-party theme layer without
solving a repository requirement. Tkinter is already distributed with standard Windows
CPython, has stable PyInstaller collection, native menus, adequate accessibility hooks,
scaling support, deterministic widget tests, and the smallest maintenance surface.
Python 3.14 and the chosen PyInstaller version are hard packaging gates, not assumptions:
Phase 5.5E cannot freeze and Phase 5.5F cannot pass until a pinned combination builds and
starts on Windows CI.

The root uses `ttk.Frame` pages selected by a left `ttk.Treeview`-style navigation
control. The native menu bar contains File, View, and Help; Help contains About and
Check for Updates. Pages are instantiated after the root exists but remain passive.
Phase 5.1D creates the About surface without a version value; Phase 5.5D is the sole phase
that wires its version consumer after projection verification.
One controller owns page state; views never import database, providers, runtime
composition, cryptography, or HTTP modules. DPI awareness is set once before root
creation; ttk styles use Windows scaling and system colors. Keyboard traversal,
accelerators, focus indication, readable names, and 200% DPI are acceptance gates.

The Scout page retains the Romanian product layout:

- top controls: `PERIOADA`, `CATEGORIA`;
- central primary action: `CAUTĂ`;
- progress bar and status;
- `REZULTATE`, numeric summary, failed-source panel, and HTML-report action;
- footer containing executed period/category and final state.

The exact Romanian resource keys and default translations are normative:

1. `Selectați perioada și categoria, apoi apăsați „CAUTĂ”.`
2. `Pastila citește ziarele…`
3. `verifică și compară…`
4. `scrie raportul pentru șefu’…`
5. `Gata, șefu’! Raportul este pregătit.`

They live in an immutable UTF-8 localization resource rather than widget code. Phase 5
ships Romanian only; changing displayed text requires a resource revision, not domain
logic. Status rotation is presentation-only and never claims a backend stage completed.

The Editor page loads the four validated inputs used by `editor-run`, chooses exactly
`openai` or `ollama`, model, timeout, output path, and no-replace policy, then executes:

```text
validated GUI values
  -> public Editor desktop application facade
  -> application runtime composition
  -> EditorApplicationRequestV1
  -> EditorApplicationCoordinatorV1.execute(request=...)
  -> EditorApplicationResultV1 public projection
```

The facade is the only new public application-service boundary needed by the GUI. It
wraps the currently private composition root without exporting that factory, runtime
handles, provider clients, serializers, exporters, or connections. It shares request
construction behavior with the CLI through a separately specified neutral builder; it
does not call `run_editor_command()` or parse CLI output.

## 5. Task and backend boundaries

Persistent-state names appearing in this section are non-normative task/UI context.
Frozen Persistence V6 owns their schemas and storage behavior; frozen Protocol V6 owns
restart, recovery, errors, and timeouts. Section 14 owns only path binding and presentation.

There is exactly one application-owned `DesktopTaskController`. It owns two executors:

- `application_executor`, one `ThreadPoolExecutor(max_workers=1)`, owns Scout runs,
  Editor runs, and report generation. It permits one active or queued application job;
  another run is rejected as duplicate until the first reaches a terminal state.
- `update_executor`, one `ThreadPoolExecutor(max_workers=1)`, owns application/source
  update checks and downloads. It permits one active or queued update operation. It
  never runs Scout, Editor, or report work and therefore cannot delay those jobs.

No view creates threads. Backend-owned internal concurrency, such as Scout's bounded
source polling, remains owned by that frozen backend and is not a desktop executor.

The controller state machine is `idle -> submitted -> running -> cancelling ->
completed|failed|cancelled -> idle`. A task receives an immutable request and one
existing cancellation token where the backend supports it. Polling receives cancellation
only after a separately specified Scout facade can project it; until then Scout cancel is
disabled rather than simulated. Results and finite safe errors enter a thread-safe queue.
The Tk thread drains it with `root.after(50, ...)`; workers never touch widgets. Progress
is stage-level and monotonic, never fabricated from elapsed time.

Update-state models and persistence are owned by frozen Persistence V6; retention,
transitions, restart, and failure classification are owned by frozen Protocol V6. This
task boundary consumes only their immutable projections.
The required facades are:

- `ScoutDesktopService.run(request) -> ScoutDesktopRunResult`: validates period and
  category, invokes the verified orchestration in process, persists the existing SQLite
  state, invokes a new report service, and projects counts/failures/report reference.
- `EditorDesktopService.run(request) -> EditorApplicationResultV1`: performs the public
  chain above exactly once.
- `ReportCatalogService.list/open/reveal`: returns immutable report descriptors and uses
  Windows shell opening only after resolving a regular file below the reports root.
  Corrupt/missing entries return finite categories; GUI never parses private reports.

The new HTML report service consumes a public Scout result and writes escaped static
HTML. It owns HTML; it may not reinterpret scores or execute scripts, remote resources,
or inline untrusted markup. Report listing reads its small sidecar metadata, not report
HTML. Existing report writers remain unchanged.

## 6. Windows filesystem authority

`WindowsApplicationPathsV1` is the sole path authority. In installed mode:

| Ownership | Exact location |
| --- | --- |
| Read-only binaries/resources/keys/defaults | `%LOCALAPPDATA%\Programs\PastilaScout\app\` |
| immutable Scout application configuration | `%LOCALAPPDATA%\Programs\PastilaScout\app\config\config.yaml` |
| immutable bundled source definitions | `%LOCALAPPDATA%\Programs\PastilaScout\app\config\sources.yaml` |
| SQLite database | `%LOCALAPPDATA%\PastilaScout\data\news_monitor.db` |
| reports | `%LOCALAPPDATA%\PastilaScout\reports\` |
| cache | `%LOCALAPPDATA%\PastilaScout\cache\` |
| logs | `%LOCALAPPDATA%\PastilaScout\logs\` |
| verified update downloads/sequence state | `%LOCALAPPDATA%\PastilaScout\updates\` |
| installer handoff and post-update health | `%LOCALAPPDATA%\PastilaScout\update-state\` |
| mutable trust and recovery receipts | `%LOCALAPPDATA%\PastilaScout\trust\` |
| verified source bundles/state/audit | `%LOCALAPPDATA%\PastilaScout\source-bundles\` |
| settings and user source override | `%APPDATA%\PastilaScout\` |

The per-user installer uses `%LOCALAPPDATA%\Programs`; Program Files is not used and no
elevation is requested. Application files remain read-only by policy even though the
user owns the directory. No mutable file is written beside the executable.

Development mode is selected only by a non-frozen process plus an explicit injected
mode in tests/dev entry point; it maps to repository `config/`, `data/`, and `reports/`.
Installed mode is determined by `sys.frozen` plus a bundled marker. Tests inject a path
authority rooted in `tmp_path`. No current-working-directory inference occurs in the
installed product. All paths are `pathlib.Path`, passed to wide-character Windows APIs,
and tested with non-ASCII usernames and long paths. Creation rejects reparse points for
security-sensitive update directories. Permission failure maps to configuration/storage
failure and never falls back to the install directory.

On first installed launch, the Phase 5.4D integration offers an explicit migration
screen. The user selects one development root; there is no detection scan. It offers
only the database, reports, existing development `config/settings.json`, and validated
`config/sources.yaml`. It shows source and destination, never deletes the source,
validates before activation, records a receipt, and is skipped if destination state
exists. `config/config.yaml` is development-only and never migrates, copies, transforms,
or seeds installed state. There is no silent cwd migration.

## 7. Configuration ownership and precedence

| Item | Class | Owner/location |
| --- | --- | --- |
| Scout application configuration | bundled immutable installed default; development repository file | installed `app\config\config.yaml`; development `config/config.yaml` |
| default sources | bundled immutable default | installed `app\config\sources.yaml` |
| trusted source set | remotely updateable trusted data | local data bundle store |
| source edits | user-editable override | roaming `sources.override.yaml` |
| Desktop preferences/log level | user-editable application settings | roaming `settings.json`; JSON schema distinct from Scout YAML |
| Editor profile/context/generation | user-selected validated documents | user paths; recent references only in settings |
| provider/model/output defaults | user-editable settings | roaming settings |
| update channel | bundled immutable | `stable`; not user-changeable in Phase 5 |
| update preferences | user-editable settings | roaming settings |
| caches/update receipts | generated runtime state | local cache/update roots |
| OpenAI key | secret credential | process environment only |
| Ollama endpoint | application provider composition | fixed local verified default; not source data |

Every format has an exact schema version, UTF-8 without BOM, duplicate-key rejection,
bounded size, NFC strings, and no unknown fields. Immutable audit/evidence records use
atomic exclusive no-replace publication; mutable single-authority settings/state use
atomic replace-with-backup publication. No caller selects between them. Precedence is validated user override, then active
verified remote source bundle, then bundled default. Overrides identify sources by
stable ID and may only change fields allowed by their schema. A corrupt user file is
quarantined by rename only with consent, reported visibly, and never silently ignored.
Application updates never overwrite roaming files.

### 7.1 Windows-state consumption and development migration closure

Phase 5.4B is a passive producer of private path, settings, and migration APIs. It does
not modify frozen startup or composition. Phase 5.4C specifies their sole initial
production consumption contract; Phase 5.4D implements it before trust bootstrap,
packaging, or installation work begins.

Installed startup resolves `WindowsApplicationPathsV1`, creates only its authorized
mutable directories, loads `settings.json`, offers the explicit first-launch migration,
selects one source-definition path, and then composes the existing facade. Development
startup uses an explicit repository development root supplied by the development entry
boundary and resolves the existing `config/config.yaml`, `config/sources.yaml`,
`data/news_monitor.db`, and `reports/` paths. Development mode never offers or executes
migration. Installed mode never falls back to those development-relative paths.
The non-frozen GUI entrypoint supplies exactly
`Path(__file__).resolve().parents[3]` as its development root and validates the expected
repository layout; failure is terminal and never falls back to the current directory.
Installed mode requires `sys.frozen` plus the bundled `default-settings-v1.json` marker.

`desktop_v1/state_composition.py` is the sole new integration boundary. The entrypoint
calls its one private composition function once while the root is withdrawn and supplies
only explicit environment/frozen/development-root inputs plus a synchronous migration-
consent callback. That function resolves state, performs the authorized initialization
and optional migration, selects source configuration, and calls
`_compose_desktop_application_facade_v1` exactly once with keyword-only `config_path`,
`sources_path`, `database_path`, and `report_directory` concrete paths. It returns the
facade plus an immutable safe projection of application settings for view construction.
The entrypoint retains both for the Shell lifetime. No global registry, service locator,
singleton, lazy discovery, second composer, or per-command resolution exists.
The state boundary runs at the existing single composer position: after root withdrawal
and before controller/view construction. In installed mode with an eligible migration
plan, the entrypoint uses a modal directory chooser and confirmation owned by 5.4D; a
cancel or refusal continues with untouched installed state, while a migration failure
terminates startup through the existing finite safe presentation. No path or configuration
content enters the failure message.

The desktop Scout adapter retains both injected Scout paths and passes them to an
additive `poll_once(..., sources_path=...)` keyword. `poll_once` delegates their parsing
to `load_configuration`; it owns no precedence or Windows path selection. The view
receives only the validated Scout period/category and Editor profile/context/generation/
provider/model/timeout/output defaults that already correspond to its fields. Logging,
update preferences, and a future settings editor remain owned by their later milestones.

The installed immutable Scout application configuration is
`<installation-root>\config\config.yaml`; it remains parsed and validated only by
`config.py`. Its `sources_file` value does not choose runtime precedence. The integration
passes the independently selected source-definition path through the desktop Scout
adapter and `poll_once` to the existing `load_configuration(application_path,
sources_path=...)` authority. This additive injected path changes no Scout schema,
category, polling, provider, retry, or persistence semantics.
The installed file is a release-bundled immutable resource derived during packaging;
first-launch migration never creates or replaces it.

Source selection is exact: a present roaming `sources.override.yaml` is validated by
the existing Scout source validator and wins; otherwise a valid active signed bundle
wins after Phase 5.9B; otherwise the bundled immutable `config\sources.yaml` wins. Before
Phase 5.9B there is no active-bundle candidate. A malformed, inaccessible, non-regular,
or reparse user override blocks Scout composition with a finite safe error and never
falls through. Signed-bundle validation, activation, and recovery remain Phase 5.9B
ownership.

Development migration treats `config/sources.yaml` as a source-only YAML document. If
it is present, Scout validation succeeds, and roaming `sources.override.yaml` is absent,
explicit confirmed migration copies its exact bytes without transformation. If the
override exists, migration does not overwrite or merge it. An absent source is a no-op;
a malformed source fails before publication; a repeated completed migration is an
idempotent no-op. `config/config.yaml` is never eligible. Existing development
`config/settings.json`, when present, is application settings and migrates only through
the Windows settings validator to an absent roaming `settings.json`. Database and report
migration retain Section 6 ownership. No source/config/settings file is read during
development-mode migration because that operation is disabled there.

The development source/configuration migration matrix is exact:

| Mode/source/destination | Result |
| --- | --- |
| development mode | migration unavailable; existing explicit development paths remain active |
| installed mode, selected source root absent | finite no-source result; no mutation |
| `config/config.yaml` present in either mode | ignored by migration; never copied or transformed |
| `config/sources.yaml` absent, override absent | no override is created; bundled default remains selected |
| valid `config/sources.yaml`, override absent | explicit consent seeds exact validated bytes as `sources.override.yaml` |
| valid `config/sources.yaml`, override present | override wins; no copy, merge, or overwrite |
| malformed, inaccessible, or reparse `config/sources.yaml` | safe failure before publication |
| installed immutable default present | remains read-only and is never a migration destination |
| valid `config/settings.json`, roaming settings absent | explicit consent publishes validated canonical settings |
| development settings absent | migration creates no settings file |
| roaming settings present | no settings copy, merge, or overwrite |
| valid completed receipt | deterministic no-op without source reads |

## 8. Source-update architecture

Source product behavior, cryptographic content, and its Productization-domain persistence
remain defined here and in Sections 14.1 through 14.3. They are not frozen update-protocol
artifacts and cannot create a `PersistenceProtocolResultV1`.

The model is **Hybrid**: application code/defaults update with the installer; source
definitions update as signed, non-executable bundles. One bundle consists of three
separate files, never an archive:

- `sources-bundle-manifest-v1.json`;
- `sources.yaml`;
- `sources-bundle-manifest-v1.json.sig`.

The manifest is strict RFC 8785 JCS JSON and contains exactly these fields:

| Field | Exact type and rule |
| --- | --- |
| `schema` | string, exactly `pastila-scout-sources-bundle` |
| `schema_version` | integer, exactly `1` |
| `bundle_version` | stable SemVer string without build metadata |
| `sequence` | integer, `1..9223372036854775807` |
| `published_at` | canonical UTC RFC 3339 string |
| `minimum_application_version` | stable SemVer string |
| `maximum_application_version` | stable SemVer string or JSON `null` |
| `payload_filename` | string, exactly `sources.yaml` |
| `payload_size` | integer, `1..524288` |
| `payload_sha256` | 64 lowercase hexadecimal characters |
| `source_count` | integer, `0..1000` |
| `key_id` | constrained release-key identifier |
| `signature_algorithm` | string, exactly `Ed25519` |

No unknown field is accepted. The detached signature covers the exact JCS manifest
bytes; the manifest covers the exact YAML payload bytes. Field order in source JSON is
irrelevant because JCS is authoritative. The signature file uses Section 10's strict
detached-signature schema. The signature URL is the manifest URL plus `.sig`; the payload
URL is `payload_filename` resolved only as a sibling of that fixed-host manifest URL,
with no other relative segments. Source sequence acceptance uses Section 10's independent
idempotent pair algorithm.

`source_bundle_v1/yaml_loader.py` owns parsing. It subclasses `yaml.SafeLoader`, removes
all Python/object constructors, and overrides mapping construction to reject duplicate
keys by normalized NFC value before constructing a dictionary. A token/event pre-scan
rejects BOM, directives, anchors, aliases, merge keys, explicit/custom tags, non-string
mapping keys, binary/timestamp/set/ordered-map scalars, and normalization collisions.
Only null, strict booleans, finite JSON-compatible numbers, and NFC strings are allowed;
implicit YAML timestamps are disabled. Input is UTF-8, at most 512 KiB, nesting at most
10, any mapping at most 30 keys, any sequence at most 1000 items, and total parsed nodes
at most 20,000. Plain `yaml.load`, `FullLoader`, and unmodified `safe_load` are forbidden.

The YAML root contains exactly one `sources` list. Each entry contains only the existing
`SourceConfig` authority fields: required `id`, `name`, `adapter`, `url`, `enabled`, and
`source_category`; optional `disabled_reason`, `list_selector`, `link_selector`,
`title_selector`, `summary_selector`, `date_selector`, `base_url`, `max_items`,
`max_article_age_hours`, `max_articles_per_poll`, `accept_articles_without_date`, and
`prioritate`. Aliases `type`, `categories`, and `priority` are forbidden remotely so one
wire vocabulary remains. Existing strict ranges and category vocabulary apply.
`source_count` must equal the list length; IDs must be unique lowercase ASCII. URLs and
`base_url` must be absolute HTTPS, contain no userinfo or fragment, use port 443 or no
explicit port, and have a DNS hostname; disabled records are not exempt. Selector strings
are passive data accepted only for the existing HTML adapter and never evaluated as
Python, templates, shell commands, imports, or dynamic code.

All externally controlled strings are decoded as strict UTF-8, NFC-normalized exactly
once before validation, and reject NUL, C0/C1 controls, unpaired surrogates, leading or
trailing whitespace, and normalization collisions. Limits are UTF-8 byte counts after
NFC. Exact bounds are:

| Value | Bound and grammar |
| --- | --- |
| source ID | 1–64 ASCII bytes; `[a-z0-9][a-z0-9_-]{0,63}` |
| display name | 1–256 bytes; printable Unicode |
| category | exactly one frozen category token, each at most 16 ASCII bytes |
| URL/base URL | 1–2048 bytes; absolute HTTPS policy above; IDNA2008 hostname 1–253 ASCII bytes, each label 1–63; path/query together at most 1536 bytes |
| selector | null or 1–2048 bytes of opaque CSS-selector text; no interpretation beyond the existing adapter |
| disabled reason | null or 1–1024 printable Unicode bytes |
| bundle/application SemVer | 1–128 ASCII bytes; strict SemVer 2.0.0, no leading `v`; stable artifacts forbid prerelease/build metadata |
| key ID | 1–64 ASCII bytes; `[a-z0-9][a-z0-9._-]{0,63}` |
| schema identifier | 1–96 ASCII bytes; `[a-z0-9][a-z0-9.-]{0,95}` |
| timestamp | exactly 20 ASCII bytes, `YYYY-MM-DDTHH:MM:SSZ`; valid calendar UTC; fractional seconds/offsets forbidden |
| raw SHA-256 | exactly 64 lowercase hexadecimal ASCII bytes |
| tagged SHA-256 | exactly `sha256:` plus the raw form |
| operation ID | exactly 32 lowercase hexadecimal ASCII bytes |
| filename | exact fixed filename named by its schema; no arbitrary filename |

Optional `list_selector`, `link_selector`, `title_selector`, `summary_selector`, and
`date_selector` use the selector bound; all present selectors must be non-empty. Numeric
and boolean source fields retain the frozen strict `SourceConfig` types/ranges. Manifest,
receipt, pointer, audit, health, and trust JSON reject duplicate keys before object
construction, unknown fields, non-NFC strings, booleans where integers are required, and
numbers outside their stated ranges.

Persisted bundle directories, verified receipts, active pointers, activation publication,
startup reconstruction, audit recovery, rollback, retention, and cleanup are
Productization source-domain concerns defined by Sections 8 and 14.1 through 14.3. They
never alter frozen Protocol or Persistence semantics.
Precedence is validated user override, active verified remote bundle, bundled immutable
default. Overrides key by source ID and permit `add`, `modify`, or `disable`; deletion is
represented only by `disable`, never a tombstone. An added ID must meet the full source
schema. `modify` may change any source field except `id`; unknown IDs are invalid unless
the operation is `add`. A user may explicitly re-enable a remotely disabled source only
when the resulting record independently passes the full enabled-source validation; the
UI warns that this overrides publisher guidance. One invalid override invalidates that
override document visibly and does not alter the active bundle. User files are never
overwritten.

Compatibility requires current application version greater than or equal to minimum and,
when non-null, less than or equal to maximum. Uncertain or unparsable compatibility fails
closed. Offline uses the last verified active bundle or bundled default. Settings offers
manual refresh; startup checks at most once per 24 hours if enabled.

## 9. Version, packaging, and installer

`project.version` in `pyproject.toml` is the single version authority. Build tooling
reads it through standards-based package metadata and fails if unavailable. The same
value is projected mechanically into `pastila_scout.__version__`, GUI About, CLI
`--version`, Windows four-part file version (`major.minor.patch.0`), Inno `AppVersion`,
manifest `latest_version`, artifact names, and logs. No generated projection is edited.
Parity tests compare all projections. Versions follow SemVer 2.0.0; Phase 5 publishes
stable versions only and forbids build metadata in stable artifacts.

The exact Python projection in `src/pastila_scout/__init__.py` uses
`importlib.metadata.version("pastila-news-monitor")`; only `PackageNotFoundError` maps to
the exact development fallback `0.0.0-dev`. The distribution name is exactly
`pastila-news-monitor`. Source/editable installations with metadata expose
`project.version`; an unpackaged source tree may expose the fallback. Stable build and
packaging gates reject the fallback, prerelease, build metadata, or any mismatch. No
second editable version literal or generated version authority exists.

Every runtime/build consumer uses that one projection: CLI `--version`, GUI About, and
file logging import `pastila_scout.__version__`; the PyInstaller version-resource helper,
Inno build, update-manifest generator, artifact-name generator, and release-tag validator
invoke the packaged version-projection check and consume its exact verified value. Package
metadata is the projection input, not a competing consumer. Only the release operator
edits `project.version`; no consumer parses `pyproject.toml` directly. Phase 5.5D wires
CLI, GUI About, and logging together and must pass parity before Phase 5.5E. Later
packaging, installer, updater-manifest, artifact, log, and release tests compare their
outputs to `pastila_scout.__version__` and fail on divergence.

The executable packager is **PyInstaller**, pinned in the build environment after its
Python 3.14 compatibility gate. It produces a **one-folder**, x64, windowed GUI named
`PastilaScout.exe` and a console `pastila-scout.exe` from one shared bundle. One-folder
is required for startup speed, inspectable resources, safer atomic installer replacement,
and fewer antivirus self-extraction heuristics. The spec file enumerates Tcl/Tk data,
certificates, schemas, source defaults, localization, icons, and the Ed25519 public key;
hidden imports are explicit. Release builds have no console window for the GUI; an
unsigned console debug build is separate and cannot use the stable endpoint. Builds are
clean and pinned but are not claimed bit-reproducible. File version, product name,
company, copyright, and icon resources are mandatory.

`packaging/pyinstaller/build.ps1` accepts exactly `-BuildMode development|stable`; absence,
another value, or mixed resources fails. Development mode uses only the verified fixture
root at `tests/fixtures/windows-trust/development-bootstrap-root-v1.json`, the development
endpoint, an explicit `DEVELOPMENT — UNTRUSTED` window/About mark, and optionally console
diagnostics. Stable mode requires frozen production bootstrap resources, canonical stable
version, fixed stable endpoints, final icon/notices/defaults, and later release-pipeline
Authenticode; it rejects fixture/test keys, fallback version, endpoint override, and
unsigned trust resources.

Before a PyInstaller build the exact inventory and producer tags are:

| Input | Exact repository path | Required producer |
| --- | --- | --- |
| application icon | `packaging/resources/PastilaScout.ico` | Phase 5.5F build preparation, verified before PyInstaller invocation |
| Tcl/Tk runtime | pinned Python installation paths recorded by `packaging/pyinstaller/PastilaScout.spec` | Phase 5.5E clean Windows compatibility probe |
| bootstrap root contract | `resources/trust/bootstrap-root-v1.json` | `phase-5.5b-trust-bootstrap-r1-verified` |
| bootstrap raw public key | `resources/trust/pastila-root-1.pub` | `phase-5.5b-trust-bootstrap-r1-verified` |
| version projection | `src/pastila_scout/__init__.py` and package metadata | `phase-5.5d-version-projection-r1-verified` |
| bundled source defaults | `config/sources.yaml` | frozen baseline plus Phase 5.5E hash inventory |
| immutable Scout application configuration | `config/config.yaml` | frozen Scout configuration baseline plus Phase 5.5E hash inventory; never a roaming settings file |
| default Windows application settings | `src/pastila_scout/desktop_v1/default-settings-v1.json` | `phase-5.4b-windows-state-r1-verified` |
| Romanian localization | `src/pastila_scout/desktop_v1/resources.py` | `phase-5.5d-version-projection-r1-verified` |
| licenses/notices | `packaging/resources/THIRD-PARTY-NOTICES.txt` | Phase 5.5F build preparation, verified before PyInstaller invocation |

Packaging consumes these inputs and never generates a trust identity or edits version
authority ad hoc.

The installer is **Inno Setup 6**, per-user, x64, non-administrative, with stable AppId.
It installs below `%LOCALAPPDATA%\Programs\PastilaScout`, creates a Start Menu shortcut,
offers an opt-in Desktop shortcut, registers no file associations, upgrades the same
AppId, closes the app through a cooperative mutex protocol, preserves all AppData, and
supports silent uninstall of binaries only. Uninstall asks separately whether to remove
user data; default is preserve. Inno's actual cancel/revert and file-replacement behavior
is accepted without claiming a general transactional rollback; Section 13 is the sole
binary failure and manual-recovery authority.

Exact release artifacts are:

- `PastilaScout-<version>-win-x64.zip` (one-folder diagnostic distribution);
- `PastilaScout-Setup-<version>-win-x64.exe` (installer/update payload);
- `PastilaScout-Setup-<version>-win-x64.exe.sig` (Ed25519 signature);
- `pastila-scout-update-manifest-v1.json` and `.sig`;
- `sources/<bundle-version>/sources-bundle-manifest-v1.json` and `.sig`;
- `sources/<bundle-version>/sources.yaml`;
- `SHA256SUMS.txt` (operator aid; never a trust root).

## 10. Trust and signing

This section owns Productization trust policy and trust-domain persistence. Trust records
are not frozen update-protocol artifacts and cannot produce a Protocol public error or
runtime result. Frozen Protocol and Persistence ownership remains unchanged.

The verified trust-bootstrap milestone materializes three non-secret repository artifacts:
`resources/trust/pastila-root-1.pub`, `resources/trust/bootstrap-root-v1.json`, and
`resources/trust/bootstrap-root-provenance-v1.json`. The `.pub` file is exactly 32 raw
Ed25519 public-key bytes. The strict-JCS bootstrap object contains exactly `schema` =
`pastila-scout-bootstrap-root`, `schema_version` = 1, `key_id` = `pastila-root-1`,
`algorithm` = `Ed25519`, `public_key_filename` = `pastila-root-1.pub`,
`public_key_sha256` = the raw 64-lowercase-hex SHA-256 of those 32 bytes,
`provenance_filename` = `bootstrap-root-provenance-v1.json`, and
`provenance_sha256` = the raw SHA-256 of the exact provenance bytes. The strict-JCS
provenance object contains exactly `schema` = `pastila-scout-root-provenance`,
`schema_version` = 1, `key_id`, `public_key_sha256`, `generated_offline_at`,
`independent_verifier_ids` (exactly two distinct 1–64-byte operator IDs), and
`verification_receipt_ids` (exactly two distinct 1–128-byte non-secret external receipt
IDs). The two files cross-identify the same key/hash; neither contains private material.

The identity named by this specification is a placeholder until materialization. Stable
packaging is forbidden until an externally generated production offline keypair supplies
the public bytes, two independent operators verify key ID/hash/provenance, and the three
artifacts are frozen by `phase-5.5b-trust-bootstrap-r1-verified`. The private root never
enters the repository, builder, CI, logs, or artifacts. Tests use only
`tests/fixtures/windows-trust/development-pastila-root-1.pub` and
`tests/fixtures/windows-trust/development-bootstrap-root-v1.json`; stable build mode
rejects either fixture path or hash.

Authenticode signs and RFC 3161 timestamps both PE executables and the installer using
a production code-signing certificate, which is a deployment prerequisite and is not
claimed to exist. Application-level signatures use **Ed25519** with two levels. The
offline root public key `pastila-root-1` is bundled read-only; its private key remains
offline and signs only trust metadata. Online release keys sign application manifests,
source manifests, and payload signatures only while authorized by root-signed metadata.
Private keys remain outside the repository in a hardware-backed service or token.
Development uses a distinct root, release key, and endpoint; a development build is
permanently marked and cannot accept stable artifacts.

Application manifests, source-bundle manifests, and installer bytes each have detached
Ed25519 signatures; `sources.yaml` is authenticated transitively by the signed manifest's
size and SHA-256.
HTTPS and SHA-256 are defense in depth, never sufficient trust. Canonical JSON uses
RFC 8785 JCS over the complete manifest; the detached `.sig` prevents recursive
canonicalization. Signature files are strict JSON:
`{"algorithm":"Ed25519","key_id":"pastila-release-1","signature":"<base64>"}`
with no unknown fields; `signature` is canonical padded base64 of exactly 64 signature
bytes (88 ASCII characters), and `key_id` names the actual root or release key used. Only the
source manifest has a detached signature. `sources.yaml` has no embedded or detached
signature and is accepted only when its exact byte length and SHA-256 match that signed
manifest; changing one YAML byte invalidates authentication. A fourth bundle artifact is
forbidden.

Trust metadata is fixed at
`https://updates.pastila.ro/windows/x64/stable/trust-metadata-v1.json` with detached
`.sig`. It is strict JCS JSON with exactly: `schema` = `pastila-scout-trust-metadata`,
`schema_version` = 1, `sequence` in `1..9223372036854775807`, canonical `generated_at`,
`expires_at`, `root_key_id`, `release_keys`, `revoked_key_ids`, and
`minimum_trusted_sequence`. Each release-key object has `key_id`, base64 raw Ed25519
`public_key`, canonical `not_before`/`not_after`, `allowed_channel` exactly `stable`, and
inclusive `minimum_sequence`/`maximum_sequence`. IDs are unique; revoked IDs cannot be
active; `release_keys` contains 1–32 entries and `revoked_key_ids` 0–256 key IDs; unknown
fields fail. Its detached signature uses the root key and Section 10's
signature-file schema. Expiry cannot exceed 90 days after generation.

Trust metadata is accepted only when the root signature is valid, root ID is bundled,
time interval contains the current trusted UTC time, Section 10's independent idempotent
pair algorithm accepts it, and `minimum_trusted_sequence` does not exceed its sequence.
A still-valid cached copy may be used offline until `expires_at`; after
expiry, already installed binaries and local features remain usable, but no new update
or source bundle is accepted. Rotation publishes newer root-signed metadata containing
both old and new release keys; after clients accept it, manifests may use the new key.
Revocation publishes newer root-signed metadata listing the compromised release key and
authorizing its replacement. A release key never authorizes its own rotation/revocation.

Root rotation requires an application release whose Authenticode-signed binaries bundle
both root keys and an old-root-signed transition naming the new root; only a later release
may remove the old root. A compromised root requires an independently obtained,
Authenticode-signed recovery installer or manual trusted reinstall. No network record
signed only by the compromised root is sufficient. Compromise freezes publishing and
the stable pointer until recovery.

Compromised-root recovery is a distinct executable protocol. An Authenticode-signed
recovery installer embeds one RCDATA resource named `PASTILA_ROOT_RECOVERY_V1`, containing
strict JCS JSON with exactly:

| Field | Exact type |
| --- | --- |
| `recovery_schema` | exactly `pastila-scout-root-recovery` |
| `recovery_schema_version` | integer exactly `1` |
| `recovery_operation_id` | operation-ID grammar |
| `old_root_key_id` / `new_root_key_id` | distinct key-ID grammar values |
| `new_root_public_key` | canonical base64 encoding of exactly 32 Ed25519 public-key bytes |
| `new_trust_metadata_sequence` | integer `1..9223372036854775807` |
| `new_trust_metadata` | exact trust-metadata object for the new hierarchy |
| `new_trust_metadata_signature` | detached-signature object signed by the new root |
| `publisher_identity_policy` | exactly `stable-recovery-publisher-v1` |
| `issued_at` | canonical timestamp |

`scripts/windows-recovery/build-root-recovery-resource.py` is the sole resource-generation
authority. It accepts explicit files containing old/new root IDs, the 32-byte new public
key, initial new trust-metadata JCS, its new-root detached signature, a CSPRNG operation
ID, and the immutable expected Authenticode publisher policy. Before output it verifies
all schemas, IDs, key/metadata/signature agreement, sequence, timestamps, canonical bytes,
and absence of private-key material. It writes only canonical
`packaging/windows/root-recovery/resources/PASTILA_ROOT_RECOVERY_V1.json`; Inno embeds its
exact bytes as RCDATA identifier `PASTILA_ROOT_RECOVERY_V1`, and packaging verification
records the resource SHA-256. Neither input nor output contains a private signing key.
Phase 5.7H verifies the tooling with development roots and a visibly non-stable recovery
artifact; it does not prebuild a hypothetical stable recovery. During a real incident,
the same frozen tooling consumes independently supplied public recovery inputs, and the
result is usable only after final Authenticode signing/timestamping under the immutable
recovery-publisher policy and independent verification.

Ordinary Ed25519 state does not authorize this resource. Recovery requires successful
`WinVerifyTrust`, Code Signing EKU, valid RFC 3161 timestamp, normalized publisher subject
equal to the immutable stable recovery-publisher policy bundled with the installed app,
and the explicit recovery resource. The UI displays old/new root IDs and publisher,
requires explicit consent, and suspends all update/source activation first. A clean
manually downloaded Authenticode-verified recovery installer uses the same protocol.

Bundled bootstrap trust is installer-owned and read-only at
`<install-dir>\resources\trust\bootstrap-root-v1.json`, with its raw public key at
`<install-dir>\resources\trust\pastila-root-1.pub`. The running application never changes
either file; only a normal signed application installation replaces bundled resources.
Mutable trust is updater-owned exclusively under `%LOCALAPPDATA%\PastilaScout\trust\` and
contains only `active-root-v1.json`, `trust-metadata-v1.json`,
`trust-metadata-v1.json.sig`, `trust-state-v1.json`, and `recovery-receipt-v1.json`.
No mutable trust file exists beside the executable.

The mutable active-root schema and nullability are Productization trust-domain contracts
defined by Sections 10 and 14.2; the cryptographic meaning of each transition kind follows.
For `BOOTSTRAP`, active ID/key equal bundled bootstrap bytes exactly and both transition
fields are null. `NORMAL_ROOT_ROTATION` changes the root only through the old-root-signed,
dual-root application transition in Section 10; both transition fields identify
`<install-dir>\resources\trust\root-transition-v1.json`. That strict-JCS receipt contains
exactly `schema` = `pastila-scout-root-transition`, `schema_version` = 1, `operation_id`,
`old_root_key_id`, `new_root_key_id`, `new_root_public_key`, `authorized_at`, and
`old_root_signature` (the detached-signature object over every preceding JCS field).
Its SHA-256 must equal `transition_receipt_sha256`, the old ID/key must equal the prior
active root, the new ID/key must equal the new application-bundled root, and the containing
application must pass Authenticode policy. Phase 5 V1 emits no normal-root transition;
support is fail-closed until a later application-release specification authorizes this
exact resource. Release-key rotation changes trust metadata only and never uses this
transition kind. `AUTHENTICODE_RECOVERY` requires both transition fields and the hash must
identify the exact valid recovery receipt. Unknown kinds or combinations fail closed.

Startup strictly loads the bundled bootstrap first. If no mutable active root exists, it
uses that root and `WindowsTrustStoreV1` in
`src/pastila_scout/windows_trust_v1/state.py` alone initializes `BOOTSTRAP` state
atomically; it does not fabricate trust metadata, which is accepted only after normal
root-signature verification. If mutable state exists, it
strictly validates schema and bootstrap identity, then accepts only exact `BOOTSTRAP`, a
valid bundled normal-root transition receipt, or an independently Authenticode-authorized
recovery receipt. It then validates the detached trust metadata under that selected root
and the matching monotonic trust-state pair. Malformed state, missing/invalid transition
evidence, or arbitrary root substitution disables remote application/source update and
shows repair guidance; it never silently falls back to a bootstrap root that recovery or
rotation had superseded. Ordinary Scout/Editor work continues. Same-user replacement is
outside the strong boundary, while format corruption and unauthorized transitions are
detected whenever loaded.

The recovery component backs up the mutable trust directory, validates the embedded new-
root key and signature over the embedded initial metadata, then atomically replaces its
`active-root-v1.json`, `trust-metadata-v1.json`, `trust-metadata-v1.json.sig`, and
`trust-state-v1.json` with flushed same-volume files. It removes the old root from active
trust, retains it only in audit/receipt history, initializes the pair to the embedded
sequence/hash, writes the receipt, and only then resumes checks. No old-root or online-
release signature can perform this transition.

The recovery-receipt schema and its Productization-domain atomic publication/rollback are
defined by Sections 10, 14.2, and 14.3.

Sequence-state schemas, publication, acceptance, replay/equivocation, corruption, and
recovery are Productization trust-domain rules in Sections 10, 14.2, and 14.3; they never
participate in Protocol V6 public-error precedence.

Authenticode provides Windows publisher identity/SmartScreen reputation and an additional
PE/installer verification layer; it never replaces Ed25519 manifest trust. Stable policy
requires a valid Windows chain, expected normalized publisher subject, Code Signing EKU,
and an RFC 3161 timestamp valid when signing. A timestamped certificate may be expired
now if it was valid at signing. Online revocation is attempted; offline revocation status
is reported as indeterminate and requires the Ed25519 checks to pass. Publisher-subject
changes require root-signed trust metadata plus a release policy revision; a leaf
thumbprint is logged but not permanently pinned. Only visibly marked non-stable builds
may use the development certificate and keys.

## 11. Update endpoint and manifest

The stable endpoint is fixed at
`https://updates.pastila.ro/windows/x64/stable/pastila-scout-update-manifest-v1.json`;
its detached signature is the same URL plus `.sig`. `updates.pastila.ro` static object
storage is a deployment prerequisite. Redirects are disabled. TLS 1.2+ is required,
system proxy settings are honored, total timeout is 10 seconds (3-second connect),
manifest limit is 64 KiB, no cookies/authentication are sent, cache uses ETag only, and
the user agent is `PastilaScout/<version> Windows/x64 UpdateClient/1`. All artifact URLs
must be HTTPS on exactly `updates.pastila.ro`, port 443, with no userinfo, fragment, or
path traversal. A compromised server cannot create accepted bytes without the key.

The detached-signed manifest is strict UTF-8 JCS JSON, no BOM, duplicate keys, unknown
fields, or non-NFC strings:

```json
{
  "schema": "pastila-scout-update-manifest",
  "schema_version": 1,
  "channel": "stable",
  "sequence": 1,
  "latest_version": "1.0.0",
  "minimum_supported_version": "0.1.0",
  "published_at": "2026-08-06T00:00:00Z",
  "release_notes": "Plain text, at most 4000 UTF-8 bytes.",
  "installer": {
    "url": "https://updates.pastila.ro/windows/x64/stable/PastilaScout-Setup-1.0.0-win-x64.exe",
    "size": 1,
    "sha256": "64 lowercase hexadecimal characters",
    "signature_url": "https://updates.pastila.ro/windows/x64/stable/PastilaScout-Setup-1.0.0-win-x64.exe.sig"
  },
  "source_bundle": {
    "sequence": 1,
    "manifest_url": "https://updates.pastila.ro/windows/x64/stable/sources/1.0.0/sources-bundle-manifest-v1.json",
    "manifest_size": 1,
    "manifest_sha256": "64 lowercase hexadecimal characters",
    "manifest_signature_url": "https://updates.pastila.ro/windows/x64/stable/sources/1.0.0/sources-bundle-manifest-v1.json.sig"
  },
  "key_id": "pastila-release-1"
}
```

`source_bundle` is either that exact object or JSON `null`; its sequence must equal the
downloaded source manifest sequence, and the source manifest remains the authority for
bundle version, payload, and compatibility. Integers are non-boolean
and positive; installer maximum is 512 MiB. Timestamps are
canonical UTC. SemVer parsing is exact. `minimum_supported_version` means an older app
must direct the user to the website but still cannot trust an unsigned path. Release
notes are plain text only. The key must be currently authorized by accepted root-signed
trust metadata for `stable` and this manifest sequence. Manifest freshness accepts a
verified cached result for 15 minutes, but replay/sequence and version rules always apply.

## 12. Update checks and UI

After the root is visible and idle callbacks have run, `root.after(5000, ...)` submits
exactly one startup check per launch if enabled. It is bounded, non-blocking, never
installs/downloads, never blocks Scout/Editor, logs ordinary offline failure, shows no
error dialog, and shows one non-intrusive banner only for a verified newer version.
It never prompts twice in a session.

Help > Check for Updates remains available even when startup checks are disabled. It
opens Update Center and requests a fresh network response (`Cache-Control: no-cache`),
unless an identical check is already active, in which case it focuses that operation.
It reports Up to date, Update available, Service unavailable, or Metadata could not be
verified using safe text. It offers retry and never exposes exceptions. Manual state is
separate from the startup-notification suppression state.

Update Center shows current/latest version, release date, plain release notes, size,
stable channel, trust status, download progress, install state, and restart requirement.
Buttons are Check again, Download update, Install and restart, Later, and Close.
Download is enabled only for verified newer metadata; Install only for a fully verified
payload and idle application; Later/Close never install.

## 13. Download, handoff, rollback, and migration

Download verification, rollback limits, and migration policy remain normative here.
Handoff/health schemas and storage are owned by frozen Persistence V6; publication order,
synchronization, process identity, restart, timeout, recovery, cleanup, and public errors
are owned by frozen Protocol V6. This section owns only Productization download and
installer UX integration.

Downloads use `%LOCALAPPDATA%\PastilaScout\updates\downloads\`. The downloader creates
a cryptographically random exclusive `.part` file below a reparse-free owned directory,
streams in 1 MiB chunks, enforces declared and 512 MiB maximum size, checks free space
for size plus 100 MiB, uses 30-second connect and 5-minute total timeout, and supports
cancellation. Missing/mismatched Content-Length fails; compression is disabled; resume
is not supported in V1. It fsyncs, verifies exact size, SHA-256, release-key Ed25519
signature, and Authenticode policy, then atomically renames to
`<sha256>.verified.exe`. One updater service owns handles and cleanup. Partial/untrusted
files are deleted; cleanup failure is logged and never makes them executable.

The initial installer-launch design accepts a bounded residual same-user path race; no
native launcher is claimed. Immediately before launch, `InstallerLaunchAuthorityV1`:

1. opens every update-directory component with `CreateFileW`,
   `FILE_READ_ATTRIBUTES`, `FILE_SHARE_READ`, and
   `FILE_FLAG_BACKUP_SEMANTICS|FILE_FLAG_OPEN_REPARSE_POINT`, rejecting any reparse point;
2. opens the installer with `CreateFileW`, `GENERIC_READ|FILE_READ_ATTRIBUTES`,
   `FILE_SHARE_READ` only (no write/delete sharing), `OPEN_EXISTING`, and
   `FILE_FLAG_OPEN_REPARSE_POINT|FILE_FLAG_SEQUENTIAL_SCAN`;
3. rejects reparse metadata, obtains volume serial number and 128-bit file ID through
   `GetFileInformationByHandleEx(FileIdInfo)`, and compares them, size, and supplementary
   last-write metadata with the verified receipt;
4. hashes bytes through that handle and reruns Authenticode verification against the
   path while the restrictive handle remains open;
5. calls `CreateProcessW` using the fully resolved fixed path and fixed argument vector,
   then closes the handle only after successful process creation.

Identity, size, hash, signature, or reparse change fails closed. `CreateProcessW` launches
by path rather than by an existing file handle, so this immediate revalidation and
write/delete-sharing denial minimizes but does not mathematically eliminate a final race
against a fully compromised same-user process. That attacker is outside the strong local
integrity boundary; eliminating the residual requires a separately specified native
launcher and is not part of V1.

Install and restart follow frozen Protocol V6 exclusively. After its prescribed preparation,
the old GUI finishes/cancels work, closes SQLite/resources, flushes logs, performs the
checks above, and starts the installer with fixed `/CURRENTUSER`, `/VERYSILENT`,
`/RESTARTAPPLICATIONS`, and
`/HANDOFFOP=<operation-id>`, where the value is exactly the handoff operation ID, then
exits. The installer waits on the
application mutex, installs without elevation, and relaunches with the fixed internal
arguments `--update-result <operation-id> --installer-process-id <decimal-process-id>`;
these values must match the handoff record. No URL, arbitrary argument, or install path
comes from the manifest. The
running executable never overwrites itself.

Installer handoff/receipt schema is owned by frozen Persistence V6. Old-GUI/installer/
new-GUI ordering, process identity, publication, polling, crash recovery, reconciliation,
cleanup, and errors are owned by frozen Protocol V6. No rule in this chapter supplements
those contracts.

Rollback guarantees are intentionally limited:

- Before installer launch, invalid trust/hash/identity/version, insufficient space, or
  user cancellation leaves installed files unchanged.
- Once Inno Setup starts modifying files, its configured cancel/revert and file-handling
  behavior is used, but no universal transaction or restoration guarantee is claimed.
  Failure may leave the application partly or fully updated depending on failure point.
  The installer exit code and safe diagnostic are retained; the UI never states that an
  automatic rollback occurred.
- Post-update health failure offers explicit manual recovery; there is no watchdog or
  automatic binary downgrade.

Exactly two application installers are retained under
`updates/installers/<version>-<sha256>/`: the current verified installer and the previous
verified installer. Each reuse revalidates root trust, release-key authorization,
manifest signature, exact size/hash, file identity, and Authenticode policy. After two
subsequent healthy launches, installers older than those two are deleted by the updater;
cleanup failure is non-fatal. Recovery shows current/previous versions and reason, then
requires explicit consent before launching the previous installer through the same
launch authority. Manual retry of the current installer is allowed for seven days or
until its signing authorization/manifest becomes invalid, whichever is earlier.

Manual previous-version recovery is the sole downgrade exception. It is permitted only
for the exact retained artifact named by the locally stored, formerly accepted manifest
receipt; all signatures, file identity, hash, Authenticode, database compatibility, and
receipt-to-artifact lineage are revalidated. The UI names both versions and warns that it
is a recovery downgrade. Explicit consent creates a one-use nonce; it does not lower or
reset any highest-seen sequence, authorize a network-supplied older artifact, or suppress
the next offer of the newer release. If the current database schema is unsupported by
the previous application, recovery is refused rather than downgrading the database.

Health receipt schema is owned by frozen Persistence V6. Lineage, initialization,
monotonic timing, stages, restart abandonment, recovery, retention, cleanup, and errors
are owned by frozen Protocol V6. Productization health presentation observes database
compatibility but never owns migration.

SQLite authority is `PRAGMA user_version`. The desktop-managed target is exactly `1`;
legacy repository databases are version `0`. Version 1 introduces version authority only
and preserves the current logical schema—no desktop table, index, trigger, or data column
is added. The sole future owner is
`src/pastila_scout/windows_state_v1/migrations.py`, containing exactly
`TARGET_SCHEMA_VERSION = 1` and `MIGRATIONS = {0: _migrate_0_to_1}`. The function first
recognizes the exact version-0 structure below and then sets `PRAGMA user_version = 1`
inside the migration transaction; no other module registers migrations.

Target 1 has no triggers and exactly these tables/structural invariants:

| Table | Exact columns and constraints |
| --- | --- |
| `sources` | `id TEXT PRIMARY KEY`; non-null `name`, `type`, `url`, `enabled`, `created_at`, `updated_at`; `categories TEXT NOT NULL DEFAULT '[]'`; `priority INTEGER NOT NULL DEFAULT 1` |
| `events` | `id INTEGER PRIMARY KEY AUTOINCREMENT`; non-null `canonical_title`, `normalized_title`, `first_seen_at`, `last_seen_at`, `article_count INTEGER DEFAULT 0`, `source_count INTEGER DEFAULT 0`, `created_at`, `updated_at`; nullable `summary`, `category`, `canonical_article_id`, `canonical_selection_reason`, `first_published_at`, `last_published_at` |
| `articles` | `id INTEGER PRIMARY KEY AUTOINCREMENT`; non-null `source_id`, `url`, `normalized_url TEXT UNIQUE`, `title`, `normalized_title`, `discovered_at`; nullable `summary`, `published_at`, `raw_payload`, `event_id`; foreign keys `source_id -> sources.id`, `event_id -> events.id` |
| `poll_runs` | `id INTEGER PRIMARY KEY AUTOINCREMENT`; non-null `started_at`, `status`, `sources_checked INTEGER DEFAULT 0`, `articles_found INTEGER DEFAULT 0`, `articles_inserted INTEGER DEFAULT 0`; nullable `finished_at`, `error_message` |
| `editorial_queue` | `id INTEGER PRIMARY KEY AUTOINCREMENT`; `article_id INTEGER NOT NULL UNIQUE -> articles.id ON DELETE CASCADE`; `status` limited to pending/claimed/reviewed/rejected; `priority INTEGER NOT NULL DEFAULT 0`; `queued_at` non-null; nullable `claimed_at`, `reviewed_at`, `reviewer`, `notes`; nullable `decision` limited to keep/reject/backup |
| `event_categories` | non-null `event_id -> events.id ON DELETE CASCADE`, `category`, `position`; primary key `(event_id, category)`; unique `(event_id, position)`; category frozen vocabulary; position `0..2` |

Target 1 has exactly indexes `idx_articles_source_id(source_id)`,
`idx_articles_published_at(published_at)`,
`idx_articles_normalized_title(normalized_title)`,
`idx_articles_event_id(event_id)`, `idx_events_last_seen_at(last_seen_at)`,
`idx_poll_runs_started_at(started_at)`, and
`idx_editorial_queue_status_priority(status, priority DESC)`, plus SQLite automatic
indexes implied by primary/unique constraints. Version-0 recognition requires exactly
these user tables, columns, declared types, nullability, defaults, primary/unique/check/
foreign-key constraints, indexes, and no user triggers; unrelated `sqlite_*` internals
are ignored. Unknown/malformed version 0 is `LEGACY_SCHEMA_UNSUPPORTED`, is not backed up
as migratable or mutated, and remains available only for explicit export/support.

For `user_version == 1`, exact target validation runs and normal services open. For
`user_version > 1`, fail closed without mutation or backup replacement and display
`Baza de date necesită o versiune mai nouă a aplicației.` Negative/non-integer values or
unknown structure fail as unsupported. No best-effort schema patching is permitted.

Migration sequence is exact: acquire the application-wide migration mutex and exclusive
SQLite connection; prove no ordinary DB owner remains; run `PRAGMA quick_check`; validate
the current schema/version; require free space of database size times two plus 100 MiB;
create `data/backups/news_monitor-v<source>-<UTC>-<sha256>.db` with SQLite backup API;
fsync it and parent; reopen it read-only, run `quick_check`, and compare recorded size and
SHA-256; begin `BEGIN EXCLUSIVE`; apply every contiguous migration; set `user_version`
after each successful step; run `foreign_key_check` and `quick_check`; commit; close and
reopen application services. Migration functions must be transaction-safe and yield the
target schema when run once; restart idempotency is supplied by the committed version,
not by rerunning a step at the same version.

Any missing registry step, backup/integrity/free-space/lock failure aborts before mutation.
Any migration or final integrity failure rolls back the transaction, closes the failed
connection, preserves the original database and validated backup, blocks Scout/Editor
writes, leaves Reports/diagnostics available, and shows a safe migration error. Binary
installation never opens or migrates the database; reports, logs, and settings are never
rewritten.

## 14. Frozen Update Protocol Integration and Productization Presentation

Frozen Windows Update Protocol V6 is the sole normative authority for public error
identity, semantic origin, precedence, final authority, retryability, cleanup, and its
persistent/cross-process protocol behavior. This chapter remains Productization's
normative owner only for safe presentation, capability projection, and Productization
integration. Protocol-like wording here is contextual unless explicitly identified as a
Productization projection; an apparent semantic conflict is a specification defect, not
an alternate Protocol rule.

### 14.1 Productization filesystem integration

The first four rows bind frozen Persistence V6 artifact identities to Productization-owned
installed-mode paths only. Writer, reader, mutation, reconstruction, lifetime, and cleanup
ownership are consumed unchanged from Persistence `ART-001..004` and `OWN-001..005` and
Protocol V6; no path row grants semantic authority.

| Artifact or Productization domain | Exact path | Normative authority |
| --- | --- | --- |
| Persistence `UPDATE_STATE` (`ART-001`) | `%LOCALAPPDATA%\PastilaScout\updates\update-state-v1.json` | frozen Persistence `ART-001`, `KEY-001`, `OWN-001..002`; frozen Protocol V6 owns all runtime use |
| Persistence `RETAINED_INSTALLER_BYTES` (`ART-004`) | bytes below `%LOCALAPPDATA%\PastilaScout\updates\installers\`; retained record remains nested in `UPDATE_STATE` | frozen Persistence `ART-004`, `KEY-004`, `OWN-002..003`; frozen Protocol V6 owns retention and cleanup decisions |
| Persistence `HANDOFF_RECEIPT` (`ART-002`) | `%LOCALAPPDATA%\PastilaScout\update-state\installer-handoff-v1.json` | frozen Persistence `ART-002`, `KEY-002`, `OWN-004`; frozen Protocol V6 owns runtime use |
| Persistence `HEALTH_RECEIPT` (`ART-003`) | `%LOCALAPPDATA%\PastilaScout\update-state\health-receipt-v1.json` | frozen Persistence `ART-003`, `KEY-003`, `OWN-005`; frozen Protocol V6 owns runtime use |
| application sequence state | `%LOCALAPPDATA%\PastilaScout\updates\state-v1.json` | Productization application-metadata sequence authority |
| `TrustState` sequence | `%LOCALAPPDATA%\PastilaScout\trust\trust-state-v1.json` | Productization `WindowsTrustStoreV1` |
| active trust root | `%LOCALAPPDATA%\PastilaScout\trust\active-root-v1.json` | Productization `WindowsTrustStoreV1` or independently authorized recovery transition |
| trust recovery receipt | `%LOCALAPPDATA%\PastilaScout\trust\recovery-receipt-v1.json` | Productization Authenticode-authorized recovery authority |
| `SourceBundlePointerV1` | `%LOCALAPPDATA%\PastilaScout\source-bundles\active-v1.json` | Productization source activation authority |
| `VerifiedBundleReceiptV1` | `source-bundles\sequence-<decimal>\verified-receipt-v1.json` | Productization source activation authority |
| source activation audit | `source-bundles\audit\activation-<sequence>-<operation-id>.json` | Productization source activation/recovery authority |
| source sequence state | `%LOCALAPPDATA%\PastilaScout\source-bundles\sequence-state-v1.json` | Productization source sequence authority |

No reader becomes a writer. There is no shutdown snapshot, GUI-owned authoritative copy,
secondary cache, directory-scan reconstruction, or reconstruction of update state from
handoff, health, trust, installer, or source records.
This table is exhaustive for mutable protocol state. SQLite business data, settings,
logs/reports, downloaded signed content, immutable installed resources, and installer
payload bytes retain their domain owners and are not cross-process protocol authority.

### 14.2 Productization-domain schemas and frozen Persistence consumption

Frozen Persistence V6 Sections 3 through 8 exclusively define the `UPDATE_STATE`,
`HANDOFF_RECEIPT`, `HEALTH_RECEIPT`, and `RETAINED_INSTALLER_BYTES` representations,
field inventories, reusable types, invariants, reconstruction, and canonical serialization.
Productization binds their abstract keys to Section 14.1 paths and consumes their immutable
projections; it defines no alternate field, enum, nullability, normalization, or wire rule.

`SourceBundlePointerV1` is `pastila-scout-active-source-bundle` version `1` with exactly
`active_sequence`, `active_manifest_sha256`, `active_payload_sha256`, `previous_sequence`,
`previous_payload_sha256`, and `activated_at` as defined by Section 8 grammar; previous
fields are both null or both non-null. `VerifiedBundleReceiptV1` is
`pastila-scout-source-verification` version `1` with exactly `bundle_sequence`,
`manifest_sha256`, `payload_sha256`, `verified_at`, `verification_key_id`, and
`application_version`. The application/source/trust sequence files retain their exact
schema fields below.

Application sequence state is `pastila-scout-application-sequence` version `1` with
exactly `highest_seen_sequence` (range integer or null),
`highest_seen_canonical_sha256` (raw hash or null), and `highest_seen_version` (stable
SemVer or null), all null or all non-null. Source sequence state is
`pastila-scout-source-sequence` version `1` with exactly the same nullable sequence/hash
pair. `TrustState` is `pastila-scout-trust-sequence` version `1` with exactly that pair and
`expires_at` (canonical timestamp or null), all observation fields null or non-null.

`active-root-v1.json` is `pastila-scout-active-root` version `1` with exactly
`active_root_key_id`, `active_root_public_key` (canonical base64 of 32 Ed25519 bytes),
`bootstrap_root_key_id`, `transition_kind` (`BOOTSTRAP`, `NORMAL_ROOT_ROTATION`, or
`AUTHENTICODE_RECOVERY`), `transition_operation_id` (operation ID or null),
`transition_receipt_sha256` (raw SHA-256 or null), and `activated_at`. Bootstrap requires
equal active/bootstrap identity and null transition fields; both other kinds require both
transition fields and their exact Section 10 cryptographic evidence.

The trust recovery receipt is `pastila-scout-root-recovery-receipt` version `1` with
exactly `recovery_operation_id`, old/new root key IDs, `new_trust_sequence`,
`new_trust_metadata_sha256`, `authenticode_publisher`, `completed_at`, and
`user_consented=true`. A source activation audit is
`pastila-scout-source-activation-audit` version `1` with exactly `operation_id`, `action`,
`occurred_at`, previous/next sequence, `outcome`, and `failure_code`; it is evidence only.

The application, source, and trust sequence acceptance algorithm is identical but applied
independently: fully verify first; null pair accepts/establishes; greater sequence accepts/
replaces; equal sequence/equal hash is idempotent; equal sequence/different hash emits
`METADATA_SEQUENCE_EQUIVOCATION`; lower sequence emits `METADATA_REPLAY`. Manual retained-
installer recovery never lowers a pair. Malformed or one-sided state emits
`SEQUENCE_CACHE_INVALID`; it is never reconstructed from downloaded metadata.

Source activation creates an exclusive temporary sequence directory, verifies manifest,
payload, schema, signature, compatibility, and sequence, writes its verification receipt,
publishes the final directory, then atomically publishes the pointer before exposing it
in memory. Startup validates the pointer and all four non-reparse regular artifacts. A
valid previous pair replaces an invalid active pair atomically; otherwise immutable
bundled defaults are used without fabricating a remote pointer. Missing audit evidence is
regenerated and never invalidates an otherwise valid pointer. Only active and previous
directories survive cleanup; referenced directories are never deleted.

Trust startup loads immutable bootstrap material first, then validates the mutable active
root, transition evidence, signed trust metadata, and monotonic trust-state pair. Missing
mutable state initializes only exact bootstrap-root state; malformed or unauthorized
mutable state disables application/source updates and never silently falls back after a
rotation/recovery. Normal rotation and independently Authenticode-authorized recovery use
their Section 10 cryptographic contracts but publish every mutable record through Section
14.3. Trust recovery remains the only writer during its explicit transition and restores
the prior flushed set on publication failure.

### 14.3 Atomic persistence

For the four frozen Persistence artifacts, Productization invokes only the injected
`PersistentStoreV1` and consumes the exact serialization, validation, store-result,
lower-authority, and atomic-publication contracts in frozen Persistence V6 Sections 8
through 10. Frozen Protocol V6 alone converts those lower facts into runtime results.
Productization performs no second publication algorithm, rollback inference, error
mapping, cleanup selection, or authority decision.

Productization-owned source, trust, and application-sequence records retain the atomic
publication rules in Sections 8 and 10 of this document. Those domain records are not
Persistence V6 artifacts and cannot produce or replace a `PersistenceProtocolResultV1`.

### 14.4 Frozen cross-process Protocol consumption

Frozen Protocol V6 exclusively defines synchronization, handoff ordering, process
identity, restart reconciliation, health lifecycle, timeout behavior, public errors,
authority, retryability, cleanup, diagnostics, and result validity. Productization invokes
that Protocol through its public runtime boundary and may only render the resulting
Section 14.6 presentation. The GUI, installer UX, and packaging layers add no transition,
polling rule, failure mapping, recovery decision, or persisted phase.

### 14.5 Frozen restart behavior consumption

Frozen Protocol V6 Sections 5 through 10 exclusively define restart, reconstruction,
recovery, state transition, timeout, authority, retryability, cleanup, diagnostics, and
capability inputs. Productization renders only the safe message, capability projection,
and visible action selected by Section 14.6 from the complete Protocol result. It does not
reconstruct a restart matrix or resume any operation.

The Productization metadata cache remains process-local for UI freshness only. It grants
no Protocol legality, download authority, retryability, cleanup, or restart behavior.

### 14.6 Exhaustive presentation of Protocol V6-selected errors

The first table in this section is the sole Productization presentation inventory for the
34 closed `PersistenceFormatErrorCodeV1` members owned by Protocol V6. Each public failure
emits its listed code as the stable log identifier plus a separate random diagnostic
correlation ID. `app/source/update` capability columns use `yes`, `no`, or `repair-only`.
GUI, Scout, and Editor remain usable unless explicitly stated.
`app=yes` means GUI, Scout, and Editor are each usable; `app=no` means stable application
startup fails before any of those surfaces claim authority. No protocol code disables
only Scout or only Editor. Source and update capabilities remain independently explicit.
The guidance column is presentation text only: it never defines authority, retryability,
cleanup, precedence, or semantic origin. Actual Retry and cleanup presentation consumes
the complete `PersistenceProtocolResultV1` through the closed projection rules following
the table; it is never inferred from the public error code.

| Code | Exact safe Romanian message | Non-authoritative user guidance | app/source/update capability |
| --- | --- | --- | --- |
| `UPDATE_STATE_MALFORMED` | `Fișierul de stare al actualizatorului este deteriorat. Cod: {id}` | repair guidance; cleanup presentation comes only from the runtime result | yes/no/no |
| `UPDATE_STATE_QUARANTINED` | `Starea nevalidă a actualizatorului a fost izolată. Cod: {id}` | repair; retain diagnostic 30 days | yes/no/no |
| `UPDATE_STATE_PERSISTENCE_FAILED` | `Starea actualizatorului nu a putut fi salvată. Cod: {id}` | storage-repair guidance; cleanup presentation comes only from the runtime result | yes/no/no |
| `OBSERVATION_PUBLICATION_FAILED` | `Rezultatul actualizării a fost salvat, dar nu poate fi afișat. Cod: {id}` | retry visibility comes only from the runtime result; no Productization cleanup | yes/yes/repair-only |
| `UPDATE_CHECK_FAILED` | `Verificarea actualizărilor a eșuat. Cod: {id}` | retry visibility comes only from the runtime result; no cleanup | yes/yes/repair-only |
| `UPDATE_OPERATION_INTERRUPTED` | `Operația de actualizare a fost întreruptă. Cod: {id}` | explicit recheck | yes/yes/repair-only |
| `UPDATE_METADATA_RECHECK_REQUIRED` | `Metadatele actualizării trebuie verificate din nou. Cod: {id}` | manual recheck; discard candidate | yes/yes/repair-only |
| `UPDATE_DOWNLOAD_INTERRUPTED` | `Descărcarea actualizării a fost întreruptă. Cod: {id}` | recheck/download; delete partial | yes/yes/repair-only |
| `UPDATE_DOWNLOAD_FAILED` | `Descărcarea actualizării a eșuat. Cod: {id}` | retry visibility comes only from the runtime result; Protocol owns temporary cleanup | yes/yes/repair-only |
| `UPDATE_MANIFEST_INCOMPATIBLE` | `Actualizarea nu este compatibilă cu această versiune. Cod: {id}` | newer compatible metadata; discard | yes/yes/yes |
| `RETAINED_INSTALLER_MISSING` | `Instalatorul verificat nu mai este disponibil. Cod: {id}` | fresh-download guidance; no Productization cleanup | yes/yes/yes |
| `RETAINED_INSTALLER_INVALID` | `Instalatorul păstrat nu mai este valid. Cod: {id}` | fresh-download guidance; cleanup and revalidation presentation come only from the runtime result | yes/yes/yes |
| `RETAINED_INSTALLER_HASH_MISMATCH` | `Instalatorul păstrat nu corespunde verificării. Cod: {id}` | fresh download; quarantine | yes/yes/yes |
| `RETAINED_INSTALLER_REVALIDATION_FAILED` | `Instalatorul păstrat nu a trecut reverificarea. Cod: {id}` | recheck or fresh-download guidance; Protocol owns revalidation | yes/yes/yes |
| `HANDOFF_RECEIPT_MISSING` | `Confirmarea pornirii instalării lipsește. Cod: {id}` | repair; retain bytes non-executable | yes/yes/no |
| `HANDOFF_RECEIPT_MALFORMED` | `Confirmarea pornirii instalării este deteriorată. Cod: {id}` | repair guidance; cleanup presentation comes only from the runtime result | yes/yes/no |
| `HANDOFF_RECEIPT_PERSISTENCE_FAILED` | `Starea instalării nu a putut fi salvată. Cod: {id}` | storage-repair guidance; cleanup presentation comes only from the runtime result; launch nothing | yes/yes/no |
| `HANDOFF_RECEIPT_STALE` | `Confirmarea veche a instalării a expirat. Cod: {id}` | recheck guidance; expose only the safe retained diagnostic | yes/yes/repair-only |
| `HANDOFF_LINEAGE_MISMATCH` | `Confirmarea instalării nu corespunde actualizării. Cod: {id}` | repair; quarantine receipt | yes/yes/no |
| `HANDOFF_PROCESS_IDENTITY_MISMATCH` | `Procesul instalatorului nu poate fi identificat sigur. Cod: {id}` | repair; no mutation | yes/yes/no |
| `HANDOFF_PROCESS_IDENTITY_UNAVAILABLE` | `Identitatea procesului instalatorului nu poate fi citită. Cod: {id}` | explicit recheck; terminate/await child | yes/yes/no |
| `HANDOFF_PROCESS_NOT_OBSERVED` | `Procesul instalatorului nu mai este activ. Cod: {id}` | manual recovery; retain truthful receipt | yes/yes/no |
| `INSTALLER_HANDOFF_CANCELLED` | `Pornirea instalării a fost anulată.` | no Retry control for this result; a later handoff is a new explicit operation; retain the safe diagnostic | yes/yes/yes |
| `INSTALLER_PRELAUNCH_VERIFICATION_FAILED` | `Instalatorul nu mai poate fi verificat. Cod: {id}` | fresh-download guidance; Protocol owns quarantine | yes/yes/yes |
| `INSTALLER_PROCESS_START_FAILED` | `Instalatorul nu a putut fi pornit. Cod: {id}` | recheck; retain trusted bytes non-executable | yes/yes/repair-only |
| `INSTALLER_RECEIPT_TIMEOUT` | `Confirmarea pornirii instalării nu a sosit la timp. Cod: {id}` | explicit recheck; installer exits unchanged | yes/yes/repair-only |
| `INSTALLER_MUTEX_TIMEOUT` | `Aplicația nu s-a închis la timp pentru instalare. Cod: {id}` | explicit recheck; installer exits unchanged | yes/yes/repair-only |
| `HEALTH_RECEIPT_MALFORMED` | `Starea actualizării nu poate fi verificată. Cod: {id}` | repair guidance; cleanup presentation comes only from the runtime result | yes/yes/no |
| `HEALTH_RECEIPT_PERSISTENCE_FAILED` | `Starea verificării noii versiuni nu a putut fi salvată. Cod: {id}` | storage-repair guidance; cleanup presentation comes only from the runtime result; stop validation | yes/yes/no |
| `HEALTH_INITIALIZATION_LINEAGE_MISSING` | `Confirmarea noii versiuni lipsește. Cod: {id}` | repair; create no health receipt | yes/yes/no |
| `HEALTH_INITIALIZATION_LINEAGE_MISMATCH` | `Confirmarea noii versiuni nu corespunde instalării. Cod: {id}` | repair; create no health receipt | yes/yes/no |
| `HEALTH_VALIDATION_TIMEOUT` | `Verificarea noii versiuni nu s-a încheiat la timp. Cod: {id}` | recovery; abandon receipt | yes/yes/no |
| `HEALTH_VALIDATION_INTERRUPTED` | `Verificarea noii versiuni a fost întreruptă. Cod: {id}` | recovery; abandon receipt | yes/yes/no |
| `HEALTH_VALIDATION_FAILED` | `Noua versiune nu a trecut verificarea de pornire. Cod: {id}` | manual recovery; retain diagnostic | yes/yes/no |

Productization's five version-projection errors are not `PersistenceFormatErrorCodeV1`
members and are therefore excluded from the preceding Protocol V6 inventory. Their
existing presentation authority remains Productization-owned and is closed separately:

| Productization version code | Exact safe Romanian message | User guidance | app/source/update capability |
| --- | --- | --- | --- |
| `VERSION_PROJECTION_UNAVAILABLE` | `Versiunea aplicației nu poate fi determinată. Cod: {id}` | reinstall | no/no/no |
| `VERSION_PROJECTION_MISMATCH` | `Versiunea aplicației nu este consecventă. Cod: {id}` | reinstall | no/no/no |
| `STABLE_FALLBACK_VERSION_REJECTED` | `Pachetul stabil nu conține versiunea verificată. Cod: {id}` | rebuild/reinstall | no/no/no |
| `GUI_VERSION_WIRING_UNAVAILABLE` | `Versiunea interfeței nu poate fi afișată. Cod: {id}` | reinstall | no/no/no |
| `LOGGING_VERSION_MISMATCH` | `Versiunea pentru diagnosticare nu este consecventă. Cod: {id}` | reinstall | no/no/no |

| Projection rule | Protocol-owned input | Exact Productization presentation |
| --- | --- | --- |
| `PRES-RETRY-001` | `RETRYABLE` | show the existing Retry control enabled for a new explicit operation; never imply automatic retry |
| `PRES-RETRY-002` | `NOT_RETRYABLE` | hide or disable the Retry control; guidance may expose a separately named repair, reinstall, recheck, or support action only where its presentation row already names it |

| Projection rule | Protocol-owned cleanup | Exact Productization presentation and ownership |
| --- | --- | --- |
| `PRES-CLEANUP-001` | `NONE` | show no cleanup action or cleanup claim |
| `PRES-CLEANUP-002` | `DELETE_OWNED_TEMPORARY` | report no user cleanup action; Protocol owns deletion of its temporary artifact |
| `PRES-CLEANUP-003` | `RETRY_OWNED_CLEANUP` | show storage-repair guidance only; `ProtocolWriterV1` exclusively owns the finite cleanup obligation and any explicit cleanup request |
| `PRES-CLEANUP-004` | `QUARANTINE_INVALID_ARTIFACT` | show the row's existing repair guidance; Protocol owns quarantine |
| `PRES-CLEANUP-005` | `RETAIN_DIAGNOSTIC` | expose only the safe correlation/support affordance; Protocol owns diagnostic retention |
| `PRES-CLEANUP-006` | `REVALIDATE` | expose the row's existing recheck or fresh-operation guidance; Protocol owns revalidation semantics |

| Projection rule | Protocol-owned authority | Exact Productization presentation |
| --- | --- | --- |
| `PRES-AUTHORITY-001` | `NONE` | display no authoritative update artifact from the failed operation |
| `PRES-AUTHORITY-002` | `PRIOR` | retain the previously displayed authoritative update state; do not claim publication of a replacement |
| `PRES-AUTHORITY-003` | `NEW` | display the new authoritative state only when its observation projection is available; otherwise use the `OBSERVATION_PUBLICATION_FAILED` presentation |

Productization consumes these three fields independently from the complete runtime result.
It never derives one from another or from the public error. Productization performs no
cleanup and creates no retry, authority, or precedence semantics.

Trust, source-bundle, version, signature, replay/equivocation, migration, and ordinary GUI
codes in Section 14.9 remain separate Productization-domain presentation categories, not
`PersistenceFormatErrorCodeV1` members. They may not reuse or replace a Protocol V6 code.
For a `PersistenceProtocolResultV1`, Productization accepts the public error already
selected by Protocol V6 Section 11.1 and never re-evaluates precedence, semantic origin,
authority, retryability, or cleanup. Cleanup failure remains only Protocol's redacted
secondary diagnostic and never replaces the selected presentation row.

This presentation closure adds no roadmap phase or implementation path. Existing Phase
5.7F produces the Protocol result, and Phase 5.8 Update Center consumes these
Productization projections. Their authorized paths, prerequisites, and ownership remain
unchanged.

### 14.7 Frozen timeout authority consumption

Frozen Protocol V6 exclusively owns every receipt, mutex, combined-gate, and health
deadline, clock source, start instant, polling cadence, expiry result, and audit-time
projection. Productization consumes only the resulting runtime status and presentation
dimensions; it starts no second timer and infers no timeout from wall-clock data.

The 15-minute metadata cache is a separate Productization UI/network freshness concern.
It is process-local, monotonic, never persisted, and never grants Protocol legality,
authority, retryability, cleanup, or recovery behavior.

### 14.8 Productization presentation verification matrix

Protocol V6 owns protocol verification and Persistence V6 owns wire/store verification.
The matrix below verifies only Productization's deterministic presentation of their frozen
outputs; it does not retest or redefine runtime semantics.

| Verification ID | Input public error and exact Protocol dimensions | Expected safe message | Expected app/source/update capability | Expected visible action and cleanup presentation |
| --- | --- | --- | --- | --- |
| `VERIFY-PROTOCOL-PRESENTATION-001` | `UPDATE_STATE_MALFORMED`; exact sources=`RED-090, RED-094, RED-098, RED-102, RED-106, RED-110, SEM-003`; exact authority/retryability/cleanup set=`NEW/RETRYABLE/DELETE_OWNED_TEMPORARY; NONE/NOT_RETRYABLE/NONE; PRIOR/NOT_RETRYABLE/QUARANTINE_INVALID_ARTIFACT; PRIOR/RETRYABLE/DELETE_OWNED_TEMPORARY` | `Fișierul de stare al actualizatorului este deteriorat. Cod: {id}` | `yes/no/no` | Retry enabled only for RETRYABLE input and disabled for NOT_RETRYABLE input; DELETE_OWNED_TEMPORARY => Protocol deletes its temporary; no user cleanup; NONE => no cleanup action; QUARANTINE_INVALID_ARTIFACT => repair guidance; Protocol owns quarantine; guidance=`repair guidance; cleanup presentation comes only from the runtime result` |
| `VERIFY-PROTOCOL-PRESENTATION-002` | `UPDATE_STATE_QUARANTINED`; exact sources=`SEM-026`; exact authority/retryability/cleanup set=`NEW/NOT_RETRYABLE/RETAIN_DIAGNOSTIC` | `Starea nevalidă a actualizatorului a fost izolată. Cod: {id}` | `yes/no/no` | Retry hidden or disabled; RETAIN_DIAGNOSTIC => safe correlation/support only; guidance=`repair; retain diagnostic 30 days` |
| `VERIFY-PROTOCOL-PRESENTATION-003` | `UPDATE_STATE_PERSISTENCE_FAILED`; exact sources=`RED-001, RED-005, RED-009, RED-013, RED-017, RED-021, RED-025, RED-029, RED-033, RED-037, RED-041, RED-045, RED-049, RED-053, RED-056, RED-059, RED-062, RED-065, RED-068, RED-071, RED-074, RED-078, RED-082, RED-086`; exact authority/retryability/cleanup set=`NEW/RETRYABLE/DELETE_OWNED_TEMPORARY; NONE/NOT_RETRYABLE/NONE; NONE/RETRYABLE/DELETE_OWNED_TEMPORARY; PRIOR/RETRYABLE/DELETE_OWNED_TEMPORARY; PRIOR/RETRYABLE/NONE; PRIOR/RETRYABLE/RETRY_OWNED_CLEANUP` | `Starea actualizatorului nu a putut fi salvată. Cod: {id}` | `yes/no/no` | Retry enabled only for RETRYABLE input and disabled for NOT_RETRYABLE input; DELETE_OWNED_TEMPORARY => Protocol deletes its temporary; no user cleanup; NONE => no cleanup action; RETRY_OWNED_CLEANUP => storage-repair guidance only; ProtocolWriterV1 owns cleanup; guidance=`storage-repair guidance; cleanup presentation comes only from the runtime result` |
| `VERIFY-PROTOCOL-PRESENTATION-004` | `OBSERVATION_PUBLICATION_FAILED`; exact sources=`SEM-027, SEM-028, SEM-029`; exact authority/retryability/cleanup set=`NEW/RETRYABLE/NONE` | `Rezultatul actualizării a fost salvat, dar nu poate fi afișat. Cod: {id}` | `yes/yes/repair-only` | Retry enabled for the new explicit operation; no automatic retry; NONE => no cleanup action; guidance=`retry visibility comes only from the runtime result; no Productization cleanup` |
| `VERIFY-PROTOCOL-PRESENTATION-005` | `UPDATE_CHECK_FAILED`; exact sources=`SEM-023`; exact authority/retryability/cleanup set=`PRIOR/RETRYABLE/NONE` | `Verificarea actualizărilor a eșuat. Cod: {id}` | `yes/yes/repair-only` | Retry enabled for the new explicit operation; no automatic retry; NONE => no cleanup action; guidance=`retry visibility comes only from the runtime result; no cleanup` |
| `VERIFY-PROTOCOL-PRESENTATION-006` | `UPDATE_OPERATION_INTERRUPTED`; exact sources=`SEM-030`; exact authority/retryability/cleanup set=`PRIOR/RETRYABLE/NONE` | `Operația de actualizare a fost întreruptă. Cod: {id}` | `yes/yes/repair-only` | Retry enabled for the new explicit operation; no automatic retry; NONE => no cleanup action; guidance=`explicit recheck` |
| `VERIFY-PROTOCOL-PRESENTATION-007` | `UPDATE_METADATA_RECHECK_REQUIRED`; exact sources=`SEM-031`; exact authority/retryability/cleanup set=`PRIOR/RETRYABLE/NONE` | `Metadatele actualizării trebuie verificate din nou. Cod: {id}` | `yes/yes/repair-only` | Retry enabled for the new explicit operation; no automatic retry; NONE => no cleanup action; guidance=`manual recheck; discard candidate` |
| `VERIFY-PROTOCOL-PRESENTATION-008` | `UPDATE_DOWNLOAD_INTERRUPTED`; exact sources=`SEM-032`; exact authority/retryability/cleanup set=`PRIOR/RETRYABLE/DELETE_OWNED_TEMPORARY` | `Descărcarea actualizării a fost întreruptă. Cod: {id}` | `yes/yes/repair-only` | Retry enabled for the new explicit operation; no automatic retry; DELETE_OWNED_TEMPORARY => Protocol deletes its temporary; no user cleanup; guidance=`recheck/download; delete partial` |
| `VERIFY-PROTOCOL-PRESENTATION-009` | `UPDATE_DOWNLOAD_FAILED`; exact sources=`SEM-024`; exact authority/retryability/cleanup set=`PRIOR/RETRYABLE/DELETE_OWNED_TEMPORARY` | `Descărcarea actualizării a eșuat. Cod: {id}` | `yes/yes/repair-only` | Retry enabled for the new explicit operation; no automatic retry; DELETE_OWNED_TEMPORARY => Protocol deletes its temporary; no user cleanup; guidance=`retry visibility comes only from the runtime result; Protocol owns temporary cleanup` |
| `VERIFY-PROTOCOL-PRESENTATION-010` | `UPDATE_MANIFEST_INCOMPATIBLE`; exact sources=`SEM-025`; exact authority/retryability/cleanup set=`PRIOR/NOT_RETRYABLE/NONE` | `Actualizarea nu este compatibilă cu această versiune. Cod: {id}` | `yes/yes/yes` | Retry hidden or disabled; NONE => no cleanup action; guidance=`newer compatible metadata; discard` |
| `VERIFY-PROTOCOL-PRESENTATION-011` | `RETAINED_INSTALLER_MISSING`; exact sources=`SEM-001`; exact authority/retryability/cleanup set=`NONE/RETRYABLE/NONE` | `Instalatorul verificat nu mai este disponibil. Cod: {id}` | `yes/yes/yes` | Retry enabled for the new explicit operation; no automatic retry; NONE => no cleanup action; guidance=`fresh-download guidance; no Productization cleanup` |
| `VERIFY-PROTOCOL-PRESENTATION-012` | `RETAINED_INSTALLER_INVALID`; exact sources=`RED-004, RED-008, RED-012, RED-016, RED-020, RED-024, RED-028, RED-032, RED-036, RED-040, RED-044, RED-048, RED-052, RED-077, RED-081, RED-085, RED-089, RED-093, RED-097, RED-101, RED-105, RED-109, RED-113, SEM-006`; exact authority/retryability/cleanup set=`NEW/RETRYABLE/DELETE_OWNED_TEMPORARY; NONE/NOT_RETRYABLE/NONE; NONE/RETRYABLE/DELETE_OWNED_TEMPORARY; PRIOR/NOT_RETRYABLE/REVALIDATE; PRIOR/RETRYABLE/DELETE_OWNED_TEMPORARY; PRIOR/RETRYABLE/NONE; PRIOR/RETRYABLE/RETRY_OWNED_CLEANUP` | `Instalatorul păstrat nu mai este valid. Cod: {id}` | `yes/yes/yes` | Retry enabled only for RETRYABLE input and disabled for NOT_RETRYABLE input; DELETE_OWNED_TEMPORARY => Protocol deletes its temporary; no user cleanup; NONE => no cleanup action; RETRY_OWNED_CLEANUP => storage-repair guidance only; ProtocolWriterV1 owns cleanup; REVALIDATE => recheck or fresh-operation guidance; Protocol owns revalidation; guidance=`fresh-download guidance; cleanup and revalidation presentation come only from the runtime result` |
| `VERIFY-PROTOCOL-PRESENTATION-013` | `RETAINED_INSTALLER_HASH_MISMATCH`; exact sources=`SEM-011`; exact authority/retryability/cleanup set=`PRIOR/RETRYABLE/QUARANTINE_INVALID_ARTIFACT` | `Instalatorul păstrat nu corespunde verificării. Cod: {id}` | `yes/yes/yes` | Retry enabled for the new explicit operation; no automatic retry; QUARANTINE_INVALID_ARTIFACT => repair guidance; Protocol owns quarantine; guidance=`fresh download; quarantine` |
| `VERIFY-PROTOCOL-PRESENTATION-014` | `RETAINED_INSTALLER_REVALIDATION_FAILED`; exact sources=`SEM-012`; exact authority/retryability/cleanup set=`PRIOR/RETRYABLE/REVALIDATE` | `Instalatorul păstrat nu a trecut reverificarea. Cod: {id}` | `yes/yes/yes` | Retry enabled for the new explicit operation; no automatic retry; REVALIDATE => recheck or fresh-operation guidance; Protocol owns revalidation; guidance=`recheck or fresh-download guidance; Protocol owns revalidation` |
| `VERIFY-PROTOCOL-PRESENTATION-015` | `HANDOFF_RECEIPT_MISSING`; exact sources=`SEM-002, SEM-008`; exact authority/retryability/cleanup set=`NONE/RETRYABLE/NONE` | `Confirmarea pornirii instalării lipsește. Cod: {id}` | `yes/yes/no` | Retry enabled for the new explicit operation; no automatic retry; NONE => no cleanup action; guidance=`repair; retain bytes non-executable` |
| `VERIFY-PROTOCOL-PRESENTATION-016` | `HANDOFF_RECEIPT_MALFORMED`; exact sources=`RED-091, RED-095, RED-099, RED-103, RED-107, RED-111, SEM-004`; exact authority/retryability/cleanup set=`NEW/RETRYABLE/DELETE_OWNED_TEMPORARY; NONE/NOT_RETRYABLE/NONE; PRIOR/NOT_RETRYABLE/QUARANTINE_INVALID_ARTIFACT; PRIOR/RETRYABLE/DELETE_OWNED_TEMPORARY` | `Confirmarea pornirii instalării este deteriorată. Cod: {id}` | `yes/yes/no` | Retry enabled only for RETRYABLE input and disabled for NOT_RETRYABLE input; DELETE_OWNED_TEMPORARY => Protocol deletes its temporary; no user cleanup; NONE => no cleanup action; QUARANTINE_INVALID_ARTIFACT => repair guidance; Protocol owns quarantine; guidance=`repair guidance; cleanup presentation comes only from the runtime result` |
| `VERIFY-PROTOCOL-PRESENTATION-017` | `HANDOFF_RECEIPT_PERSISTENCE_FAILED`; exact sources=`RED-002, RED-006, RED-010, RED-014, RED-018, RED-022, RED-026, RED-030, RED-034, RED-038, RED-042, RED-046, RED-050, RED-054, RED-057, RED-060, RED-063, RED-066, RED-069, RED-072, RED-075, RED-079, RED-083, RED-087`; exact authority/retryability/cleanup set=`NEW/RETRYABLE/DELETE_OWNED_TEMPORARY; NONE/NOT_RETRYABLE/NONE; NONE/RETRYABLE/DELETE_OWNED_TEMPORARY; PRIOR/RETRYABLE/DELETE_OWNED_TEMPORARY; PRIOR/RETRYABLE/NONE; PRIOR/RETRYABLE/RETRY_OWNED_CLEANUP` | `Starea instalării nu a putut fi salvată. Cod: {id}` | `yes/yes/no` | Retry enabled only for RETRYABLE input and disabled for NOT_RETRYABLE input; DELETE_OWNED_TEMPORARY => Protocol deletes its temporary; no user cleanup; NONE => no cleanup action; RETRY_OWNED_CLEANUP => storage-repair guidance only; ProtocolWriterV1 owns cleanup; guidance=`storage-repair guidance; cleanup presentation comes only from the runtime result; launch nothing` |
| `VERIFY-PROTOCOL-PRESENTATION-018` | `HANDOFF_RECEIPT_STALE`; exact sources=`SEM-013`; exact authority/retryability/cleanup set=`PRIOR/RETRYABLE/RETAIN_DIAGNOSTIC` | `Confirmarea veche a instalării a expirat. Cod: {id}` | `yes/yes/repair-only` | Retry enabled for the new explicit operation; no automatic retry; RETAIN_DIAGNOSTIC => safe correlation/support only; guidance=`recheck guidance; expose only the safe retained diagnostic` |
| `VERIFY-PROTOCOL-PRESENTATION-019` | `HANDOFF_LINEAGE_MISMATCH`; exact sources=`SEM-007`; exact authority/retryability/cleanup set=`PRIOR/NOT_RETRYABLE/QUARANTINE_INVALID_ARTIFACT` | `Confirmarea instalării nu corespunde actualizării. Cod: {id}` | `yes/yes/no` | Retry hidden or disabled; QUARANTINE_INVALID_ARTIFACT => repair guidance; Protocol owns quarantine; guidance=`repair; quarantine receipt` |
| `VERIFY-PROTOCOL-PRESENTATION-020` | `HANDOFF_PROCESS_IDENTITY_MISMATCH`; exact sources=`SEM-014`; exact authority/retryability/cleanup set=`PRIOR/NOT_RETRYABLE/NONE` | `Procesul instalatorului nu poate fi identificat sigur. Cod: {id}` | `yes/yes/no` | Retry hidden or disabled; NONE => no cleanup action; guidance=`repair; no mutation` |
| `VERIFY-PROTOCOL-PRESENTATION-021` | `HANDOFF_PROCESS_IDENTITY_UNAVAILABLE`; exact sources=`SEM-015`; exact authority/retryability/cleanup set=`PRIOR/RETRYABLE/NONE` | `Identitatea procesului instalatorului nu poate fi citită. Cod: {id}` | `yes/yes/no` | Retry enabled for the new explicit operation; no automatic retry; NONE => no cleanup action; guidance=`explicit recheck; terminate/await child` |
| `VERIFY-PROTOCOL-PRESENTATION-022` | `HANDOFF_PROCESS_NOT_OBSERVED`; exact sources=`SEM-016`; exact authority/retryability/cleanup set=`PRIOR/NOT_RETRYABLE/RETAIN_DIAGNOSTIC` | `Procesul instalatorului nu mai este activ. Cod: {id}` | `yes/yes/no` | Retry hidden or disabled; RETAIN_DIAGNOSTIC => safe correlation/support only; guidance=`manual recovery; retain truthful receipt` |
| `VERIFY-PROTOCOL-PRESENTATION-023` | `INSTALLER_HANDOFF_CANCELLED`; exact sources=`SEM-033`; exact authority/retryability/cleanup set=`PRIOR/NOT_RETRYABLE/RETAIN_DIAGNOSTIC` | `Pornirea instalării a fost anulată.` | `yes/yes/yes` | Retry hidden or disabled; RETAIN_DIAGNOSTIC => safe correlation/support only; guidance=`no Retry control for this result; a later handoff is a new explicit operation; retain the safe diagnostic` |
| `VERIFY-PROTOCOL-PRESENTATION-024` | `INSTALLER_PRELAUNCH_VERIFICATION_FAILED`; exact sources=`SEM-017`; exact authority/retryability/cleanup set=`PRIOR/RETRYABLE/QUARANTINE_INVALID_ARTIFACT` | `Instalatorul nu mai poate fi verificat. Cod: {id}` | `yes/yes/yes` | Retry enabled for the new explicit operation; no automatic retry; QUARANTINE_INVALID_ARTIFACT => repair guidance; Protocol owns quarantine; guidance=`fresh-download guidance; Protocol owns quarantine` |
| `VERIFY-PROTOCOL-PRESENTATION-025` | `INSTALLER_PROCESS_START_FAILED`; exact sources=`SEM-034`; exact authority/retryability/cleanup set=`PRIOR/RETRYABLE/RETAIN_DIAGNOSTIC` | `Instalatorul nu a putut fi pornit. Cod: {id}` | `yes/yes/repair-only` | Retry enabled for the new explicit operation; no automatic retry; RETAIN_DIAGNOSTIC => safe correlation/support only; guidance=`recheck; retain trusted bytes non-executable` |
| `VERIFY-PROTOCOL-PRESENTATION-026` | `INSTALLER_RECEIPT_TIMEOUT`; exact sources=`SEM-018`; exact authority/retryability/cleanup set=`PRIOR/RETRYABLE/NONE` | `Confirmarea pornirii instalării nu a sosit la timp. Cod: {id}` | `yes/yes/repair-only` | Retry enabled for the new explicit operation; no automatic retry; NONE => no cleanup action; guidance=`explicit recheck; installer exits unchanged` |
| `VERIFY-PROTOCOL-PRESENTATION-027` | `INSTALLER_MUTEX_TIMEOUT`; exact sources=`SEM-019`; exact authority/retryability/cleanup set=`PRIOR/RETRYABLE/NONE` | `Aplicația nu s-a închis la timp pentru instalare. Cod: {id}` | `yes/yes/repair-only` | Retry enabled for the new explicit operation; no automatic retry; NONE => no cleanup action; guidance=`explicit recheck; installer exits unchanged` |
| `VERIFY-PROTOCOL-PRESENTATION-028` | `HEALTH_RECEIPT_MALFORMED`; exact sources=`RED-092, RED-096, RED-100, RED-104, RED-108, RED-112, SEM-005`; exact authority/retryability/cleanup set=`NEW/RETRYABLE/DELETE_OWNED_TEMPORARY; NONE/NOT_RETRYABLE/NONE; PRIOR/NOT_RETRYABLE/QUARANTINE_INVALID_ARTIFACT; PRIOR/RETRYABLE/DELETE_OWNED_TEMPORARY` | `Starea actualizării nu poate fi verificată. Cod: {id}` | `yes/yes/no` | Retry enabled only for RETRYABLE input and disabled for NOT_RETRYABLE input; DELETE_OWNED_TEMPORARY => Protocol deletes its temporary; no user cleanup; NONE => no cleanup action; QUARANTINE_INVALID_ARTIFACT => repair guidance; Protocol owns quarantine; guidance=`repair guidance; cleanup presentation comes only from the runtime result` |
| `VERIFY-PROTOCOL-PRESENTATION-029` | `HEALTH_RECEIPT_PERSISTENCE_FAILED`; exact sources=`RED-003, RED-007, RED-011, RED-015, RED-019, RED-023, RED-027, RED-031, RED-035, RED-039, RED-043, RED-047, RED-051, RED-055, RED-058, RED-061, RED-064, RED-067, RED-070, RED-073, RED-076, RED-080, RED-084, RED-088`; exact authority/retryability/cleanup set=`NEW/RETRYABLE/DELETE_OWNED_TEMPORARY; NONE/NOT_RETRYABLE/NONE; NONE/RETRYABLE/DELETE_OWNED_TEMPORARY; PRIOR/RETRYABLE/DELETE_OWNED_TEMPORARY; PRIOR/RETRYABLE/NONE; PRIOR/RETRYABLE/RETRY_OWNED_CLEANUP` | `Starea verificării noii versiuni nu a putut fi salvată. Cod: {id}` | `yes/yes/no` | Retry enabled only for RETRYABLE input and disabled for NOT_RETRYABLE input; DELETE_OWNED_TEMPORARY => Protocol deletes its temporary; no user cleanup; NONE => no cleanup action; RETRY_OWNED_CLEANUP => storage-repair guidance only; ProtocolWriterV1 owns cleanup; guidance=`storage-repair guidance; cleanup presentation comes only from the runtime result; stop validation` |
| `VERIFY-PROTOCOL-PRESENTATION-030` | `HEALTH_INITIALIZATION_LINEAGE_MISSING`; exact sources=`SEM-010`; exact authority/retryability/cleanup set=`NONE/NOT_RETRYABLE/RETAIN_DIAGNOSTIC` | `Confirmarea noii versiuni lipsește. Cod: {id}` | `yes/yes/no` | Retry hidden or disabled; RETAIN_DIAGNOSTIC => safe correlation/support only; guidance=`repair; create no health receipt` |
| `VERIFY-PROTOCOL-PRESENTATION-031` | `HEALTH_INITIALIZATION_LINEAGE_MISMATCH`; exact sources=`SEM-009`; exact authority/retryability/cleanup set=`PRIOR/NOT_RETRYABLE/RETAIN_DIAGNOSTIC` | `Confirmarea noii versiuni nu corespunde instalării. Cod: {id}` | `yes/yes/no` | Retry hidden or disabled; RETAIN_DIAGNOSTIC => safe correlation/support only; guidance=`repair; create no health receipt` |
| `VERIFY-PROTOCOL-PRESENTATION-032` | `HEALTH_VALIDATION_TIMEOUT`; exact sources=`SEM-020`; exact authority/retryability/cleanup set=`PRIOR/RETRYABLE/RETAIN_DIAGNOSTIC` | `Verificarea noii versiuni nu s-a încheiat la timp. Cod: {id}` | `yes/yes/no` | Retry enabled for the new explicit operation; no automatic retry; RETAIN_DIAGNOSTIC => safe correlation/support only; guidance=`recovery; abandon receipt` |
| `VERIFY-PROTOCOL-PRESENTATION-033` | `HEALTH_VALIDATION_INTERRUPTED`; exact sources=`SEM-021`; exact authority/retryability/cleanup set=`PRIOR/RETRYABLE/RETAIN_DIAGNOSTIC` | `Verificarea noii versiuni a fost întreruptă. Cod: {id}` | `yes/yes/no` | Retry enabled for the new explicit operation; no automatic retry; RETAIN_DIAGNOSTIC => safe correlation/support only; guidance=`recovery; abandon receipt` |
| `VERIFY-PROTOCOL-PRESENTATION-034` | `HEALTH_VALIDATION_FAILED`; exact sources=`SEM-022`; exact authority/retryability/cleanup set=`PRIOR/NOT_RETRYABLE/RETAIN_DIAGNOSTIC` | `Noua versiune nu a trecut verificarea de pornire. Cod: {id}` | `yes/yes/no` | Retry hidden or disabled; RETAIN_DIAGNOSTIC => safe correlation/support only; guidance=`manual recovery; retain diagnostic` |
| `VERIFY-PROTOCOL-PRESENTATION-CLOSURE` | enumerate the closed 34-member `PersistenceFormatErrorCodeV1` and the preceding presentation cases | exactly 34 Protocol codes, 34 presentation rows, and 34 material verification rows; missing=0; Productization-only=0; duplicate=0; serialized-name mismatch=0 | every capability cell is one exact `yes/no/repair-only` triple | every action consumes only the runtime authority/retryability/cleanup fields; no code-derived retry or cleanup |
Every implementation phase consuming a protocol artifact must execute the applicable row
in addition to its focused tests. Tests cannot override this chapter's normative result.

### 14.9 Domain security, logging, offline behavior, and Productization presentation catalog

This subsection defines separate Productization-domain categories and does not extend the
closed Protocol V6 error inventory in Section 14.6. Settings/security narrative is
normative only for its domain; it cannot define Protocol-owned persistence,
synchronization, restart, timeout, recovery, cleanup, or error precedence.

Defaults are: startup application update check enabled; automatic verified download
disabled; automatic installation disabled; stable channel fixed; source-data check
enabled once per 24 hours; notifications enabled. Users may disable startup/source
checks. Manual Check for Updates always works. Automatic installation is never present.

Security mitigations are normative:

- server/MITM/DNS/mirror: fixed host, TLS, detached Ed25519, Authenticode;
- malformed/duplicate/oversized data: strict bounded parsers before semantic use;
- path traversal/reparse/local tampering: fixed roots, component validation, exclusive
  creation, reparse rejection, retained handles, final identity/hash verification;
- downgrade/replay: SemVer plus monotonic signed sequence and installed-version state;
- partial/hash/signature mismatch: never rename to verified and never execute;
- installer TOCTOU: verified file handle and immediate pre-launch revalidation;
- release-note injection: plain text rendered in a text widget, no HTML;
- credential leakage: credentials remain in provider authority, redacted environment,
  no request/response bodies, client reprs, or raw exceptions in telemetry.

The strong threat boundary is remote authenticity, not a compromised Windows user.
Guaranteed properties are Ed25519 authenticity of accepted manifests/bundles, exact
payload hash/size, Authenticode publisher checking, rejection of observed downgrade or
replay, detection of modified signed artifacts whenever reverified, and safe failure.
A malicious process running as the same user can modify profile files, reset highest-seen
sequence caches, replace per-user binaries, or alter process memory; V1 cannot guarantee
immutable binaries, unresettable counters, or protection from arbitrary same-user file
replacement. `%LOCALAPPDATA%` is never called tamper-proof. Application/source/trust
state is stored redundantly with hashes to detect accidental corruption and provide
best-effort evidence, not as a trust root. Installed executable Authenticode is checked
before update-sensitive operations and a mismatch disables update/recovery launch and
reports `Instalarea locală pare modificată. Cod: {id}`. DPAPI is not used as an integrity
mechanism. Append-only diagnostics are best-effort evidence only.

File logs are UTF-8 at the local logs path, rotating at 5 MiB, five backups, maximum
30-day retention. They record safe event ID, UTC time, app version, stage, category,
neutral outcome, update version/hash prefix, and elapsed time. They exclude API keys,
headers, provider/generated bodies, full signed payloads, and unnecessary private paths.
Users see a random 128-bit support ID. An explicit support bundle includes redacted
logs, version, settings schema status, and checksums, never credentials/database/content.

The following table is a GUI localization/catalog continuation of Section 14.6.
Unparenthesized categories are display groupings, never alternative public codes; for any
persistence/cross-process event, Productization consumes the exact Protocol V6-selected
code and runtime result fields, then emits only Section 14.6's message, capability, and
closed presentation projections.

| Category | Safe Romanian message | Retry | Continue/restart |
| --- | --- | --- | --- |
| Scout failure | `Căutarea nu a putut fi finalizată. Cod: {id}` | yes | continue |
| Editor validation | `Datele Editorului nu sunt valide. Cod: {id}` | after edit | continue |
| Editor execution | `Generarea Editorului a eșuat. Cod: {id}` | yes | continue |
| Report open | `Raportul nu poate fi deschis. Cod: {id}` | yes | continue |
| Configuration | `Configurația nu este validă. Cod: {id}` | after edit | continue |
| Update unavailable | `Serviciul de actualizare nu este disponibil.` | yes | continue |
| Metadata invalid | `Actualizarea nu a putut fi verificată. Cod: {id}` | yes | continue |
| Download failed | `Descărcarea actualizării a eșuat. Cod: {id}` | yes | continue |
| Verification failed | `Actualizarea nu este de încredere și nu va fi instalată. Cod: {id}` | recheck | continue |
| Installation failed | `Instalarea actualizării a eșuat. Cod: {id}` | yes | continue/repair |
| Migration failed | `Datele nu au putut fi actualizate în siguranță. Cod: {id}` | no | restart after support |
| Partial installer failure | `Instalarea poate fi incompletă. Folosiți opțiunile de reparare. Cod: {id}` | manual recovery | restart/repair |
| Recovery available | `Este disponibil un instalator anterior verificat.` | explicit consent | repair |
| Local installation modified | `Instalarea locală pare modificată. Cod: {id}` | reinstall | stop updates |
| Trust metadata invalid | `Autoritatea de actualizare nu a putut fi verificată. Cod: {id}` | recheck | continue |
| Release key revoked | `Cheia acestei actualizări a fost revocată. Cod: {id}` | no | continue |
| Database newer | `Baza de date necesită o versiune mai nouă a aplicației.` | no | reports only |
| Migration backup failed | `Copia de siguranță a bazei de date a eșuat. Cod: {id}` | after space/permission fix | reports only |
| Source bundle incompatible | `Lista de surse nu este compatibilă cu această versiune.` | app update | keep active |
| Source rollback failed | `Lista anterioară de surse nu a putut fi restaurată. Cod: {id}` | retry | keep active |
| Source rollback completed | `Lista anterioară de surse a fost restaurată.` | not applicable | continue |
| Download cancelled (`UPDATE_DOWNLOAD_CANCELLED`) | `Descărcarea actualizării a fost anulată.` | yes | application continues; updates enabled |
| Sequence equivocation (`METADATA_SEQUENCE_EQUIVOCATION`) | `Metadatele de actualizare sunt contradictorii. Cod: {id}` | newer metadata only | application continues; affected updates disabled |
| Metadata replay (`METADATA_REPLAY`) | `Au fost respinse metadate de actualizare mai vechi. Cod: {id}` | fresh check | application continues; candidate rejected |
| Active source pointer invalid (`SOURCE_ACTIVE_POINTER_INVALID`) | `Lista activă de surse nu este validă. Cod: {id}` | automatic recovery once | application continues with recovered/default sources |
| Bundled source fallback (`SOURCE_DEFAULT_FALLBACK`) | `Se folosesc sursele incluse în aplicație.` | manual refresh | application continues; remote source activation disabled until valid |
| Source audit recovery (`SOURCE_AUDIT_RECOVERED`) | `Istoricul activării surselor a fost refăcut.` | not applicable | application continues |
| Legacy DB unsupported (`LEGACY_SCHEMA_UNSUPPORTED`) | `Baza de date existentă nu are un format acceptat. Cod: {id}` | support/export | writes disabled; reports/support available |
| Root recovery required (`ROOT_RECOVERY_REQUIRED`) | `Autoritatea de actualizare trebuie reparată.` | recovery installer | application continues; update/source disabled |
| Root recovery failed (`ROOT_RECOVERY_FAILED`) | `Repararea autorității de actualizare a eșuat. Cod: {id}` | manual reinstall | application continues; update/source disabled |
| Trust hierarchy disabled (`TRUST_HIERARCHY_DISABLED`) | `Actualizările sunt dezactivate până la repararea autorității.` | repair | application continues; update/source disabled |
| Mutable trust invalid (`MUTABLE_TRUST_STORE_INVALID`) | `Starea autorității de actualizare nu este validă. Cod: {id}` | repair | application continues; update/source disabled |
| Trust transition receipt invalid (`TRUST_TRANSITION_RECEIPT_INVALID`) | `Tranziția autorității nu poate fi verificată. Cod: {id}` | repair/reinstall | application continues; update/source disabled |
| Root recovery unavailable (`ROOT_RECOVERY_COMPONENT_UNAVAILABLE`) | `Instrumentul de reparare a autorității nu este disponibil.` | manual trusted reinstall | application continues; update/source disabled |
| Bootstrap trust missing (`BOOTSTRAP_TRUST_RESOURCE_MISSING`) | `Resursa inițială de încredere lipsește. Cod: {id}` | reinstall | application continues offline; update/source disabled |
| Development trust rejected (`DEVELOPMENT_TRUST_IN_STABLE_BUILD`) | `Pachetul stabil conține o resursă de dezvoltare nepermisă.` | rebuild | stable build/start fails |
| Internal GUI defect | `Aplicația a întâmpinat o eroare internă. Cod: {id}` | restart | continue if safe |

No production dialog shows a traceback. Offline launch never waits for updates. Local
database/reports and deterministic Scout facilities remain available. Network polling
fails through Scout's result model; OpenAI fails through the verified provider boundary;
Ollama works when its local service/model exists. Cached verified source data remains
active. Manual update check reports unavailable without harming the application.

## 15. Test architecture

Deterministic unit tests cover path/config/version authorities, controllers, view models,
finite errors, passive imports, and denial of environment/socket/client access at help
and import. Tk tests create a withdrawn root on Windows CI; controller tests inject a
synchronous executor/clock/transport. Worker tests cover state transitions, duplicate
runs, cancellation, close while running, queue delivery, and zero widget access from
workers. UI tests cover navigation, button states, Update Center, keyboard/accessibility,
200% DPI, Romanian resources, and no traceback. A small Windows UI Automation smoke test
is separate from domain tests.

Packaging tests build from a clean wheel and verify GUI start, no console window,
resource lookup, non-ASCII/long writable paths, read-only install tree, CLI and
`editor-run`, fake/offline Scout and Editor composition, version parity, icon/version
resources, installer upgrade, and uninstall's preserve/remove-data choices. No provider
live execution is required.

The updater harness injects a local fake transport and fake process launcher and covers:
no update, available update, malformed/duplicate/oversized manifest, bad signature/hash/
size, wrong host, redirect, downgrade, replay, incompatible minimum, timeout, interruption,
disk full, cancellation, decline, cache expiry, and disabled startup. Executor tests prove
a startup check delays neither Scout nor Editor, startup/manual attach to one HTTP request,
downloads serialize independently of application work, and both executors shut down once.

Installer safety tests cover reparse components, file-ID/volume/size/hash changes,
replacement immediately before launch, restrictive share-mode behavior, path-based
residual-race documentation, pre-launch rejection leaving installation unchanged, Inno
failure never reporting automatic rollback, manual previous-installer recovery, retention,
and full authenticity revalidation. Local-threat tests cover detected executable change,
corrupt/reset sequence caches, explicit reset recovery, and the documented same-user
limitation. Disposable Windows VMs exercise install failures at multiple phases without
asserting unsupported transactional restoration.

Source tests cover exact JCS manifest and detached signature, duplicate YAML keys before
construction, aliases, anchors, merges, tags, Python constructors, nesting/node/size
limits, NFC collisions, scalar restrictions, URL policy, schema/count/hash/signature and
compatibility failures, override operations, atomic activation, audit, retention, and
successful/failed rollback. Migration tests cover every supported source version, newer
database, missing step, lock contention, space/backup/backup-validation failures,
migration exception, foreign-key/quick-check failure, transaction rollback, preserved
original/backup, and restart idempotency. Trust tests cover active/expired/revoked release
keys, root-signed rotation/revocation, stale/invalid trust sequence, offline expiry,
compromised release-key recovery, and Authenticode recovery for root compromise.
Cryptographic fixtures use only development keys.

Frozen Protocol V6 owns runtime-protocol verification and frozen Persistence V6 owns
wire/store verification. Every consuming roadmap phase runs those frozen matrices plus
Section 14.8's Productization presentation matrix and its domain-specific tests.

Version tests prove the pre-5.5D About surface and logging have no version consumer, then
Phase 5.5D wires package, CLI, GUI About, and logging to exactly one projection before any
packaging consumer. Later PyInstaller, Inno, manifest, artifact, log, and release fixtures
must consume that projection without parsing `pyproject.toml`; roadmap lint rejects any
version-consuming row before Phase 5.5D or an unlisted consumer path.

## 16. Release and key operations

The stable release sequence is exact:

1. start from a verified clean baseline, update only canonical `project.version`, and
   commit `Release Pastila Scout <version>`;
2. run full offline, GUI, security, packaging, and installer-upgrade tests;
3. create immutable signed candidate tag `v<version>-rc.1` on that source commit;
4. build final wheel/one-folder application and installer exactly once from that tag in
   an isolated pinned Windows builder, embedding final version resources before signing;
5. Authenticode-sign and timestamp executable, uninstaller, and installer final bytes;
6. verify signed bytes, then calculate final sizes/hashes and Ed25519-sign payloads;
7. generate/sign an optional source bundle, then generate the canonical application
   manifest containing its final facts and sign with the authorized release key;
8. publish immutable versioned artifacts to a non-stable staging prefix;
9. download and byte/signature-verify every published artifact;
10. smoke-test fresh installation and previous-version update from published bytes;
11. atomically publish the already signed stable manifest pointer;
12. create signed final tag `v<version>` on the same source commit only after published
    verification; its annotation records application/source/trust sequences and final
    artifact hashes.

Signing never precedes final bytes and stable never exposes unsigned artifacts. Candidate
and final tags must resolve to the same source commit. A failed release increments the
version before any rebuild; different bytes are never published under the same version.
Artifact attestations link tag, builder, and hashes. Production keys use hardware-backed
custody with two-person approval. Production/development keys are separate. CI output
and artifacts never contain private keys.

## 17. Bounded implementation roadmap

The GUI cannot directly reuse `poll_once()` as a complete product result and cannot
legally import the Editor's private composition factory. Therefore a facade contract is
an explicit first milestone. `DesktopApplicationFacadeV1` owns only immutable GUI-neutral
Scout/Editor requests, safe progress events, cancellation association, and structured
results. `ScoutDesktopResultV1` contains outcome, counters, failed-source IDs, executed
period/category, and optional report reference. `EditorDesktopResultV1` contains the
unchanged public `EditorApplicationResultV1` projection. The facade performs no widget,
update, packaging, credential, or provider-specific work. Its public package is
`pastila_scout.desktop_application_v1`; composition implementations remain private.

Production desktop composition has one owner and one caller. Phase 5.3B's private
`pastila_scout.desktop_editor_v1.composition` module owns construction of the production
Scout operation supplied by verified Phase 5.2B, construction of the production Editor
operation by reusing `_compose_editor_application_runtime_v1()`, and exactly one
`DesktopApplicationFacadeV1` from those two dependencies. Its exact private boundary is
`_compose_desktop_application_facade_v1() -> DesktopApplicationFacadeV1`. It raises one
fixed private composition error from no cause when dependency or facade construction
fails. The composer is passive on import, creates no Tk object or executor, performs no
operation execution, and returns one fresh composed facade per invocation. It does not
cache a process-global facade, expose a service locator, invoke a CLI/subprocess, or
reconstruct provider composition. Phase 5.3A owns the exact private composition-error
contract; Phase 5.3C consumes that error without redefining it.

Phase 5.3B's focused test must prove passive import, explicit construction only, one
facade construction, exact identity of the selected Scout and Editor dependencies, no Tk
or executor construction, no provider/runtime duplication, no CLI/subprocess, no global
singleton, no retry or fallback, and one-construction cardinality. Phase 5.3D's focused
test must prove one startup composer call, reuse of that facade by both named shell
bindings, safe composition-failure projection, and zero composition during import or per
button activation.

Phase 5.3D is the first production GUI consumer. At explicit `pastila-scout-gui`
application startup, and never at import or first button activation, the private desktop
startup integration calls the Phase 5.3B composer exactly once before constructing the
main window, controller, or executors. The entrypoint retains that facade in its local
shell-lifetime bindings and binds it through the shell's named Scout and Editor integration
surfaces. Button actions reuse the retained facade. If composition fails, no main window,
controller, or executor is constructed: the entrypoint consumes the one private composition
error, projects the one finite Romanian startup-configuration presentation owned by Phase
5.3C, and terminates without retry, fallback, or raw exception disclosure. The
shell/controller continue to own Tk, the publication queue, and both executors. Composition
owns none of them. Windows path/state and updater composition remain their later owners and
are not absorbed by this application-facade boundary.

Common forbidden scope for every row is frozen Scout/Editor/provider semantics, GUI
business-logic duplication, fallback/routing/retry, live-provider tests, and any path not
listed in that row. “Private” API means no addition to the package `__all__`; “public”
means only the named facade types plus Phase 5.5D's exact `pastila_scout.__version__`.
Every implementation phase runs focused/full offline
tests and static gates before its stated verdict. Commit/tag actions occur only after
independent verification and outside the implementation task.

The `Prerequisite` column names every exact frozen milestone that must exist before its
row may begin. It never denotes the historical revision that introduced a concept, a
superseded Productization tag, or an unfrozen development state. A future prerequisite
must equal exactly one preceding producer row's output tag; an already frozen prerequisite
must resolve to its recorded commit before work begins. Multiple prerequisites are
conjunctive and each must satisfy the same rule.

The external Productization root for completed rows through Phase 5.3D is the frozen
Revision 10 output `phase-5-windows-desktop-productization-spec-v10-roadmap-baseline-ready`.
The external Productization root for every unfrozen row beginning with Phase 5.4A is
`phase-5-windows-desktop-productization-spec-v12-windows-state-consumption-roadmap-ready`.
Each is produced by freezing this document outside the roadmap and therefore creates no
roadmap self-dependency.

| Phase | Prerequisite | Exact authorized paths | Exact focused tests | API impact | Additional forbidden scope | Expected verdict | Commit message | Tag |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 5.1A Facade specification | `phase-5-windows-desktop-productization-spec-v10-roadmap-baseline-ready` | `docs/windows-application/DesktopApplicationFacadeSpecificationV1.md` | none; specification review | specifies public facade only | production/tests/GUI | `PHASE_5_1A_DESKTOP_APPLICATION_FACADE_SPECIFICATION_V1_READY_FOR_FREEZE` | `Specify desktop application facade V1` | `phase-5.1a-desktop-application-facade-spec-v1-ready` |
| 5.1B Facade implementation | `phase-5.1a-desktop-application-facade-spec-v1-ready` | `src/pastila_scout/desktop_application_v1/__init__.py`, `src/pastila_scout/desktop_application_v1/models.py`, `src/pastila_scout/desktop_application_v1/services.py`, `src/pastila_scout/desktop_application_v1/errors.py` | `tests/test_desktop_application_v1.py` | adds only specified public requests/results/services | Tk/widgets/HTML/paths/updates | `PHASE_5_1B_DESKTOP_APPLICATION_FACADE_REVISION_1_VERIFIED` | `Add verified desktop application facade` | `phase-5.1b-desktop-application-facade-r1-verified` |
| 5.1C Shell specification | `phase-5.1b-desktop-application-facade-r1-verified` | `docs/windows-application/DesktopShellSpecificationV1.md` | none; specification review | specifies private desktop layer | backend implementation/packaging | `PHASE_5_1C_DESKTOP_SHELL_SPECIFICATION_V1_READY_FOR_FREEZE` | `Specify Windows desktop shell V1` | `phase-5.1c-desktop-shell-spec-v1-ready` |
| 5.1D Shell implementation | `phase-5.1c-desktop-shell-spec-v1-ready` | `src/pastila_scout/desktop_v1/__init__.py`, `src/pastila_scout/desktop_v1/entrypoint.py`, `src/pastila_scout/desktop_v1/controller.py`, `src/pastila_scout/desktop_v1/models.py`, `src/pastila_scout/desktop_v1/views.py`, `src/pastila_scout/desktop_v1/resources.py`, `src/pastila_scout/desktop_v1/errors.py`, `pyproject.toml` | `tests/test_desktop_shell_v1.py` | private GUI plus `pastila-scout-gui` entry point; About has no version value | backend execution/paths/updater/version consumption | `PHASE_5_1D_DESKTOP_SHELL_REVISION_1_VERIFIED` | `Add verified Windows desktop shell` | `phase-5.1d-desktop-shell-r1-verified` |
| 5.2A Scout GUI specification | `phase-5.1d-desktop-shell-r1-verified` | `docs/windows-application/ScoutDesktopIntegrationSpecificationV1.md` | none; specification review | specifies private Scout adapter/report facade | Editor/updates | `PHASE_5_2A_SCOUT_DESKTOP_SPECIFICATION_V1_READY_FOR_FREEZE` | `Specify Scout desktop integration V1` | `phase-5.2a-scout-desktop-spec-v1-ready` |
| 5.2B Scout GUI implementation | `phase-5.2a-scout-desktop-spec-v1-ready` | `src/pastila_scout/desktop_scout_v1/__init__.py`, `src/pastila_scout/desktop_scout_v1/models.py`, `src/pastila_scout/desktop_scout_v1/service.py`, `src/pastila_scout/desktop_report_v1/__init__.py`, `src/pastila_scout/desktop_report_v1/models.py`, `src/pastila_scout/desktop_report_v1/service.py`, `src/pastila_scout/desktop_report_v1/html.py` | `tests/test_desktop_scout_v1.py`, `tests/test_desktop_report_v1.py` | facade implementation private; frozen facade unchanged | Editor/updates/existing reports | `PHASE_5_2B_SCOUT_DESKTOP_REVISION_1_VERIFIED` | `Add verified Scout desktop integration` | `phase-5.2b-scout-desktop-r1-verified` |
| 5.3A Editor GUI and desktop composition specification | `phase-5.2b-scout-desktop-r1-verified` | `docs/windows-application/EditorDesktopIntegrationSpecificationV1.md` | none; specification review | specifies the private Editor operation and sole private production `DesktopApplicationFacadeV1` composer | Tk/executors/Scout behavior/updates/provider changes/CLI reuse | `PHASE_5_3A_EDITOR_DESKTOP_SPECIFICATION_V1_READY_FOR_FREEZE` | `Specify Editor desktop integration V1` | `phase-5.3a-editor-desktop-spec-v1-ready` |
| 5.3B Editor GUI and desktop composition implementation | `phase-5.3a-editor-desktop-spec-v1-ready` | `src/pastila_scout/desktop_editor_v1/__init__.py`, `src/pastila_scout/desktop_editor_v1/models.py`, `src/pastila_scout/desktop_editor_v1/service.py`, `src/pastila_scout/desktop_editor_v1/composition.py` | `tests/test_desktop_editor_v1.py` | private Editor adapter plus sole private production facade composer | Tk/executors/Scout behavior/updates/provider changes/CLI subprocess/global state | `PHASE_5_3B_EDITOR_DESKTOP_REVISION_1_VERIFIED` | `Add verified Editor desktop integration` | `phase-5.3b-editor-desktop-r1-verified` |
| 5.3C Desktop startup integration specification | `phase-5.3b-editor-desktop-r1-verified` | `docs/windows-application/DesktopStartupIntegrationSpecificationV1.md` | none; specification review | specifies entrypoint invocation, failure presentation, facade handoff and lifetime, and unchanged shell executor ownership | backend/provider/path/update semantics/packaging/public API/composition redefinition | `PHASE_5_3C_DESKTOP_STARTUP_INTEGRATION_SPECIFICATION_V1_READY_FOR_FREEZE` | `Specify desktop startup integration V1` | `phase-5.3c-desktop-startup-integration-spec-v1-ready` |
| 5.3D Desktop startup integration implementation | `phase-5.3c-desktop-startup-integration-spec-v1-ready` | `src/pastila_scout/desktop_v1/entrypoint.py`, `src/pastila_scout/desktop_v1/resources.py` | `tests/test_desktop_startup_integration_v1.py`, `tests/test_desktop_shell_v1.py` | private startup wiring and finite Romanian startup-failure resource only; no public Python API | backend/provider/path/update semantics/packaging/CLI subprocess/singletons/service locators/controller/view/model redesign | `PHASE_5_3D_DESKTOP_STARTUP_INTEGRATION_REVISION_1_VERIFIED` | `Add verified desktop startup integration` | `phase-5.3d-desktop-startup-integration-r1-verified` |
| 5.4A Windows state specification | `phase-5.3d-desktop-startup-integration-r1-verified` and `phase-5-windows-desktop-productization-spec-v12-windows-state-consumption-roadmap-ready` | `docs/windows-application/WindowsStateSpecificationV1.md` | none; specification review | specifies private path/settings/migration APIs | packaging/updater | `PHASE_5_4A_WINDOWS_STATE_SPECIFICATION_V1_READY_FOR_FREEZE` | `Specify Windows application state V1` | `phase-5.4a-windows-state-spec-v1-ready` |
| 5.4B Windows state implementation | `phase-5.4a-windows-state-spec-v1-ready` | `src/pastila_scout/windows_state_v1/__init__.py`, `src/pastila_scout/windows_state_v1/paths.py`, `src/pastila_scout/windows_state_v1/settings.py`, `src/pastila_scout/windows_state_v1/migrations.py`, `src/pastila_scout/windows_state_v1/errors.py`, `src/pastila_scout/desktop_v1/default-settings-v1.json` | `tests/test_windows_paths_v1.py`, `tests/test_windows_settings_v1.py`, `tests/test_windows_migrations_v1.py` | private | installer/updater/source bundles | `PHASE_5_4B_WINDOWS_STATE_REVISION_1_VERIFIED` | `Add verified Windows application state` | `phase-5.4b-windows-state-r1-verified` |
| 5.4C Windows state consumption specification | `phase-5.4b-windows-state-r1-verified` | `docs/windows-application/WindowsStateConsumptionSpecificationV1.md` | none; specification review | specifies private installed/development state injection, source selection, and migration presentation | packaging/updater/source-bundle implementation/Scout semantics/GUI redesign | `PHASE_5_4C_WINDOWS_STATE_CONSUMPTION_SPECIFICATION_V1_READY_FOR_FREEZE` | `Specify Windows state consumption V1` | `phase-5.4c-windows-state-consumption-spec-v1-ready` |
| 5.4D Windows state consumption implementation | `phase-5.4c-windows-state-consumption-spec-v1-ready` | `src/pastila_scout/desktop_v1/state_composition.py`, `src/pastila_scout/desktop_v1/settings.py`, `src/pastila_scout/desktop_v1/entrypoint.py`, `src/pastila_scout/desktop_v1/views.py`, `src/pastila_scout/desktop_v1/resources.py`, `src/pastila_scout/desktop_editor_v1/composition.py`, `src/pastila_scout/desktop_scout_v1/service.py`, `src/pastila_scout/poller.py` | `tests/test_windows_state_consumption_v1.py`, `tests/test_desktop_startup_integration_v1.py`, `tests/test_desktop_shell_v1.py`, `tests/test_desktop_editor_v1.py`, `tests/test_desktop_scout_v1.py`, `tests/test_poller.py` | private state-bound desktop startup/composition only | packaging/updater/source-bundle implementation/Scout semantics/CLI/global state/service locators/GUI redesign/settings editor | `PHASE_5_4D_WINDOWS_STATE_CONSUMPTION_REVISION_1_VERIFIED` | `Add verified Windows state consumption` | `phase-5.4d-windows-state-consumption-r1-verified` |
| 5.5A Trust bootstrap specification | `phase-5.4d-windows-state-consumption-r1-verified` | `docs/windows-application/TrustBootstrapSpecificationV1.md` | none; specification review | specifies immutable non-secret bootstrap resources | private keys/updater/packaging | `PHASE_5_5A_TRUST_BOOTSTRAP_SPECIFICATION_V1_READY_FOR_FREEZE` | `Specify Windows trust bootstrap V1` | `phase-5.5a-trust-bootstrap-spec-v1-ready` |
| 5.5B Trust bootstrap materialization | `phase-5.5a-trust-bootstrap-spec-v1-ready` | `resources/trust/pastila-root-1.pub`, `resources/trust/bootstrap-root-v1.json`, `resources/trust/bootstrap-root-provenance-v1.json`, `tests/fixtures/windows-trust/development-pastila-root-1.pub`, `tests/fixtures/windows-trust/development-bootstrap-root-v1.json` | `tests/test_trust_bootstrap_resource_v1.py` | no runtime API | private material/updater/packaging/stable build without verified production public key | `PHASE_5_5B_TRUST_BOOTSTRAP_REVISION_1_VERIFIED` | `Materialize verified Windows trust bootstrap` | `phase-5.5b-trust-bootstrap-r1-verified` |
| 5.5C Version projection specification | `phase-5.5b-trust-bootstrap-r1-verified` | `docs/windows-application/VersionProjectionSpecificationV1.md` | none; specification review | specifies `pastila_scout.__version__` only | packaging/GUI redesign/second version authority | `PHASE_5_5C_VERSION_PROJECTION_SPECIFICATION_V1_READY_FOR_FREEZE` | `Specify package version projection V1` | `phase-5.5c-version-projection-spec-v1-ready` |
| 5.5D Version projection implementation | `phase-5.5c-version-projection-spec-v1-ready` | `src/pastila_scout/__init__.py`, `src/pastila_scout/cli.py`, `src/pastila_scout/logging_config.py`, `src/pastila_scout/desktop_v1/views.py`, `src/pastila_scout/desktop_v1/resources.py` | `tests/test_package_version_projection_v1.py`, `tests/test_cli.py`, `tests/test_logging.py`, `tests/test_desktop_shell_v1.py` | adds `pastila_scout.__version__`, root CLI `--version`, GUI About projection, and log projection only | other CLI/GUI/log behavior/`project.version` changes/packaging/updater | `PHASE_5_5D_VERSION_PROJECTION_REVISION_1_VERIFIED` | `Add verified package version projection` | `phase-5.5d-version-projection-r1-verified` |
| 5.5E Executable packaging specification | `phase-5.5d-version-projection-r1-verified` | `docs/windows-application/WindowsExecutablePackagingSpecificationV1.md` | none; specification review and clean Windows PyInstaller probe | no Python API | installer/updater/release publication | `PHASE_5_5E_WINDOWS_EXECUTABLE_SPECIFICATION_V1_READY_FOR_FREEZE` | `Specify Windows executable packaging V1` | `phase-5.5e-windows-executable-spec-v1-ready` |
| 5.5F Executable packaging implementation | `phase-5.5e-windows-executable-spec-v1-ready` | `packaging/pyinstaller/PastilaScout.spec`, `packaging/pyinstaller/version_info.txt.in`, `packaging/pyinstaller/build.ps1`, `packaging/resources/PastilaScout.ico`, `packaging/resources/THIRD-PARTY-NOTICES.txt` | `tests/packaging/test_frozen_application_v1.py`, `tests/packaging/test_version_parity_v1.py`, `tests/packaging/test_build_mode_v1.py` | no Python public API | installer/updater/release publication/trust generation | `PHASE_5_5F_WINDOWS_EXECUTABLE_REVISION_1_VERIFIED` | `Add verified Windows executable packaging` | `phase-5.5f-windows-executable-r1-verified` |
| 5.6A Installer specification | `phase-5.5f-windows-executable-r1-verified` | `docs/windows-application/WindowsInstallerSpecificationV1.md` | none; specification review | none | updater/download/root recovery/rollback overclaims | `PHASE_5_6A_WINDOWS_INSTALLER_SPECIFICATION_V1_READY_FOR_FREEZE` | `Specify per-user Windows installer V1` | `phase-5.6a-windows-installer-spec-v1-ready` |
| 5.6B Installer implementation | `phase-5.6a-windows-installer-spec-v1-ready` | `packaging/inno/PastilaScout.iss`, `packaging/inno/build-installer.ps1` | `tests/packaging/test_inno_installer_v1.py` | none | updater/download/root recovery/rollback overclaims | `PHASE_5_6B_WINDOWS_INSTALLER_REVISION_1_VERIFIED` | `Add verified per-user Windows installer` | `phase-5.6b-windows-installer-r1-verified` |
| 5.7A Frozen update Protocol prerequisite | `phase-4.3-editor-cli-run-r6-verified` | `docs/windows-update/WindowsUpdateProtocolSpecificationV1.md` | frozen Protocol V6 verification matrix | no Productization API | Productization/Persistence implementation | `PHASE_5_7A_WINDOWS_UPDATE_PROTOCOL_SPECIFICATION_V6_READY_FOR_FREEZE` | `Finalize Windows Update Protocol Specification V6` | `phase-5.7a-windows-update-protocol-spec-v6-ready` |
| 5.7B Frozen Persistence prerequisite | `phase-5.7a-windows-update-protocol-spec-v6-ready` | `docs/windows-update/WindowsUpdatePersistenceFormatSpecificationV1.md` | frozen Persistence V6 verification matrix | no Productization API | Productization/Protocol redesign | `PHASE_5_7B_WINDOWS_UPDATE_PERSISTENCE_FORMAT_SPECIFICATION_V6_READY_FOR_FREEZE` | `Finalize Windows Update Persistence Format Specification V6` | `phase-5.7b-windows-update-persistence-format-spec-v6-ready` |
| 5.7C Update trust contracts specification | `phase-5.6b-windows-installer-r1-verified` and `phase-5.7b-windows-update-persistence-format-spec-v6-ready` | `docs/windows-application/UpdateTrustContractsSpecificationV1.md` | none; specification review | specifies private bootstrap/active trust APIs | ordinary updater/UI/source bundles/recovery implementation | `PHASE_5_7C_UPDATE_TRUST_CONTRACTS_SPECIFICATION_V1_READY_FOR_FREEZE` | `Specify Windows update trust contracts V1` | `phase-5.7c-update-trust-contracts-spec-v1-ready` |
| 5.7D Update trust contracts implementation | `phase-5.7c-update-trust-contracts-spec-v1-ready` | `src/pastila_scout/windows_trust_v1/__init__.py`, `src/pastila_scout/windows_trust_v1/models.py`, `src/pastila_scout/windows_trust_v1/bootstrap.py`, `src/pastila_scout/windows_trust_v1/state.py`, `src/pastila_scout/windows_trust_v1/canonical.py`, `src/pastila_scout/windows_trust_v1/errors.py` | `tests/test_windows_trust_bootstrap_v1.py`, `tests/test_windows_trust_state_v1.py`, `tests/test_windows_trust_rotation_v1.py` | private | networking/UI/source bundles/recovery execution/private keys | `PHASE_5_7D_UPDATE_TRUST_CONTRACTS_REVISION_1_VERIFIED` | `Add verified Windows update trust contracts` | `phase-5.7d-update-trust-contracts-r1-verified` |
| 5.7E Ordinary updater specification | `phase-5.7d-update-trust-contracts-r1-verified` and `phase-5.7b-windows-update-persistence-format-spec-v6-ready` | `docs/windows-application/SignedUpdaterSpecificationV1.md` | none; specification review | specifies private update APIs consuming frozen Protocol/Persistence and injected trust | UI/source bundles/root recovery/release workflow | `PHASE_5_7E_SIGNED_UPDATER_SPECIFICATION_V1_READY_FOR_FREEZE` | `Specify signed Windows updater V1` | `phase-5.7e-signed-updater-spec-v1-ready` |
| 5.7F Ordinary updater implementation | `phase-5.7e-signed-updater-spec-v1-ready` | `src/pastila_scout/windows_update_v1/__init__.py`, `src/pastila_scout/windows_update_v1/models.py`, `src/pastila_scout/windows_update_v1/canonical.py`, `src/pastila_scout/windows_update_v1/persistence.py`, `src/pastila_scout/windows_update_v1/protocol.py`, `src/pastila_scout/windows_update_v1/client.py`, `src/pastila_scout/windows_update_v1/download.py`, `src/pastila_scout/windows_update_v1/launch.py`, `src/pastila_scout/windows_update_v1/state.py`, `src/pastila_scout/windows_update_v1/errors.py` | `tests/test_windows_update_persistence_v1.py`, `tests/test_windows_update_protocol_v1.py`, `tests/test_windows_update_manifest_v1.py`, `tests/test_windows_update_download_v1.py`, `tests/test_windows_update_launch_v1.py`, `tests/test_windows_update_state_v1.py` | private | widgets/source bundles/root recovery/private keys/fallback/frozen-contract changes | `PHASE_5_7F_SIGNED_UPDATER_REVISION_1_VERIFIED` | `Add verified signed Windows updater` | `phase-5.7f-signed-updater-r1-verified` |
| 5.7G Root recovery installer specification | `phase-5.7f-signed-updater-r1-verified` | `docs/windows-application/RootRecoveryInstallerSpecificationV1.md` | none; specification review | specifies private recovery protocol | GUI redesign/provider/runtime changes/ordinary-updater fallback/silent trust replacement | `PHASE_5_7G_ROOT_RECOVERY_INSTALLER_SPECIFICATION_V1_READY_FOR_FREEZE` | `Specify Windows root recovery installer V1` | `phase-5.7g-root-recovery-installer-spec-v1-ready` |
| 5.7H Root recovery installer implementation | `phase-5.7g-root-recovery-installer-spec-v1-ready` | `packaging/windows/root-recovery/PastilaScoutRootRecovery.iss`, `packaging/windows/root-recovery/PastilaScoutRootRecovery.spec`, `packaging/windows/root-recovery/build-root-recovery.ps1`, `packaging/windows/root-recovery/resources/PASTILA_ROOT_RECOVERY_V1.json`, `scripts/windows-recovery/build-root-recovery-resource.py`, `src/pastila_scout/windows_trust_v1/recovery_contracts.py`, `src/pastila_scout/windows_trust_v1/recovery_transition.py`, `src/pastila_scout/windows_trust_v1/recovery_entrypoint.py` | `tests/test_windows_trust_recovery_contracts_v1.py`, `tests/test_windows_trust_recovery_transition_v1.py`, `tests/test_windows_root_recovery_packaging_v1.py` | private | GUI redesign/provider/runtime changes/ordinary-updater fallback/silent trust replacement/private keys | `PHASE_5_7H_ROOT_RECOVERY_INSTALLER_REVISION_1_VERIFIED` | `Add verified Windows root recovery installer` | `phase-5.7h-root-recovery-installer-r1-verified` |
| 5.7I Integrated trust/recovery verification | `phase-5.7h-root-recovery-installer-r1-verified` | `docs/windows-application/TrustRecoveryVerificationRecordV1.md` | `tests/test_windows_trust_recovery_integration_v1.py` | none | production changes/GUI/source bundles/private keys/live stable publication | `PHASE_5_7I_TRUST_RECOVERY_INTEGRATION_REVISION_1_VERIFIED` | `Verify integrated Windows trust recovery` | `phase-5.7i-trust-recovery-integration-r1-verified` |
| 5.8 Update Center | `phase-5.7i-trust-recovery-integration-r1-verified` | `src/pastila_scout/desktop_v1/update_controller.py`, `src/pastila_scout/desktop_v1/update_views.py`, `src/pastila_scout/desktop_v1/views.py`, `src/pastila_scout/desktop_v1/controller.py`, `src/pastila_scout/desktop_v1/resources.py` | `tests/test_desktop_update_center_v1.py` | private GUI | trust/downloader semantics/source bundles | `PHASE_5_8_UPDATE_CENTER_REVISION_1_VERIFIED` | `Add verified desktop Update Center` | `phase-5.8-update-center-r1-verified` |
| 5.9A Source-bundle specification | `phase-5.8-update-center-r1-verified` | `docs/windows-application/SourceBundleSpecificationV1.md` | none; specification review | specifies private bundle APIs | source loader implementation/remote publication | `PHASE_5_9A_SOURCE_BUNDLE_SPECIFICATION_V1_READY_FOR_FREEZE` | `Specify signed source bundles V1` | `phase-5.9a-source-bundle-spec-v1-ready` |
| 5.9B Source-bundle implementation | `phase-5.9a-source-bundle-spec-v1-ready` | `src/pastila_scout/source_bundle_v1/__init__.py`, `src/pastila_scout/source_bundle_v1/models.py`, `src/pastila_scout/source_bundle_v1/canonical.py`, `src/pastila_scout/source_bundle_v1/yaml_loader.py`, `src/pastila_scout/source_bundle_v1/validation.py`, `src/pastila_scout/source_bundle_v1/activation.py`, `src/pastila_scout/source_bundle_v1/audit.py`, `src/pastila_scout/source_bundle_v1/errors.py`, `src/pastila_scout/desktop_v1/source_update_controller.py`, `src/pastila_scout/desktop_v1/settings.py` | `tests/test_source_bundle_manifest_v1.py`, `tests/test_source_bundle_yaml_v1.py`, `tests/test_source_bundle_activation_v1.py`, `tests/test_source_bundle_desktop_v1.py` | private | existing `config.py`/provider/source polling semantics | `PHASE_5_9B_SOURCE_BUNDLE_REVISION_1_VERIFIED` | `Add verified signed source bundles` | `phase-5.9b-source-bundle-r1-verified` |
| 5.10 Release E2E | `phase-5.9b-source-bundle-r1-verified` | `scripts/windows-release/build-release.ps1`, `scripts/windows-release/generate-manifest.py`, `scripts/windows-release/sign-release.ps1`, `.github/workflows/windows-release.yml`, `docs/windows-application/WindowsReleaseRunbookV1.md` | `tests/release/test_windows_release_manifest_v1.py`, `tests/release/test_windows_release_workflow_v1.py` | none | backend/GUI semantics/private keys/stable live publish in CI | `PHASE_5_10_WINDOWS_PRODUCT_REVISION_1_VERIFIED` | `Add verified Windows release pipeline` | `phase-5.10-windows-product-r1-verified` |

Phase 5.5E cannot freeze until its clean Windows probe records a PyInstaller version that
supports Python 3.14. Phase 5.5B requires externally generated production public root
material but never its private key. Phase 5.7F requires a provisioned development endpoint
and release key; Phase 5.7H requires independently Authenticode-authorized recovery test
fixtures. Stable publication requires the production endpoint and Authenticode
certificate. The future implementation chain is facade -> shell -> Scout -> Editor and
private facade composition -> desktop startup integration -> state -> state consumption -> trust bootstrap ->
version projection -> packaging -> installer -> trust
contracts -> updater -> root recovery -> integrated verification -> Update Center ->
source bundles -> release. Frozen Protocol 5.7A and Persistence 5.7B are already available
inputs to the explicitly named trust/updater prerequisites; they are not rerun in future
row order. No future row consumes a later artifact or absorbs later work.

## 18. Compatibility and public API policy

The GUI is additive. Existing CLI syntax/default behavior, `editor-run`, verified
application runtime composition, provider-neutral OpenAI/Ollama semantics, environment-
gated Ollama tests, SQLite data, report formats, source validation, user configuration,
and all frozen contracts remain intact. Packaging changes location resolution only when
the installed GUI/CLI composition explicitly selects installed mode; source functions
retain injected paths.

Only `pastila_scout.__version__` and immutable request/result application facades may be
public. Desktop views,
controllers, updater cryptography, source activation, path resolution, runtime handles,
provider clients, composition factories, serializer/exporter internals, and database
connections remain private product layers. No GUI invokes a CLI subprocess where an
in-process authority exists. The installer alone is an external process boundary.

## 19. Contradiction and determinism review

All load-bearing choices have one owner: Tkinter/ttk; one sidebar window; one application
executor and one update executor; AppData path authority; user-override then signed-bundle then
bundled-default precedence; `pyproject.toml` version; PyInstaller one-folder; per-user
Inno Setup; Windows x64/stable only; fixed `updates.pastila.ro` endpoint; detached
offline-root-authorized Ed25519 release keys plus Authenticode; explicit-consent manual
binary recovery; Hybrid signed source bundles; `PRAGMA user_version`; and the singular
roadmap above. There is no alternative GUI, package tool, installer, endpoint, update
channel, signature trust root, retry owner, cleanup owner, or automatic install.

Repository searches for GUI/desktop/Windows/exe/installer/MSIX/Inno/WiX/PyInstaller/
Nuitka/version/update/updater/manifest/signature/source bundle/AppData/Program Files/
startup check/rollback/migration/release found no competing production owner. Historical
docs are backend milestones and are non-normative for Phase 5. The existing project-
relative paths are explicitly development-mode defaults, not installed-mode authority.

Two independent implementers following this document must produce materially equivalent
framework, navigation, dual-executor topology, update deduplication, filesystem,
state-consumption boundary, development-config classification, source precedence,
version, build, installer, artifact names, endpoint, schema, root/release-key
trust, checks, bounded path launch, honest recovery, source parsing/activation,
`user_version` migration registry, release flow, and exact phase paths. A divergence in
any such choice is a defect, not an implementation option.
In particular they must produce identical Productization path bindings, messages,
capabilities, visible actions, bootstrap/active trust locations and precedence,
root-recovery component/resource, metadata-backed version projection, packaging inventory,
and acyclic roadmap. They must consume byte-identical Persistence V6 artifacts and exact
Protocol V6 runtime results without reconstructing either contract. Every version consumer
is wired only in or after Phase 5.5D.

Revision 4 changes only authority closure: retained-installer ownership, handoff exits and
receipt, mutable trust placement/precedence, recovery implementation scope, version
projection authorization, bootstrap production, and their tests/dependencies. It does not
change Tkinter/ttk, sidebar layout, dual executors, source-bundle schemas/precedence,
sequence acceptance, SQLite target/migration, health-stage authority, truthful Inno
rollback limits, residual TOCTOU model, Ed25519/Authenticode hierarchy, manual recovery,
or release signing/publication order.

Revision 5 refines only update-state persistence/restart, handoff-receipt recovery,
new-process health timing, and version-consumer wiring. It changes no GUI framework or
layout, executor, PyInstaller/Inno choice, updater/trust hierarchy, source-bundle contract,
SQLite authority, filesystem root, signing rule, manual rollback, or release workflow.

Revision 6 closes only persistence reconstruction, installer synchronization/process
identity, monotonic health timeout/restart resolution, and their finite failure/test
contracts. It does not change GUI framework/layout, executor ownership, provider or
credential ownership, packaging/installer selection, update trust, source bundles,
SQLite authority, filesystem roots, release signing/publication, rollback, or roadmap.

Revision 7 consolidated those contracts into Section 14. Revision 8 preserves its
Productization integration and presentation while deferring public error identity,
semantic origin, precedence, authority, retryability, cleanup, and protocol behavior to
frozen Windows Update Protocol V6. Sections 5, 8, 10, and 13 retain only domain context.
Two implementers must derive identical Productization messages, capabilities, and visible
actions from Protocol V6 plus Section 14.6, without a second semantic reduction. Revisions
7 and 8 change no GUI,
packaging, installer technology, updater cryptography, trust hierarchy, source schema,
SQLite schema, release flow, version authority, or roadmap path.

Revision 9 removes duplicated Protocol/Persistence schemas, runtime sequencing, restart,
timeout, store, error-origin, and verification ownership; retains only Productization path
binding and presentation; and closes the roadmap by reserving 5.7A/5.7B for the frozen
specifications and adding their concrete implementation paths to the signed updater phase.
It changes no wire value, Protocol projection, GUI architecture, packaging technology,
trust policy, source schema, SQLite schema, release flow, or version authority.

Revision 12 closes the Windows-state producer/consumer edge and development configuration
migration ownership. It adds the specification-first 5.4C/5.4D pair, makes 5.5A consume
verified state integration, classifies `config/config.yaml` as development-only and
non-migrating, permits only validated byte-identical `config/sources.yaml` seeding of an
absent roaming override, and makes the V12 freeze tag an external prerequisite of 5.4A.
It changes no completed milestone through 5.3D, Scout schema or runtime semantics,
settings schema, database/report/Editor authority, packaging technology, installer,
updater, trust, source-bundle cryptography, Protocol/Persistence, or release behavior.

## 20. Findings and readiness

Repository gaps found were absence of GUI, installed path authority, HTML product report,
packaging, installer, updater, signing/release infrastructure, and GUI-facing facades.
They are intentional future work and each has an exact owner and phased prerequisite
above. Revision 12 additionally reproduced and closed the missing state-consumption edge
and ambiguous development-config migration rule. No Critical, Major, or blocking Minor
specification finding remains. No production,
test, packaging, configuration, or workflow file is changed by this specification.
