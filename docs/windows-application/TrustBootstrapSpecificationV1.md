# Trust Bootstrap Specification V1

## 1. Authority, scope, and readiness

`TRUST-001` This document is the Phase 5.5A authority at
`docs/windows-application/TrustBootstrapSpecificationV1.md`. Its prerequisite is
`phase-5.4d-windows-state-consumption-r1-verified`. Its freeze verdict, commit subject,
and tag are respectively
`PHASE_5_5A_TRUST_BOOTSTRAP_SPECIFICATION_V1_READY_FOR_FREEZE`,
`Specify Windows trust bootstrap V1`, and
`phase-5.5a-trust-bootstrap-spec-v1-ready`.

`TRUST-002` Phase 5.5B changes exactly these resource paths:

- `resources/trust/pastila-root-1.pub`
- `resources/trust/bootstrap-root-v1.json`
- `resources/trust/bootstrap-root-provenance-v1.json`
- `tests/fixtures/windows-trust/development-pastila-root-1.pub`
- `tests/fixtures/windows-trust/development-bootstrap-root-v1.json`

Its sole test owner is `tests/test_trust_bootstrap_resource_v1.py`. Phase 5.5B adds no
runtime API or Python production module. Private material, updater behavior, packaging,
and a stable build without a verified production public key are forbidden.

`TRUST-003` The bootstrap resources are immutable, non-secret verification authority.
They grant no signing capability. A private key, seed, signing password, HSM credential,
API secret, recovery secret, or encrypted private-key blob never enters the repository,
builder, CI, logs, application bundle, fixture set, or bootstrap metadata.

`TRUST-004` Phase 5.5A specifies only initial public trust material. It does not implement
key generation, signing, trust-metadata signing, payload verification, download,
activation, update discovery, installer verification, release publication, revocation,
rotation, recovery, restart, handoff, rollback, or UI.

## 2. Trust identity and key resource

`TRUST-005` The production bootstrap root identity is exactly `pastila-root-1`. It names
one Ed25519 public key. The identifier is case-sensitive and is never normalized,
aliased, inferred from bytes, selected from the environment, or reused for different key
bytes. Version `1` is part of the literal identifier; it defines no rotation procedure.

`TRUST-006` `resources/trust/pastila-root-1.pub` contains exactly 32 raw Ed25519 public-key
bytes. It is binary: it has no PEM wrapper, DER container, base64, UTF-8 marker, byte-order
mark, prefix, suffix, or newline. Empty, short, long, text-wrapped, or otherwise malformed
content is invalid.

`TRUST-007` The authoritative public-key fingerprint is SHA-256 over those exact 32 bytes,
represented as exactly 64 lowercase hexadecimal ASCII characters without a `sha256:`
prefix. The key filename, key identifier, algorithm, and fingerprint are distinct fields;
none substitutes for another.

`TRUST-008` The production public bytes remain a placeholder until Phase 5.5B receives an
externally generated production offline keypair and freezes only its public bytes. The
private root remains offline. Stable packaging is forbidden until the exact production
resources are verified and tagged by `phase-5.5b-trust-bootstrap-r1-verified`.

## 3. Bootstrap metadata

`TRUST-009` `resources/trust/bootstrap-root-v1.json` is UTF-8 without a byte-order mark and
is exactly one RFC 8785 JCS object with no leading or trailing whitespace and no trailing
newline. It contains exactly these keys and values:

| Key | JSON type | Exact value or constraint |
| --- | --- | --- |
| `schema` | string | `pastila-scout-bootstrap-root` |
| `schema_version` | integer | `1` |
| `key_id` | string | `pastila-root-1` |
| `algorithm` | string | `Ed25519` |
| `public_key_filename` | string | `pastila-root-1.pub` |
| `public_key_sha256` | string | SHA-256 form from `TRUST-007` |
| `provenance_filename` | string | `bootstrap-root-provenance-v1.json` |
| `provenance_sha256` | string | raw lowercase SHA-256 of the exact provenance bytes |

Duplicate, missing, or extra keys are invalid. JSON booleans and numbers of another type
never substitute for the stated types.

`TRUST-010` JCS is the byte authority for both JSON resources. A parsed object that is
semantically equivalent but whose bytes are not its RFC 8785 serialization is invalid.
The canonical bootstrap bytes therefore use JCS lexicographic member ordering and no
insignificant whitespace.

