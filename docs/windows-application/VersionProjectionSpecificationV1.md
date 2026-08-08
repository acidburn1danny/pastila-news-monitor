# Version Projection Specification V1

## 1. Authority, identity, and scope

`VERPROJ-001` This document is the Phase 5.5C Version Projection Specification V1. Its
prerequisite is the annotated tag `phase-5.5b-trust-bootstrap-r1-verified`, resolving to
commit `51212b4f3c529d35b3127397cc147bb7b328a08a`. Phase 5.5C owns exactly this
specification path and creates no production code, test, fixture, resource, or formal
freeze. Phase 5.5D is the sole immediate implementation owner.

The roadmap identity reserved for a later formal freeze is:

- verdict `PHASE_5_5C_VERSION_PROJECTION_SPECIFICATION_V1_READY_FOR_FREEZE`;
- commit subject `Specify package version projection V1`;
- tag `phase-5.5c-version-projection-spec-v1-ready`.

`VERPROJ-002` The canonical application/package version is the one version value owned by
`[project].version` in `pyproject.toml`. The source authority is that field. Distribution
metadata is the packaging-standard installed projection derived from it. Installed
metadata means metadata available for the exact installed distribution. Development or
uninstalled metadata-absence state means only the observable result that the exact lookup
raises `PackageNotFoundError`; application code does not infer why metadata is absent or
classify the surrounding installation. Version projection is the deterministic one-way
derivation from installed metadata to the runtime projection. The projected version is the resulting `str` exposed as
`pastila_scout.__version__`. Parity means exact string equality among projections of the
same canonical authority.

Application/package version is distinct from PE, installer, bundle, update, Protocol,
Persistence, settings, SQLite, and trust-bootstrap schema versions. Stable Phase 5 version
means an accepted application/package version without prerelease or build metadata. The
development fallback is the single literal defined in Section 4; it is not a stable
version or a source authority.

## 2. Single authority and installed metadata

`VERPROJ-003` `[project].version` in repository-root `pyproject.toml` is the sole canonical
application/package-version authority. Package code, CLI, logging, GUI, settings,
environment variables, databases, updater state, packaging configuration, installer
configuration, Git objects, and generated files never define an independent authoritative
version literal.

`VERPROJ-004` Installed distribution metadata is a standards-based derived representation,
not a second authority. Build and release verification must prove that its version derives
from the canonical field. Application runtime does not read or parse `pyproject.toml`, and
no consumer repairs a metadata mismatch by copying either value over the other.

`VERPROJ-005` Phase 5.5D obtains the candidate runtime version only by calling
`importlib.metadata.version("pastila-news-monitor")`. The distribution identity is exactly
`pastila-news-monitor`, and that exact literal is the lookup argument. Standards-based
distribution-name matching may apply its packaging-defined name canonicalization while
resolving installed metadata; the application performs no name normalization of its own
and tries no alternate distribution name, package name, filename, environment variable,
entry-point metadata, Git tag, or network lookup.

`VERPROJ-006` When the exact distribution metadata exists, Phase 5.5D validates the string
returned by `importlib.metadata.version` against Section 3 and exposes that exact string.
The application performs no additional packaging normalization. Any normalization applied
while standards-based metadata is built must still produce a value that passes the exact
grammar and release parity gates. The stable grammar's canonical core form is also a valid
Python packaging version form and requires no application normalization; any returned
lexical difference is assessed as returned rather than repaired. Runtime never parses
`pyproject.toml` to compare it.

## 3. Stable version grammar and public projection

`VERPROJ-007` The sole public package projection is `pastila_scout.__version__`. Its type is
exactly `str`. Importing the package root performs only the local metadata lookup,
validation, or authorized fallback defined here; it performs no application composition
and exports no version service, mutable holder, or second version value.

`VERPROJ-008` A valid installed Phase 5 version is 1 through 128 ASCII bytes and has the
exact stable SemVer core grammar:

```text
(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)
```

