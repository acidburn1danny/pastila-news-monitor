# Trust Bootstrap Specification V1

## 1. Authority, maintenance precedence, scope, and readiness

`TRUST-001` This document is the maintained Phase 5.5A authority at
`docs/windows-application/TrustBootstrapSpecificationV1.md`. The original specification
is immutable history at `phase-5.5a-trust-bootstrap-spec-v1-ready`, commit
`556ee1a3269329dd78745e2f6bbf8e96dfc5ac07`, with SHA-256
`1F19D796BFAC4E87E897C27E999B6251986A207141BB01BC27183923DA476693`. This maintenance
consumes that original authority plus verified overlay
`phase-5-productization-single-owner-trust-policy-maintenance-r1-verified`, commit
`1b8ef121b4ff5d147b069d91a68c33156c51f3a6`. The overlay takes precedence only where the
original requires organizational provenance, multiple operators, external receipts, or
mandatory enterprise ceremony. All unchanged technical trust requirements remain
inherited, including verified 5.4D as the original Phase 5.5A prerequisite. Subsequent
Phase 5.5B work consumes this maintained specification; it must not interpret the original
eight-member/three-resource model as current authority.

`TRUST-002` Phase 5.5B changes exactly these four public resource/test-vector paths:

- `resources/trust/pastila-root-1.pub`
- `resources/trust/bootstrap-root-v1.json`
- `tests/fixtures/windows-trust/development-pastila-root-1.pub`
- `tests/fixtures/windows-trust/development-bootstrap-root-v1.json`

Its sole test owner is `tests/test_trust_bootstrap_resource_v1.py`. Phase 5.5B adds no
runtime API or Python production module. No provenance resource, hidden fixture, private
material, updater behavior, packaging behavior, or stable build without a verified
production public key is authorized.

`TRUST-003` The bootstrap resources are immutable, non-secret verification authority and
grant no signing capability. A private key, seed, signing password, HSM credential, API
secret, recovery secret, encrypted private-key blob, or development private-key fixture
never enters the repository, builder, CI, logs, application bundle, fixture set, or
bootstrap metadata. Private-key storage and operational hardening remain outside Phase
5.5A and cannot change public-resource validity.

`TRUST-004` Phase 5.5A specifies only initial public trust material. It does not implement
key generation, signing, trust-metadata signing, payload verification, download,
activation, update discovery, installer verification, release publication, revocation,
rotation, recovery, restart, handoff, rollback, UI, operator approval, or a key ceremony.

## 2. Trust identity and production public-key resource

`TRUST-005` The production bootstrap root identity is exactly `pastila-root-1`. It names
one Ed25519 public key. The identifier is case-sensitive and is never normalized,
aliased, inferred from bytes, selected from the environment, or reused for different key
bytes. Version `1` is part of the literal identifier and defines no rotation procedure.

`TRUST-006` `resources/trust/pastila-root-1.pub` contains exactly 32 raw Ed25519 public-key
bytes. It is binary: it has no PEM wrapper, DER container, base64, UTF-8 marker,
byte-order mark, prefix, suffix, or newline. Empty, short, long, text-wrapped, or otherwise
malformed content is invalid.

`TRUST-007` The authoritative public-key fingerprint is SHA-256 over those exact 32 bytes,
represented as exactly 64 lowercase hexadecimal ASCII characters without a `sha256:`
prefix. Uppercase, short, long, prefixed, or nonhexadecimal forms are invalid. The key
filename, key identifier, algorithm, and fingerprint are distinct and none substitutes
for another.

`TRUST-008` Before Phase 5.5B, the single owner supplies the exact production public bytes
from the owner-controlled Ed25519 signing authority. Phase 5.5B freezes only those public
bytes and their deterministic bootstrap metadata. No verifier, witness, receipt,
generation timestamp, external organization, HSM, second person, offline host, removable
medium, or custody claim is a validity input. Offline generation, encrypted storage, and
hardware custody are optional owner-selected hardening and must not be claimed unless
actually used. Stable packaging remains forbidden until the exact production resources
are verified and frozen by the later corrected Phase 5.5B identity.

## 3. Bootstrap metadata and closed binding

