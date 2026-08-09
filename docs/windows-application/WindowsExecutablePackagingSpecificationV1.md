# Windows Executable Packaging Specification V1

## 1. Authority, identity, and scope

`PKG-001` This document is the Phase 5.5E Windows Executable Packaging Specification V1.
Its prerequisite is the annotated tag `phase-5.5d-version-projection-r1-verified`, which
resolves to commit `8ad71abbbfe3dc003021c5a5bb4256bb1f71d40e`. Phase 5.5E owns exactly
this document and the mandatory external compatibility evidence defined below. It creates
no packaging implementation, Python API, test, dependency, executable, installer,
updater, publication artifact, commit, tag, or claim that the external probe has passed.

The identity reserved for a later formal freeze is:

- verdict `PHASE_5_5E_WINDOWS_EXECUTABLE_SPECIFICATION_V1_READY_FOR_FREEZE`;
- commit subject `Specify Windows executable packaging V1`;
- annotated tag `phase-5.5e-windows-executable-spec-v1-ready`.

`PKG-002` Authority is cumulative and precedence-aware. The maintained Productization
authority, frozen Windows State and State Consumption authorities, corrected single-owner
Trust Bootstrap specification and materialization, and frozen Version Projection V1 are
normative inputs. Explicit maintenance overlays prevail over conflicting historical
enterprise ceremony or provenance language without rewriting old tags. Frozen Protocol
V6 and Persistence V6 remain later updater inputs and confer no packaging ownership.

`PKG-003` The following terms have exact meanings in this specification:

- **executable package**: the complete Phase 5.5F Windows onedir output;
- **shared onedir bundle**: one directory containing shared modules and resources plus
  the two authorized launchers;
- **GUI launcher** and **console launcher**: respectively `PastilaScout.exe` and
  `pastila-scout.exe`;
- **installed application root**: `%LOCALAPPDATA%\Programs\PastilaScout\app`;
- **immutable bundled resource**: shipped input read from, but never mutated beneath,
  the installed application root;
- **mutable state**: owner-writable application data governed outside the install tree;
- **clean wheel**: a newly built standards-based wheel installed without importing from
  the source checkout;
- **clean probe environment**: a new isolated Windows x64 Python environment satisfying
  Section 10;
- **PyInstaller probe**: the complete external build and execution experiment in this
  specification;
- **probe evidence**: the non-secret external record defined in Section 16;
- **repository residue**: any probe-created or modified repository path, index entry, or
  untracked artifact;
- **hidden/dynamic import**: a required import not safely established by ordinary static
  PyInstaller analysis, including computed or `import_module` imports;
- **stable package**: an executable package whose canonical version satisfies frozen
  stable-version authority and whose resources are production resources;
- **version projection**: the one-way projection from installed distribution metadata to
  `pastila_scout.__version__` and its consumers;
- **disposable probe artifact**: probe input, output, environment, or evidence stored
  outside the repository and carrying no runtime authority.

## 2. Executable architecture and roots

`PKG-004` The target is Windows x64, built with a complete Python 3.14 distribution and a
PyInstaller version accepted by Section 9. The package is onedir only. Onefile, another
packager, a parallel bundle, and architecture-neutral or 32-bit output are forbidden.

`PKG-005` One shared onedir bundle contains exactly two launchers. The windowed launcher
is exactly `PastilaScout.exe`, uses `pastila_scout.desktop_v1.entrypoint:main`, and has no
release console. The console launcher is exactly `pastila-scout.exe` and uses
`pastila_scout.cli:main`. No third launcher or new application entry point is permitted.

`PKG-006` Installed mode derives its sole application root as
`%LOCALAPPDATA%\Programs\PastilaScout\app` through frozen State Consumption behavior.
PyInstaller extraction, loader, executable, `_MEIPASS`, current-directory, repository,
home, registry, or mutable environment paths are not application-root authority and are
never fallback roots. PyInstaller internals may locate loader-owned bundle components
only to materialize the governed installed layout; they do not alter application policy.

