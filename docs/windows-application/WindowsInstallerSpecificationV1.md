# Windows Installer Specification V1

Status: Phase 5.6A candidate for independent review. This document specifies
installer behavior only. It does not authorize implementation, signing, updating,
publication, or changes to the frozen application package.

## 1. Authority and scope

The immediate prerequisite is the annotated tag
`phase-5.5f-windows-executable-r1-verified` at
`47af1a3012807eee4695551cd2b413def5ebc6b2`. The installer consumes the exact
frozen Phase 5.5F application-package architecture and does not become a second
packaging, version, trust, state, or runtime authority.

The maintained Windows Desktop Productization authority fixes Inno Setup 6, a
per-user x64 installation, no administrative requirement, one stable AppId, a
Start Menu shortcut, an opt-in Desktop shortcut, preservation of AppData, and an
application payload below `%LOCALAPPDATA%\Programs\PastilaScout`. Frozen Windows
State and State Consumption own mutable paths and development-state migration.
Frozen Version Projection owns `0.1.0` and every future projected version. Frozen
Trust Bootstrap owns the immutable production public trust resources. Windows
Update Protocol V6 and Persistence V6 constrain only future handoff compatibility;
they do not authorize updater behavior here.

Historical Productization descriptions that predate the maintained single-owner
trust model or corrected Phase 5.5B resource set are not installer authority.

| Concern | Effective authority | Superseded authority | Installer implication |
| --- | --- | --- | --- |
| Product topology and installer handoff | Maintained `WindowsDesktopProductizationSpecificationV1.md` | Pre-maintenance Productization interpretations | Inno Setup 6, per-user x64, stable AppId, canonical root and bounded 5.6 ownership |
| Executable payload | `phase-5.5f-windows-executable-r1-verified` | Probes and pre-freeze candidates | Consume one verified flat onedir; do not repackage or redesign it |
| Packaging contract | Current maintained `WindowsExecutablePackagingSpecificationV1.md` | Original frozen 5.5E wording where maintained | Enforce package topology/resources and later-owner boundary |
| Mutable paths/settings | Frozen Windows State and State Consumption chain | Development-relative startup behavior | Preserve external state; installer owns no schema or migration |
| Desktop startup | Frozen facade, shell, Scout/Editor integration, and startup tags | Roadmap-only GUI descriptions | Shortcuts launch existing entry points; installer adds no runtime composition |
| Version | Frozen Version Projection V1 and 5.5D | Editable literals and `0.0.0-dev` | Project only installed distribution metadata; no installer version authority |
| Bootstrap trust | Maintained 5.5A and corrected frozen 5.5B | Provenance/two-operator resource model | Install exact two-resource production bootstrap; no key generation or mutable trust |
| Notices and branding | Frozen 5.5F resources | Superseded notices candidates and provisional branding | Reuse exact current corpus and icon; no fallback |
| Future update state | Frozen Protocol V6 and Persistence V6 | Earlier protocol/persistence revisions | Preserve compatibility and state; implement no updater behavior |
| Signing/publication | Later Productization owners | Any implied 5.6 signing responsibility | Excluded from 5.6A/B |

The exact frozen Phase 5.5F committed owner set is:

| Path | Bytes | SHA-256 |
| --- | ---: | --- |
| `packaging/pyinstaller/PastilaScout.spec` | 3,152 | `C396EB59622878EB868EE8F80329118A4C2F41D9D7AC32B7FE6087F833867F9A` |
| `packaging/pyinstaller/version_info.txt.in` | 745 | `B543EFBA8AA340707DC6E81C792381A2B6B9C9BD36857D6AF53B14CB16F78CE3` |
| `packaging/pyinstaller/build.ps1` | 22,174 | `C2A0E04BF391E15F6574FD8BE50C6BF5FE96468FF4BE78D541E9EB29A377CC44` |
| `packaging/resources/PastilaScout.ico` | 176,052 | `605B76E16C442C97E0268A8203B7F898EE2DE5B17A1654DC043D1F7718B3D947` |
| `packaging/resources/THIRD-PARTY-NOTICES.txt` | 165,124 | `20DA9DC9E2B66EF7C1774D83A777F4593DB531BC48E6CB4ED4E74604AF096686` |
| `tests/packaging/test_frozen_application_v1.py` | 7,852 | `BC57C795E0762119003CC5CD07CC3557387FE2E96B2A55D77151EA551FA1BD8C` |
| `tests/packaging/test_version_parity_v1.py` | 2,494 | `A81B34CF2AEA1E3C4364EA9A519349D86B45468E35D149E78A9835CB9EB542CB` |
| `tests/packaging/test_build_mode_v1.py` | 13,712 | `4716B59AE563C0F93E0624F49A4142A0F35EE35B4E83E99BA176768ADA6E2F05` |