`TRUST-009` `resources/trust/bootstrap-root-v1.json` is UTF-8 without a byte-order mark and
is exactly one RFC 8785 JCS object with no leading or trailing whitespace and no trailing
newline. It contains exactly these six members:

| Key | JSON type | Exact value or constraint |
| --- | --- | --- |
| `schema` | string | `pastila-scout-bootstrap-root` |
| `schema_version` | integer | `1` |
| `key_id` | string | `pastila-root-1` |
| `algorithm` | string | `Ed25519` |
| `public_key_filename` | string | `pastila-root-1.pub` |
| `public_key_sha256` | string | SHA-256 form from `TRUST-007` |

Duplicate, missing, or extra members are invalid. JSON booleans, null, arrays, objects,
and numbers of another type never substitute for the stated types. In particular,
`provenance_filename` and `provenance_sha256` are forbidden extra members.

`TRUST-010` JCS is the byte authority for the bootstrap JSON. A parsed object that is
semantically equivalent but whose bytes are not its RFC 8785 serialization is invalid.
Canonical bytes use JCS lexicographic member ordering and no insignificant whitespace.

`TRUST-011` The bootstrap object and public-key bytes form one closed pair. The JSON
`key_id` equals `pastila-root-1`; `public_key_filename` is the literal sibling basename;
and `public_key_sha256` equals SHA-256 of the exact raw key bytes. `schema_version` is JSON
integer `1`; a missing, boolean, fractional, string, negative, zero, or other integer
version is invalid. Any identity, filename, type, version, or hash mismatch invalidates
the pair.

`TRUST-012` The algorithm identity is exactly case-sensitive `Ed25519` and the key format
is exactly a raw 32-byte public key. No alias, negotiation, fallback, multiple active
roots, certificate chain, self-signature, TOFU, remote discovery, automatic agility,
mutable-state override, or development-to-production substitution exists. A future
change requires new explicit authority.

## 4. Deterministic development test vector

`TRUST-013` Development fixtures are exactly
`tests/fixtures/windows-trust/development-pastila-root-1.pub` and
`tests/fixtures/windows-trust/development-bootstrap-root-v1.json`. The public-key fixture
is the public RFC 8032 Ed25519 verification-vector value whose exact 32 bytes in lowercase
hexadecimal notation are
`d75a980182b10ab7d54bfed3c964073a0ee172f3daa62325af021a68f707511a`; the file contains
those decoded raw bytes, not hexadecimal text. Their SHA-256 is
`21fe31dfa154a261626bf854046fd2271b7bed4b6abe45aa58877ef47f9721b9`. The bootstrap
fixture has the same six member names, JSON types, schema, version, key ID, and algorithm
as `TRUST-009`, but its `public_key_filename` is the exact sibling basename
`development-pastila-root-1.pub` and its `public_key_sha256` is that fixture-key digest.
Its exact JCS UTF-8 bytes are
`{"algorithm":"Ed25519","key_id":"pastila-root-1","public_key_filename":"development-pastila-root-1.pub","public_key_sha256":"21fe31dfa154a261626bf854046fd2271b7bed4b6abe45aa58877ef47f9721b9","schema":"pastila-scout-bootstrap-root","schema_version":1}`
and have SHA-256
`e39d301d0c3edf1ab3e93e438a2ed7b59f28eb55d81189d75e1e3453433e5ea6`. No development
private-key or provenance fixture is authorized or implied.

`TRUST-014` Development fixtures are deterministic public test authority only. They need
no generation event, verifier, witness, receipt, or ceremony. Stable mode requires the
production paths and literal `pastila-root-1.pub` binding and rejects either development
fixture path, the literal `development-pastila-root-1.pub` binding, either fixture hash,
or fixture bytes copied under a production path. Matching schema or key ID never promotes
a fixture to production authority. Fixtures never replace, seed, copy, repair, or
authorize production trust.

## 5. Immutable paths and resource behavior

`TRUST-015` Repository mode resolves production resources from the repository root and
installed mode resolves them beneath the immutable application root at
`resources/trust/`. Later consumers receive an explicit immutable root established by
their owning composition boundary. There is no CWD, home, username, registry,
environment-selected, roaming, local-state, downloaded, user-selected, or network trust
root, and no installed-to-development fallback.