`PKG-007` The executable package operates from an arbitrary current directory and with
the installed application root read-only. It imports no source-checkout module and writes
no settings, logs, reports, cache, database, migration state, or generated configuration
beside either executable.

## 3. Runtime resource contract

`PKG-008` Phase 5.5F shall materialize this closed runtime-resource classification. A
required item is included exactly once under its governed installed identity; exclusion
items are absent unless a later owner explicitly introduces them.

| Resource class | Repository/input authority | Mutability | Packaging verification |
| --- | --- | --- | --- |
| Scout application configuration | `config/config.yaml` | immutable | hash inventory and installed resolution |
| bundled source defaults | `config/sources.yaml` | immutable | hash inventory and installed resolution |
| desktop default settings | `src/pastila_scout/desktop_v1/default-settings-v1.json` | immutable | installed resolution |
| production raw trust key | `resources/trust/pastila-root-1.pub` | immutable | exact bytes, size, hash, and resolution |
| production bootstrap object | `resources/trust/bootstrap-root-v1.json` | immutable | exact canonical members, hash binding, and resolution |
| Tcl/Tk runtime | accepted Python 3.14 installation | immutable | source/version record, initialization, GUI startup |
| CA/certificate data | actual HTTP/TLS dependency data | immutable | offline path/load resolution |
| distribution metadata | clean installed wheel | immutable | exact distribution lookup and stable version |
| localization/module data | actual `pastila_scout` runtime modules | immutable | GUI text/module resolution |
| application/dependencies | package modules and declared actual runtime dependencies | immutable | import and offline composition coverage |

`PKG-009` Tests, documentation, caches, wheel/build work products, generated mutable state,
development trust, ceremony provenance, verifier/operator/receipt material, private keys,
and deferred provider SDKs are excluded. The controlled-revision pricing YAML is excluded
unless a concrete production runtime consumer is independently proven before 5.5F; test
or benchmark references alone do not qualify it. Reports are generated mutable HTML under
the governed report root; current report rendering has no static HTML/template asset to
bundle. Current contract schemas are Python-owned models rather than external runtime JSON
schema files. A later code change must prove an actual runtime file consumer before either
class enters the resource inventory; Productization's generic “schemas” inventory does
not authorize speculative files.

## 4. Trust, state, and version

`PKG-010` Stable packaging includes exactly two production trust resources:
`pastila-root-1.pub` and `bootstrap-root-v1.json`. The public key is exactly 32 raw
Ed25519 bytes. The strict-JCS bootstrap object contains exactly `schema`,
`schema_version`, `key_id`, `algorithm`, `public_key_filename`, and
`public_key_sha256`, with the frozen identities and lowercase SHA-256 binding.

`PKG-011` Packaging generates, rotates, repairs, substitutes, or downloads no trust.
Private material, development trust, provenance, mutable override, fallback trust, TOFU,
optional verification, and fabricated ceremony facts are forbidden. The probe verifies
only public-resource presence, exactness, cross-binding, and installed resolution.

`PKG-012` Writable roaming state remains under `%APPDATA%\PastilaScout`; writable local
data, database, logs, reports, and cache remain under `%LOCALAPPDATA%\PastilaScout` as
assigned by frozen Windows State authority. The executable package neither changes these
owners nor creates mutable state inside the bundle.

`PKG-013` The probe uses isolated `APPDATA` and `LOCALAPPDATA`, exercises an arbitrary
CWD, a read-only application root, a non-ASCII writable root, and a long writable path
where the host supports it. Failure, fallback into the bundle/repository, or reliance on
the invoking directory fails the probe.

`PKG-014` Version authority remains the one-way chain
`project.version -> installed distribution metadata -> pastila_scout.__version__ ->`
runtime and packaging consumers. Runtime never parses `pyproject.toml`, reads Git, or
uses an environment or generated literal as a second authority.