The whole string must match. It has exactly three non-negative decimal components, ASCII
digits and two ASCII full stops only. Leading `v`, leading zeroes in multi-digit
components, signs, whitespace, Unicode digits, empty components, extra components,
prerelease identifiers, and build metadata are invalid. This is the stable subset of
SemVer 2.0.0 required for Phase 5 publication.

## 4. Development fallback and failures

`VERPROJ-009` The exact development fallback is `0.0.0-dev`. It is returned only when the
exact lookup in `VERPROJ-005` raises `importlib.metadata.PackageNotFoundError`. This is an
exception-based boundary, not an attempt to distinguish source trees, editable installs,
wheel installs, damaged installations, or packaging modes through filesystem, Git,
environment, or caller heuristics. Source-tree use may therefore expose the fallback;
editable and wheel installs with valid metadata expose their metadata version. Any stable
artifact or installed health check that observes the fallback is invalid and fails its
own gate, even if missing metadata caused it. The fallback is never written into canonical
metadata, accepted as stable authority, persisted as a repair, or selected by a flag,
environment value, setting, or caller.

`VERPROJ-010` If distribution metadata exists but its returned value is not a `str` or does
not match `VERPROJ-008`, package import fails closed with `RuntimeError` and the finite
message `invalid installed package version`. It never falls back, trims, normalizes,
repairs, or discloses raw invalid metadata in the message.

`VERPROJ-011` Any metadata lookup failure other than `PackageNotFoundError`, including I/O,
permission, corruption, or unexpected implementation failures, propagates unchanged. The
projection catches no broad `Exception` or `BaseException`. `KeyboardInterrupt`,
`SystemExit`, `GeneratorExit`, and `MemoryError` are never converted to a version.

`VERPROJ-012` Validation performs no trimming, leading-`v` removal, Unicode conversion,
case rewriting, component padding, component dropping, prerelease/build stripping, or
other normalization. Consequently `v1.2.3`, `01.2.3`, `1.02.3`, `1.2.03`, `1.2`, padded
forms, Unicode-digit forms, `1.2.3-alpha`, and `1.2.3+build` are invalid installed values.
Only metadata absence, not invalid metadata, produces the fallback.

The complete exception taxonomy is therefore:

| State | Result |
| --- | --- |
| Metadata exists and matches the stable grammar | expose the exact returned `str` |
| Exact distribution metadata is absent | expose `0.0.0-dev` |
| Metadata exists but its version is invalid | raise the finite `RuntimeError` from `VERPROJ-010` |
| Lookup fails unexpectedly | propagate the original failure unchanged |
| A downstream projection differs | that downstream owner fails its parity gate; never repair or fall back |

## 5. Determinism, parity, and layering

`VERPROJ-013` Projection is deterministic. The same valid installed metadata yields the
same byte-for-byte Python string, and genuine absence yields the same fallback. Current
time, randomness, UUIDs, Git state, branch, tags, environment, locale, architecture,
hostname, username, installation path, file timestamps, network state, mutable settings,
and database state are forbidden inputs.

`VERPROJ-014` Phase 5.5C defines parity as exact equality to the one projected application
version. Phase 5.5D implements `pastila_scout.__version__`, root CLI `--version`, GUI About,
and logging projections and tests their equality. A consumer never parses
`pyproject.toml`, carries an editable version literal, or substitutes fallback for a
divergence.

`VERPROJ-015` Phase 5.5C does not define PE `FileVersion`, PE `ProductVersion`, the Windows
four-part `major.minor.patch.0` projection, MSI/MSIX versioning, Inno `AppVersion`,
installer metadata, executable resources, or artifact filenames. Phase 5.5E specifies
packaging, Phase 5.5F implements executable packaging projections, Phase 5.6 owns installer
projection, and Phase 5.10 owns release orchestration. Each later owner derives from the
verified application projection and fails on divergence.

`VERPROJ-016` Version projection consumes no trust-bootstrap field or cryptographic fact.
Phase 5.5B is prerequisite completion only. Phase 5.5C does not read the root key ID, raw
public bytes, public-key hash, algorithm, bootstrap schema/version, resource filenames, or
development fixtures; it accesses no private key and defines no signing or signed
canonical bytes.