## 4. Provenance metadata

`TRUST-011` `resources/trust/bootstrap-root-provenance-v1.json` is UTF-8 without a
byte-order mark and is exactly one RFC 8785 JCS object with no leading or trailing
whitespace and no trailing newline. It contains exactly:

| Key | JSON type | Exact value or constraint |
| --- | --- | --- |
| `schema` | string | `pastila-scout-root-provenance` |
| `schema_version` | integer | `1` |
| `key_id` | string | `pastila-root-1` |
| `public_key_sha256` | string | SHA-256 form from `TRUST-007` |
| `generated_offline_at` | string | valid UTC `YYYY-MM-DDTHH:MM:SSZ` calendar value |
| `independent_verifier_ids` | array | exactly two distinct operator-ID strings |
| `verification_receipt_ids` | array | exactly two distinct external receipt-ID strings |

Duplicate, missing, or extra keys are invalid.

The provenance object is immutable non-secret evidence that two operators checked the
public identity. It is not an independent signing key, an alternate trust root, or an
authorization source when the key/bootstrap binding fails.

`TRUST-012` Each operator ID is non-empty NFC text whose UTF-8 encoding is at most 64
bytes. Each receipt ID is non-empty NFC text whose UTF-8 encoding is at most 128 bytes.
Neither permits C0/C1 controls, surrogate code points, leading or trailing whitespace,
or secret material. Array order is the externally recorded verification order and is
therefore preserved; the two entries in each array are unequal by exact string identity.

`TRUST-013` `generated_offline_at` records the externally performed public-key generation
event at whole-second UTC precision. It is the only time-bearing bootstrap field. It is
not generated at application startup or build time and is not a freshness, expiry,
rotation, or authorization decision.

## 5. Cross-resource binding and versions

`TRUST-014` The bootstrap object, provenance object, and public-key bytes form one closed
triple. Both JSON `key_id` values equal `pastila-root-1`; both
`public_key_sha256` values equal SHA-256 of the raw key bytes; the bootstrap filenames are
the literal sibling basenames; and bootstrap `provenance_sha256` equals SHA-256 of the
exact provenance JCS bytes. Any mismatch invalidates the triple.

`TRUST-015` Both schema versions are JSON integer `1`. A missing, boolean, fractional,
string, negative, zero, or other integer version is invalid. Unsupported versions fail
closed. There is no negotiation, implicit upgrade, migration, best-effort parsing, or
version fallback.

`TRUST-016` The current algorithm identity is exactly case-sensitive `Ed25519` and the key
format is exactly raw 32-byte public key. No algorithm alias, negotiation, fallback,
multiple active roots, certificate chain, self-signature, TOFU, remote discovery, or
automatic agility exists. A future phase requires a new explicit schema/identity.

## 6. Development fixtures and immutable paths

`TRUST-017` Development fixtures are exactly
`tests/fixtures/windows-trust/development-pastila-root-1.pub` and
`tests/fixtures/windows-trust/development-bootstrap-root-v1.json`. The key file follows
the exact raw-32-byte contract and is distinct from the production public key. The JSON
file is an externally supplied, non-secret, strict-JCS test vector with the exact eight
bootstrap keys and a binding to that fixture key. Its complete test-vector facts are an
input to materialization and its exact bytes are frozen by Phase 5.5B. It is not a
production bootstrap triple. Phase 5.5B creates no development provenance fixture and
the fixture JSON never authorizes or implies that hidden sixth resource.

`TRUST-018` Development fixtures are test authority only. Stable mode rejects their path
or hash. They never replace, seed, copy, or repair production resources. The fixture
bootstrap's provenance fields are test-vector data and are never validated as a
production provenance resource; only the three production resources form the closed
triple in `TRUST-014`.

`TRUST-019` Repository mode resolves production resources from the repository root and
installed mode resolves them beneath the immutable application root at
`resources/trust/`. Later consumers receive an explicit immutable root established by
their owning composition boundary. There is no CWD, home, username, registry,
environment-selected, roaming, local-state, downloaded, user-selected, or network trust
root, and no installed-to-development fallback.

`TRUST-020` The same built artifact exposes the same logical production trust triple in
development inspection and installed packaging. Bootstrap resources are bundle-controlled
inputs, not Windows settings or mutable application state. They are never regenerated,
silently repaired, or copied to mutable storage as authority.