These paths are immutable inputs, not Phase 5.6 candidate paths.

`INS-001` Phase 5.6A owns only this specification. Phase 5.6B may own only the
installer definition, build wrapper, tests, reused frozen resources, and external
verification evidence named in Section 18.

`INS-002` The installer MUST preserve every frozen Phase 5.5F runtime and package
decision, including the flat shared onedir, exactly two launchers, GUI/console
subsystem split, resources, trust, notices, icon, version projection, provider
boundaries, and external mutable-state architecture.

`INS-003` Runtime code MUST NOT import, locate, or branch on Inno Setup, installer
metadata, installer staging names, or uninstall registration.

## 2. Platform, identity, and topology

The product display name is `Pastila Scout`. The stable Inno AppId is the exact
case-sensitive string `PastilaScout`. These are installer identities, not publisher
or version authorities.

`INS-004` The supported target MUST be native Windows x64 on Windows 10 version
1809 or later and Windows 11. A 32-bit OS or non-x64 process architecture MUST fail
before payload mutation.

`INS-005` Installation MUST be per-user, MUST use the current interactive user's
profile, MUST NOT require elevation, and MUST refuse an execution context that
would redirect ownership to another user.

`INS-006` The canonical install root MUST be
`%LOCALAPPDATA%\Programs\PastilaScout`; the immutable application root MUST be its
`app` child. Installer-private staging and rollback directories MAY exist only as
temporary siblings beneath the canonical install root.

`INS-007` The application root MUST contain only the governed flat Phase 5.5F app
bundle. Installer metadata, logs, downloaded inputs, evidence, and mutable user
state MUST NOT be placed inside `app`.

`INS-008` The installer MUST register one per-user product identity with AppId
`PastilaScout`. A version change MUST upgrade that identity rather than creating a
side-by-side product.

## 3. Frozen payload acceptance

The 5.6B build wrapper receives a verified Phase 5.5F `app` directory and an
external deterministic inventory for that directory. The inventory is build
evidence, not a repository or runtime authority. It binds every relative path,
file type, byte length, and SHA-256 digest. It is retained outside the repository
with installer-build evidence and is not installed.

The inventory bytes are strict RFC 8785 JCS for one JSON array. Each array member
has exactly `path`, `type`, `size`, and `sha256`. `path` is a non-empty relative
forward-slash path with no empty, dot, dot-dot, drive, UNC, backslash, leading-
slash, trailing-slash, control, or case-insensitive duplicate form. Members are
sorted by UTF-8 ordinal `path`. `type` is exactly `directory` or `file`.
Directories have `size=null` and `sha256=null`; files have a nonnegative integer
byte size and an uppercase 64-hex SHA-256. The input root itself is implicit and
is not a member. Empty directories, when present, are represented explicitly.

`INS-009` Before invoking Inno Setup, the build wrapper MUST verify the complete
payload against its supplied inventory and MUST reject a missing, extra, duplicate,
non-regular, or byte-mismatched entry.

`INS-010` Accepted payload topology MUST have exactly two top-level executables:
`PastilaScout.exe` and `pastila-scout.exe`; no third top-level executable and no
`_internal` application root are permitted.

`INS-011` Both launchers MUST project the same stable SemVer obtained from installed
`pastila-news-monitor` distribution metadata. `0.0.0-dev`, prerelease, build
metadata, malformed versions, and launcher/package disagreement MUST fail before
installer creation.

`INS-012` The payload MUST contain the exact frozen production bootstrap JSON and
raw public key, current `THIRD-PARTY-NOTICES.txt`, `PastilaScout.ico`-derived
launcher branding, certifi CA data, Tcl/Tk data, bundled configuration, default
settings, localization, and distribution metadata required by Phase 5.5F.

`INS-013` Payload acceptance MUST reject private keys, development/test trust,
test fixtures, repository metadata, source checkout paths, build/probe/evidence
residue, mutable databases, reports, logs, caches, or updater state.

`INS-014` The installer build MUST consume the payload bytes without modifying,
normalizing, regenerating, or substituting any application file.

`INS-065` The wrapper MUST reject inventory bytes that are not exact JCS, violate
the schema or ordering above, disagree with a fresh no-follow enumeration, name
an unsupported filesystem object, or whose own SHA-256 was not recorded with the
accepted 5.5F evidence. The installer MUST embed the validated expected entries
as construction data, not install the external inventory as runtime payload.