`VERPROJ-017` Phase 5.5C defines no update eligibility, ordering, equality policy,
downgrade prevention, anti-rollback sequence, remote version lookup, persisted update
state, or release selection. Later signed-source and updater owners may consume the
verified application version under their own canonicalization, signature, compatibility,
and persistence contracts.

`VERPROJ-018` Application/package version is independent of frozen Protocol V6 stable
version fields, Persistence V6 wire/store fields, SQLite `PRAGMA user_version`, settings
schema versions, source/update manifest schema versions, and trust-bootstrap
`schema_version`. Phase 5.5C modifies none of those authorities, schemas, or records.

`VERPROJ-019` Projection performs no network I/O, database access, mutable-settings access,
application-directed filesystem search, arbitrary-file read, subprocess or Git execution,
provider loading, GUI initialization, updater initialization, trust loading, logging
configuration, or write. Only the standards-based local distribution-metadata lookup,
including discovery internal to that standard-library API, belongs to Phase 5.5D.

`VERPROJ-020` Package-root version projection imports only Python standard-library metadata
facilities needed by this contract. It does not import desktop, provider, Editor, updater,
trust, database, configuration, CLI, or composition modules; creates no cycle; and performs
no registration or construction side effect.

`VERPROJ-025` Phase 5.5D initializes `pastila_scout.__version__` once during each execution
of the package-root module and binds the resulting ordinary `str` at module scope.
Repeated attribute reads perform no new lookup. A deliberate `importlib.reload` executes
module initialization and the lookup again under the then-injected metadata behavior;
tests monkeypatch lookup behavior before initial import or reload. This contract does not
claim that Python callers cannot rebind a module attribute; conformance depends on no
production owner mutating or overriding the binding after initialization.

## 6. Exact downstream ownership

`VERPROJ-021` Phase 5.5D has prerequisite
`phase-5.5c-version-projection-spec-v1-ready` and owns exactly these production paths:

- `src/pastila_scout/__init__.py`;
- `src/pastila_scout/cli.py`;
- `src/pastila_scout/logging_config.py`;
- `src/pastila_scout/desktop_v1/views.py`;
- `src/pastila_scout/desktop_v1/resources.py`.

Its test owners are exactly `tests/test_package_version_projection_v1.py`,
`tests/test_cli.py`, `tests/test_logging.py`, and `tests/test_desktop_shell_v1.py`. It adds
only `pastila_scout.__version__`, root CLI `--version`, GUI About projection, and log
projection. It excludes other CLI, GUI, and logging behavior, changes to
`project.version`, packaging, and updater behavior.

`VERPROJ-022` Phase 5.5E and Phase 5.5F own executable-packaging specification and
implementation after verified 5.5D; Phase 5.6 owns installer specification and
implementation; and Phase 5.10 owns the release pipeline. Those phases consume the
verified version but do not become source authorities. Phase 5.5C creates none of their
files, probes, metadata, artifacts, scripts, tests, or release behavior.

## 7. Security, proportionality, and reproducibility

`VERPROJ-023` Validation fails closed against a mutable or second authority, environment or
Git override, silent normalization, invalid-metadata fallback, divergent package/CLI/GUI/
log identities, stable use of the development fallback, and conflation of display version
with signed or update trust identity. Version projection never incorporates trust-key or
private material.

`VERPROJ-024` Given the same authoritative metadata state, two independent implementers
produce the same projected string, failure category, and side-effect-free import behavior.
No version service, registry, signed version database, approval, receipt, second operator,
HSM, ceremony, or persistence layer is required. Historical proof uses immutable tags;
runtime projection does not use Git. All requirements below have one material verification
row and no hidden owner.

## 8. Verification matrix