## 7. Validation and safe boundaries

`TRUST-021` Phase 5.5B materializes bytes and verifies them in
`tests/test_trust_bootstrap_resource_v1.py`; it adds no runtime loader or value object.
Later consumers load only explicit immutable paths, return immutable validated values,
and perform no networking, persistence, update action, download, or arbitrary payload
signature verification while loading the bootstrap triple.

`TRUST-022` Phase 5.5B verification rejects every row:

| Invalid condition | Required result |
| --- | --- |
| key or metadata resource missing, non-regular, reparse-backed, empty, or inaccessible | reject as invalid bootstrap resource |
| key length not exactly 32 raw bytes | reject as invalid key format |
| malformed UTF-8/JSON, BOM, duplicate/extra/missing key, or non-JCS bytes | reject as invalid metadata |
| wrong schema, version, key ID, algorithm, filename, or field type | reject as invalid identity |
| malformed SHA-256 or either computed hash mismatch | reject as invalid binding |
| invalid timestamp, verifier IDs, receipt IDs, or distinctness | reject as invalid provenance |
| absolute, parent-relative, separator-bearing, or nonliteral resource reference | reject as invalid path reference |

No row falls back to another key, metadata object, mode, or network source.

`TRUST-023` Phase 5.5B defines no runtime exception or public error API. Its test-local
validation reports only the invalid category under test and does not emit raw file
contents, filesystem paths, parser text, operator receipt contents, or
signing-infrastructure details. Public-key bytes are public rather than secret, but test
diagnostics still minimize detail. Any test helper preserves `KeyboardInterrupt`,
`SystemExit`, `GeneratorExit`, and `MemoryError`. Later runtime consumers own their own
separately specified safe exception boundary.

`TRUST-024` Phase 5.5A and Phase 5.5B impose no Python runtime value-class shape. A later
runtime consumer owns any value-object hardening under its own frozen specification.
Phase 5.5B creates no Python value type, mutable global, current-root singleton, service
locator, runtime replacement, environment root, or user-selected root.

## 8. Consumer and lifecycle exclusions

`TRUST-025` Later signed-source and updater phases rely only on the validated immutable
root identity, public verification bytes, exact algorithm/key-format metadata, and
deterministic bootstrap validation outcome. Phase 5.5A does not define their manifests,
signatures, download, activation, replay policy, trust metadata, installer checks,
release keys, or persistence behavior.

`TRUST-026` Operational root rotation is excluded: no rollover schedule, dual trust,
old/new selection, revocation service, transition receipt, recovery certificate, or
automatic replacement is defined. The identifier and schema version preserve only a
future explicit evolution seam.

`TRUST-027` PyInstaller, Inno Setup, Authenticode, installer scripts, build orchestration,
resource collection, and release publication remain later owners. Packaging consumes the
verified resources and never creates or edits trust identity ad hoc.

## 9. Phase 5.5B ownership and reproducibility

`TRUST-028` Phase 5.5B ownership is exact and non-overlapping:

| Owner | Sole responsibility |
| --- | --- |
| `resources/trust/pastila-root-1.pub` | production raw Ed25519 public bytes |
| `resources/trust/bootstrap-root-v1.json` | production bootstrap JCS and binding |
| `resources/trust/bootstrap-root-provenance-v1.json` | production offline provenance JCS |
| `tests/fixtures/windows-trust/development-pastila-root-1.pub` | non-production raw fixture key |
| `tests/fixtures/windows-trust/development-bootstrap-root-v1.json` | non-production fixture bootstrap JCS |
| `tests/test_trust_bootstrap_resource_v1.py` | every material validation and integrity obligation |

No hidden resource, production module, fixture, test, manifest, or private-key path is
authorized.

`TRUST-029` Given the same externally supplied production public key, provenance facts,
and complete non-secret development test-vector facts, two
implementers produce byte-identical raw key, bootstrap JCS, and provenance JCS resources.
The production variable facts are the 32 public bytes, offline UTC event time, two
operator IDs, and two receipt IDs. Filenames, production schemas, versions, identity,
algorithm, encoding, hashes, member ordering, and whitespace are fixed here. Phase 5.5B
records the exact fixture-vector bytes and hashes so neither platform serialization nor
locally generated randomness can change them.