## 4. Path safety and pre-mutation validation

`INS-015` All source, destination, stage, rollback, shortcut, log, and uninstall
paths MUST be resolved to absolute Windows paths using case-insensitive,
trailing-separator-insensitive comparison before mutation.

`INS-016` Source and destination MUST be distinct and neither may equal, contain,
or be contained by the other after normalization. The build wrapper MUST reject
aliases caused by `.`/`..`, alternate separators, short names, case, or trailing
spaces/dots.

`INS-017` Every existing component from the selected root through the application,
stage, and rollback targets MUST be opened or inspected without following a
reparse point. A symlink, junction, mount point, or other reparse escape MUST fail.

`INS-018` Before payload mutation, the installer MUST validate platform, current
user scope, canonical destination, running-instance state, payload metadata,
version policy, writable parent, destination topology, and sufficient free space.

`INS-019` Free-space validation MUST cover the new payload, temporary stage,
rollback copy/rename needs, installer overhead, and a fixed 64 MiB safety margin.

`INS-020` A non-empty destination not owned by the same AppId and valid uninstall
registration MUST be a destination conflict. The installer MUST NOT adopt, merge,
or delete it.

## 5. Placement, replacement, and failure semantics

Inno Setup owns its documented cancel/revert and file-replacement behavior. This
specification does not claim a general filesystem transaction. The required model
is validate, stage on the destination volume, verify, replace, repair surfaces,
and retain only bounded rollback material until success.

`INS-021` The installer MUST stage the complete immutable payload beneath the
canonical install root on the same volume, verify its inventory again, and publish
only after all pre-mutation checks pass.

`INS-022` Reinstall and upgrade MUST replace the complete installer-owned `app`
directory rather than overlaying files. This MUST remove stale immutable files
that are absent from the new inventory.

`INS-023` Before replacement, the installer MUST ensure both launchers and all
known product processes are stopped. Interactive installation MAY request an
ordinary close; unattended installation MUST fail if safe closure is unavailable.

`INS-024` If replacement fails after the old payload is displaced, the installer
MUST attempt restoration of the prior complete payload and prior installer-owned
surfaces. It MUST report honestly whether restoration succeeded.

`INS-025` Stage and rollback directories MUST use unpredictable operation-local
names, MUST remain beneath the verified canonical root, MUST reject reparse points,
and MUST be removed after confirmed success. Failed cleanup MUST be reported and
MUST NOT be described as rollback failure when the active payload is valid.

`INS-026` Shortcut or uninstall-registration failure after payload publication
MUST trigger repair or rollback of installer-owned surfaces. It MUST never delete
or alter external user state.

`INS-069` Phase 5.6B MUST realize the sequence without a helper executable or DLL:
the wrapper emits deterministic Inno file declarations into its external work
root with the temporary destination as target; Inno Pascal verifies those staged
entries against embedded expected size/hash data, preserves the prior `app` by a
same-parent directory rename, renames verified stage `app` into the canonical
location, creates installer surfaces, and restores the preserved directory if a
later required step fails. Inno's documented revert behavior remains responsible
for declarative surfaces and extracted temporary files. Pascal owns only the two
bounded directory renames, verification, restoration, and cleanup. A rename or
restoration failure is terminal and reported honestly; no copy fallback, reboot
replacement, or second runnable root is permitted.

## 6. Mutable state and migration

Frozen Windows State owns roaming settings and local databases, caches, reports,
logs, migrations, and future update state beneath `%APPDATA%\PastilaScout` and
`%LOCALAPPDATA%\PastilaScout`. The installer owns none of their schemas.

`INS-027` Fresh install, reinstall, repair, upgrade, downgrade rejection, and
default uninstall MUST preserve all external mutable state byte-for-byte except
for normal application activity outside the installer process.

`INS-028` The installer MUST NOT copy development-relative state, invoke
development migration, seed settings, create databases, transform schemas, or
make migration eligibility decisions. First-launch migration remains exclusively
application-owned.

`INS-029` Installer detection of external state MAY be used only to display the
user-data preservation choice during uninstall. It MUST NOT validate or interpret
that state as an installation prerequisite.

`INS-030` Optional user-data removal MUST be a separate, unchecked, interactive
uninstall choice with an irreversible-action warning. It MAY remove only the two
canonical PastilaScout state roots after alias/reparse validation. Silent uninstall
MUST preserve user data.

## 7. Launch surfaces and registration

`INS-031` Installation MUST create one per-user Start Menu shortcut named
`Pastila Scout` targeting `app\PastilaScout.exe`, with the frozen icon and the
install root as working directory.