`TRUST-016` The same built artifact exposes the same logical production trust pair in
development inspection and installed packaging. Bootstrap resources are bundle-controlled
inputs, not Windows settings or mutable application state. They are never regenerated,
silently repaired, or copied to mutable storage as authority.

## 6. Phase 5.5B validation and safe boundaries

`TRUST-017` Phase 5.5B materializes the four resource/vector files from `TRUST-002` and
verifies them in `tests/test_trust_bootstrap_resource_v1.py`; it adds no runtime loader,
value object, public API, or production Python module. Later consumers load only explicit
immutable paths and perform no networking, persistence, update action, download, or
arbitrary payload signature verification while loading the bootstrap pair.

`TRUST-018` Phase 5.5B verification rejects every row:

| Invalid condition | Required result |
| --- | --- |
| key or metadata resource missing, non-regular, reparse-backed, empty, or inaccessible | reject as invalid bootstrap resource |
| key length not exactly 32 raw bytes | reject as invalid key format |
| malformed UTF-8/JSON, BOM, duplicate/extra/missing member, or non-JCS bytes | reject as invalid metadata |
| wrong schema, version, key ID, algorithm, filename, or field type | reject as invalid identity |
| malformed, uppercase, or non-64-lowercase-hex SHA-256 | reject as invalid digest |
| computed public-key hash mismatch | reject as invalid binding |
| absolute, parent-relative, separator-bearing, or nonliteral key reference | reject as invalid path reference |
| production resource uses a development path/filename, equals fixture bytes, or has a key/bootstrap hash equal to the corresponding fixture hash | reject as development trust in production |
| private-material form or unauthorized resource/test path present | reject as forbidden scope |

No row falls back to another key, metadata object, mode, mutable state, or network source.

`TRUST-019` Phase 5.5B defines no runtime exception or public error API. Test-local
validation reports only the invalid category and does not emit raw resource contents,
filesystem paths, parser text, or signing-infrastructure details. Public-key bytes are
public, but diagnostics still minimize detail. Any test helper preserves
`KeyboardInterrupt`, `SystemExit`, `GeneratorExit`, and `MemoryError`.

`TRUST-020` Phase 5.5A and Phase 5.5B impose no Python runtime value-class shape. A later
runtime consumer owns value-object hardening under its own frozen specification. Phase
5.5B creates no value type, mutable global, current-root singleton, service locator,
runtime replacement, environment root, or user-selected root.

## 7. Consumer, packaging, and lifecycle boundaries

`TRUST-021` Later signed-source, updater, and packaging phases rely only on the validated
immutable root identity, public verification bytes, exact algorithm/key format, six-member
bootstrap metadata, and deterministic fail-closed validation outcome. They do not consume
operator, receipt, timestamp, witness, custody, or provenance facts. Phase 5.5A defines no
manifest signature, download, activation, replay, release-key, installer, or persistence
behavior. Packaging includes only the validated public pair, rejects missing or malformed
resources and development fixtures, and never creates or edits trust identity ad hoc.

`TRUST-022` Operational rotation and recovery remain excluded: no rollover schedule,
dual-trust selection, revocation service, transition artifact, recovery certificate, or
automatic replacement is defined. PyInstaller, Inno Setup, Authenticode, build
orchestration, signing operations, release publication, and recovery implementation
remain later owners. Nothing here makes signature verification optional.

## 8. Exact ownership, reproducibility, and historical integrity

`TRUST-023` Phase 5.5B ownership is exact and non-overlapping:

| Owner | Sole responsibility |
| --- | --- |
| `resources/trust/pastila-root-1.pub` | owner-supplied production raw Ed25519 public bytes |
| `resources/trust/bootstrap-root-v1.json` | production six-member bootstrap JCS and key binding |
| `tests/fixtures/windows-trust/development-pastila-root-1.pub` | exact public-only fixture bytes from `TRUST-013` |
| `tests/fixtures/windows-trust/development-bootstrap-root-v1.json` | exact public-only fixture bootstrap JCS from `TRUST-013` |
| `tests/test_trust_bootstrap_resource_v1.py` | every material validation and integrity obligation |

No hidden resource, production module, fixture, test, manifest, provenance object, or
private-key path is authorized.