`PKG-015` A stable package rejects missing or divergent metadata, `0.0.0-dev`, and any
prerelease, build-metadata, or malformed form forbidden by Version Projection V1. The
canonical runtime string is distinct from deterministic Windows `FileVersion` and
`ProductVersion` projections. Phase 5.5F derives the Windows four-part form and other PE
fields; installer and artifact-name projections remain later-owned.

## 5. Dependencies, imports, GUI, and certificates

`PKG-016` The bundle includes only currently supported OpenAI and Ollama execution paths
and their actual dependencies. OpenAI uses the declared `openai` SDK. Ollama uses
`httpx`, not an Ollama SDK. Claude, Gemini, and other deferred SDKs are not included merely
because provider identities exist. Packaging requires no credential, provider server, or
live provider call.

`PKG-017` Phase 5.5F owns an explicit, reviewable hidden-import inventory. At minimum its
analysis covers dynamic imports of `openai`, `httpx`,
`pastila_scout.provider_runtime_openai_bridged_v2`, its composition module, the
`pastila_scout.provider_execution_openai_sdk_v2` package and client/mapping/models
modules, `pastila_scout.editor_generation_authority_v1`, the Ollama executor package,
and every other production `import_module`, `__import__`, lazy, or computed import
reachable from either launcher. Static imports may be analyzer-owned; dynamic imports
are never presumed discoverable without evidence.

`PKG-018` Missing required imports fail the probe. Phase 5.5E creates no hook or permanent
specification file. Phase 5.5F materializes only the empirically proven import set and
must not hide an unknown omission by aggregating all repository or provider modules.

`PKG-019` The accepted Python 3.14 installation contains complete Tcl/Tk data. The probe
records Python, Tcl, and Tk versions and resolved source locations, proves Tcl/Tk
initialization, and observes bounded GUI startup rather than treating import success as
startup success. `PastilaScout.exe` must not create a release console.

`PKG-020` CA/certificate resources required by actual packaged HTTP/TLS dependencies are
discoverable and loadable without a repository path. This is an offline resource test;
it performs no DNS lookup, network connection, credential retrieval, or certificate
authority redesign. The probe records `ssl.get_default_verify_paths()`, whether the
installed dependency graph uses a bundled CA provider such as `certifi`, every selected
CA file/directory origin, and successful local `SSLContext` construction/loading. A
Windows certificate-store result is valid only when the packaged interpreter can open it
offline; a bundled CA result is valid only when its installed file exists in the bundle.
No generic certificate directory is added merely to make this gate pass.

## 6. Phase boundaries

`PKG-021` Phase 5.5F owns exactly these production paths:

- `packaging/pyinstaller/PastilaScout.spec`;
- `packaging/pyinstaller/version_info.txt.in`;
- `packaging/pyinstaller/build.ps1`;
- `packaging/resources/PastilaScout.ico`;
- `packaging/resources/THIRD-PARTY-NOTICES.txt`.

It owns exactly `tests/packaging/test_frozen_application_v1.py`,
`tests/packaging/test_version_parity_v1.py`, and
`tests/packaging/test_build_mode_v1.py`. Its prerequisite is
`phase-5.5e-windows-executable-spec-v1-ready`, verdict is
`PHASE_5_5F_WINDOWS_EXECUTABLE_REVISION_1_VERIFIED`, commit subject is
`Add verified Windows executable packaging`, and tag is
`phase-5.5f-windows-executable-r1-verified`. Phase 5.5E creates none of these paths.

`PKG-022` Phase 5.5F implements the permanent spec, proven toolchain pin, shared bundle,
build modes, PE resources, icon/notices, resource/import inventories, and packaging tests.
It consumes trust and version authority but generates neither. Development and stable
inputs remain disjoint and mixed resources fail closed.

`PKG-023` Phases 5.6A/5.6B own installation, uninstall, shortcuts, registry, AppId,
elevation policy, placement, upgrade, and installer tests. Phase 5.5E specifies only the
output and root handoff necessary for those later owners.