`INS-032` A Desktop GUI shortcut MAY be created only by an unchecked explicit
installation task. Its target, icon, arguments, and working directory MUST equal
the Start Menu GUI shortcut semantics.

`INS-033` CLI shortcuts, PATH mutation, command aliases, file associations,
protocol handlers, Explorer context menus, services, scheduled tasks, startup
entries, and shell extensions are FORBIDDEN in V1.

`INS-034` The installer MUST create per-user Add/Remove Programs registration with
display name `Pastila Scout`, version from the verified package projection,
AppId `PastilaScout`, x64 architecture, canonical install location, frozen icon,
and a safely quoted uninstall command.

`INS-035` Publisher, company, copyright, support URL, update URL, and website
fields MUST be omitted unless exact owner-approved values are supplied as governed
5.6B inputs. They MUST NOT be inferred from package names or fabricated.

`INS-036` Estimated size MAY be recorded only as the deterministic sum of installed
immutable payload and installer-owned metadata, rounded using one documented Inno
Setup-compatible rule.

`INS-067` Registration MUST use the current user's 64-bit uninstall registry view.
Inno-generated `UninstallString` and `QuietUninstallString` MUST be safely quoted,
target the same uninstaller, and differ only by standard quiet arguments. Quiet
uninstall MUST remove binaries/surfaces only and MUST have no user-data-removal
argument. HKLM, the 32-bit uninstall view, and a per-machine registration are
forbidden.

## 8. Version and lifecycle policy

`INS-037` Installer version, artifact version, Add/Remove Programs version, and
embedded application version MUST be exact projections of installed distribution
metadata. The installer definition MUST contain no independently editable version.

`INS-038` A fresh install MUST publish the complete verified payload and all
required installer-owned surfaces without reading or changing external state.

`INS-039` A same-version reinstall MUST act as deterministic repair: verify the
incoming payload, completely replace immutable payload bytes, restore required
shortcuts/registration, honor the current Desktop-shortcut task choice, and
preserve external state.

`INS-040` An upgrade to a greater stable SemVer MUST replace the complete immutable
payload, remove stale immutable files, update shortcuts and registration, preserve
external state, and leave application schema migration to application startup.

`INS-041` A local installer whose stable SemVer is lower than the registered
version MUST fail before mutation. V1 defines no downgrade override because state
compatibility is not proven; future authenticated recovery remains separately owned.

`INS-042` A malformed, development, prerelease, build-metadata, missing, or
mismatched version MUST fail before installer creation and before installation.

`INS-043` Standard Inno per-user silent installation switches MAY be supported for
future bounded handoff compatibility, but they MUST use identical validation,
destination, version, state-preservation, and failure semantics. No custom updater
mode or network behavior is authorized.

`INS-066` Direct interactive installation MUST use Inno Setup Restart Manager only
to identify processes holding files beneath the canonical `app`, request their
ordinary close, and wait at most 30 seconds. If any relevant process or lock remains,
installation MUST abort before payload mutation. Silent installation MUST perform
the same detection but MUST neither prompt nor request closure; any relevant process
or lock is an immediate pre-mutation failure. Forced termination, FilesInUse reboot
scheduling, delayed replacement at reboot, and automatic application restart are
forbidden. The later Protocol V6 `/RESTARTAPPLICATIONS` and cooperative application-
mutex handoff remain 5.7-owned and are not implemented or simulated by 5.6B.

## 9. Uninstall

`INS-044` Default uninstall MUST remove only the immutable `app` payload,
installer-private metadata and temporary material, Start Menu shortcut, installer-
created Desktop shortcut, and per-user uninstall registration.

`INS-045` Default and silent uninstall MUST preserve settings, databases, caches,
reports, logs, exports, migration records, update state, trust state, and any other
user-owned files outside the install root.

`INS-046` Explicit interactive user-data removal MUST occur only after product
binary removal has been decided, MUST list the two canonical state roots, MUST
revalidate aliases/reparse points immediately before deletion, and MUST refuse any
path outside those roots.

`INS-047` Uninstall failure MUST identify the failed ownership class—process,
payload, shortcut, registration, temporary cleanup, or optional user-data removal—
without claiming that unrelated classes were removed.

## 10. Trust, notices, branding, and network boundary

`INS-048` The installer MUST install the frozen production public trust resources
unchanged and read-only with the application payload. It MUST NOT generate keys,
accept private or development trust, fetch trust, create mutable trust, implement
TOFU, or provide fallback trust.