`TRUST-024` Given identical owner-supplied production public bytes, two implementers
produce byte-identical production key and bootstrap resources; the development resources
are byte-identical constants from `TRUST-013`. Filenames, schema, version, identity,
algorithm, encoding, hash representation, member ordering, and whitespace are fixed
here. Phase 5.5B verifies the original frozen 5.5A tag/commit/SHA, the verified
Productization maintenance tag/commit, the later maintained-5.5A identity, verified 5.4D,
and the exact five-path delta from its maintained prerequisite. Historical proof uses
immutable Git objects and tags, never stale future-worktree equality.

## 9. Verification matrix

Every row is a material executable obligation of
`tests/test_trust_bootstrap_resource_v1.py`.

| Verification | Requirement | Material proof |
| --- | --- | --- |
| `TRUST-V001` | `TRUST-001` | Assert original 5.5A and Productization-maintenance identities, precedence, path, and historical SHA. |
| `TRUST-V002` | `TRUST-002` | Assert exact four resource/vector paths, one test owner, and forbidden provenance resource. |
| `TRUST-V003` | `TRUST-003` | Scan names, resources, metadata, and fixture set for every forbidden private-material form. |
| `TRUST-V004` | `TRUST-004` | Static exclusion scan for generation, signing, ceremony, runtime, packaging, and lifecycle behavior. |
| `TRUST-V005` | `TRUST-005` | Assert exact case-sensitive production key identity and non-aliasing. |
| `TRUST-V006` | `TRUST-006` | Assert exact 32 raw bytes and reject text, container, BOM, and newline variants. |
| `TRUST-V007` | `TRUST-007` | Recompute lowercase SHA-256 and reject uppercase, prefixed, malformed, and wrong-length forms. |
| `TRUST-V008` | `TRUST-008` | Assert owner-supplied public-only input, stable gating, and absence of mandatory ceremony facts. |
| `TRUST-V009` | `TRUST-009` | Parse pairs strictly and assert the exact six bootstrap members, types, values, and forbidden extras. |
| `TRUST-V010` | `TRUST-010` | Re-encode with RFC 8785 JCS and require exact byte equality. |
| `TRUST-V011` | `TRUST-011` | Tamper identity, filename, version, type, and hash independently and require pair invalidation. |
| `TRUST-V012` | `TRUST-012` | Reject algorithm/key-format aliases, fallback, TOFU, multiple roots, and mutable overrides. |
| `TRUST-V013` | `TRUST-013` | Decode the exact 32 public bytes; recompute the raw-key hash; reconstruct the exact development-filename JCS bytes/hash; and assert absence of private/provenance fixtures. |
| `TRUST-V014` | `TRUST-014` | Mutate path, filename, bytes, key hash, bootstrap hash, schema, and key ID independently; require stable rejection whenever any development identity remains. |
| `TRUST-V015` | `TRUST-015` | Verify explicit immutable path matrix and reject discovery, environment, mutable, and fallback variants. |
| `TRUST-V016` | `TRUST-016` | Assert identical bundled pair exposure and no regeneration, mutable copy, or repair authority. |
| `TRUST-V017` | `TRUST-017` | Assert exact resource/test-only delta, zero runtime API/module, and zero loader effects. |
| `TRUST-V018` | `TRUST-018` | Execute every invalid-condition row and assert finite fail-closed rejection without fallback. |
| `TRUST-V019` | `TRUST-019` | Audit test-local diagnostics and process controls for bounded safe behavior. |
| `TRUST-V020` | `TRUST-020` | Assert absence of value types, globals, locators, runtime replacement, and selected roots. |
| `TRUST-V021` | `TRUST-021` | Audit signed-source/updater/packaging inputs and reject dependence on removed governance facts. |
| `TRUST-V022` | `TRUST-022` | Static absence of lifecycle, signing, packaging implementation, and optional-verification behavior. |
| `TRUST-V023` | `TRUST-023` | Map every sole responsibility to the exact four resources plus one test and reject hidden owners. |
| `TRUST-V024` | `TRUST-024` | Two independent materializers produce identical resources and verify the complete maintained history/delta chain. |

## 10. Readiness

The maintained specification is ready only when all 24 requirements and all 24
verification rows are unique and paired; missing, orphan, duplicate, and pseudo-test
counts are zero; no private material, provenance resource, organizational ceremony fact,
or hidden owner exists; and two independent implementers converge on the exact resources
and validation behavior above.