`PKG-024` Later 5.7 owners exclusively define updater trust, download, replacement,
launch, rollback, recovery, and persistence. Phase 5.10 owns signing orchestration,
publication, channels, uploads, release notes, and live release validation. Authenticode,
RFC 3161 timestamps, certificates, SmartScreen reputation, stable endpoints, and signing
credentials are not 5.5E implementations or probe prerequisites.

## 7. PyInstaller selection and clean environment

`PKG-025` PyInstaller is a build tool, not a runtime dependency. Candidate selection uses
the recorded Python Package Index release metadata available at probe resolution time.
Starting with the highest non-yanked stable release whose declared Python compatibility
admits the exact probe interpreter, candidates are tested in descending version order;
prereleases are excluded. The source URL, distribution filename, SHA-256, resolution
timestamp, and ordered candidate list are evidence. The first candidate for which every
probe row passes is selected; a failed candidate is recorded and creates no pin. If no
candidate passes, the probe fails. Phase 5.5F pins that single proven version and artifact
hash in its build environment. An explicitly approved private mirror may supply the same
files, but cannot change their index identities, hashes, order, or selection result.

`PKG-026` The probe runs before 5.5E formal freeze, never on a host known to lack
PyInstaller or complete Tcl/Tk. It runs on Windows x64 with a fresh isolated environment,
complete 64-bit Python 3.14 and Tcl/Tk, the exact candidate PyInstaller, and no reused
PyInstaller cache, build tree, installed package, or editable installation.

`PKG-027` Dependency provisioning is a distinct preparation stage. It may use an approved
package source to populate the isolated environment or external wheelhouse. After inputs
are provisioned, the build, launcher, resource, and provider-composition probe executes
offline. Network access, credentials, OpenAI calls, and an Ollama server are forbidden in
the executable probe.

`PKG-028` The application input is a newly built wheel produced by the repository's
existing standards-based Python build authority. The evidence records its SHA-256. The
wheel is installed into the clean environment, and the source checkout is removed from
`sys.path`, `PYTHONPATH`, CWD, and process import reachability. Installed distribution
metadata and resolved module paths must prove execution from that wheel. The probe records
every active `.pth` file and the resulting `sys.path`; it fails if either adds the
repository, source checkout, development tree, or another unrecorded external package
root. Development files outside the wheel are unavailable to the execution account.

The probe follows this fixed order, with every angle-bracket value resolved to an
absolute external path or recorded exact version before invocation:

1. record repository HEAD, index, tracked status, and untracked inventory;
2. create `<probe-root>`, `<venv>`, `<wheelhouse>`, `<work>`, `<dist>`, `<spec>`,
   `<layout>`, and `<evidence>` outside the repository;
3. build one wheel with the repository's standards-based build frontend into
   `<wheelhouse>`, hash it, and make no editable installation;
4. create `<venv>` from the recorded Python 3.14 executable, install the wheel, its
   provisioned locked dependencies, and exactly `PyInstaller==<candidate-version>`;
5. from an unrelated external CWD with `PYTHONPATH` absent, record distribution metadata,
   imported module origins, dependency versions, Tcl/Tk initialization and source paths;
6. generate only an external disposable probe spec using explicit `--specpath <spec>`.
   Its captured content maps the two exact entry modules to one windowed and one console
   EXE, collects them into one shared onedir, and declares only the independently derived
   required data and dynamic imports. Build that recorded spec using explicit
   `--workpath <work>` and `--distpath <dist>`; the generated file is evidence scaffolding,
   never repository authority or a source of expected hashes, filenames, or identities;