`INS-049` The exact current `THIRD-PARTY-NOTICES.txt` supplied by the verified
payload MUST be installed. A missing, stale, substituted, generated, or fallback
notices corpus MUST fail payload acceptance.

`INS-050` Installer, shortcut, and Add/Remove Programs branding MUST reuse the
frozen `PastilaScout.ico`. No alternate icon, downloaded branding, or placeholder
is permitted.

`INS-051` Phase 5.6 MUST perform no network access. Payload download, update
checking, signature retrieval, timestamping, telemetry, crash submission, and
publication belong to later explicitly authorized phases.

`INS-052` Authenticode, RFC 3161 timestamping, Ed25519 release signatures, and
source authenticity are not installer-construction authority in Phase 5.6A/B.
Their absence MUST NOT be misrepresented as verification, and no private signing
material may enter repository or installer inputs.

## 11. Technology and deterministic construction

`INS-053` Phase 5.6B MUST use governed Inno Setup 6 and record the exact compiler
version, installer definition SHA-256, wrapper SHA-256, payload-inventory SHA-256,
payload version, build command, environment, output size, and output SHA-256.

`INS-054` Installer creation MUST be offline from a clean external work root using
only the verified payload, the two authorized 5.6B files, frozen icon, version
projection, optional exact owner metadata, and a pre-provisioned governed Inno
Setup compiler. Missing input MUST fail; automatic download is forbidden.

`INS-055` Builds are required to be deterministic in inputs, topology, metadata,
and behavior. Byte-for-byte installer reproducibility is not claimed unless Inno
Setup and PE timestamp behavior are separately proven and authorized.

`INS-068` Implementation allocation is exact: ordinary identity, architecture,
privilege, file, icon, shortcut, uninstall, and compression settings use native
Inno declarations; lifecycle checks, staged inventory verification, bounded
rename/restoration, canonical `app` removal during uninstall, state-removal
confirmation, and safe logging use Inno Pascal;
payload/inventory/toolchain validation and deterministic generated declarations
use `build-installer.ps1`; `GetFinalPathNameByHandleW`, `GetFileInformationByHandleEx`,
`GetVolumeInformationW`, and `IsWow64Process2` MAY be invoked from Pascal as system
Windows APIs for canonical identity, reparse/volume checks, and native AMD64
verification. No other executable, DLL, service, driver, scheduled task, or runtime
Python component is authorized. A requirement not enforceable by those mechanisms
MUST fail the 5.6B architecture gate rather than introduce a hidden helper.

| Major behavior | Required mechanism | Enforceability |
| --- | --- | --- |
| Product identity, architecture, privilege, compression, icons, shortcuts, and uninstall registration | Native Inno declarations | Directly enforceable |
| Deterministic payload inventory and toolchain acceptance | PowerShell build wrapper | Directly enforceable before compilation |
| Deterministic file-entry construction | PowerShell-generated Inno declarations | Directly enforceable and reviewable as generated input |
| Canonical-path, reparse, volume, and native-AMD64 checks | Inno Pascal plus the named Windows APIs | Directly enforceable on the target host |
| Stage verification, bounded directory activation/restoration, and canonical application removal | Inno Pascal | Directly enforceable with failure injection |
| Restart Manager close request and lock refusal | Native Inno behavior plus bounded Pascal policy | Directly enforceable in lifecycle tests |
| Mutable-state removal confirmation and bounded installer logging | Inno Pascal | Directly enforceable in lifecycle tests |
| Byte-identical installer reproducibility | No authorized mechanism or proven authority | Not enforceable and not claimed |
| Code signing, timestamping, updating, or release distribution | Outside Phase 5.6B | Not enforceable here; separately owned |

## 12. External inputs

| Input | Specification | Implementation | Public release | Owner-controlled |
| --- | --- | --- | --- | --- |
| Frozen 5.5F app payload and inventory | Required | Required | Required | Governed evidence |
| Governed Inno Setup 6 compiler | Identified | Required | Required | Provisioned toolchain |
| Frozen icon/notices/trust/version | Required authority | Required by payload | Required | Frozen |
| Publisher/legal fields | Not required | Optional exact input | Advisable | Yes |
| Signing certificate/private key | Excluded | Excluded | Optional/later | Yes/external |
| Timestamp service | Excluded | Excluded | Optional/later | External |
| Distribution/update URL | Excluded | Excluded | Later only | Yes |
| License/custom installer text | Not required | Omit unless approved | Optional | Yes |

## 13. Failures and diagnostics

