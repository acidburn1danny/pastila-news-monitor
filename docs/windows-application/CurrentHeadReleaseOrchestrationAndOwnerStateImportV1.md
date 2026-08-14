# Current-HEAD release and owner-state maintenance

This note records the bounded release-maintenance boundary added after the
`3d0bb961` readiness audit. It does not revise Phase 5.6B qualification.

## Proven prior-build evidence

The retained `v1-release-360e1a7-20260813-001` wheel contains 550 Python files
that match commit `360e1a7e9dfb8640c405fa06f873a0cf90ab2ce3` byte-for-byte. Its
bundled source configuration also matches that commit. The resulting installer
was compiled with Inno Setup 6.7.3 and successfully installed per-user.

The retained work directory proves that the normal installer used deterministic
generated payload-file and payload-verification includes. The exact interactive
shell command was not retained. Reconstructing that command from the generated
includes, `PastilaScout.iss`, and the successful payload is therefore an
inference, now replaced by `build-release-installer.ps1` and its durable receipt.

## Release boundary

`build-installer.ps1` remains the frozen, candidate-bound Phase 5.6B
qualification wrapper. Normal current-HEAD builds use the separately named
`build-release-installer.ps1`. PlanOnly validates the current repository and
bundle, emits a sorted payload manifest and generated Inno includes, and records
the exact future ISCC command without compiling an installer.

Tracked changes are a blocker. Untracked files are permitted because owner
operational state is intentionally untracked; their complete porcelain entries
are recorded as excluded state and the payload must be outside the repository.
The packaged application's local wheel is recovered from its `direct_url.json`,
hash-verified, and every packaged `pastila_scout/*.py` source plus canonical
`sources.yaml` is compared byte-for-byte with the clean accepted HEAD. Thus an
old bundle cannot be relabelled as a current-HEAD release. A fresh current-HEAD
bundle and its retained local wheel are required; no prior installer, payload
inventory, or Phase 5.6B evidence is an input.

Immediately before the single ISCC invocation, compile mode rechecks HEAD,
tracked cleanliness, generated include identities, and every payload hash. It
checks the payload again after compilation before finalizing the installer
identity and Authenticode observation. The JSON receipt is atomically replaced;
PlanOnly records `planned` with null installer fields and never invokes ISCC.
Absolute payload paths appear only as build-time Inno `Source` values; installed
destinations remain relative below the staged application directory.

## Owner-state boundary

`pastila_scout.owner_state_import_v1` is an explicit maintenance command and is
never called during startup. The owner policy is:

- replace the installed database with the accepted authoritative development DB;
- replace ActiveProject only with explicit `--include-active-project` authority,
  relocating its developed-material files into installed reports;
- preserve installed settings and source overrides;
- preserve the historical one-time development-migration receipt;
- write a separate `owner-state-import-v1.json` receipt;
- back up every replaced file and restore it on validation failure.

The CLI accepts only the exact `%LOCALAPPDATA%\PastilaScout` target and a Pastila
Scout Git development root; UNC roots, overlapping roots, and reparse-point
escapes fail closed. Process enumeration must prove both GUI and CLI launchers
stopped, and database lock checks cover source/target concurrency. A source DB
with WAL/SHM/journal sidecars is rejected. Target sidecars are backed up and
removed as part of the rollback-covered replacement sequence.

The database is an owner-authoritative exact replacement, never a merge. Source
validation checks schema, SQLite integrity/foreign keys, final-five category
rows, scalar agreement, IDs, and article references. Optional ActiveProject
identity includes its deterministically relocated JSON and every material hash;
therefore `already_current` is returned only when every requested item matches.
Editor envelopes are checked against their embedded canonical `payload_sha256`
contract, while the importer separately records and compares whole-file SHA-256
for byte-exact transfer and idempotency.
Settings, source overrides, unrelated reports, and the historical migration
receipt are not replaced. Existing receipts and all potentially replaced files
are recorded with existence, size, hash, and collision-safe relative backups.
Multi-file publication uses same-filesystem staging plus `os.replace`; injected
or real failure rolls replacements back in reverse order and revalidates the
restored database.

The owner-PC command must first run with `--preflight`; `--apply` is reserved for
the controlled packaged verification task after the application is closed.
Neither mode runs from desktop startup or the installer, and both require normal
user-writable state paths. Version remains `0.1.0`; no signing or publication is
performed by this prerequisite review.