7. place the resulting shared onedir contents at `<isolated-LOCALAPPDATA>\Programs\`
   `PastilaScout\app`, establish isolated AppData roots and read-only app permissions,
   disconnect runtime networking, and execute the matrix in Section 10;
8. collect sanitized evidence, dispose or explicitly retain external artifacts, and
   repeat the repository inventory comparison.

Dependency acquisition may precede the offline boundary, but steps 5 through 8 use no
source-tree import and steps 7 through 8 permit no runtime network. Exact sanitized
commands, resolved paths, exit codes, and output hashes are part of the evidence record;
failure at any ordered step prevents later steps from converting the result to PASS.

## 8. Probe filesystem and installed-layout emulation

`PKG-029` Every probe-created venv, wheel, wheelhouse, workpath, distpath, specpath,
cache, log, temporary configuration, installed-layout tree, and evidence record resides
under explicit disposable roots outside the repository. The probe passes explicit
PyInstaller work, dist, and spec paths and never emits a repository `.spec` file.

`PKG-030` Before and after the probe, evidence records HEAD, index state, tracked status,
the complete untracked and ignored inventory, and a recursive repository filesystem
manifest excluding `.git` but including ignored paths. The manifest records relative path,
entry type, size, and SHA-256 for every regular file; directory and symlink/reparse
identities are recorded without traversal. Pre-existing ignored files are not presumed
clean merely because Git suppresses them. A pass requires identical pre/post manifests
and Git state, no configuration/trust/state pollution, and no build, dist, spec, venv,
wheelhouse, cache, or packaging implementation residue. Disposable outputs are removed or
retained only in an identified external evidence location.

`PKG-031` Without implementing an installer, the probe emulates the installed application
root beneath isolated `%LOCALAPPDATA%\Programs\PastilaScout\app`, places the shared
bundle according to the governed layout, makes the application root read-only for the
execution gates, and supplies separate writable isolated AppData roots.
The harness derives the expected absolute root directly from the frozen literal and the
recorded isolated `LOCALAPPDATA`, not from the temporary spec. Process/file observations
must show immutable reads at that exact path and no reads from another candidate root.

## 9. Launcher and offline composition protocol

`PKG-032` The GUI gate proves one `PastilaScout.exe` exists in the shared bundle, has the
windowed subsystem/no release console, initializes Tcl/Tk, reaches a bounded observable
startup-ready state, resolves immutable resources, uses external writable state, and can
be terminated cleanly by the harness. A mere successful import or process creation is
insufficient. The external harness records a fixed timeout, process identity, and Windows
UI Automation observation of one visible enabled top-level Pastila Scout window whose UI
thread responds within that timeout. It separately inspects the PE subsystem and verifies
that the launched GUI has no attached console window. The harness then requests ordinary
window close and requires bounded clean process exit; timeout, manual-only observation,
an unresponsive/hidden-only window, forced-kill-only completion, or a console is FAIL.

`PKG-033` The console gate proves one `pastila-scout.exe` exists in the same bundle,
starts as a console program, returns deterministic `--version` output equal to
`pastila_scout.__version__`, observes a stable non-fallback version, resolves required
imports, and operates without source checkout or CWD dependence.

`PKG-034` Offline composition/import exercises both supported provider paths far enough
to load their production composition and dependency boundaries without creating a live
request. It supplies no API key, connects to no OpenAI endpoint or Ollama server, and
fails on a missing required hidden import or accidental deferred-provider dependency.

`PKG-035` Resource gates verify installed resolution of both configs, desktop defaults,
both exact production trust resources, installed metadata, Tcl/Tk, certificate data,
localization, and required application/dependency modules. Where objectively inspectable,
they also verify absence of private keys, development trust, provenance, tests, deferred
SDKs, source files not needed at runtime, and mutable state in the bundle.
Expected resource paths, bytes, schema members, hashes, module identities, and version are
derived independently from the cited frozen repository authorities and clean wheel before
the temporary spec is read. Observed bundle results are compared to that independent
record; copying expectations from the generated spec or probe configuration is forbidden.

`PKG-036` State gates execute with arbitrary CWD and isolated AppData, exercise non-ASCII
and supported long writable paths, and detect writes beneath the read-only application
root. A permission failure caused by an attempted bundle write, repository lookup, or
fallback root is a probe failure, not an allowed platform limitation.

## 10. Warnings and normative probe matrix

`PKG-037` Every analyzer, build, and runtime warning is recorded and classified as
informational, known-benign optional, or correctness-affecting. An accepted warning has a
specific justification. A missing required module/resource, Tcl/Tk fault,
architecture/version mismatch, repository fallback, or unexplained correctness-affecting
warning fails the probe. Blanket suppression and build-success-only acceptance are
forbidden.

`PKG-038` The complete external probe passes only when every row below passes. “N/A” is
permitted only where the row explicitly says “where supported” or “where inspectable,”
and evidence explains the platform limitation. Any other absent, skipped, indeterminate,
or contradicted result is FAIL.

| Gate | Objective evidence | PASS condition | FAIL condition |
| --- | --- | --- | --- |
| Environment | OS/CPU/Python inventory | Windows x64; complete 64-bit Python 3.14 | mismatch or incomplete runtime |
| PyInstaller | exact version and invocation | one recorded candidate | absent, floating, or changed candidate |
| Clean wheel | wheel hash, `.pth`, `sys.path`, metadata, module paths | new installed wheel/metadata; no checkout or external development import | editable/source/`.pth` leakage or missing metadata |
| Architecture | PE and bundle inventory | x64 Windows output | wrong or indeterminate architecture |
| Bundle | directory and launcher inventory | one onedir bundle; exactly two launchers | onefile, extra launcher, or split bundle |
| GUI | PE subsystem, UI Automation, timeout/close record | responsive visible window, Tcl/Tk ready, no console, clean close | import-only, hidden/unresponsive, hang, forced kill, crash, or console |
| Console | captured `--version` | exact stable projection and successful exit | fallback, mismatch, or failed start |
| Resources | frozen-authority expectations versus installed lookup/hashes | every independently expected resource resolves exactly | self-confirming, missing, divergent, or repository lookup |
| Trust | byte/schema/hash checks | exact two-resource production authority | private/dev/provenance/mutable/fallback trust |
| Tcl/Tk | source/version/init evidence | complete data and successful initialization | missing data or initialization failure |
| Certificates | offline path/load check | actual CA data resolves locally | missing or repository/network dependence |
| Imports | import inventory and execution | all reachable required modules resolve | missing import or blanket aggregation |
| Providers | offline OpenAI/Ollama composition | both supported boundaries load offline | live call, credential, server, or deferred SDK |
| Installed root | resolved-path evidence | exact governed isolated app root | `_MEIPASS`, CWD, home, repository, or override root |
| Mutable state | filesystem before/after | writes only to governed isolated AppData | bundle/repository write |
| Arbitrary CWD | launch from unrelated directory | behavior unchanged | CWD dependence |
| Read-only install | permissions and execution result | required behavior succeeds | attempted install-tree mutation |
| Non-ASCII/long state | path and result | succeeds where supported | application path handling failure |
| Forbidden content | bundle inventory/secret scan | prohibited classes absent where inspectable | prohibited content found |
| Warnings | warning ledger | all warnings justified and non-affecting | unexplained correctness-affecting warning |
| Network/credentials | harness/process evidence | probe execution remains offline and secret-free | network, API key, or provider connectivity used |
| Hygiene | Git plus full ignored-aware filesystem manifests | repository byte/entry inventory unchanged; disposition recorded | residue, dirty index, ignored change, or unexplained output |

## 11. Evidence and reproducibility

`PKG-039` Probe evidence is retained outside Git and contains no credential, private key,
environment secret, user document, or sensitive provider payload. It records Windows
edition/build and architecture; Python/PyInstaller/Tcl/Tk versions and source paths;
wheel hash; relevant immutable input hashes; exact sanitized commands and explicit paths;
executable/bundle inventories; warnings and dispositions; every gate result; cleanup or
external retention; and final repository state. A timestamp is evidence provenance only,
never runtime authority.

`PKG-040` A successful probe establishes a pinned, recorded toolchain, deterministic
configuration/resource/import inventory, deterministic version/resource mapping, and a
behaviorally reproducible build/probe procedure. It does not claim byte-identical PE,
archive, timestamp, path, bootloader, or filesystem output.

## 12. Security, proportionality, and resolved decisions

`PKG-041` Packaging fails closed against private/development trust leakage, mutable trust
override, source-tree or CWD fallback, bundled mutable state, missing required imports or
resources, a second version authority, deferred-provider aggregation, repository residue,
and stable use of the development fallback. A diagnostic convenience never relaxes a
stable gate.

`PKG-042` The proportionate design is one shared onedir bundle, the two existing entry
points, one later permanent PyInstaller spec owner, and one external clean probe. Onefile,
extra entry points, parallel packagers, all-provider SDK aggregation, enterprise ceremony
artifacts, and premature signing, installer, updater, or release machinery are rejected.

`PKG-043` Historical references to mandatory provenance, verifier or receipt identifiers,
multiple operators, dual custody, or a third production trust resource are superseded by
the frozen Productization and Phase 5.5A single-owner maintenance chain and the verified
two-resource Phase 5.5B materialization. This resolution changes no cryptographic trust
guarantee and leaves no packaging contradiction.

`PKG-044` PyInstaller patch selection follows the deterministic stable-version ordering in
the `PKG-025` selection requirement; environment-specific Tcl/Tk paths, warning instances,
exact resolved commands,
and the final exhaustive hidden-import set are recorded from the clean environment under
the protocols above. These are closed decision procedures, not permission to guess facts
or leave a freeze gate open. Two independent implementers using the same recorded index
snapshot therefore converge on candidate order, architecture, inputs, failures, and
evidence.

## 13. Requirements and verification

`PKG-045` Normative requirements are exactly `PKG-001` through `PKG-050`. Verification
rows are exactly `V-001` through `V-050`, each maps one requirement exactly once, and no
row without a normative requirement is a test. Missing, orphaned, and duplicate mappings
must each equal zero.

`PKG-046` **Specification review** means byte-level Markdown/integrity checks plus an
independent semantic comparison against every cited frozen authority. It cannot satisfy a
row designated **external probe**, **5.5F**, or **later**.

`PKG-047` **External probe** means execution of Sections 7 through 11 in the clean
environment before formal 5.5E freeze. Current-host inspection, source tests, mocked
PyInstaller behavior, or prose review cannot substitute for it.

`PKG-048` **5.5F verification** means material tests against the permanent packaging
implementation in the exact Phase 5.5F-owned paths. 5.5E neither creates those tests nor
claims their future result.

`PKG-049` **Later verification** belongs to the named installer, updater, signing, or
release owner and is included only to establish a handoff. It cannot expand Phase 5.5E or
become a 5.5E freeze prerequisite unless an earlier frozen authority explicitly says so.

`PKG-050` Phase 5.5E is ready for independent review and clean probe only when its one
file is locally coherent: Critical, Major, and Minor findings; traceability gaps;
contradictions; blocking ambiguities; scope expansion; implementer divergence;
probe-protocol gaps; and known false-positive probe holes are all zero. Formal freeze
additionally requires successful external evidence for every probe row.

| Verification ID | Requirement | Owner/method | Material verification |
| --- | --- | --- | --- |
| `V-001` | `PKG-001` | specification review | prerequisite, one-file scope, and reserved identity match roadmap |
| `V-002` | `PKG-002` | specification review | maintained precedence and frozen inputs are reproduced |
| `V-003` | `PKG-003` | specification review | every defined term is used consistently |
| `V-004` | `PKG-004` | external probe | Windows x64/Python 3.14/onedir output inventory passes |
| `V-005` | `PKG-005` | external probe | exact two launcher names, entry points, and subsystems pass |
| `V-006` | `PKG-006` | external probe | resolved installed root is exact and no fallback is observed |
| `V-007` | `PKG-007` | external probe | arbitrary-CWD/read-only/no-checkout behavior passes |
| `V-008` | `PKG-008` | specification review + 5.5F | table is authoritative; implementation inventory matches it |
| `V-009` | `PKG-009` | external probe + 5.5F | forbidden-resource inventory is absent |
| `V-010` | `PKG-010` | external probe | exact key bytes and six-member bootstrap cross-binding pass |
| `V-011` | `PKG-011` | specification review + external probe | no generation/private/dev/provenance/fallback trust exists |
| `V-012` | `PKG-012` | external probe | writes remain in governed isolated AppData roots |
| `V-013` | `PKG-013` | external probe | CWD, read-only, non-ASCII, and supported long-path gates pass |
| `V-014` | `PKG-014` | specification review + external probe | installed metadata is sole runtime version source |
| `V-015` | `PKG-015` | external probe + 5.5F | stable/fallback/parity and PE projection gates pass |
| `V-016` | `PKG-016` | external probe + 5.5F | only actual OpenAI/Ollama dependencies are bundled |
| `V-017` | `PKG-017` | specification review + 5.5F | exhaustive production dynamic-import inventory is explicit |
| `V-018` | `PKG-018` | external probe + 5.5F | omissions fail and permanent implementation owns proven set |
| `V-019` | `PKG-019` | external probe | Tcl/Tk source, initialization, and bounded GUI startup pass |
| `V-020` | `PKG-020` | external probe | actual CA data resolves offline outside repository |
| `V-021` | `PKG-021` | specification review | literal 5.5F paths and identity match roadmap |
| `V-022` | `PKG-022` | 5.5F | permanent build modes, pin, resources, and tests pass |
| `V-023` | `PKG-023` | specification review + later | installer handoff is bounded and later implementation verifies it |
| `V-024` | `PKG-024` | specification review + later | updater/release/signing handoffs are bounded |
| `V-025` | `PKG-025` | external probe + 5.5F | accepted exact version has complete PASS evidence and later pin |
| `V-026` | `PKG-026` | external probe | fresh compatible environment inventory passes |
| `V-027` | `PKG-027` | external probe | provisioning is separated and execution is offline/secret-free |
| `V-028` | `PKG-028` | external probe | wheel hash, installed metadata, and module paths prove isolation |
| `V-029` | `PKG-029` | external probe | all generated paths are explicit and external |
| `V-030` | `PKG-030` | external probe | repository pre/post state is identical and outputs disposed |
| `V-031` | `PKG-031` | external probe | isolated installed layout and read-only application root pass |
| `V-032` | `PKG-032` | external probe | complete GUI launcher gate passes, not import-only |
| `V-033` | `PKG-033` | external probe | console start and exact stable `--version` pass |
| `V-034` | `PKG-034` | external probe | both provider compositions load without network/credentials |
| `V-035` | `PKG-035` | external probe | required presence and inspectable forbidden absence pass |
| `V-036` | `PKG-036` | external probe | state/CWD/read-only/path matrix passes |
| `V-037` | `PKG-037` | specification review + external probe | warning ledger has no unexplained affecting warning |
| `V-038` | `PKG-038` | external probe | every normative probe-matrix row passes |
| `V-039` | `PKG-039` | external probe | complete sanitized external evidence record exists |
| `V-040` | `PKG-040` | specification review + external probe | reproducibility record exists without bit-identity claim |
| `V-041` | `PKG-041` | specification review + external probe | every named fail-closed threat has an effective gate |
| `V-042` | `PKG-042` | specification review | no disproportionate packaging mechanism enters scope |
| `V-043` | `PKG-043` | specification review | maintenance precedence resolves historical conflict |
| `V-044` | `PKG-044` | specification review + external probe | decision procedures close environment-specific facts |
| `V-045` | `PKG-045` | specification review | ID/count script reports 50/50 and zero mapping defects |
| `V-046` | `PKG-046` | specification review | review evidence does not impersonate executable evidence |
| `V-047` | `PKG-047` | external probe | actual external execution evidence exists before freeze |
| `V-048` | `PKG-048` | 5.5F | permanent implementation tests verify their owned artifacts |
| `V-049` | `PKG-049` | specification review + later | later rows remain handoffs, not false 5.5E passes |
| `V-050` | `PKG-050` | specification review | local-fixpoint counters are zero; freeze remains probe-gated |