`INS-056` The installer MUST distinguish at least: invalid payload, unsupported
platform, invalid user scope, topology/alias/reparse violation, destination
conflict, running application, permission failure, insufficient space, staging,
verification, replacement, shortcut, registration, version mismatch, downgrade,
uninstall, rollback, and cleanup failure.

`INS-057` Interactive failures MUST be concise and actionable and MUST name a safe
path or corrective action only when doing so discloses no secret. Silent failures
MUST return a documented nonzero exit code and write the same bounded category to
the installer log.

`INS-058` Installer logs MUST be local, per-operation, bounded, and stored outside
the application root under the frozen log authority at
`%LOCALAPPDATA%\PastilaScout\logs\installer`. Logs MAY contain versions, stages,
safe paths, exit codes, and hashes; they MUST exclude
credentials, private material, document contents, environment dumps, provider
payloads, and telemetry identifiers.

`INS-059` No failure path may retry with weaker validation, alternate roots,
repository files, CWD-relative resources, network acquisition, or partial trust.

## 14. Security model

| Threat | Frozen mitigation | Installer requirement | Residual risk |
| --- | --- | --- | --- |
| Payload substitution | 5.5F inventory/resource gates | Complete inventory validation and byte-preserving consumption | Local source may be untrusted before validation |
| Traversal/alias | Windows State absolute-root rules | Absolute normalization, ancestry rejection, and destination ownership checks | Same-user race bounded by immediate revalidation |
| Junction/reparse escape | Alias-safe state authority | Reject and revalidate reparse components | Same-user mutation between checks |
| Stale files | Flat governed onedir | Complete directory replacement | Cleanup may require manual action |
| Privilege escalation | Per-user authority | No elevation or cross-user install | User account compromise |
| User-data deletion | External state ownership | Preserve by default; explicit narrow removal | Owner-confirmed deletion is irreversible |
| Trust substitution | Immutable bootstrap | Install exact payload; no trust generation/fetch | Future signing is separately owned |
| Shortcut hijack | Fixed launcher/root | Exact targets and quoted commands | Same-user post-install mutation |
| Uninstall injection | Stable AppId | Safely generated per-user command | Registry mutation by compromised user |
| CWD/environment dependence | Frozen installed composition | Absolute targets; offline inputs | Host OS/toolchain compromise |

## 15. Installed-layout acceptance

`INS-060` Phase 5.6B verification MUST install into a clean non-administrative
Windows profile and prove canonical roots, complete payload inventory, exactly two
launchers, version parity, resources, trust, notices, icon, shortcuts, registration,
and absence of mutable state inside `app`.

`INS-061` Acceptance MUST launch CLI `--version` and the GUI from an unrelated CWD,
prove no repository dependency or network/credential use, and repeat relevant
read-only-root, non-ASCII profile, and governed long-path checks without re-proving
unchanged PyInstaller internals.

`INS-062` Lifecycle tests MUST use disposable external profiles and copies. They
MUST verify fresh install, reinstall, repair, upgrade, downgrade rejection,
uninstall, reinstall after uninstall, state preservation/removal choice,
interruption/failure, destination conflict, reparse/alias attack, arbitrary CWD,
non-ASCII path, long path, and non-elevated execution.

## 16. Lifecycle matrix

| Scenario | Required result |
| --- | --- |
| Clean install | Complete payload and required surfaces; no state mutation |
| Same-version reinstall | Complete replacement and deterministic repair |
| Missing shortcut/registration | Recreated from verified payload metadata |
| Upgrade | Greater stable SemVer replaces payload; state preserved |
| Downgrade | Rejected before mutation |
| Default uninstall | Installer-owned material removed; user data preserved |
| Explicit data removal | Only canonical state roots removed after confirmation |
| Reinstall after uninstall | Fresh payload; preserved state remains consumable |
| Interrupted/failed install | Prior valid payload restored when displaced; honest status |
| Destination conflict | Refused without adoption or deletion |
| Reparse/alias attack | Refused before mutation or deletion |
| Non-ASCII profile | Install, launch, repair, and uninstall succeed |
| Governed long path | Validation and lifecycle succeed within supported limits |
| Arbitrary-CWD launch | CLI and GUI use installed absolute/resource semantics |
| No-admin execution | Succeeds without elevation; cross-user scope refused |

## 17. Architectural Humility decisions