| Verification | Requirement | Phase | Material proof |
| --- | --- | --- | --- |
| `VERPROJ-V001` | `VERPROJ-001` | specification review | Verify prerequisite, one-file specification scope, reserved identity, and 5.5D boundary. |
| `VERPROJ-V002` | `VERPROJ-002` | specification review | Audit every defined term and distinguish all non-application version domains. |
| `VERPROJ-V003` | `VERPROJ-003` | 5.5D and later parity tests | Scan every consumer for a second authority or independently edited literal. |
| `VERPROJ-V004` | `VERPROJ-004` | 5.5D and build tests | Prove metadata derivation and absence of runtime `pyproject.toml` parsing or repair. |
| `VERPROJ-V005` | `VERPROJ-005` | 5.5D tests | Spy on the exact lookup and reject alternate distribution names or sources. |
| `VERPROJ-V006` | `VERPROJ-006` | 5.5D and build tests | Assert exact returned-string exposure and fail parity on build normalization divergence. |
| `VERPROJ-V007` | `VERPROJ-007` | 5.5D tests | Assert public name/type and lightweight package-root import with no second projection object. |
| `VERPROJ-V008` | `VERPROJ-008` | 5.5D tests | Accept stable grammar boundaries and reject every excluded syntax and byte bound. |
| `VERPROJ-V009` | `VERPROJ-009` | 5.5D and packaging tests | Raise exact absence, require the fallback, and reject fallback in stable packaging. |
| `VERPROJ-V010` | `VERPROJ-010` | 5.5D tests | Supply malformed present metadata and assert the finite fail-closed `RuntimeError`. |
| `VERPROJ-V011` | `VERPROJ-011` | 5.5D tests | Inject unexpected and process-control failures and assert unchanged propagation. |
| `VERPROJ-V012` | `VERPROJ-012` | 5.5D tests | Exercise every listed near-valid value and prove zero repair or fallback. |
| `VERPROJ-V013` | `VERPROJ-013` | 5.5D tests | Vary every forbidden ambient input and prove invariant output and behavior. |
| `VERPROJ-V014` | `VERPROJ-014` | 5.5D tests | Compare package, CLI, About, and logging projections and reject divergence. |
| `VERPROJ-V015` | `VERPROJ-015` | packaging/installer/release tests | Verify later Windows projections derive mechanically and remain absent from 5.5C/5.5D scope. |
| `VERPROJ-V016` | `VERPROJ-016` | specification and 5.5D review | Prove prerequisite-only trust use and zero key/bootstrap/signing imports. |
| `VERPROJ-V017` | `VERPROJ-017` | specification and updater review | Prove update and signed-source semantics remain exclusively later-owned. |
| `VERPROJ-V018` | `VERPROJ-018` | specification and frozen-contract review | Verify no Protocol, Persistence, DB, settings, manifest, or trust-schema change. |
| `VERPROJ-V019` | `VERPROJ-019` | 5.5D tests | Block side-effect APIs and prove the lookup is the only permitted local read. |
| `VERPROJ-V020` | `VERPROJ-020` | 5.5D import tests | Inspect imports and execute isolated package-root import without composition side effects. |
| `VERPROJ-V021` | `VERPROJ-021` | specification and 5.5D scope tests | Assert exact implementation/test path sets, additions, and exclusions. |
| `VERPROJ-V022` | `VERPROJ-022` | roadmap and later scope tests | Assert each packaging/installer/release handoff remains in its named owner. |
| `VERPROJ-V023` | `VERPROJ-023` | 5.5D security tests | Mutate every prohibited authority/fallback/parity path and require fail-closed behavior. |
| `VERPROJ-V024` | `VERPROJ-024` | specification and 5.5D reproducibility tests | Run two materializers and audit unique, complete requirement-to-verification traceability. |
| `VERPROJ-V025` | `VERPROJ-025` | 5.5D tests | Assert one lookup per module execution, stable repeated reads, deterministic reload, and no production rebinding. |

## 9. Readiness and handoff

This specification is ready for independent review only when all 25 requirements and all
25 verification rows are unique and paired; missing, orphaned, duplicate, and pseudo-test
counts are zero; contradiction and blocking-ambiguity counts are zero; two implementers
converge; and repository scope contains only this candidate document. Readiness does not
authorize Phase 5.5D implementation, staging, commit, or tag creation.