`TRUST-030` Phase 5.5B verifies prerequisite tag
`phase-5.5a-trust-bootstrap-spec-v1-ready`, its frozen specification bytes, the verified
5.4D tag/commit, and the exact six-resource/test-path delta from that prerequisite.
Historical proof uses immutable Git objects and tags, never future-worktree equality.

## 10. Verification matrix

Every row is a material executable obligation of
`tests/test_trust_bootstrap_resource_v1.py`.

| Verification | Requirement | Material proof |
| --- | --- | --- |
| `TRUST-V001` | `TRUST-001` | Assert prerequisite, path, verdict, subject, and tag literals. |
| `TRUST-V002` | `TRUST-002` | Assert exact five resources plus one test and no hidden owner. |
| `TRUST-V003` | `TRUST-003` | Scan resource names/bytes/JSON for forbidden private-material forms. |
| `TRUST-V004` | `TRUST-004` | Static exclusion scan for execution, networking, packaging, and rotation behavior. |
| `TRUST-V005` | `TRUST-005` | Assert exact case-sensitive production key identity. |
| `TRUST-V006` | `TRUST-006` | Assert exact 32 raw bytes and reject text/container/newline variants. |
| `TRUST-V007` | `TRUST-007` | Recompute raw lowercase SHA-256 and reject representation variants. |
| `TRUST-V008` | `TRUST-008` | Assert stable gating and absence of production private bytes. |
| `TRUST-V009` | `TRUST-009` | Parse pairs strictly; assert exact bootstrap keys, types, values, and bytes. |
| `TRUST-V010` | `TRUST-010` | Re-encode with RFC 8785 JCS and require byte equality. |
| `TRUST-V011` | `TRUST-011` | Assert exact provenance keys, types, values, UTF-8, and JCS bytes. |
| `TRUST-V012` | `TRUST-012` | Exercise ID size, NFC, control, whitespace, order, and distinctness boundaries. |
| `TRUST-V013` | `TRUST-013` | Validate exact UTC grammar/calendar and reject runtime-generated semantics. |
| `TRUST-V014` | `TRUST-014` | Swap/tamper each resource and require cross-binding rejection. |
| `TRUST-V015` | `TRUST-015` | Reject every wrong JSON type/value and unsupported version. |
| `TRUST-V016` | `TRUST-016` | Reject algorithm/key-format aliases, fallback, and multiple-root variants. |
| `TRUST-V017` | `TRUST-017` | Validate exact two fixture paths, distinct raw fixture key, strict-JCS vector, and absence of a sixth resource. |
| `TRUST-V018` | `TRUST-018` | Assert fixture hash/path rejection and that fixture provenance data cannot validate as production evidence. |
| `TRUST-V019` | `TRUST-019` | Verify explicit immutable path matrix and reject discovery/override variants. |
| `TRUST-V020` | `TRUST-020` | Assert no mutable-state copy, regeneration, or repair authority. |
| `TRUST-V021` | `TRUST-021` | Assert Phase 5.5B has zero runtime module/API and zero effects. |
| `TRUST-V022` | `TRUST-022` | Execute every invalid-condition row and assert finite failure without fallback. |
| `TRUST-V023` | `TRUST-023` | Audit test-local diagnostics/process controls and absence of a runtime exception API. |
| `TRUST-V024` | `TRUST-024` | Assert 5.5B adds no value type, global, locator, or runtime replacement. |
| `TRUST-V025` | `TRUST-025` | Static boundary audit against signed-bundle/updater behavior. |
| `TRUST-V026` | `TRUST-026` | Static absence of rotation/revocation/recovery mechanisms. |
| `TRUST-V027` | `TRUST-027` | Static absence of packaging/build/release mechanics. |
| `TRUST-V028` | `TRUST-028` | Map each responsibility to the exact literal path set. |
| `TRUST-V029` | `TRUST-029` | Independent materializers produce byte-identical resources from identical facts. |
| `TRUST-V030` | `TRUST-030` | Verify immutable prerequisite chain and exact 5.5B Git delta. |

## 11. Readiness

The specification is ready only when all 30 requirements and all 30 verification rows
are unique and paired; missing, orphan, duplicate, and pseudo-test counts are zero; no
private material or hidden owner exists; and two independent implementers converge on
the exact resources and validation behavior above.