| Feature | Need | Complexity | Authority impact | Decision |
| --- | --- | ---:| --- | --- |
| Start Menu GUI shortcut | Normal launch | Low | Existing | Keep |
| Desktop shortcut | User preference | Low | Existing | Keep opt-in |
| PATH/CLI shortcut | No demonstrated need | Medium | New shell authority | Forbid |
| Same-version repair | Corruption recovery | Medium | Installer-owned | Keep, full replacement |
| Downgrade | Compatibility unproven | High | Recovery/state authority | Forbid |
| User-data removal | Uninstall expectation | Medium | State boundary | Keep explicit/unchecked |
| Silent install | Future bounded handoff | Low | Existing Inno behavior | Keep same semantics |
| Silent data removal | No need | High risk | State authority | Forbid |
| Self-update/network | Later-owned | High | New runtime authority | Defer |
| Signing | Public-release concern | High/external | Release authority | Defer |
| Custom installer UI | No need | Medium | New presentation owner | Forbid |
| Sophisticated transaction engine | No proof/value | High | Competing filesystem owner | Simplify to bounded stage/restore |

## 18. Phase 5.6B handoff

Phase 5.6B owns exactly:

- `packaging/inno/PastilaScout.iss`;
- `packaging/inno/build-installer.ps1`;
- `tests/packaging/test_inno_installer_v1.py`;
- unchanged reuse of the frozen Phase 5.5F payload and resources;
- external preparation, build, lifecycle, and integration evidence.

It owns no production Python module, runtime API, updater, signing key, release
workflow, source bundle, version literal, alternate icon/notices/trust resource, or
repository evidence manifest.

`INS-063` Two independent implementations conform only if they choose the exact
identity, roots, payload validation, shortcuts, registration, lifecycle, state,
version, trust, offline, diagnostics, and verification semantics in this document.

`INS-064` Phase 5.6B MUST fail its final scope gate unless its candidate consists
only of the three repository paths above and independently retained external evidence.

## 19. Requirements and traceability

| ID | Requirement summary | Verification method | Future owner |
| --- | --- | --- | --- |
| INS-001 | Single specification/implementation ownership | Scope and Git-path audit | 5.6A/5.6B review |
| INS-002 | Preserve frozen package decisions | Static/candidate comparison | Installer tests |
| INS-003 | Runtime independent of installer | Import/search test | Installer tests |
| INS-004 | Windows 10 1809+/11 x64 | Platform negative/positive tests | Build wrapper/installer |
| INS-005 | Per-user, non-admin, same user | Token/elevation tests | Installer |
| INS-006 | Canonical roots | Installed-layout test | Installer |
| INS-007 | App-root ownership | Recursive inventory test | Installer tests |
| INS-008 | Stable AppId and one product | Registry/upgrade test | Installer |
| INS-009 | Complete inventory binding | Payload mutation matrix | Build wrapper |
| INS-010 | Exactly two launchers | Root inventory test | Build wrapper/tests |
| INS-011 | Stable version parity | PE/metadata/CLI test | Build wrapper/tests |
| INS-012 | Required resources | Resource inventory test | Build wrapper/tests |
| INS-013 | Forbidden payload content | Recursive negative scan | Build wrapper/tests |
| INS-014 | Byte-preserving consumption | Pre/post hash comparison | Build wrapper |
| INS-065 | Canonical inventory schema and evidence binding | JCS/schema/order/enumeration mutation matrix | Build wrapper/tests |
| INS-015 | Absolute normalized paths | Path-table unit tests | Build wrapper/installer |
| INS-016 | Alias/ancestry rejection | Alias matrix | Build wrapper/installer |
| INS-017 | Reparse rejection | Junction/symlink tests | Installer tests |
| INS-018 | Complete preflight | Fail-before-mutation tests | Installer |
| INS-019 | Space calculation | Boundary tests | Installer |
| INS-020 | Destination ownership conflict | Disposable conflict test | Installer |
| INS-021 | Same-volume staged publication | Lifecycle observation | Installer |
| INS-022 | Full replacement/stale removal | Reinstall/upgrade test | Installer |
| INS-023 | Running-process handling | Interactive/silent tests | Installer |
| INS-024 | Bounded restoration | Injected replacement failure | Installer |
| INS-025 | Safe stage/rollback cleanup | Path/failure tests | Installer |
| INS-026 | Surface failure handling | Injected shortcut/registry failure | Installer |
| INS-069 | Helper-free staged activation and restoration | Generated-script audit and injected lifecycle failures | Installer tests/evidence |
| INS-027 | State preservation | Pre/post state inventory | Installer tests |
| INS-028 | Application-owned migration | Call/import/state audit | Installer tests |
| INS-029 | No state interpretation | Instrumented state fixtures | Installer tests |
| INS-030 | Explicit data-removal choice | Interactive/silent uninstall tests | Installer |
| INS-031 | Required Start Menu shortcut | Shortcut target inspection | Installer tests |
| INS-032 | Opt-in Desktop shortcut | Task-choice matrix | Installer tests |
| INS-033 | Forbidden shell surfaces | Registry/PATH/task scan | Installer tests |
| INS-034 | Required ARP registration | Per-user registry inspection | Installer tests |
| INS-035 | No fabricated metadata | Input/registry negative tests | Build wrapper/tests |
| INS-036 | Deterministic optional size | Registry/value test | Installer tests |
| INS-067 | Exact per-user uninstall registration and quiet parity | 64-bit HKCU registry/command execution matrix | Installer tests |
| INS-037 | Single version projection | Cross-surface parity test | Build wrapper/tests |
| INS-038 | Fresh-install behavior | Lifecycle test | Installer tests |
| INS-039 | Reinstall/repair behavior | Lifecycle test | Installer tests |
| INS-040 | Upgrade behavior | Two-version lifecycle test | Installer tests |
| INS-041 | Downgrade rejection | Older-version negative test | Installer tests |
| INS-042 | Invalid-version rejection | Version mutation matrix | Build wrapper/tests |
| INS-043 | Silent install parity | Interactive/silent comparison | Installer tests |
| INS-066 | Bounded direct-install process handling | Restart Manager interactive/silent lock matrix | Installer tests |
| INS-044 | Binary uninstall ownership | Post-uninstall inventory | Installer tests |
| INS-045 | Default state preservation | State hash comparison | Installer tests |
| INS-046 | Narrow explicit state deletion | Reparse/path/deletion matrix | Installer tests |
| INS-047 | Honest uninstall failure | Injected failure matrix | Installer tests |
| INS-048 | Immutable production trust | Resource hash/forbidden scan | Build wrapper/tests |
| INS-049 | Exact notices | Notices identity tests | Build wrapper/tests |
| INS-050 | Frozen icon reuse | PE/shortcut/ARP icon tests | Build wrapper/tests |
| INS-051 | Zero network | Process/network observation | Build/lifecycle tests |
| INS-052 | Signing boundary | Scope/input/secret scan | 5.6B review |
| INS-053 | Governed Inno evidence | Toolchain/provenance audit | Build wrapper |
| INS-054 | Offline clean construction | Clean-environment build | Build wrapper |
| INS-055 | Honest determinism claim | Two-build semantic comparison | 5.6B review |
| INS-068 | Closed implementability allocation | Static mechanism/API/helper audit | 5.6B review |
| INS-056 | Failure taxonomy | Failure-injection matrix | Installer tests |
| INS-057 | Actionable bounded errors | UI/exit/log assertions | Installer tests |
| INS-058 | Safe local logging | Log path/content tests | Installer tests |
| INS-059 | No weak fallback | Adversarial negative tests | Installer tests |
| INS-060 | Installed-layout acceptance | Clean-profile integration | Installer tests/evidence |
| INS-061 | Runtime launch acceptance | CLI/GUI integration | Installer evidence |
| INS-062 | Complete lifecycle matrix | Disposable-profile matrix | Installer tests/evidence |
| INS-063 | Deterministic implementer outcome | Two-implementer review | Independent review |
| INS-064 | Exact 5.6B scope | Git/candidate path audit | 5.6B review |

There are 69 normative requirements and 69 verification rows. Every requirement is
declared once and mapped once; there are no orphan, duplicate, or pseudo-test rows.

## 20. Adversarial and two-implementer closure

Two independent implementers receive the same fixed technology, identity, platform,
roots, input contract, validation sequence, full-directory replacement model, process
handling, shortcuts, registration, state rules, version policy, uninstall behavior,
security boundary, evidence obligations, and three-path implementation owner. They have
no architectural choice requiring invention; differences may be only non-normative Inno
syntax or test-fixture organization within the one test file.

The adversarial review rejects wrong or partial payloads, old notices, alternate icons,
private/development trust, a third launcher, stale upgrade files, alias/ancestry overlap,
reparse escape, foreign destinations, running-process races, second version literals,
unsafe downgrade, silent state deletion, fabricated publisher fields, CWD/repository
fallback, online acquisition, signing leakage, and updater behavior. Failure injection
closes placement, shortcut, registration, rollback, uninstall, and cleanup ambiguity.

The bounded residual risks are same-user mutation between path checks, host/toolchain
compromise, antivirus interference, and Inno Setup's documented non-transactional edge
cases. Phase 5.6B must observe and report them; it must not invent a kernel-level
transaction, service, privileged helper, or updater to eliminate them.
