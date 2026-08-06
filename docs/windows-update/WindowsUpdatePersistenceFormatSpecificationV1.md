# Windows Update Persistence Format Specification V1

## 1. Scope

| Requirement | Owned rule |
| --- | --- |
| `SCP-001` | This document exclusively owns persisted artifact schemas, scalar and reusable persistence types, JSON representation, canonical serialization, logical artifact identifiers, storage contracts, artifact ownership, atomic publication, lower store failures, the wire encoding of Protocol-owned `PersistenceFormatErrorCodeV1` members, persistence requirement identifiers, and persistence verification. |
| `SCP-002` | This document owns no state transition, restart decision, synchronization, process handoff, runtime timeout, health lifecycle, presentation, product architecture, cryptographic policy, content distribution, business-data storage, or deployment behavior. |
| `SCP-003` | A consumer may select when to read or write an artifact, but every accepted or emitted byte representation must satisfy this document without alteration. |
| `SCP-004` | `ProtocolDiagnosticsV1` is runtime-only authority imported from frozen Windows Update Protocol V6; it is excluded from this wire contract, never serialized or validated as a persisted artifact, and never participates in reconstruction or compatibility. |
| `SCP-005` | Frozen Windows Update Protocol V6 exclusively owns protocol applicability, success and failure semantic projection, public-error precedence, final authority, retryability, cleanup, diagnostics, and runtime-result validity through `ProtocolApplicabilityMatrixV1`, `COMP`, `RED`, `SAP`, `SEM`, and `PersistenceProtocolResultV1`; this document only supplies and validates the lower persistence facts consumed by those authorities. |

## 2. Terminology

| Requirement | Term | Exact meaning |
| --- | --- | --- |
| `TRM-001` | artifact | one named persisted JSON record or opaque retained-installer byte object |
| `TRM-002` | artifact identifier | protocol-stable `PersistentArtifactKindV1` member resolved by composition to one opaque `ArtifactKeyV1` |
| `TRM-003` | authoritative | the single destination object accepted after complete reconstruction |
| `TRM-004` | audit-only | evidence that never reconstructs another artifact or grants mutation authority |
| `TRM-005` | `PersistentStore` | injected owner of opaque-key read, exclusive temporary creation, complete write, durable flush, atomic create, atomic replace, quarantine, and identity-checked deletion |
| `TRM-006` | persistence writer | injected persistence component that constructs, validates, serializes, publishes, and reconstructs persisted artifacts; protocol cleanup decisions remain owned by frozen Protocol V6 |
| `TRM-007` | persistence reader | read-only consumer of an immutable artifact reconstructed by the persistence writer; it owns no Protocol runtime decision |
| `TRM-008` | reconstruction | strict byte decoding, schema validation, invariant validation, and immutable object construction without repair or normalization |

## 3. Scalar types

| Requirement | Type | Representation | Encoding | Bounds | Grammar |
| --- | --- | --- | --- | --- | --- |
| `SCL-001` | `SchemaIdentifier` | JSON string | ASCII subset of UTF-8 | 20, 21, or 25 bytes | one schema literal defined in Section 7 |
| `SCL-002` | `SchemaVersion` | JSON integer | JCS decimal integer | exactly `1` | boolean forbidden |
| `SCL-003` | `ProtocolVersion` | JSON integer | JCS decimal integer | exactly `1` | boolean forbidden |
| `SCL-004` | `OperationId` | JSON string | lowercase ASCII | exactly 32 bytes | `[0-9a-f]{32}` generated from 16 CSPRNG bytes |
| `SCL-005` | `ArtifactKeyV1` | abstract store key, never serialized inside a record | NFC UTF-8 | 1..1024 encoded bytes | nonempty; no NUL, C0/C1 controls, or unpaired surrogates; exact code-point equality; `/`, `\`, and `..` have no special meaning and are permitted |
| `SCL-006` | `ManifestSequence` | JSON integer | JCS decimal integer | `1..9223372036854775807` | boolean forbidden |
| `SCL-007` | `SHA256` | JSON string | lowercase ASCII | exactly 64 bytes | `[0-9a-f]{64}` |
| `SCL-008` | `RFC3339Timestamp` | JSON string | ASCII subset of UTF-8 | exactly 20 bytes | valid UTC calendar value `YYYY-MM-DDTHH:MM:SSZ`; whole-second precision |
| `SCL-009` | `MonotonicDuration` | non-persisted unsigned integer | implementation integer nanoseconds | `0..18446744073709551615` | never serialized |
| `SCL-010` | `FileSize` | JSON integer | JCS decimal integer | `1..536870912` | boolean forbidden |
| `SCL-011` | `Pid` | JSON integer | JCS decimal integer | `1..4294967295` | boolean forbidden |
| `SCL-012` | `FileTime` | JSON integer | JCS decimal integer | `0..18446744073709551615` | boolean forbidden |
| `SCL-013` | `PathKey` | JSON string | NFC UTF-8 | 1..1024 encoded bytes | opaque nonempty artifact key; no NUL, C0/C1 controls, or unpaired surrogates; `/`, `\`, and `..` are permitted; no filesystem interpretation |
| `SCL-014` | `StableVersionV1` | JSON string | ASCII | 1..128 encoded bytes | nonempty ASCII string; exact equality; no parsing or normalization; `v1.2.3`, `1.2.3-alpha`, `1.2.3+build`, and `release-2026.08` are permitted |
| `SCL-015` | `PrintableIdentity` | JSON string | NFC UTF-8 | 1..256 bytes | printable characters only; no C0/C1 controls |
| `SCL-016` | `StorageIdentity` | JSON string | ASCII subset of UTF-8 | 1..256 bytes | opaque nonempty identity; exact equality only |
| `SCL-017` | `StrictBoolean` | JSON boolean | JCS literal | one boolean | exactly `true` or `false` |
| `SCL-018` | `ProtocolErrorCode` | JSON string | uppercase ASCII plus underscore | 1..64 bytes | exactly one serialized value in Section 11 |

## 4. Reusable types

| Requirement | Closed-vocabulary rule |
| --- | --- |
| `CLS-001` | The `PAK`, `PSO`, `PSS`, `PSA`, and `PFC` tables are the only five closed persistence vocabularies; a symbolic name serializes to its listed value, while aliases, unknown members, custom members, subclass extensions, and caller-selected extensions are rejected. |

| Requirement | `PersistentArtifactKindV1` member | Serialized value | Exact meaning | Permitted use |
| --- | --- | --- | --- | --- |
| `PAK-001` | `UPDATE_STATE` | `UPDATE_STATE` | canonical update-state JSON artifact | key derivation, schema selection, Protocol condition input |
| `PAK-002` | `HANDOFF_RECEIPT` | `HANDOFF_RECEIPT` | canonical installer-handoff JSON artifact | key derivation, schema selection, Protocol condition input |
| `PAK-003` | `HEALTH_RECEIPT` | `HEALTH_RECEIPT` | canonical health JSON artifact | key derivation, schema selection, Protocol condition input |
| `PAK-004` | `RETAINED_INSTALLER_BYTES` | `RETAINED_INSTALLER_BYTES` | opaque verified installer bytes | key derivation, identity validation, Protocol condition input |
| `PAK-005` | closure | n/a | exactly the four preceding members exist | no aliases, extension point, unknown member, or custom member |

| Requirement | `PersistentStoreOperationV1` member | Serialized value | Exact meaning | Permitted use |
| --- | --- | --- | --- | --- |
| `PSO-001` | `READ` | `READ` | retrieve complete bytes | `read` only |
| `PSO-002` | `EXISTS` | `EXISTS` | test key presence without retrieving bytes | `exists` only |
| `PSO-003` | `CREATE` | `CREATE` | atomically create absent destination | `create` only |
| `PSO-004` | `REPLACE` | `REPLACE` | atomically replace present destination | `replace` only |
| `PSO-005` | `DELETE` | `DELETE` | identity-checked deletion | `delete` only |
| `PSO-006` | `QUARANTINE` | `QUARANTINE` | move source authority to quarantine key | `quarantine` only |
| `PSO-007` | closure | n/a | exactly the six preceding members exist | no aliases, extension point, unknown member, or custom member |

| Requirement | Lower store operation | Structurally valid lower statuses |
| --- | --- | --- |
| `OLS-001` | `READ` | `COMPLETED`, `NOT_FOUND`, `FAILED` |
| `OLS-002` | `EXISTS` | `COMPLETED`, `FAILED` |
| `OLS-003` | `CREATE` | `COMPLETED`, `FAILED` |
| `OLS-004` | `REPLACE` | `COMPLETED`, `FAILED` |
| `OLS-005` | `DELETE` | `COMPLETED`, `NOT_FOUND`, `FAILED` |
| `OLS-006` | `QUARANTINE` | `COMPLETED`, `NOT_FOUND`, `FAILED` |
| `OLS-007` | closure | a status absent from the six preceding rows is rejected before lower store-result construction; these structural shapes do not grant Protocol legality, which belongs only to APP |

| Requirement | `PersistentStoreStatusV1` member | Serialized value | Exact meaning | Permitted use |
| --- | --- | --- | --- | --- |
| `PSS-001` | `COMPLETED` | `COMPLETED` | requested operation completed | operation-specific success row |
| `PSS-002` | `NOT_FOUND` | `NOT_FOUND` | authoritative key was absent | read, delete, or quarantine result; never an exists result |
| `PSS-003` | `FAILED` | `FAILED` | one finite store failure occurred | result carrying exactly one failure code |
| `PSS-004` | closure | n/a | exactly the three preceding members exist | no aliases, extension point, unknown member, or custom member |

| Requirement | `PersistentStoreAuthorityV1` member | Serialized value | Exact meaning | Permitted use |
| --- | --- | --- | --- | --- |
| `PSA-001` | `NONE` | `NONE` | no authoritative destination exists | operation-specific result matrix |
| `PSA-002` | `PRIOR` | `PRIOR` | pre-operation destination remains authoritative | operation-specific result matrix |
| `PSA-003` | `NEW` | `NEW` | newly published destination is authoritative | operation-specific result matrix |
| `PSA-004` | closure | n/a | exactly the three preceding members exist | no aliases, extension point, unknown member, or custom member |

| Requirement | `ArtifactKeyV1` rule | Exact contract | Permitted use |
| --- | --- | --- | --- |
| `AKY-001` | representation | immutable NFC Unicode string whose UTF-8 encoding is 1..1024 bytes and contains no NUL, C0/C1 control, or unpaired surrogate | store operation parameter and key-derivation result only |
| `AKY-002` | equality | exact normalized code-point equality; equal logical inputs derive byte-identical keys | comparison and lookup |
| `AKY-003` | opacity | `/`, `\`, and `..` are ordinary permitted characters; the key has no filesystem semantics | injected store resolves the key internally |
| `AKY-004` | collision rule | two distinct artifact identities or retained-installer operation IDs must not derive the same key | composition rejects a collision before a store call |
| `AKY-005` | wire separation | never substitutes for `PathKey` and owns no persisted field | no JSON serialization |

| Requirement | Type | Representation | Exact members/invariant |
| --- | --- | --- | --- |
| `TYP-001` | `Nullable<T>` | JSON `null` or `T` | accepts only null or a fully valid `T` |
| `TYP-002` | `UpdateState` | JSON string | `IDLE`, `CHECKING_STARTUP`, `CHECKING_MANUAL`, `UPDATE_AVAILABLE`, `DOWNLOADING`, `DOWNLOAD_CANCELLED`, `VERIFIED`, `INSTALL_PENDING`, `FAILED` |
| `TYP-003` | `HandoffOutcome` | JSON string | `PREPARED`, `LAUNCHED`, `CANCELLED`, `LAUNCH_FAILED` |
| `TYP-004` | `HealthStage` | JSON string | `STARTED`, `VERSION_VALIDATED`, `RESOURCES_VALIDATED`, `PATHS_VALIDATED`, `DATA_VALIDATED`, `INSTANCE_INITIALIZED`, `COMPLETE` |
| `TYP-005` | `HealthOutcome` | JSON string | `PENDING`, `HEALTHY`, `UNHEALTHY`, `ABANDONED` |
| `TYP-006` | `HandoffFailureCode` | `ProtocolErrorCode` subset | `HANDOFF_PROCESS_IDENTITY_UNAVAILABLE`, `INSTALLER_PROCESS_START_FAILED` |
| `TYP-007` | `HealthFailureCode` | `ProtocolErrorCode` subset | `HEALTH_VALIDATION_FAILED`, `HEALTH_VALIDATION_TIMEOUT`, `HEALTH_VALIDATION_INTERRUPTED` |
| `TYP-008` | `RetainedFailureCode` | `ProtocolErrorCode` subset | `UPDATE_STATE_PERSISTENCE_FAILED`, `HANDOFF_RECEIPT_MISSING`, `HANDOFF_RECEIPT_PERSISTENCE_FAILED`, `HANDOFF_PROCESS_IDENTITY_UNAVAILABLE`, `INSTALLER_PROCESS_START_FAILED`, `INSTALLER_RECEIPT_TIMEOUT`, `INSTALLER_MUTEX_TIMEOUT` |
| `TYP-009` | `PersistentStoreStatusV1` | closed enum | exactly the members in `PSS-001..003`; `PSS-004` is the closure rule and is not a member |
| `TYP-010` | `PersistentStoreAuthorityV1` | closed enum | exactly the members in `PSA-001..003`; `PSA-004` is the closure rule and is not a member |
| `TYP-011` | reserved | n/a | no type authority; identifier retained and permanently unavailable |
| `TYP-012` | `CanonicalBytesV1` | immutable bytes | complete nonempty canonical bytes accepted by Section 8; retained installer bytes use immutable bytes without JSON canonicalization |
| `TYP-013` | reserved | n/a | no type authority; identifier retained and permanently unavailable |
| `TYP-014` | store result records | immutable structural records | exact field and validity tables in Section 9 |

## 5. Artifact identifiers

| Requirement | Kind | Serialized identifier | Schema | Key derivation | Lifetime | Authority | Classification | Reconstruction |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ART-001` | `UPDATE_STATE` | `UPDATE_STATE` | `windows-update-state`, version 1 | `KEY-001` | until explicit protocol-data removal | persistence writer acting only when requested by frozen Protocol V6 | authoritative | destination object only |
| `ART-002` | `HANDOFF_RECEIPT` | `HANDOFF_RECEIPT` | `windows-installer-handoff`, version 1 | `KEY-002` | through terminal reconciliation | persistence writer acting only when requested by frozen Protocol V6 | authoritative | destination object only |
| `ART-003` | `HEALTH_RECEIPT` | `HEALTH_RECEIPT` | `windows-update-health`, version 1 | `KEY-003` | through terminal reconciliation | persistence writer acting only when requested by frozen Protocol V6 | authoritative | destination object only |
| `ART-004` | `RETAINED_INSTALLER_BYTES` | `RETAINED_INSTALLER_BYTES` | immutable opaque bytes identified by retained record | `KEY-004` | while referenced or retained by an allowed failure | persistence writer acting only when requested by frozen Protocol V6 | non-authoritative without retained record | never by key enumeration |

| Requirement | Function | Parameters | Return | Invalid combinations | Finite error |
| --- | --- | --- | --- | --- | --- |
| `KEY-001` | `derive_key` | `UPDATE_STATE`, operation ID null | `ArtifactKeyV1("windows-update-state-v1")` | non-null operation ID | `INVALID_KEY` |
| `KEY-002` | `derive_key` | `HANDOFF_RECEIPT`, operation ID null | `ArtifactKeyV1("windows-installer-handoff-v1")` | non-null operation ID | `INVALID_KEY` |
| `KEY-003` | `derive_key` | `HEALTH_RECEIPT`, operation ID null | `ArtifactKeyV1("windows-update-health-v1")` | non-null operation ID | `INVALID_KEY` |
| `KEY-004` | `derive_key` | `RETAINED_INSTALLER_BYTES`, non-null `OperationId` | `ArtifactKeyV1("windows-retained-installer-" + operation_id)` | null or invalid operation ID | `INVALID_KEY` |

## 6. Artifact ownership

| Requirement | Artifact | Writer | Readers | Mutation owner | Cleanup owner | Reconstruction owner |
| --- | --- | --- | --- | --- | --- | --- |
| `OWN-001` | `UPDATE_STATE` | persistence writer | persistence reader | persistence writer | frozen Protocol V6; store owns only private temporaries | persistence writer |
| `OWN-002` | retained installer record nested in `UPDATE_STATE` | persistence writer | persistence reader | persistence writer | frozen Protocol V6; store owns only private temporaries | persistence writer with update state only |
| `OWN-003` | `RETAINED_INSTALLER_BYTES` | persistence writer admits one immutable identity | persistence reader | none after admission | frozen Protocol V6 requests any identity-checked deletion; store performs one request | none; identity comes only from retained record |
| `OWN-004` | `HANDOFF_RECEIPT` | persistence writer | persistence reader | persistence writer | frozen Protocol V6; store owns only private temporaries | persistence writer |
| `OWN-005` | `HEALTH_RECEIPT` | persistence writer | persistence reader | persistence writer | frozen Protocol V6; store owns only private temporaries | persistence writer |

## 7. Persistent schemas

| Requirement | Schema | Field | Reusable type | JSON type | Nullable | Bounds | Grammar | Normalization | Cross-field invariant |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `SCH-UF-001` | `UpdateStateFileV1` | `schema` | `SchemaIdentifier` literal `windows-update-state` | string | never | 20, 21, or 25 ASCII bytes | one exact schema literal | none (ASCII is NFC) | exact literal |
| `SCH-UF-002` | `UpdateStateFileV1` | `schema_version` | `SchemaVersion` | integer | never | exactly 1 | decimal integer; boolean forbidden | none | exact integer `1` |
| `SCH-UF-003` | `UpdateStateFileV1` | `update_state` | `UpdateStateV1` object | object | never | exact declared field set | strict object | nested strings NFC | every nested field valid |
| `SCH-US-001` | `UpdateStateV1` | `state` | `UpdateState` | string | never | closed vocabulary | exact uppercase member | none (ASCII is NFC) | one closed member |
| `SCH-US-002` | `UpdateStateV1` | `current_version` | `StableVersionV1` | string | never | 1..128 ASCII bytes | nonempty ASCII string; no parsing or normalization | none (ASCII is NFC) | exact serialized value |
| `SCH-US-003` | `UpdateStateV1` | `latest_version` | `Nullable<StableVersionV1>` | string | allowed | null or 1..128 ASCII bytes | null or nonempty ASCII string; no parsing or normalization | none (ASCII is NFC) | non-null only with accepted candidate evidence or retained installer |
| `SCH-US-004` | `UpdateStateV1` | `active_operation_id` | `Nullable<OperationId>` | string | allowed | null or 32 ASCII bytes | null or [0-9a-f]{32} | none (ASCII is NFC) | non-null exactly in checking, downloading, or `INSTALL_PENDING` |
| `SCH-US-005` | `UpdateStateV1` | `active_manifest_sequence` | `Nullable<ManifestSequence>` | integer | allowed | null or 1..9223372036854775807 | null or decimal integer; boolean forbidden | none | null exactly when manifest hash is null |
| `SCH-US-006` | `UpdateStateV1` | `active_manifest_sha256` | `Nullable<SHA256>` | string | allowed | null or 64 ASCII bytes | null or [0-9a-f]{64} | none (ASCII is NFC) | null exactly when manifest sequence is null |
| `SCH-US-007` | `UpdateStateV1` | `failure_code` | `Nullable<ProtocolErrorCode>` | string | allowed | null or 1..64 ASCII bytes | null or one exact Section 11 value | none (ASCII is NFC) | non-null exactly in `FAILED` |
| `SCH-US-008` | `UpdateStateV1` | `notification_shown` | `StrictBoolean` | boolean | never | one boolean | true or false only | none | exact boolean |
| `SCH-US-009` | `UpdateStateV1` | `retained_installer` | `Nullable<RetainedVerifiedInstallerV1>` | object | allowed | null or exact declared field set | null or strict object | nested strings NFC | non-null only in `VERIFIED`, retained `CHECKING_MANUAL`, `INSTALL_PENDING`, or `FAILED` with `RetainedFailureCode` |
| `SCH-RI-001` | `RetainedVerifiedInstallerV1` | `version` | `StableVersionV1` | string | never | 1..128 ASCII bytes | nonempty ASCII string; no parsing or normalization | none (ASCII is NFC) | exact candidate version |
| `SCH-RI-002` | `RetainedVerifiedInstallerV1` | `manifest_sequence` | `ManifestSequence` | integer | never | 1..9223372036854775807 | decimal integer; boolean forbidden | none | exact accepted sequence |
| `SCH-RI-003` | `RetainedVerifiedInstallerV1` | `manifest_sha256` | `SHA256` | string | never | 64 ASCII bytes | [0-9a-f]{64} | none (ASCII is NFC) | exact accepted manifest hash |
| `SCH-RI-004` | `RetainedVerifiedInstallerV1` | `installer_key` | `PathKey` | string | never | 1..1024 UTF-8 bytes | NFC opaque nonempty key; no controls; /, \\ and .. permitted | input must already be NFC | resolves only through `PersistentStore` |
| `SCH-RI-005` | `RetainedVerifiedInstallerV1` | `installer_size` | `FileSize` | integer | never | 1..536870912 | decimal integer; boolean forbidden | none | equals retained byte length |
| `SCH-RI-006` | `RetainedVerifiedInstallerV1` | `installer_sha256` | `SHA256` | string | never | 64 ASCII bytes | [0-9a-f]{64} | none (ASCII is NFC) | equals retained byte hash |
| `SCH-RI-007` | `RetainedVerifiedInstallerV1` | `verified_at` | `RFC3339Timestamp` | string | never | 20 ASCII bytes | YYYY-MM-DDTHH:MM:SSZ valid UTC calendar value | none (ASCII is NFC) | audit-only timestamp |
| `SCH-RI-008` | `RetainedVerifiedInstallerV1` | `publisher_subject` | `PrintableIdentity` | string | never | 1..256 UTF-8 bytes | printable NFC; no controls | input must already be NFC | exact external verification projection |
| `SCH-RI-009` | `RetainedVerifiedInstallerV1` | `leaf_certificate_sha256` | `SHA256` | string | never | 64 ASCII bytes | [0-9a-f]{64} | none (ASCII is NFC) | exact external verification projection |
| `SCH-RI-010` | `RetainedVerifiedInstallerV1` | `signature_timestamp` | `RFC3339Timestamp` | string | never | 20 ASCII bytes | YYYY-MM-DDTHH:MM:SSZ valid UTC calendar value | none (ASCII is NFC) | audit-only timestamp |
| `SCH-RI-011` | `RetainedVerifiedInstallerV1` | `storage_identity` | `StorageIdentity` | string | never | 1..256 ASCII bytes | opaque nonempty identity | none (ASCII is NFC) | must match before read or cleanup |
| `SCH-HR-001` | `InstallerHandoffReceiptV1` | `schema` | `SchemaIdentifier` literal `windows-installer-handoff` | string | never | 20, 21, or 25 ASCII bytes | one exact schema literal | none (ASCII is NFC) | exact literal |
| `SCH-HR-002` | `InstallerHandoffReceiptV1` | `schema_version` | `SchemaVersion` | integer | never | exactly 1 | decimal integer; boolean forbidden | none | exact integer `1` |
| `SCH-HR-003` | `InstallerHandoffReceiptV1` | `operation_id` | `OperationId` | string | never | 32 ASCII bytes | [0-9a-f]{32} | none (ASCII is NFC) | exact operation lineage |
| `SCH-HR-004` | `InstallerHandoffReceiptV1` | `target_version` | `StableVersionV1` | string | never | 1..128 ASCII bytes | nonempty ASCII string; no parsing or normalization | none (ASCII is NFC) | equals retained version |
| `SCH-HR-005` | `InstallerHandoffReceiptV1` | `manifest_sequence` | `ManifestSequence` | integer | never | 1..9223372036854775807 | decimal integer; boolean forbidden | none | equals retained sequence |
| `SCH-HR-006` | `InstallerHandoffReceiptV1` | `manifest_sha256` | `SHA256` | string | never | 64 ASCII bytes | [0-9a-f]{64} | none (ASCII is NFC) | equals retained manifest hash |
| `SCH-HR-007` | `InstallerHandoffReceiptV1` | `installer_key` | `PathKey` | string | never | 1..1024 UTF-8 bytes | NFC opaque nonempty key; no controls; /, \\ and .. permitted | input must already be NFC | equals retained key |
| `SCH-HR-008` | `InstallerHandoffReceiptV1` | `installer_size` | `FileSize` | integer | never | 1..536870912 | decimal integer; boolean forbidden | none | equals retained size |
| `SCH-HR-009` | `InstallerHandoffReceiptV1` | `installer_sha256` | `SHA256` | string | never | 64 ASCII bytes | [0-9a-f]{64} | none (ASCII is NFC) | equals retained hash |
| `SCH-HR-010` | `InstallerHandoffReceiptV1` | `publisher_subject` | `PrintableIdentity` | string | never | 1..256 UTF-8 bytes | printable NFC; no controls | input must already be NFC | equals retained publisher identity |
| `SCH-HR-011` | `InstallerHandoffReceiptV1` | `consented_at` | `RFC3339Timestamp` | string | never | 20 ASCII bytes | YYYY-MM-DDTHH:MM:SSZ valid UTC calendar value | none (ASCII is NFC) | audit-only timestamp |
| `SCH-HR-012` | `InstallerHandoffReceiptV1` | `launch_attempted_at` | `Nullable<RFC3339Timestamp>` | string | allowed | null or 20 ASCII bytes | null or YYYY-MM-DDTHH:MM:SSZ valid UTC calendar value | none (ASCII is NFC) | non-null exactly for `LAUNCHED` or `LAUNCH_FAILED` |
| `SCH-HR-013` | `InstallerHandoffReceiptV1` | `process_id` | `Nullable<Pid>` | integer | allowed | null or 1..4294967295 | null or decimal integer; boolean forbidden | none | non-null exactly for `LAUNCHED` |
| `SCH-HR-014` | `InstallerHandoffReceiptV1` | `process_creation_time` | `Nullable<FileTime>` | integer | allowed | null or 0..18446744073709551615 | null or decimal integer; boolean forbidden | none | non-null exactly for `LAUNCHED` |
| `SCH-HR-015` | `InstallerHandoffReceiptV1` | `outcome` | `HandoffOutcome` | string | never | closed vocabulary | PREPARED, LAUNCHED, CANCELLED, or LAUNCH_FAILED | none (ASCII is NFC) | one closed member |
| `SCH-HR-016` | `InstallerHandoffReceiptV1` | `failure_code` | `Nullable<HandoffFailureCode>` | string | allowed | null or closed two-member vocabulary | null or HANDOFF_PROCESS_IDENTITY_UNAVAILABLE or INSTALLER_PROCESS_START_FAILED | none (ASCII is NFC) | non-null exactly for `LAUNCH_FAILED` |
| `SCH-HL-001` | `HealthReceiptV1` | `schema` | `SchemaIdentifier` literal `windows-update-health` | string | never | 20, 21, or 25 ASCII bytes | one exact schema literal | none (ASCII is NFC) | exact literal |
| `SCH-HL-002` | `HealthReceiptV1` | `schema_version` | `SchemaVersion` | integer | never | exactly 1 | decimal integer; boolean forbidden | none | exact integer `1` |
| `SCH-HL-003` | `HealthReceiptV1` | `operation_id` | `OperationId` | string | never | 32 ASCII bytes | [0-9a-f]{32} | none (ASCII is NFC) | exact handoff lineage |
| `SCH-HL-004` | `HealthReceiptV1` | `installed_version` | `StableVersionV1` | string | never | 1..128 ASCII bytes | nonempty ASCII string; no parsing or normalization | none (ASCII is NFC) | observed installed version |
| `SCH-HL-005` | `HealthReceiptV1` | `expected_version` | `StableVersionV1` | string | never | 1..128 ASCII bytes | nonempty ASCII string; no parsing or normalization | none (ASCII is NFC) | equals handoff target version |
| `SCH-HL-006` | `HealthReceiptV1` | `manifest_sequence` | `ManifestSequence` | integer | never | 1..9223372036854775807 | decimal integer; boolean forbidden | none | equals handoff sequence |
| `SCH-HL-007` | `HealthReceiptV1` | `installer_sha256` | `SHA256` | string | never | 64 ASCII bytes | [0-9a-f]{64} | none (ASCII is NFC) | equals handoff installer hash |
| `SCH-HL-008` | `HealthReceiptV1` | `stage` | `HealthStage` | string | never | closed vocabulary | STARTED, VERSION_VALIDATED, RESOURCES_VALIDATED, PATHS_VALIDATED, DATA_VALIDATED, INSTANCE_INITIALIZED, or COMPLETE | none (ASCII is NFC) | one closed member |
| `SCH-HL-009` | `HealthReceiptV1` | `outcome` | `HealthOutcome` | string | never | closed vocabulary | PENDING, HEALTHY, UNHEALTHY, or ABANDONED | none (ASCII is NFC) | `HEALTHY` requires `COMPLETE`; `UNHEALTHY` and `ABANDONED` forbid `COMPLETE` |
| `SCH-HL-010` | `HealthReceiptV1` | `started_at` | `RFC3339Timestamp` | string | never | 20 ASCII bytes | YYYY-MM-DDTHH:MM:SSZ valid UTC calendar value | none (ASCII is NFC) | audit-only timestamp |
| `SCH-HL-011` | `HealthReceiptV1` | `deadline_at` | `RFC3339Timestamp` | string | never | 20 ASCII bytes | YYYY-MM-DDTHH:MM:SSZ valid UTC calendar value | none (ASCII is NFC) | audit projection exactly 30 seconds after `started_at` |
| `SCH-HL-012` | `HealthReceiptV1` | `completed_at` | `Nullable<RFC3339Timestamp>` | string | allowed | null or 20 ASCII bytes | null or YYYY-MM-DDTHH:MM:SSZ valid UTC calendar value | none (ASCII is NFC) | null exactly for `PENDING` |
| `SCH-HL-013` | `HealthReceiptV1` | `failure_code` | `Nullable<HealthFailureCode>` | string | allowed | null or closed three-member vocabulary | null or HEALTH_VALIDATION_FAILED, HEALTH_VALIDATION_TIMEOUT, or HEALTH_VALIDATION_INTERRUPTED | none (ASCII is NFC) | null for `PENDING`/`HEALTHY`; `UNHEALTHY` uses failed; `ABANDONED` uses timeout or interrupted |
| `SCH-HL-014` | `HealthReceiptV1` | `recovery_offered` | `StrictBoolean` | boolean | never | one boolean | true or false only | none | false for `PENDING`/`HEALTHY`; true only after recovery acknowledgement |

## 8. Canonical serialization

| Requirement | Failure stage | Exact wire-format rule | Frozen Protocol handling |
| --- | --- | --- | --- |
| `SER-001` | invalid input model | authoritative reconstruction of the exact schema is required before encoding; copied-invalid/partial objects rejected | submit `SAP-003`, `SAP-004`, or `SAP-005` solely by update-state, handoff, or health artifact identity; Protocol consumes the same-numbered SEM row |
| `SER-002` | unsupported scalar | reject any scalar type not declared in Sections 3 and 4 | submit `SAP-003`, `SAP-004`, or `SAP-005` solely by update-state, handoff, or health artifact identity; Protocol consumes the same-numbered SEM row |
| `SER-003` | string normalization | require NFC; reject BOM, NUL, C0/C1 controls, and unpaired surrogates | submit `SAP-003`, `SAP-004`, or `SAP-005` solely by update-state, handoff, or health artifact identity; Protocol consumes the same-numbered SEM row |
| `SER-004` | integer/non-finite bounds | reject booleans in integer positions, non-integers, non-finite values, and out-of-bound values | submit `SAP-003`, `SAP-004`, or `SAP-005` solely by update-state, handoff, or health artifact identity; Protocol consumes the same-numbered SEM row |
| `SER-005` | unknown enum | reject every value outside its closed reusable type | submit `SAP-003`, `SAP-004`, or `SAP-005` solely by update-state, handoff, or health artifact identity; Protocol consumes the same-numbered SEM row |
| `SER-006` | canonical encoding | encode complete object as strict UTF-8 RFC 8785 JCS with no BOM; inability to encode is rejection before storage | submit `SAP-003`, `SAP-004`, or `SAP-005` solely by update-state, handoff, or health artifact identity; Protocol consumes the same-numbered SEM row |
| `SER-007` | size bound | reject canonical JSON outside `1..1048576` bytes | submit `SAP-003`, `SAP-004`, or `SAP-005` solely by update-state, handoff, or health artifact identity; Protocol consumes the same-numbered SEM row |
| `SER-008` | canonical equality | equal objects produce byte-identical encoding; decoding performs no trim/coercion/normalization/repair/default insertion | successful bytes remain a wire-format fact; any failure condition is dispatched only through SAP/SEM |

## 9. Atomic persistence

| Requirement | Operation | Exact keyword-only signature | Side effect and atomicity | Finite failures | Authority after success | Authority after failure | Store-private housekeeping |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `STR-001` | construction | injected `PersistentStoreV1` capability | passive: zero storage, process, clock, environment, or network action | none | unchanged | unchanged | none |
| `STR-002` | read | `read(*, key: ArtifactKeyV1) -> StoreReadResultV1` | one complete immutable read; no mutation | `ACCESS_DENIED`, `INVALID_KEY`, `READ_FAILED` | `PRIOR` | failure-specific `PRIOR` or `NONE` | none |
| `STR-003` | exists | `exists(*, key: ArtifactKeyV1) -> StoreExistsResultV1` | one presence observation; no byte read and no mutation | `ACCESS_DENIED`, `INVALID_KEY`, `READ_FAILED` | `PRIOR` when value true; `NONE` when false | failure-specific `PRIOR` or `NONE` | none |
| `STR-004` | create | `create(*, key: ArtifactKeyV1, payload: CanonicalBytesV1) -> StoreMutationResultV1` | atomic durable create only when absent; never overwrites | `ACCESS_DENIED`, `ALREADY_EXISTS`, `INVALID_KEY`, `WRITE_FAILED`, `FLUSH_FAILED`, `ATOMIC_PUBLICATION_FAILED`, `DURABILITY_FAILED` | `NEW` | `PRIOR` for `ALREADY_EXISTS`; `NEW` for post-switch `DURABILITY_FAILED`; otherwise `NONE` | store removes private temporaries |
| `STR-005` | replace | `replace(*, key: ArtifactKeyV1, payload: CanonicalBytesV1) -> StoreMutationResultV1` | atomic durable replacement only when present; no observation gap | `ACCESS_DENIED`, `NOT_FOUND`, `INVALID_KEY`, `WRITE_FAILED`, `FLUSH_FAILED`, `ATOMIC_PUBLICATION_FAILED`, `DURABILITY_FAILED` | `NEW` | `NONE` for `NOT_FOUND` or `INVALID_KEY`; `NEW` for post-switch `DURABILITY_FAILED`; otherwise `PRIOR` | store removes private temporaries |
| `STR-006` | delete | `delete(*, key: ArtifactKeyV1, expected_storage_identity: Nullable<StorageIdentity>) -> StoreDeleteResultV1` | identity-checked deletion; absent destination returns `NOT_FOUND` status with null failure; mismatch or failure deletes nothing | `ACCESS_DENIED`, `INVALID_KEY`, `IDENTITY_MISMATCH`, `DELETE_FAILED` | `NONE` | `NONE` for `NOT_FOUND` status or `INVALID_KEY`; otherwise `PRIOR` | none; store performs exactly one requested delete and owns no retry |
| `STR-007` | quarantine | `quarantine(*, key: ArtifactKeyV1, quarantine_key: ArtifactKeyV1) -> StoreQuarantineResultV1` | atomically publishes quarantine object and removes source authority; absent source returns `NOT_FOUND` status with null failure | `ACCESS_DENIED`, `ALREADY_EXISTS`, `INVALID_KEY`, `ATOMIC_PUBLICATION_FAILED`, `DURABILITY_FAILED`, `QUARANTINE_FAILED` | `NEW` | `NONE` for `NOT_FOUND` status or `INVALID_KEY`; `NEW` for post-switch `DURABILITY_FAILED`; otherwise `PRIOR` | store removes private temporaries |
| `STR-008` | exception boundary | six operation signatures above | only the finite categories in `EXC-001..034` are converted; unexpected defects and process-control exceptions propagate unchanged | `EXC-001..034` only | exact `EXC-*` row | exact `EXC-*` row | exact `EXC-*` row |

| Requirement | Operation | Caught exception category | Result status | Failure | Authority |
| --- | --- | --- | --- | --- | --- |
| `EXC-001` | `READ` | `InvalidArtifactKeyError` | `FAILED` | `INVALID_KEY` | `NONE` |
| `EXC-002` | `READ` | `PermissionError` | `FAILED` | `ACCESS_DENIED` | `PRIOR` |
| `EXC-003` | `READ` | `FileNotFoundError` | `NOT_FOUND` | null | `NONE` |
| `EXC-004` | `READ` | `StoreReadIOError` | `FAILED` | `READ_FAILED` | `PRIOR` |
| `EXC-005` | `EXISTS` | `InvalidArtifactKeyError` | `FAILED` | `INVALID_KEY` | `NONE` |
| `EXC-006` | `EXISTS` | `PermissionError` | `FAILED` | `ACCESS_DENIED` | `PRIOR` |
| `EXC-007` | `EXISTS` | `FileNotFoundError` | `COMPLETED` with exists false | null | `NONE` |
| `EXC-008` | `EXISTS` | `StoreReadIOError` | `FAILED` | `READ_FAILED` | `PRIOR` |
| `EXC-009` | `CREATE` | `InvalidArtifactKeyError` | `FAILED` | `INVALID_KEY` | `NONE` |
| `EXC-010` | `CREATE` | `PermissionError` | `FAILED` | `ACCESS_DENIED` | `NONE` |
| `EXC-011` | `CREATE` | `FileExistsError` | `FAILED` | `ALREADY_EXISTS` | `PRIOR` |
| `EXC-012` | `CREATE` | `StoreWriteError` | `FAILED` | `WRITE_FAILED` | `NONE` |
| `EXC-013` | `CREATE` | `StoreFlushError` | `FAILED` | `FLUSH_FAILED` | `NONE` |
| `EXC-014` | `CREATE` | `StoreAtomicPublicationError` | `FAILED` | `ATOMIC_PUBLICATION_FAILED` | `NONE` |
| `EXC-015` | `CREATE` | `StoreDurabilityError` | `FAILED` | `DURABILITY_FAILED` | `NEW` |
| `EXC-016` | `REPLACE` | `InvalidArtifactKeyError` | `FAILED` | `INVALID_KEY` | `NONE` |
| `EXC-017` | `REPLACE` | `PermissionError` | `FAILED` | `ACCESS_DENIED` | `PRIOR` |
| `EXC-018` | `REPLACE` | `FileNotFoundError` | `FAILED` | `NOT_FOUND` | `NONE` |
| `EXC-019` | `REPLACE` | `StoreWriteError` | `FAILED` | `WRITE_FAILED` | `PRIOR` |
| `EXC-020` | `REPLACE` | `StoreFlushError` | `FAILED` | `FLUSH_FAILED` | `PRIOR` |
| `EXC-021` | `REPLACE` | `StoreAtomicPublicationError` | `FAILED` | `ATOMIC_PUBLICATION_FAILED` | `PRIOR` |
| `EXC-022` | `REPLACE` | `StoreDurabilityError` | `FAILED` | `DURABILITY_FAILED` | `NEW` |
| `EXC-023` | `DELETE` | `InvalidArtifactKeyError` | `FAILED` | `INVALID_KEY` | `NONE` |
| `EXC-024` | `DELETE` | `PermissionError` | `FAILED` | `ACCESS_DENIED` | `PRIOR` |
| `EXC-025` | `DELETE` | `FileNotFoundError` | `NOT_FOUND` | null | `NONE` |
| `EXC-026` | `DELETE` | `StoreIdentityMismatchError` | `FAILED` | `IDENTITY_MISMATCH` | `PRIOR` |
| `EXC-027` | `DELETE` | `StoreDeleteError` | `FAILED` | `DELETE_FAILED` | `PRIOR` |
| `EXC-028` | `QUARANTINE` | `InvalidArtifactKeyError` | `FAILED` | `INVALID_KEY` | `NONE` |
| `EXC-029` | `QUARANTINE` | `PermissionError` | `FAILED` | `ACCESS_DENIED` | `PRIOR` |
| `EXC-030` | `QUARANTINE` | `FileNotFoundError` | `NOT_FOUND` | null | `NONE` |
| `EXC-031` | `QUARANTINE` | `FileExistsError` | `FAILED` | `ALREADY_EXISTS` | `PRIOR` |
| `EXC-032` | `QUARANTINE` | `StoreAtomicPublicationError` | `FAILED` | `ATOMIC_PUBLICATION_FAILED` | `PRIOR` |
| `EXC-033` | `QUARANTINE` | `StoreDurabilityError` | `FAILED` | `DURABILITY_FAILED` | `NEW` |
| `EXC-034` | `QUARANTINE` | `StoreQuarantineError` | `FAILED` | `QUARANTINE_FAILED` | `PRIOR` |
| `EXC-035` | six operations | `KeyboardInterrupt`, `SystemExit`, or `GeneratorExit` | unconverted | n/a | unchanged by propagation |
| `EXC-036` | six operations | exception outside `EXC-001..034` | unconverted private/internal defect | n/a | unchanged by propagation |
| `EXC-037` | closure | a generic `except Exception` or open exception tuple is prohibited | n/a | n/a | n/a |

| Requirement | Result model | Field | Exact type | Public representation | Nullable | Invariant |
| --- | --- | --- | --- | --- | --- | --- |
| `RSF-001` | `StoreReadResultV1` | `status` | `PersistentStoreStatusV1` | enum serialized value | no | exact tuple in `RVR-001..005` |
| `RSF-002` | `StoreReadResultV1` | `payload` | `Nullable<CanonicalBytesV1>` | immutable bytes or null | yes | non-null exactly for `COMPLETED` |
| `RSF-003` | `StoreReadResultV1` | `failure` | `Nullable<PersistentStoreFailureCodeV1>` | enum serialized value or null | yes | non-null exactly for `FAILED` |
| `RSF-004` | `StoreReadResultV1` | `authority` | `PersistentStoreAuthorityV1` | enum serialized value | no | exact value in `RVR-001..005` |
| `RSF-005` | `StoreExistsResultV1` | `status` | `PersistentStoreStatusV1` | enum serialized value | no | only `COMPLETED` or `FAILED` |
| `RSF-006` | `StoreExistsResultV1` | `exists` | `Nullable<StrictBoolean>` | Boolean or null | yes | non-null exactly for `COMPLETED` |
| `RSF-007` | `StoreExistsResultV1` | `failure` | `Nullable<PersistentStoreFailureCodeV1>` | enum serialized value or null | yes | non-null exactly for `FAILED` |
| `RSF-008` | `StoreExistsResultV1` | `authority` | `PersistentStoreAuthorityV1` | enum serialized value | no | exact value in `EVR-001..005` |
| `RSF-009` | `StoreMutationResultV1` | `status` | `PersistentStoreStatusV1` | enum serialized value | no | only `COMPLETED` or `FAILED` |
| `RSF-010` | `StoreMutationResultV1` | `failure` | `Nullable<PersistentStoreFailureCodeV1>` | enum serialized value or null | yes | null on completion; non-null on failure |
| `RSF-011` | `StoreMutationResultV1` | `authority` | `PersistentStoreAuthorityV1` | enum serialized value | no | exact value in `MVR-001..016` |
| `RSF-012` | `StoreDeleteResultV1` | `status` | `PersistentStoreStatusV1` | enum serialized value | no | exact tuple in `DVR-001..006` |
| `RSF-013` | `StoreDeleteResultV1` | `failure` | `Nullable<PersistentStoreFailureCodeV1>` | enum serialized value or null | yes | non-null exactly for `FAILED` |
| `RSF-014` | `StoreDeleteResultV1` | `authority` | `PersistentStoreAuthorityV1` | enum serialized value | no | `NONE` on completion/not found; `PRIOR` on failure |
| `RSF-015` | `StoreQuarantineResultV1` | `status` | `PersistentStoreStatusV1` | enum serialized value | no | exact tuple in `QVR-001..008` |
| `RSF-016` | `StoreQuarantineResultV1` | `failure` | `Nullable<PersistentStoreFailureCodeV1>` | enum serialized value or null | yes | non-null exactly for `FAILED` |
| `RSF-017` | `StoreQuarantineResultV1` | `authority` | `PersistentStoreAuthorityV1` | enum serialized value | no | exact value in `QVR-001..008` |
| `RSF-018` | `StoreReadResultV1` | `operation` | `PersistentStoreOperationV1` | enum serialized value | no | exactly `READ` |
| `RSF-019` | `StoreExistsResultV1` | `operation` | `PersistentStoreOperationV1` | enum serialized value | no | exactly `EXISTS` |
| `RSF-020` | `StoreMutationResultV1` | `operation` | `PersistentStoreOperationV1` | enum serialized value | no | exactly `CREATE` or `REPLACE`; the chosen member governs `FAM-*` validation |
| `RSF-021` | `StoreDeleteResultV1` | `operation` | `PersistentStoreOperationV1` | enum serialized value | no | exactly `DELETE` |
| `RSF-022` | `StoreQuarantineResultV1` | `operation` | `PersistentStoreOperationV1` | enum serialized value | no | exactly `QUARANTINE` |

| Requirement | Result type | Operation | Status | Payload/existence | Failure | Authority | Valid |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `RVR-001` | `StoreReadResultV1` | `READ` | `COMPLETED` | nonempty immutable bytes | null | `PRIOR` | yes |
| `RVR-002` | `StoreReadResultV1` | `READ` | `NOT_FOUND` | null | null | `NONE` | yes |
| `RVR-003` | `StoreReadResultV1` | `READ` | `FAILED` | null | `ACCESS_DENIED` | `PRIOR` | yes |
| `RVR-004` | `StoreReadResultV1` | `READ` | `FAILED` | null | `INVALID_KEY` | `NONE` | yes |
| `RVR-005` | `StoreReadResultV1` | `READ` | `FAILED` | null | `READ_FAILED` | `PRIOR` | yes |
| `RVR-006` | `StoreReadResultV1` | not `READ` | any | any | any | any | no |
| `RVR-007` | `StoreReadResultV1` | `READ` | tuple absent from `RVR-001..005` | any | any | any | no |
| `EVR-001` | `StoreExistsResultV1` | `EXISTS` | `COMPLETED` | Boolean true | null | `PRIOR` | yes |
| `EVR-002` | `StoreExistsResultV1` | `EXISTS` | `COMPLETED` | Boolean false | null | `NONE` | yes |
| `EVR-003` | `StoreExistsResultV1` | `EXISTS` | `FAILED` | null | `ACCESS_DENIED` | `PRIOR` | yes |
| `EVR-004` | `StoreExistsResultV1` | `EXISTS` | `FAILED` | null | `INVALID_KEY` | `NONE` | yes |
| `EVR-005` | `StoreExistsResultV1` | `EXISTS` | `FAILED` | null | `READ_FAILED` | `PRIOR` | yes |
| `EVR-006` | `StoreExistsResultV1` | not `EXISTS` | any | any | any | any | no |
| `EVR-007` | `StoreExistsResultV1` | `EXISTS` | tuple absent from `EVR-001..005`, including `NOT_FOUND` | any | any | any | no |
| `MVR-001` | `StoreMutationResultV1` | `CREATE` | `COMPLETED` | n/a | null | `NEW` | yes |
| `MVR-002` | `StoreMutationResultV1` | `CREATE` | `FAILED` | n/a | `ACCESS_DENIED` | `NONE` | yes |
| `MVR-003` | `StoreMutationResultV1` | `CREATE` | `FAILED` | n/a | `ALREADY_EXISTS` | `PRIOR` | yes |
| `MVR-004` | `StoreMutationResultV1` | `CREATE` | `FAILED` | n/a | `INVALID_KEY` | `NONE` | yes |
| `MVR-005` | `StoreMutationResultV1` | `CREATE` | `FAILED` | n/a | `WRITE_FAILED` | `NONE` | yes |
| `MVR-006` | `StoreMutationResultV1` | `CREATE` | `FAILED` | n/a | `FLUSH_FAILED` | `NONE` | yes |
| `MVR-007` | `StoreMutationResultV1` | `CREATE` | `FAILED` | n/a | `ATOMIC_PUBLICATION_FAILED` | `NONE` | yes |
| `MVR-008` | `StoreMutationResultV1` | `CREATE` | `FAILED` | n/a | `DURABILITY_FAILED` | `NEW` | yes |
| `MVR-009` | `StoreMutationResultV1` | `REPLACE` | `COMPLETED` | n/a | null | `NEW` | yes |
| `MVR-010` | `StoreMutationResultV1` | `REPLACE` | `FAILED` | n/a | `ACCESS_DENIED` | `PRIOR` | yes |
| `MVR-011` | `StoreMutationResultV1` | `REPLACE` | `FAILED` | n/a | `NOT_FOUND` | `NONE` | yes |
| `MVR-012` | `StoreMutationResultV1` | `REPLACE` | `FAILED` | n/a | `INVALID_KEY` | `NONE` | yes |
| `MVR-013` | `StoreMutationResultV1` | `REPLACE` | `FAILED` | n/a | `WRITE_FAILED` | `PRIOR` | yes |
| `MVR-014` | `StoreMutationResultV1` | `REPLACE` | `FAILED` | n/a | `FLUSH_FAILED` | `PRIOR` | yes |
| `MVR-015` | `StoreMutationResultV1` | `REPLACE` | `FAILED` | n/a | `ATOMIC_PUBLICATION_FAILED` | `PRIOR` | yes |
| `MVR-016` | `StoreMutationResultV1` | `REPLACE` | `FAILED` | n/a | `DURABILITY_FAILED` | `NEW` | yes |
| `MVR-017` | `StoreMutationResultV1` | neither `CREATE` nor `REPLACE` | any | n/a | any | any | no |
| `MVR-018` | `StoreMutationResultV1` | `CREATE` or `REPLACE` | tuple absent from `MVR-001..016` | n/a | any | any | no |
| `DVR-001` | `StoreDeleteResultV1` | `DELETE` | `COMPLETED` | n/a | null | `NONE` | yes |
| `DVR-002` | `StoreDeleteResultV1` | `DELETE` | `NOT_FOUND` | n/a | null | `NONE` | yes |
| `DVR-003` | `StoreDeleteResultV1` | `DELETE` | `FAILED` | n/a | `ACCESS_DENIED` | `PRIOR` | yes |
| `DVR-004` | `StoreDeleteResultV1` | `DELETE` | `FAILED` | n/a | `INVALID_KEY` | `NONE` | yes |
| `DVR-005` | `StoreDeleteResultV1` | `DELETE` | `FAILED` | n/a | `DELETE_FAILED` | `PRIOR` | yes |
| `DVR-006` | `StoreDeleteResultV1` | `DELETE` | `FAILED` | n/a | `IDENTITY_MISMATCH` | `PRIOR` | yes |
| `DVR-007` | `StoreDeleteResultV1` | not `DELETE` | any | n/a | any | any | no |
| `DVR-008` | `StoreDeleteResultV1` | `DELETE` | tuple absent from `DVR-001..006` | n/a | any | any | no |
| `QVR-001` | `StoreQuarantineResultV1` | `QUARANTINE` | `COMPLETED` | n/a | null | `NEW` | yes |
| `QVR-002` | `StoreQuarantineResultV1` | `QUARANTINE` | `NOT_FOUND` | n/a | null | `NONE` | yes |
| `QVR-003` | `StoreQuarantineResultV1` | `QUARANTINE` | `FAILED` | n/a | `ACCESS_DENIED` | `PRIOR` | yes |
| `QVR-004` | `StoreQuarantineResultV1` | `QUARANTINE` | `FAILED` | n/a | `ALREADY_EXISTS` | `PRIOR` | yes |
| `QVR-005` | `StoreQuarantineResultV1` | `QUARANTINE` | `FAILED` | n/a | `INVALID_KEY` | `NONE` | yes |
| `QVR-006` | `StoreQuarantineResultV1` | `QUARANTINE` | `FAILED` | n/a | `ATOMIC_PUBLICATION_FAILED` | `PRIOR` | yes |
| `QVR-007` | `StoreQuarantineResultV1` | `QUARANTINE` | `FAILED` | n/a | `DURABILITY_FAILED` | `NEW` | yes |
| `QVR-008` | `StoreQuarantineResultV1` | `QUARANTINE` | `FAILED` | n/a | `QUARANTINE_FAILED` | `PRIOR` | yes |
| `QVR-009` | `StoreQuarantineResultV1` | not `QUARANTINE` | any | n/a | any | any | no |
| `QVR-010` | `StoreQuarantineResultV1` | `QUARANTINE` | tuple absent from `QVR-001..008` | n/a | any | any | no |

| Requirement | Object-safety rule | Exact behavior |
| --- | --- | --- |
| `OBJ-001` | construction | result records are frozen structural immutable records reconstructed through their public constructor; copied-invalid state is rejected by the same validity matrix |
| `OBJ-002` | copy and equality | shallow copy and deep copy return an equal valid value; equality compares exact public type and fields without invoking dependency hooks |
| `OBJ-003` | representation | repr contains only symbolic status, failure, authority, Boolean existence, and payload length; it never contains payload bytes, paths, exceptions, tracebacks, object addresses, or credentials |
| `OBJ-004` | pickle and subclass | pickle reconstruction revalidates the public constructor; subclasses are rejected |
| `OBJ-005` | passivity | construction, reconstruction, copy, deep copy, equality, repr, and pickle perform no store call, process action, networking, environment access, clock read, or cleanup |
| `OBJ-006` | semantic boundary | lower store-result validity proves only a structurally possible storage observation; it never proves Protocol legality or selects a COMP, RED, SAP, or SEM projection |

| Requirement | Persistence call | Precondition | Success | Failure | Frozen Protocol consumption |
| --- | --- | --- | --- | --- | --- |
| `PST-001` | prepare canonical bytes | complete authoritative model or immutable retained bytes | exact bounded bytes | exact serialization failure fact; zero store calls | for JSON failure submit `SAP-003`, `SAP-004`, or `SAP-005` by artifact identity; retained opaque bytes have no serialization dispatch |
| `PST-002` | `create(key, canonical_bytes)` | valid key; destination expected absent | `COMPLETED/NEW` | exact lower store result | submit the exact outcome to APP and consume its referenced COMP or RED projection |
| `PST-003` | `replace(key, canonical_bytes)` | valid key; destination expected present | `COMPLETED/NEW` | exact lower store result | submit the exact outcome to APP and consume its referenced COMP or RED projection |
| `PST-004` | immutable projection | successful mutation or `FAILED/NEW` durability result | exactly one immutable projection | exact projection-failure condition | submit exactly `SAP-027`, `SAP-028`, or `SAP-029` by update-state, handoff, or health artifact identity |
| `PST-005` | quarantine malformed bytes | exact validation condition supplied to Protocol | one lower quarantine result | exact lower quarantine failure fact | submit the outcome to APP/RED; diagnostics and cleanup remain Protocol-owned |
| `PST-006` | delete retained bytes | retained reference durably absent; full identity supplied | `StoreDeleteResultV1(DELETE,COMPLETED,null,NONE)` | exact lower identity-mismatch or delete-failure fact | submit the outcome to APP/RED; any retry-owned cleanup follows Protocol `CLY-001..007` |

## 10. Persistence failures

| Requirement | `PersistentStoreFailureCodeV1` member | Serialized value | Exact meaning | Exact originating operations |
| --- | --- | --- | --- | --- |
| `PFC-000` | closure | n/a | this table is the sole membership authority; aliases, unknown members, custom members, and subclass extensions are rejected | n/a |
| `PFC-001` | `ACCESS_DENIED` | `ACCESS_DENIED` | operating-system authorization rejected the named operation before content mutation | `READ`, `EXISTS`, `CREATE`, `REPLACE`, `DELETE`, `QUARANTINE` |
| `PFC-002` | `ALREADY_EXISTS` | `ALREADY_EXISTS` | an exclusive-create destination already exists | `CREATE`, `QUARANTINE` |
| `PFC-003` | `NOT_FOUND` | `NOT_FOUND` | a required replacement destination is absent | `REPLACE` |
| `PFC-004` | `INVALID_KEY` | `INVALID_KEY` | `ArtifactKeyV1` validation failed before store access | `READ`, `EXISTS`, `CREATE`, `REPLACE`, `DELETE`, `QUARANTINE` |
| `PFC-005` | `READ_FAILED` | `READ_FAILED` | a non-permission read or presence-query I/O operation failed while prior storage authority remained | `READ`, `EXISTS` |
| `PFC-006` | `WRITE_FAILED` | `WRITE_FAILED` | payload writing failed before publication | `CREATE`, `REPLACE` |
| `PFC-007` | `FLUSH_FAILED` | `FLUSH_FAILED` | private temporary-byte flushing failed before publication | `CREATE`, `REPLACE` |
| `PFC-008` | `ATOMIC_PUBLICATION_FAILED` | `ATOMIC_PUBLICATION_FAILED` | atomic destination switch failed before publication | `CREATE`, `REPLACE`, `QUARANTINE` |
| `PFC-009` | `DURABILITY_FAILED` | `DURABILITY_FAILED` | namespace durability acknowledgement failed after atomic publication | `CREATE`, `REPLACE`, `QUARANTINE` |
| `PFC-010` | `DELETE_FAILED` | `DELETE_FAILED` | identity-checked deletion failed without deleting the destination | `DELETE` |
| `PFC-011` | `QUARANTINE_FAILED` | `QUARANTINE_FAILED` | quarantine publication failed before source authority changed | `QUARANTINE` |
| `PFC-012` | `IDENTITY_MISMATCH` | `IDENTITY_MISMATCH` | supplied storage identity differs from the destination identity | `DELETE` |

| Requirement | Operation | Failure code | Result status | Lower store authority |
| --- | --- | --- | --- | --- |
| `FAM-001` | `READ` | `ACCESS_DENIED` | `FAILED` | `PRIOR` |
| `FAM-002` | `READ` | `INVALID_KEY` | `FAILED` | `NONE` |
| `FAM-003` | `READ` | `READ_FAILED` | `FAILED` | `PRIOR` |
| `FAM-004` | `EXISTS` | `ACCESS_DENIED` | `FAILED` | `PRIOR` |
| `FAM-005` | `EXISTS` | `INVALID_KEY` | `FAILED` | `NONE` |
| `FAM-006` | `EXISTS` | `READ_FAILED` | `FAILED` | `PRIOR` |
| `FAM-007` | `CREATE` | `ACCESS_DENIED` | `FAILED` | `NONE` |
| `FAM-008` | `CREATE` | `ALREADY_EXISTS` | `FAILED` | `PRIOR` |
| `FAM-009` | `CREATE` | `INVALID_KEY` | `FAILED` | `NONE` |
| `FAM-010` | `CREATE` | `WRITE_FAILED` | `FAILED` | `NONE` |
| `FAM-011` | `CREATE` | `FLUSH_FAILED` | `FAILED` | `NONE` |
| `FAM-012` | `CREATE` | `ATOMIC_PUBLICATION_FAILED` | `FAILED` | `NONE` |
| `FAM-013` | `CREATE` | `DURABILITY_FAILED` | `FAILED` | `NEW` |
| `FAM-014` | `REPLACE` | `ACCESS_DENIED` | `FAILED` | `PRIOR` |
| `FAM-015` | `REPLACE` | `NOT_FOUND` | `FAILED` | `NONE` |
| `FAM-016` | `REPLACE` | `INVALID_KEY` | `FAILED` | `NONE` |
| `FAM-017` | `REPLACE` | `WRITE_FAILED` | `FAILED` | `PRIOR` |
| `FAM-018` | `REPLACE` | `FLUSH_FAILED` | `FAILED` | `PRIOR` |
| `FAM-019` | `REPLACE` | `ATOMIC_PUBLICATION_FAILED` | `FAILED` | `PRIOR` |
| `FAM-020` | `REPLACE` | `DURABILITY_FAILED` | `FAILED` | `NEW` |
| `FAM-021` | `DELETE` | `ACCESS_DENIED` | `FAILED` | `PRIOR` |
| `FAM-022` | `DELETE` | `INVALID_KEY` | `FAILED` | `NONE` |
| `FAM-023` | `DELETE` | `DELETE_FAILED` | `FAILED` | `PRIOR` |
| `FAM-024` | `DELETE` | `IDENTITY_MISMATCH` | `FAILED` | `PRIOR` |
| `FAM-025` | `QUARANTINE` | `ACCESS_DENIED` | `FAILED` | `PRIOR` |
| `FAM-026` | `QUARANTINE` | `ALREADY_EXISTS` | `FAILED` | `PRIOR` |
| `FAM-027` | `QUARANTINE` | `INVALID_KEY` | `FAILED` | `NONE` |
| `FAM-028` | `QUARANTINE` | `ATOMIC_PUBLICATION_FAILED` | `FAILED` | `PRIOR` |
| `FAM-029` | `QUARANTINE` | `DURABILITY_FAILED` | `FAILED` | `NEW` |
| `FAM-030` | `QUARANTINE` | `QUARANTINE_FAILED` | `FAILED` | `PRIOR` |

| Requirement | Frozen Protocol consumption rule | Persistence responsibility |
| --- | --- | --- |
| `CON-001` | Submit the exact artifact, operation, status, failure, and protocol context to `ProtocolApplicabilityMatrixV1` (`APP-000..160`); APP is the sole protocol legality authority. | Supply only validated lower store-result facts; do not infer legality. |
| `CON-002` | For a legal successful APP key, consume its exact `COMP-001..039` projection. | Do not derive completed authority or any runtime semantic field. |
| `CON-003` | For a legal failed APP key, consume its exact `RED-001..113` projection. | Do not derive public error, authority, retryability, cleanup, or diagnostics from `FAM-*` or any local mapping. |
| `CON-004` | For a non-store condition, submit the exact artifact, context, and condition to `SAP-001..034`, then consume the same-numbered `SEM-001..034` projection. | Do not create local non-store legality or semantic mappings. |
| `CON-005` | Construct exactly one runtime-only `PersistenceProtocolResultV1` from the selected COMP, RED, or SEM projection and validate it through frozen Protocol V6. | Never serialize, repair, normalize, or independently validate the six-field runtime result as a wire artifact. |
| `CON-006` | Public-error precedence is applied only by frozen Protocol V6 and may replace only the public error. | Preserve the independently selected authority, retryability, cleanup, and optional diagnostic unchanged. |
| `CON-007` | `FAM-001..030` supplies only the frozen lower operation/failure pair, failed status, and lower store authority consumed by APP and RED. | Retryability and cleanup are absent from FAM and are copied only from the exact frozen RED projection. |

| Requirement | Validation order | Pass condition | Failure condition | Exact Protocol handoff | Validation stop | Local wire action | Persistence output |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `VAL-001` | 1: store read | `COMPLETED` | `NOT_FOUND` or `FAILED` | submit the exact artifact/READ/status/failure/reconstruction-context tuple to APP; no local semantic lookup | yes | none; store operation already completed | validated lower result only; no runtime result |
| `VAL-002` | 2: byte-size bound | `1..1048576` bytes for JSON artifact | zero or over bound | submit `SAP-003`, `SAP-004`, or `SAP-005` solely by update-state, handoff, or health artifact identity | yes | none; any cleanup is Protocol-owned | earliest failed wire stage only; no runtime result |
| `VAL-003` | 3: UTF-8 decode | one strict UTF-8 text, no BOM | decode error or BOM | submit `SAP-003`, `SAP-004`, or `SAP-005` solely by update-state, handoff, or health artifact identity | yes | none; any cleanup is Protocol-owned | earliest failed wire stage only; no runtime result |
| `VAL-004` | 4: JSON lexical parse | one complete JSON value | lexical error/trailing content | submit `SAP-003`, `SAP-004`, or `SAP-005` solely by update-state, handoff, or health artifact identity | yes | none; any cleanup is Protocol-owned | earliest failed wire stage only; no runtime result |
| `VAL-005` | 5: duplicate keys | every object key unique | any duplicate | submit `SAP-003`, `SAP-004`, or `SAP-005` solely by update-state, handoff, or health artifact identity | yes | none; any cleanup is Protocol-owned | earliest failed wire stage only; no runtime result |
| `VAL-006` | 6: canonical form | input bytes equal JCS re-encoding | unequal bytes | submit `SAP-003`, `SAP-004`, or `SAP-005` solely by update-state, handoff, or health artifact identity | yes | none; any cleanup is Protocol-owned | earliest failed wire stage only; no runtime result |
| `VAL-007` | 7: root type | root is object | any other JSON type | submit `SAP-003`, `SAP-004`, or `SAP-005` solely by update-state, handoff, or health artifact identity | yes | none; any cleanup is Protocol-owned | earliest failed wire stage only; no runtime result |
| `VAL-008` | 8: schema identifier | exact artifact literal | missing/foreign/wrong type | submit `SAP-003`, `SAP-004`, or `SAP-005` solely by update-state, handoff, or health artifact identity | yes | none; any cleanup is Protocol-owned | earliest failed wire stage only; no runtime result |
| `VAL-009` | 9: schema version | integer `1` | missing/unknown/wrong type | submit `SAP-003`, `SAP-004`, or `SAP-005` solely by update-state, handoff, or health artifact identity | yes | none; any cleanup is Protocol-owned | earliest failed wire stage only; no runtime result |
| `VAL-010` | 10: fields | exact field set | missing or unknown field | submit `SAP-003`, `SAP-004`, or `SAP-005` solely by update-state, handoff, or health artifact identity | yes | none; any cleanup is Protocol-owned | earliest failed wire stage only; no runtime result |
| `VAL-011` | 11: field types | every field exact JSON type/nullability | mismatch | submit `SAP-003`, `SAP-004`, or `SAP-005` solely by update-state, handoff, or health artifact identity | yes | none; any cleanup is Protocol-owned | earliest failed wire stage only; no runtime result |
| `VAL-012` | 12: scalar grammar | every scalar satisfies its reusable type | bound/grammar/normalization error | submit `SAP-003`, `SAP-004`, or `SAP-005` solely by update-state, handoff, or health artifact identity | yes | none; any cleanup is Protocol-owned | earliest failed wire stage only; no runtime result |
| `VAL-013` | 13: cross-field invariants | every schema invariant holds | any invariant fails | submit `SAP-003`, `SAP-004`, or `SAP-005` solely by update-state, handoff, or health artifact identity | yes | none; any cleanup is Protocol-owned | earliest failed wire stage only; no runtime result |
| `VAL-014` | 14: accept | all prior stages pass | none | submit `APP-121`, `APP-125`, or `APP-129` solely by accepted update-state, handoff, or health artifact identity | no | none | reconstructed immutable artifact only; no runtime result |

## 11. Error enum

| Requirement | Referenced Protocol symbolic name | Serialized value |
| --- | --- | --- |
| `ERR-000` | closure rule: Protocol V6 supplies the closed 34-member `PersistenceFormatErrorCodeV1` set; aliases, extensions, unknown values, custom values, and caller-selected members are rejected; Persistence creates no membership or runtime semantic | n/a |
| `ERR-001` | `UPDATE_STATE_MALFORMED` | `UPDATE_STATE_MALFORMED` |
| `ERR-002` | `UPDATE_STATE_QUARANTINED` | `UPDATE_STATE_QUARANTINED` |
| `ERR-003` | `UPDATE_STATE_PERSISTENCE_FAILED` | `UPDATE_STATE_PERSISTENCE_FAILED` |
| `ERR-004` | `OBSERVATION_PUBLICATION_FAILED` | `OBSERVATION_PUBLICATION_FAILED` |
| `ERR-005` | `UPDATE_OPERATION_INTERRUPTED` | `UPDATE_OPERATION_INTERRUPTED` |
| `ERR-006` | `UPDATE_CHECK_FAILED` | `UPDATE_CHECK_FAILED` |
| `ERR-007` | `UPDATE_METADATA_RECHECK_REQUIRED` | `UPDATE_METADATA_RECHECK_REQUIRED` |
| `ERR-008` | `UPDATE_DOWNLOAD_INTERRUPTED` | `UPDATE_DOWNLOAD_INTERRUPTED` |
| `ERR-009` | `UPDATE_DOWNLOAD_FAILED` | `UPDATE_DOWNLOAD_FAILED` |
| `ERR-010` | `UPDATE_MANIFEST_INCOMPATIBLE` | `UPDATE_MANIFEST_INCOMPATIBLE` |
| `ERR-011` | `RETAINED_INSTALLER_MISSING` | `RETAINED_INSTALLER_MISSING` |
| `ERR-012` | `RETAINED_INSTALLER_INVALID` | `RETAINED_INSTALLER_INVALID` |
| `ERR-013` | `RETAINED_INSTALLER_HASH_MISMATCH` | `RETAINED_INSTALLER_HASH_MISMATCH` |
| `ERR-014` | `RETAINED_INSTALLER_REVALIDATION_FAILED` | `RETAINED_INSTALLER_REVALIDATION_FAILED` |
| `ERR-015` | `HANDOFF_RECEIPT_MISSING` | `HANDOFF_RECEIPT_MISSING` |
| `ERR-016` | `HANDOFF_RECEIPT_MALFORMED` | `HANDOFF_RECEIPT_MALFORMED` |
| `ERR-017` | `HANDOFF_RECEIPT_PERSISTENCE_FAILED` | `HANDOFF_RECEIPT_PERSISTENCE_FAILED` |
| `ERR-018` | `HANDOFF_RECEIPT_STALE` | `HANDOFF_RECEIPT_STALE` |
| `ERR-019` | `HANDOFF_LINEAGE_MISMATCH` | `HANDOFF_LINEAGE_MISMATCH` |
| `ERR-020` | `HANDOFF_PROCESS_IDENTITY_MISMATCH` | `HANDOFF_PROCESS_IDENTITY_MISMATCH` |
| `ERR-021` | `HANDOFF_PROCESS_IDENTITY_UNAVAILABLE` | `HANDOFF_PROCESS_IDENTITY_UNAVAILABLE` |
| `ERR-022` | `HANDOFF_PROCESS_NOT_OBSERVED` | `HANDOFF_PROCESS_NOT_OBSERVED` |
| `ERR-023` | `INSTALLER_HANDOFF_CANCELLED` | `INSTALLER_HANDOFF_CANCELLED` |
| `ERR-024` | `INSTALLER_PRELAUNCH_VERIFICATION_FAILED` | `INSTALLER_PRELAUNCH_VERIFICATION_FAILED` |
| `ERR-025` | `INSTALLER_PROCESS_START_FAILED` | `INSTALLER_PROCESS_START_FAILED` |
| `ERR-026` | `INSTALLER_RECEIPT_TIMEOUT` | `INSTALLER_RECEIPT_TIMEOUT` |
| `ERR-027` | `INSTALLER_MUTEX_TIMEOUT` | `INSTALLER_MUTEX_TIMEOUT` |
| `ERR-028` | `HEALTH_RECEIPT_MALFORMED` | `HEALTH_RECEIPT_MALFORMED` |
| `ERR-029` | `HEALTH_RECEIPT_PERSISTENCE_FAILED` | `HEALTH_RECEIPT_PERSISTENCE_FAILED` |
| `ERR-030` | `HEALTH_INITIALIZATION_LINEAGE_MISSING` | `HEALTH_INITIALIZATION_LINEAGE_MISSING` |
| `ERR-031` | `HEALTH_INITIALIZATION_LINEAGE_MISMATCH` | `HEALTH_INITIALIZATION_LINEAGE_MISMATCH` |
| `ERR-032` | `HEALTH_VALIDATION_TIMEOUT` | `HEALTH_VALIDATION_TIMEOUT` |
| `ERR-033` | `HEALTH_VALIDATION_INTERRUPTED` | `HEALTH_VALIDATION_INTERRUPTED` |
| `ERR-034` | `HEALTH_VALIDATION_FAILED` | `HEALTH_VALIDATION_FAILED` |

## 12. Protocol semantic consumption

| Requirement | Frozen Protocol authority | Exact Persistence behavior |
| --- | --- | --- |
| `PSC-001` | `ProtocolApplicabilityMatrixV1` (`APP-000..160`) | Submit the exact lower store outcome and protocol context; accept APP's legality and source without local inference. |
| `PSC-002` | `COMP-001..039` | For a legal APP success, copy the exact completed status, null public error, authority, retryability, and cleanup into the runtime result. |
| `PSC-003` | `RED-001..113` | For a legal APP failure, copy the exact failed status, public error, authority, retryability, and cleanup into the runtime result. |
| `PSC-004` | `SAP-001..034` and `SEM-001..034` | For a non-store condition, accept SAP legality and copy only the same-numbered SEM projection. |
| `PSC-005` | `PersistenceProtocolResultV1` | Consume and validate exactly six runtime-only fields: status, public error, authority, retryability, cleanup, and optional diagnostics. |
| `PSC-006` | Protocol Section 11.1 precedence | Precedence may select only the public error; Persistence never changes or infers authority, retryability, cleanup, or diagnostics. |
| `PSC-007` | `ProtocolDiagnosticsV1` | Diagnostics are runtime-only, optional, non-authoritative, never serialized, and never validated as persisted wire artifacts. |
| `PSC-008` | Protocol `CLY-001..007` | Cleanup lifecycle and retry ownership remain Protocol-owned; the store supplies exactly one requested lower operation result. |
| `PSC-009` | Protocol result validity | No terminal `UNKNOWN` authority exists; every complete runtime result carries exactly `NONE`, `PRIOR`, or `NEW` selected by COMP, RED, or SEM. |
| `PSC-010` | Wire compatibility | Every schema, field name, JSON representation, serialized public-error value, store operation, store status, store failure, and lower store authority remains unchanged. |
| `PSC-011` | Protocol `ALN-001..013` | Consume the complete frozen mechanical-alignment contract as reference-only conformance authority; do not copy or redefine any ALN runtime semantic. |

## 13. Requirement identifiers

| Requirement | Namespace owner | Covered identifiers | Stability rule |
| --- | --- | --- | --- |
| `RID-001` | scope | `SCP-*` | never reuse an identifier for changed semantics |
| `RID-002` | terminology | `TRM-*` | additions append numerically |
| `RID-003` | scalar types | `SCL-*` | scalar grammar change requires new specification revision |
| `RID-004` | reusable and closed types | `CLS-*`, `TYP-*`, `PAK-*`, `PSO-*`, `OLS-*`, `PSS-*`, `PSA-*`, `AKY-*` | membership or key-contract change requires new specification revision |
| `RID-005` | artifact inventory and keys | `ART-*`, `KEY-*` | identifier and derivation semantics are immutable within V1 |
| `RID-006` | ownership | `OWN-*` | owner change requires new specification revision |
| `RID-007` | schemas | `SCH-<schema>-*` | field ID remains bound to one exact field |
| `RID-008` | serialization | `SER-*` | ordering remains stable |
| `RID-009` | storage, results, and persistence | `STR-*`, `EXC-*`, `RSF-*`, `RVR-*`, `EVR-*`, `MVR-*`, `DVR-*`, `QVR-*`, `OBJ-*`, `PST-*` | operation or field ID remains bound to one exact boundary |
| `RID-010` | lower failures, validation, and Protocol consumption | `PFC-*`, `FAM-*`, `VAL-*`, `CON-*` | ID remains bound to one exact lower fact or consumption rule |
| `RID-011` | Protocol error wire encoding | `ERR-*` | each referenced Protocol symbol and serialized value is immutable |
| `RID-012` | Protocol semantic consumption | `PSC-*` | each identifier remains bound to one exact frozen Protocol authority |
| `RID-013` | verification | `VER-*` | a verification row maps to exactly one normative requirement; a requirement may have multiple concrete rows |

## 14. Verification matrix

| Verification ID | Requirement ID | Concrete input fixture | Concrete operation | Exact result status | Exact result payload/nullability | Exact failure enum or null | Exact authority | Exact cleanup |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `VER-SCP-001-001` | `SCP-001` | package imported with fake store call count 0 | exercise the stated scope boundary | COMPLETED | null | null | NONE | NONE |
| `VER-SCP-002-001` | `SCP-002` | package imported with fake store call count 0 | exercise the stated scope boundary | COMPLETED | null | null | NONE | NONE |
| `VER-SCP-003-001` | `SCP-003` | package imported with fake store call count 0 | exercise the stated scope boundary | COMPLETED | null | null | NONE | NONE |
| `VER-SCP-004-001` | `SCP-004` | package imported with fake store call count 0 | exercise the stated scope boundary | COMPLETED | null | null | NONE | NONE |
| `VER-TRM-001-001` | `TRM-001` | fixture for term `artifact` | exercise the named role in an in-memory store | COMPLETED | immutable role result | null | PRIOR | NONE |
| `VER-TRM-002-001` | `TRM-002` | fixture for term `artifact identifier` | exercise the named role in an in-memory store | COMPLETED | immutable role result | null | PRIOR | NONE |
| `VER-TRM-003-001` | `TRM-003` | fixture for term `authoritative` | exercise the named role in an in-memory store | COMPLETED | immutable role result | null | PRIOR | NONE |
| `VER-TRM-004-001` | `TRM-004` | fixture for term `audit-only` | exercise the named role in an in-memory store | COMPLETED | immutable role result | null | PRIOR | NONE |
| `VER-TRM-005-001` | `TRM-005` | fixture for term `PersistentStore` | exercise the named role in an in-memory store | COMPLETED | immutable role result | null | PRIOR | NONE |
| `VER-TRM-006-001` | `TRM-006` | injected persistence writer fixture | construct, validate, serialize, publish, and reconstruct one artifact | COMPLETED | immutable persistence result | null | PRIOR | Protocol-owned; zero local cleanup decision |
| `VER-TRM-007-001` | `TRM-007` | injected persistence reader fixture | read one reconstructed immutable artifact | COMPLETED | immutable persistence result | null | PRIOR | NONE |
| `VER-TRM-008-001` | `TRM-008` | fixture for term `reconstruction` | exercise the named role in an in-memory store | COMPLETED | immutable role result | null | PRIOR | NONE |
| `VER-SCL-001-001` | `SCL-001` | value `windows-update-state` | construct `SchemaIdentifier` | COMPLETED | exact input `windows-update-state` | null | NONE | NONE |
| `VER-SCL-002-001` | `SCL-002` | value `1` | construct `SchemaVersion` | COMPLETED | exact input `1` | null | NONE | NONE |
| `VER-SCL-003-001` | `SCL-003` | value `1` | construct `ProtocolVersion` | COMPLETED | exact input `1` | null | NONE | NONE |
| `VER-SCL-004-001` | `SCL-004` | value `00000000000000000000000000000000` | construct `OperationId` | COMPLETED | exact input `00000000000000000000000000000000` | null | NONE | NONE |
| `VER-SCL-005-001` | `SCL-005` | value `windows-update-state-v1` | construct `ArtifactKeyV1` | COMPLETED | exact input `windows-update-state-v1` | null | NONE | NONE |
| `VER-SCL-006-001` | `SCL-006` | value `1` | construct `ManifestSequence` | COMPLETED | exact input `1` | null | NONE | NONE |
| `VER-SCL-007-001` | `SCL-007` | value `0000000000000000000000000000000000000000000000000000000000000000` | construct `SHA256` | COMPLETED | exact input `0000000000000000000000000000000000000000000000000000000000000000` | null | NONE | NONE |
| `VER-SCL-008-001` | `SCL-008` | value `2026-08-06T12:34:56Z` | construct `RFC3339Timestamp` | COMPLETED | exact input `2026-08-06T12:34:56Z` | null | NONE | NONE |
| `VER-SCL-009-001` | `SCL-009` | value `0` | construct `MonotonicDuration` | COMPLETED | exact input `0` | null | NONE | NONE |
| `VER-SCL-010-001` | `SCL-010` | value `1` | construct `FileSize` | COMPLETED | exact input `1` | null | NONE | NONE |
| `VER-SCL-011-001` | `SCL-011` | value `1` | construct `Pid` | COMPLETED | exact input `1` | null | NONE | NONE |
| `VER-SCL-012-001` | `SCL-012` | value `0` | construct `FileTime` | COMPLETED | exact input `0` | null | NONE | NONE |
| `VER-SCL-013-001` | `SCL-013` | value `cache/../setup.exe` | construct `PathKey` | COMPLETED | exact input `cache/../setup.exe` | null | NONE | NONE |
| `VER-SCL-013-002` | `SCL-013` | value `/` | construct and round-trip `PathKey` | COMPLETED | exact input `/` | null | NONE | NONE |
| `VER-SCL-013-003` | `SCL-013` | value `\` | construct and round-trip `PathKey` | COMPLETED | exact input `\` | null | NONE | NONE |
| `VER-SCL-013-004` | `SCL-013` | value `..` | construct and round-trip `PathKey` | COMPLETED | exact input `..` | null | NONE | NONE |
| `VER-SCL-014-001` | `SCL-014` | value `release-2026.08` | construct `StableVersionV1` | COMPLETED | exact input `release-2026.08` | null | NONE | NONE |
| `VER-SCL-014-006` | `SCL-014` | one-byte ASCII value `x` | construct and round-trip `StableVersionV1` | COMPLETED | exact input `x` | null | NONE | NONE |
| `VER-SCL-014-007` | `SCL-014` | 128-byte ASCII value | construct and round-trip `StableVersionV1` | COMPLETED | exact 128-byte input | null | NONE | NONE |
| `VER-SCL-014-008` | `SCL-014` | empty string | construct `StableVersionV1` | REJECTED | null | INVALID_VALUE | NONE | NONE |
| `VER-SCL-014-009` | `SCL-014` | 129-byte ASCII value | construct `StableVersionV1` | REJECTED | null | INVALID_VALUE | NONE | NONE |
| `VER-SCL-014-010` | `SCL-014` | non-ASCII value `é` | construct `StableVersionV1` | REJECTED | null | INVALID_VALUE | NONE | NONE |
| `VER-SCL-015-001` | `SCL-015` | value `Publisher S.A.` | construct `PrintableIdentity` | COMPLETED | exact input `Publisher S.A.` | null | NONE | NONE |
| `VER-SCL-016-001` | `SCL-016` | value `volume-42` | construct `StorageIdentity` | COMPLETED | exact input `volume-42` | null | NONE | NONE |
| `VER-SCL-017-001` | `SCL-017` | value `true` | construct `StrictBoolean` | COMPLETED | exact input `true` | null | NONE | NONE |
| `VER-SCL-018-001` | `SCL-018` | value `UPDATE_STATE_MALFORMED` | construct `ProtocolErrorCode` | COMPLETED | exact input `UPDATE_STATE_MALFORMED` | null | NONE | NONE |
| `VER-CLS-001-001` | `CLS-001` | foreign alias completed for PersistentStoreStatusV1 | construct closed status enum | REJECTED | null | CONTRACT_INVALID_RESULT | NONE | NONE |
| `VER-PAK-001-001` | `PAK-001` | member `UPDATE_STATE` | construct and serialize PersistentArtifactKindV1 | COMPLETED | `UPDATE_STATE` | null | NONE | NONE |
| `VER-PAK-002-001` | `PAK-002` | member `HANDOFF_RECEIPT` | construct and serialize PersistentArtifactKindV1 | COMPLETED | `HANDOFF_RECEIPT` | null | NONE | NONE |
| `VER-PAK-003-001` | `PAK-003` | member `HEALTH_RECEIPT` | construct and serialize PersistentArtifactKindV1 | COMPLETED | `HEALTH_RECEIPT` | null | NONE | NONE |
| `VER-PAK-004-001` | `PAK-004` | member `RETAINED_INSTALLER_BYTES` | construct and serialize PersistentArtifactKindV1 | COMPLETED | `RETAINED_INSTALLER_BYTES` | null | NONE | NONE |
| `VER-PAK-005-001` | `PAK-005` | foreign member DIAGNOSTIC_RECEIPT | construct PersistentArtifactKindV1 | REJECTED | null | null | NONE | NONE |
| `VER-PSO-001-001` | `PSO-001` | member `READ` | construct and serialize PersistentStoreOperationV1 | COMPLETED | `READ` | null | NONE | NONE |
| `VER-PSO-002-001` | `PSO-002` | member `EXISTS` | construct and serialize PersistentStoreOperationV1 | COMPLETED | `EXISTS` | null | NONE | NONE |
| `VER-PSO-003-001` | `PSO-003` | member `CREATE` | construct and serialize PersistentStoreOperationV1 | COMPLETED | `CREATE` | null | NONE | NONE |
| `VER-PSO-004-001` | `PSO-004` | member `REPLACE` | construct and serialize PersistentStoreOperationV1 | COMPLETED | `REPLACE` | null | NONE | NONE |
| `VER-PSO-005-001` | `PSO-005` | member `DELETE` | construct and serialize PersistentStoreOperationV1 | COMPLETED | `DELETE` | null | NONE | NONE |
| `VER-PSO-006-001` | `PSO-006` | member `QUARANTINE` | construct and serialize PersistentStoreOperationV1 | COMPLETED | `QUARANTINE` | null | NONE | NONE |
| `VER-PSO-007-001` | `PSO-007` | foreign member UPSERT | construct PersistentStoreOperationV1 | REJECTED | null | null | NONE | NONE |
| `VER-OLS-001-001` | `OLS-001` | operation `READ` with status `COMPLETED` | construct operation result | COMPLETED | operation result | null | NONE | NONE |
| `VER-OLS-002-001` | `OLS-002` | operation `EXISTS` with status `COMPLETED` | construct operation result | COMPLETED | operation result | null | NONE | NONE |
| `VER-OLS-003-001` | `OLS-003` | operation `CREATE` with status `COMPLETED` | construct operation result | COMPLETED | operation result | null | NONE | NONE |
| `VER-OLS-004-001` | `OLS-004` | operation `REPLACE` with status `COMPLETED` | construct operation result | COMPLETED | operation result | null | NONE | NONE |
| `VER-OLS-005-001` | `OLS-005` | operation `DELETE` with status `COMPLETED` | construct operation result | COMPLETED | operation result | null | NONE | NONE |
| `VER-OLS-006-001` | `OLS-006` | operation `QUARANTINE` with status `COMPLETED` | construct operation result | COMPLETED | operation result | null | NONE | NONE |
| `VER-OLS-007-001` | `OLS-007` | EXISTS result with status NOT_FOUND | construct operation result | REJECTED | null | null | NONE | NONE |
| `VER-PSS-001-001` | `PSS-001` | member `COMPLETED` | construct and serialize PersistentStoreStatusV1 | COMPLETED | `COMPLETED` | null | NONE | NONE |
| `VER-PSS-002-001` | `PSS-002` | member `NOT_FOUND` | construct and serialize PersistentStoreStatusV1 | COMPLETED | `NOT_FOUND` | null | NONE | NONE |
| `VER-PSS-003-001` | `PSS-003` | member `FAILED` | construct and serialize PersistentStoreStatusV1 | COMPLETED | `FAILED` | null | NONE | NONE |
| `VER-PSS-004-001` | `PSS-004` | foreign member SUCCESS | construct PersistentStoreStatusV1 | REJECTED | null | null | NONE | NONE |
| `VER-PSA-001-001` | `PSA-001` | member `NONE` | construct and serialize PersistentStoreAuthorityV1 | COMPLETED | `NONE` | null | NONE | NONE |
| `VER-PSA-002-001` | `PSA-002` | member `PRIOR` | construct and serialize PersistentStoreAuthorityV1 | COMPLETED | `PRIOR` | null | NONE | NONE |
| `VER-PSA-003-001` | `PSA-003` | member `NEW` | construct and serialize PersistentStoreAuthorityV1 | COMPLETED | `NEW` | null | NONE | NONE |
| `VER-PSA-004-001` | `PSA-004` | foreign member CURRENT | construct PersistentStoreAuthorityV1 | REJECTED | null | null | NONE | NONE |
| `VER-AKY-001-001` | `AKY-001` | key cache/../setup.exe | construct twice and compare exact code points | COMPLETED | cache/../setup.exe twice | null | NONE | NONE |
| `VER-AKY-002-001` | `AKY-002` | key cache/../setup.exe | construct twice and compare exact code points | COMPLETED | cache/../setup.exe twice | null | NONE | NONE |
| `VER-AKY-003-001` | `AKY-003` | key cache/../setup.exe | construct twice and compare exact code points | COMPLETED | cache/../setup.exe twice | null | NONE | NONE |
| `VER-AKY-004-001` | `AKY-004` | key cache/../setup.exe | construct twice and compare exact code points | COMPLETED | cache/../setup.exe twice | null | NONE | NONE |
| `VER-AKY-004-002` | `AKY-004` | derive all four artifact identities plus two distinct retained-installer operation IDs | derive each key once | COMPLETED | six pairwise-distinct keys | null | NONE | NONE |
| `VER-AKY-004-003` | `AKY-004` | injected composition mapping two distinct artifact identities to one key | validate composition before store access | REJECTED | null; zero store calls | INVALID_KEY | NONE | NONE |
| `VER-AKY-005-001` | `AKY-005` | key cache/../setup.exe | construct twice and compare exact code points | COMPLETED | cache/../setup.exe twice | null | NONE | NONE |
| `VER-TYP-001-001` | `TYP-001` | representative value for `Nullable<T>` | construct the named reusable type | COMPLETED | accepts only null or a fully valid `T` | null | NONE | NONE |
| `VER-TYP-002-001` | `TYP-002` | representative value for `UpdateState` | construct the named reusable type | COMPLETED | `IDLE`, `CHECKING_STARTUP`, `CHECKING_MANUAL`, `UPDATE_AVAILABLE`, `DOWNLOADING`, `DOWNLOAD_CANCELLED`, `VERIFIED`, `INSTALL_PENDING`, `FAILED` | null | NONE | NONE |
| `VER-TYP-003-001` | `TYP-003` | representative value for `HandoffOutcome` | construct the named reusable type | COMPLETED | `PREPARED`, `LAUNCHED`, `CANCELLED`, `LAUNCH_FAILED` | null | NONE | NONE |
| `VER-TYP-004-001` | `TYP-004` | representative value for `HealthStage` | construct the named reusable type | COMPLETED | `STARTED`, `VERSION_VALIDATED`, `RESOURCES_VALIDATED`, `PATHS_VALIDATED`, `DATA_VALIDATED`, `INSTANCE_INITIALIZED`, `COMPLETE` | null | NONE | NONE |
| `VER-TYP-005-001` | `TYP-005` | representative value for `HealthOutcome` | construct the named reusable type | COMPLETED | `PENDING`, `HEALTHY`, `UNHEALTHY`, `ABANDONED` | null | NONE | NONE |
| `VER-TYP-006-001` | `TYP-006` | representative value for `HandoffFailureCode` | construct the named reusable type | COMPLETED | `HANDOFF_PROCESS_IDENTITY_UNAVAILABLE`, `INSTALLER_PROCESS_START_FAILED` | null | NONE | NONE |
| `VER-TYP-007-001` | `TYP-007` | representative value for `HealthFailureCode` | construct the named reusable type | COMPLETED | `HEALTH_VALIDATION_FAILED`, `HEALTH_VALIDATION_TIMEOUT`, `HEALTH_VALIDATION_INTERRUPTED` | null | NONE | NONE |
| `VER-TYP-008-001` | `TYP-008` | representative value for `RetainedFailureCode` | construct the named reusable type | COMPLETED | `UPDATE_STATE_PERSISTENCE_FAILED`, `HANDOFF_RECEIPT_MISSING`, `HANDOFF_RECEIPT_PERSISTENCE_FAILED`, `HANDOFF_PROCESS_IDENTITY_UNAVAILABLE`, `INSTALLER_PROCESS_START_FAILED`, `INSTALLER_RECEIPT_TIMEOUT`, `INSTALLER_MUTEX_TIMEOUT` | null | NONE | NONE |
| `VER-TYP-009-001` | `TYP-009` | members COMPLETED, NOT_FOUND, FAILED, then foreign SUCCESS | construct each value | three COMPLETED then REJECTED | exactly `PSS-001..003`; `PSS-004` contributes no value | null | NONE | NONE |
| `VER-TYP-010-001` | `TYP-010` | members NONE, PRIOR, NEW, then foreign CURRENT | construct each value | three COMPLETED then REJECTED | exactly `PSA-001..003`; `PSA-004` contributes no value | null | NONE | NONE |
| `VER-TYP-011-001` | `TYP-011` | representative value for reserved | construct the named reusable type | COMPLETED | no type authority; identifier retained and permanently unavailable | null | NONE | NONE |
| `VER-TYP-012-001` | `TYP-012` | representative value for `CanonicalBytesV1` | construct the named reusable type | COMPLETED | complete nonempty canonical bytes accepted by Section 8; retained installer bytes use immutable bytes without JSON canonicalization | null | NONE | NONE |
| `VER-TYP-013-001` | `TYP-013` | representative value for reserved | construct the named reusable type | COMPLETED | no type authority; identifier retained and permanently unavailable | null | NONE | NONE |
| `VER-TYP-014-001` | `TYP-014` | representative value for store result records | construct the named reusable type | COMPLETED | exact field and validity tables in Section 9 | null | NONE | NONE |
| `VER-ART-001-001` | `ART-001` | artifact kind `UPDATE_STATE` | resolve inventory contract | COMPLETED | schema=`windows-update-state`, version 1; key=`KEY-001` | null | PRIOR | NONE |
| `VER-ART-002-001` | `ART-002` | artifact kind `HANDOFF_RECEIPT` | resolve inventory contract | COMPLETED | schema=`windows-installer-handoff`, version 1; key=`KEY-002` | null | PRIOR | NONE |
| `VER-ART-003-001` | `ART-003` | artifact kind `HEALTH_RECEIPT` | resolve inventory contract | COMPLETED | schema=`windows-update-health`, version 1; key=`KEY-003` | null | PRIOR | NONE |
| `VER-ART-004-001` | `ART-004` | artifact kind `RETAINED_INSTALLER_BYTES` | resolve inventory contract | COMPLETED | schema=immutable opaque bytes identified by retained record; key=`KEY-004` | null | PRIOR | NONE |
| `VER-KEY-001-001` | `KEY-001` | parameters `UPDATE_STATE`, operation ID null | invoke derive_key twice | COMPLETED | `ArtifactKeyV1("windows-update-state-v1")` twice with exact equality | null | NONE | NONE |
| `VER-KEY-002-001` | `KEY-002` | parameters `HANDOFF_RECEIPT`, operation ID null | invoke derive_key twice | COMPLETED | `ArtifactKeyV1("windows-installer-handoff-v1")` twice with exact equality | null | NONE | NONE |
| `VER-KEY-003-001` | `KEY-003` | parameters `HEALTH_RECEIPT`, operation ID null | invoke derive_key twice | COMPLETED | `ArtifactKeyV1("windows-update-health-v1")` twice with exact equality | null | NONE | NONE |
| `VER-KEY-004-001` | `KEY-004` | parameters `RETAINED_INSTALLER_BYTES`, non-null `OperationId` | invoke derive_key twice | COMPLETED | `ArtifactKeyV1("windows-retained-installer-" + operation_id)` twice with exact equality | null | NONE | NONE |
| `VER-OWN-001-001` | `OWN-001` | artifact `UPDATE_STATE` with injected persistence writer and reader | perform one write, one read, one reconstruction | COMPLETED | persistence writer, reader, and reconstruction owner | null | PRIOR | frozen Protocol V6; store private temporaries only |
| `VER-OWN-002-001` | `OWN-002` | retained installer record nested in `UPDATE_STATE` with injected persistence writer and reader | perform one write, one read, one reconstruction | COMPLETED | persistence writer and reader; reconstruction with update state only | null | PRIOR | frozen Protocol V6; store private temporaries only |
| `VER-OWN-003-001` | `OWN-003` | artifact `RETAINED_INSTALLER_BYTES` with injected persistence writer and reader | perform one write and one read | COMPLETED | writer admits one immutable identity; identity comes only from retained record | null | PRIOR | frozen Protocol V6 requests one identity-checked delete |
| `VER-OWN-004-001` | `OWN-004` | artifact `HANDOFF_RECEIPT` with injected persistence writer and reader | perform one write, one read, one reconstruction | COMPLETED | persistence writer, reader, and reconstruction owner | null | PRIOR | frozen Protocol V6; store private temporaries only |
| `VER-OWN-005-001` | `OWN-005` | artifact `HEALTH_RECEIPT` with injected persistence writer and reader | perform one write, one read, one reconstruction | COMPLETED | persistence writer, reader, and reconstruction owner | null | PRIOR | frozen Protocol V6; store private temporaries only |
| `VER-SCH-UF-001-001` | `SCH-UF-001` | `UpdateStateFileV1`.`schema`=windows-update-state | reconstruct exact schema fixture | COMPLETED | field=windows-update-state; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-UF-002-001` | `SCH-UF-002` | `UpdateStateFileV1`.`schema_version`=1 | reconstruct exact schema fixture | COMPLETED | field=1; JSON=integer; nullable=never | null | PRIOR | NONE |
| `VER-SCH-UF-003-001` | `SCH-UF-003` | `UpdateStateFileV1`.`update_state`={state:IDLE,current_version:release-2026.08,latest_version:null,active_operation_id:null,active_manifest_sequence:null,active_manifest_sha256:null,failure_code:null,notification_shown:false,retained_installer:null} | reconstruct exact schema fixture | COMPLETED | field={state:IDLE,current_version:release-2026.08,latest_version:null,active_operation_id:null,active_manifest_sequence:null,active_manifest_sha256:null,failure_code:null,notification_shown:false,retained_installer:null}; JSON=object; nullable=never | null | PRIOR | NONE |
| `VER-SCH-US-001-001` | `SCH-US-001` | `UpdateStateV1`.`state`=IDLE | reconstruct exact schema fixture | COMPLETED | field=IDLE; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-US-002-001` | `SCH-US-002` | `UpdateStateV1`.`current_version`=release-2026.08 | reconstruct exact schema fixture | COMPLETED | field=release-2026.08; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-US-003-001` | `SCH-US-003` | `UpdateStateV1`.`latest_version`=release-2026.08 | reconstruct exact schema fixture | COMPLETED | field=release-2026.08; JSON=string; nullable=allowed | null | PRIOR | NONE |
| `VER-SCH-US-004-001` | `SCH-US-004` | `UpdateStateV1`.`active_operation_id`=00000000000000000000000000000000 | reconstruct exact schema fixture | COMPLETED | field=00000000000000000000000000000000; JSON=string; nullable=allowed | null | PRIOR | NONE |
| `VER-SCH-US-005-001` | `SCH-US-005` | `UpdateStateV1`.`active_manifest_sequence`=1 | reconstruct exact schema fixture | COMPLETED | field=1; JSON=integer; nullable=allowed | null | PRIOR | NONE |
| `VER-SCH-US-006-001` | `SCH-US-006` | `UpdateStateV1`.`active_manifest_sha256`=0000000000000000000000000000000000000000000000000000000000000000 | reconstruct exact schema fixture | COMPLETED | field=0000000000000000000000000000000000000000000000000000000000000000; JSON=string; nullable=allowed | null | PRIOR | NONE |
| `VER-SCH-US-007-001` | `SCH-US-007` | `UpdateStateV1`.`failure_code`=UPDATE_STATE_MALFORMED | reconstruct exact schema fixture | COMPLETED | field=UPDATE_STATE_MALFORMED; JSON=string; nullable=allowed | null | PRIOR | NONE |
| `VER-SCH-US-008-001` | `SCH-US-008` | `UpdateStateV1`.`notification_shown`=false | reconstruct exact schema fixture | COMPLETED | field=false; JSON=boolean; nullable=never | null | PRIOR | NONE |
| `VER-SCH-US-009-001` | `SCH-US-009` | `UpdateStateV1`.`retained_installer`={version:release-2026.08,...exact retained fields} | reconstruct exact schema fixture | COMPLETED | field={version:release-2026.08,...exact retained fields}; JSON=object; nullable=allowed | null | PRIOR | NONE |
| `VER-SCH-RI-001-001` | `SCH-RI-001` | `RetainedVerifiedInstallerV1`.`version`=release-2026.08 | reconstruct exact schema fixture | COMPLETED | field=release-2026.08; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-RI-002-001` | `SCH-RI-002` | `RetainedVerifiedInstallerV1`.`manifest_sequence`=1 | reconstruct exact schema fixture | COMPLETED | field=1; JSON=integer; nullable=never | null | PRIOR | NONE |
| `VER-SCH-RI-003-001` | `SCH-RI-003` | `RetainedVerifiedInstallerV1`.`manifest_sha256`=0000000000000000000000000000000000000000000000000000000000000000 | reconstruct exact schema fixture | COMPLETED | field=0000000000000000000000000000000000000000000000000000000000000000; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-RI-004-001` | `SCH-RI-004` | `RetainedVerifiedInstallerV1`.`installer_key`=cache/../setup.exe | reconstruct exact schema fixture | COMPLETED | field=cache/../setup.exe; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-RI-005-001` | `SCH-RI-005` | `RetainedVerifiedInstallerV1`.`installer_size`=1 | reconstruct exact schema fixture | COMPLETED | field=1; JSON=integer; nullable=never | null | PRIOR | NONE |
| `VER-SCH-RI-006-001` | `SCH-RI-006` | `RetainedVerifiedInstallerV1`.`installer_sha256`=0000000000000000000000000000000000000000000000000000000000000000 | reconstruct exact schema fixture | COMPLETED | field=0000000000000000000000000000000000000000000000000000000000000000; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-RI-007-001` | `SCH-RI-007` | `RetainedVerifiedInstallerV1`.`verified_at`=2026-08-06T12:34:56Z | reconstruct exact schema fixture | COMPLETED | field=2026-08-06T12:34:56Z; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-RI-008-001` | `SCH-RI-008` | `RetainedVerifiedInstallerV1`.`publisher_subject`=Publisher S.A. | reconstruct exact schema fixture | COMPLETED | field=Publisher S.A.; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-RI-009-001` | `SCH-RI-009` | `RetainedVerifiedInstallerV1`.`leaf_certificate_sha256`=0000000000000000000000000000000000000000000000000000000000000000 | reconstruct exact schema fixture | COMPLETED | field=0000000000000000000000000000000000000000000000000000000000000000; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-RI-010-001` | `SCH-RI-010` | `RetainedVerifiedInstallerV1`.`signature_timestamp`=2026-08-06T12:34:56Z | reconstruct exact schema fixture | COMPLETED | field=2026-08-06T12:34:56Z; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-RI-011-001` | `SCH-RI-011` | `RetainedVerifiedInstallerV1`.`storage_identity`=volume-42 | reconstruct exact schema fixture | COMPLETED | field=volume-42; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-HR-001-001` | `SCH-HR-001` | `InstallerHandoffReceiptV1`.`schema`=windows-update-state | reconstruct exact schema fixture | COMPLETED | field=windows-update-state; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-HR-002-001` | `SCH-HR-002` | `InstallerHandoffReceiptV1`.`schema_version`=1 | reconstruct exact schema fixture | COMPLETED | field=1; JSON=integer; nullable=never | null | PRIOR | NONE |
| `VER-SCH-HR-003-001` | `SCH-HR-003` | `InstallerHandoffReceiptV1`.`operation_id`=00000000000000000000000000000000 | reconstruct exact schema fixture | COMPLETED | field=00000000000000000000000000000000; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-HR-004-001` | `SCH-HR-004` | `InstallerHandoffReceiptV1`.`target_version`=release-2026.08 | reconstruct exact schema fixture | COMPLETED | field=release-2026.08; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-HR-005-001` | `SCH-HR-005` | `InstallerHandoffReceiptV1`.`manifest_sequence`=1 | reconstruct exact schema fixture | COMPLETED | field=1; JSON=integer; nullable=never | null | PRIOR | NONE |
| `VER-SCH-HR-006-001` | `SCH-HR-006` | `InstallerHandoffReceiptV1`.`manifest_sha256`=0000000000000000000000000000000000000000000000000000000000000000 | reconstruct exact schema fixture | COMPLETED | field=0000000000000000000000000000000000000000000000000000000000000000; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-HR-007-001` | `SCH-HR-007` | `InstallerHandoffReceiptV1`.`installer_key`=cache/../setup.exe | reconstruct exact schema fixture | COMPLETED | field=cache/../setup.exe; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-HR-008-001` | `SCH-HR-008` | `InstallerHandoffReceiptV1`.`installer_size`=1 | reconstruct exact schema fixture | COMPLETED | field=1; JSON=integer; nullable=never | null | PRIOR | NONE |
| `VER-SCH-HR-009-001` | `SCH-HR-009` | `InstallerHandoffReceiptV1`.`installer_sha256`=0000000000000000000000000000000000000000000000000000000000000000 | reconstruct exact schema fixture | COMPLETED | field=0000000000000000000000000000000000000000000000000000000000000000; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-HR-010-001` | `SCH-HR-010` | `InstallerHandoffReceiptV1`.`publisher_subject`=Publisher S.A. | reconstruct exact schema fixture | COMPLETED | field=Publisher S.A.; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-HR-011-001` | `SCH-HR-011` | `InstallerHandoffReceiptV1`.`consented_at`=2026-08-06T12:34:56Z | reconstruct exact schema fixture | COMPLETED | field=2026-08-06T12:34:56Z; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-HR-012-001` | `SCH-HR-012` | `InstallerHandoffReceiptV1`.`launch_attempted_at`=2026-08-06T12:34:56Z | reconstruct exact schema fixture | COMPLETED | field=2026-08-06T12:34:56Z; JSON=string; nullable=allowed | null | PRIOR | NONE |
| `VER-SCH-HR-013-001` | `SCH-HR-013` | `InstallerHandoffReceiptV1`.`process_id`=1 | reconstruct exact schema fixture | COMPLETED | field=1; JSON=integer; nullable=allowed | null | PRIOR | NONE |
| `VER-SCH-HR-014-001` | `SCH-HR-014` | `InstallerHandoffReceiptV1`.`process_creation_time`=0 | reconstruct exact schema fixture | COMPLETED | field=0; JSON=integer; nullable=allowed | null | PRIOR | NONE |
| `VER-SCH-HR-015-001` | `SCH-HR-015` | `InstallerHandoffReceiptV1`.`outcome`=PREPARED | reconstruct exact schema fixture | COMPLETED | field=PREPARED; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-HR-016-001` | `SCH-HR-016` | `InstallerHandoffReceiptV1`.`failure_code`=INSTALLER_PROCESS_START_FAILED | reconstruct exact schema fixture | COMPLETED | field=INSTALLER_PROCESS_START_FAILED; JSON=string; nullable=allowed | null | PRIOR | NONE |
| `VER-SCH-HL-001-001` | `SCH-HL-001` | `HealthReceiptV1`.`schema`=windows-update-state | reconstruct exact schema fixture | COMPLETED | field=windows-update-state; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-HL-002-001` | `SCH-HL-002` | `HealthReceiptV1`.`schema_version`=1 | reconstruct exact schema fixture | COMPLETED | field=1; JSON=integer; nullable=never | null | PRIOR | NONE |
| `VER-SCH-HL-003-001` | `SCH-HL-003` | `HealthReceiptV1`.`operation_id`=00000000000000000000000000000000 | reconstruct exact schema fixture | COMPLETED | field=00000000000000000000000000000000; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-HL-004-001` | `SCH-HL-004` | `HealthReceiptV1`.`installed_version`=release-2026.08 | reconstruct exact schema fixture | COMPLETED | field=release-2026.08; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-HL-005-001` | `SCH-HL-005` | `HealthReceiptV1`.`expected_version`=release-2026.08 | reconstruct exact schema fixture | COMPLETED | field=release-2026.08; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-HL-006-001` | `SCH-HL-006` | `HealthReceiptV1`.`manifest_sequence`=1 | reconstruct exact schema fixture | COMPLETED | field=1; JSON=integer; nullable=never | null | PRIOR | NONE |
| `VER-SCH-HL-007-001` | `SCH-HL-007` | `HealthReceiptV1`.`installer_sha256`=0000000000000000000000000000000000000000000000000000000000000000 | reconstruct exact schema fixture | COMPLETED | field=0000000000000000000000000000000000000000000000000000000000000000; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-HL-008-001` | `SCH-HL-008` | `HealthReceiptV1`.`stage`=STARTED | reconstruct exact schema fixture | COMPLETED | field=STARTED; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-HL-009-001` | `SCH-HL-009` | `HealthReceiptV1`.`outcome`=PENDING | reconstruct exact schema fixture | COMPLETED | field=PENDING; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-HL-010-001` | `SCH-HL-010` | `HealthReceiptV1`.`started_at`=2026-08-06T12:34:56Z | reconstruct exact schema fixture | COMPLETED | field=2026-08-06T12:34:56Z; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-HL-011-001` | `SCH-HL-011` | `HealthReceiptV1`.`deadline_at`=2026-08-06T12:34:56Z | reconstruct exact schema fixture | COMPLETED | field=2026-08-06T12:34:56Z; JSON=string; nullable=never | null | PRIOR | NONE |
| `VER-SCH-HL-012-001` | `SCH-HL-012` | `HealthReceiptV1`.`completed_at`=2026-08-06T12:34:56Z | reconstruct exact schema fixture | COMPLETED | field=2026-08-06T12:34:56Z; JSON=string; nullable=allowed | null | PRIOR | NONE |
| `VER-SCH-HL-013-001` | `SCH-HL-013` | `HealthReceiptV1`.`failure_code`=HEALTH_VALIDATION_FAILED | reconstruct exact schema fixture | COMPLETED | field=HEALTH_VALIDATION_FAILED; JSON=string; nullable=allowed | null | PRIOR | NONE |
| `VER-SCH-HL-014-001` | `SCH-HL-014` | `HealthReceiptV1`.`recovery_offered`=false | reconstruct exact schema fixture | COMPLETED | field=false; JSON=boolean; nullable=never | null | PRIOR | NONE |
| `VER-SER-001-001` | `SER-001` | UpdateStateFileV1 fixture violating only the named serialization stage | apply exact wire rule; assert dispatch key `SAP-003` and zero local semantic result | REJECTED | exact failed wire stage | Protocol reference `SEM-003` | Protocol reference `SEM-003` | Protocol reference `SEM-003` |
| `VER-SER-002-001` | `SER-002` | UpdateStateFileV1 fixture violating only the named serialization stage | apply exact wire rule; assert dispatch key `SAP-003` and zero local semantic result | REJECTED | exact failed wire stage | Protocol reference `SEM-003` | Protocol reference `SEM-003` | Protocol reference `SEM-003` |
| `VER-SER-003-001` | `SER-003` | UpdateStateFileV1 fixture violating only the named serialization stage | apply exact wire rule; assert dispatch key `SAP-003` and zero local semantic result | REJECTED | exact failed wire stage | Protocol reference `SEM-003` | Protocol reference `SEM-003` | Protocol reference `SEM-003` |
| `VER-SER-004-001` | `SER-004` | UpdateStateFileV1 fixture violating only the named serialization stage | apply exact wire rule; assert dispatch key `SAP-003` and zero local semantic result | REJECTED | exact failed wire stage | Protocol reference `SEM-003` | Protocol reference `SEM-003` | Protocol reference `SEM-003` |
| `VER-SER-005-001` | `SER-005` | UpdateStateFileV1 fixture violating only the named serialization stage | apply exact wire rule; assert dispatch key `SAP-003` and zero local semantic result | REJECTED | exact failed wire stage | Protocol reference `SEM-003` | Protocol reference `SEM-003` | Protocol reference `SEM-003` |
| `VER-SER-006-001` | `SER-006` | UpdateStateFileV1 fixture violating only the named serialization stage | apply exact wire rule; assert dispatch key `SAP-003` and zero local semantic result | REJECTED | exact failed wire stage | Protocol reference `SEM-003` | Protocol reference `SEM-003` | Protocol reference `SEM-003` |
| `VER-SER-007-001` | `SER-007` | UpdateStateFileV1 fixture violating only the named serialization stage | apply exact wire rule; assert dispatch key `SAP-003` and zero local semantic result | REJECTED | exact failed wire stage | Protocol reference `SEM-003` | Protocol reference `SEM-003` | Protocol reference `SEM-003` |
| `VER-SER-008-001` | `SER-008` | two independently reconstructed equal `UpdateStateFileV1` values | apply canonical equality rule; assert zero Protocol dispatch | COMPLETED | byte-identical canonical UTF-8 JCS | null | NONE | NONE |
| `VER-STR-001-001` | `STR-001` | injected passive PersistentStoreV1 fake with call count 0 | construct capability | COMPLETED | immutable capability | null | NONE | NONE |
| `VER-STR-002-001` | `STR-002` | fake store fixture for read | invoke the exact keyword-only signature once | COMPLETED | `read(*, key: ArtifactKeyV1) -> StoreReadResultV1` | null | `PRIOR` | none |
| `VER-STR-003-001` | `STR-003` | fake store fixture for exists | invoke the exact keyword-only signature once | COMPLETED | `exists(*, key: ArtifactKeyV1) -> StoreExistsResultV1` | null | `PRIOR` when value true; `NONE` when false | none |
| `VER-STR-004-001` | `STR-004` | fake store fixture for create | invoke the exact keyword-only signature once | COMPLETED | `create(*, key: ArtifactKeyV1, payload: CanonicalBytesV1) -> StoreMutationResultV1` | null | `NEW` | store removes private temporaries |
| `VER-STR-005-001` | `STR-005` | fake store fixture for replace | invoke the exact keyword-only signature once | COMPLETED | `replace(*, key: ArtifactKeyV1, payload: CanonicalBytesV1) -> StoreMutationResultV1` | null | `NEW` | store removes private temporaries |
| `VER-STR-006-001` | `STR-006` | fake store fixture for delete | invoke the exact keyword-only signature once | COMPLETED | `delete(*, key: ArtifactKeyV1, expected_storage_identity: Nullable<StorageIdentity>) -> StoreDeleteResultV1` | null | `NONE` | none; exactly one requested delete and zero retry |
| `VER-STR-007-001` | `STR-007` | fake store fixture for quarantine | invoke the exact keyword-only signature once | COMPLETED | `quarantine(*, key: ArtifactKeyV1, quarantine_key: ArtifactKeyV1) -> StoreQuarantineResultV1` | null | `NEW` | store removes private temporaries |
| `VER-STR-008-001` | `STR-008` | fixtures for all `EXC-001..034`, SystemExit, GeneratorExit, and unexpected RuntimeError | invoke each applicable operation once | COMPLETED | 34 finite conversions; three non-converted categories propagate unchanged | null | authority from each named EXC fixture; unchanged for propagation | store-private housekeeping from each named EXC fixture only |
| `VER-STR-004-002` | `STR-004` | destination appears after private temporary is flushed but before create publication | invoke create once | FAILED | prior destination bytes unchanged; private temporary removed | ALREADY_EXISTS | PRIOR | store-private temporary removed; zero replace fallback |
| `VER-STR-004-003` | `STR-004` | absent destination; payload write fails before publication | invoke create once | FAILED | destination remains absent; private temporary removed | WRITE_FAILED | NONE | store-private temporary removed |
| `VER-STR-004-004` | `STR-004` | absent destination; atomic create succeeds and namespace durability acknowledgement fails | invoke create once | FAILED | new destination bytes remain authoritative | DURABILITY_FAILED | NEW | store-private temporary removed; no fabricated rollback |
| `VER-STR-005-002` | `STR-005` | destination is absent at atomic replacement | invoke replace once | FAILED | destination remains absent | NOT_FOUND | NONE | zero create fallback |
| `VER-STR-005-003` | `STR-005` | prior destination exists; atomic switch fails before publication | invoke replace once | FAILED | prior destination bytes unchanged; private temporary removed | ATOMIC_PUBLICATION_FAILED | PRIOR | store-private temporary removed |
| `VER-STR-005-004` | `STR-005` | prior destination exists; atomic switch succeeds and namespace durability acknowledgement fails | invoke replace once | FAILED | new destination bytes remain authoritative | DURABILITY_FAILED | NEW | store-private temporary removed; no fabricated rollback |
| `VER-STR-006-002` | `STR-006` | destination identity differs from expected_storage_identity | invoke delete once | FAILED | destination bytes and identity unchanged | IDENTITY_MISMATCH | PRIOR | zero retry and zero Protocol cleanup selection |
| `VER-STR-007-002` | `STR-007` | source exists; quarantine publication fails before source authority changes | invoke quarantine once | FAILED | source remains authoritative; private temporary removed | QUARANTINE_FAILED | PRIOR | zero Protocol cleanup selection |
| `VER-STR-007-003` | `STR-007` | source exists; quarantine switch succeeds and namespace durability acknowledgement fails | invoke quarantine once | FAILED | quarantine destination is authoritative and source authority removed | DURABILITY_FAILED | NEW | store-private temporary removed; zero Protocol cleanup selection |
| `VER-EXC-001-001` | `EXC-001` | operation `READ`; raise `InvalidArtifactKeyError` | invoke store boundary once | `FAILED` | null | `INVALID_KEY` | `NONE` | NONE |
| `VER-EXC-002-001` | `EXC-002` | operation `READ`; raise `PermissionError` | invoke store boundary once | `FAILED` | null | `ACCESS_DENIED` | `PRIOR` | NONE |
| `VER-EXC-003-001` | `EXC-003` | operation `READ`; raise `FileNotFoundError` | invoke store boundary once | `NOT_FOUND` | null | null | `NONE` | NONE |
| `VER-EXC-004-001` | `EXC-004` | operation `READ`; raise `StoreReadIOError` | invoke store boundary once | `FAILED` | null | `READ_FAILED` | `PRIOR` | NONE |
| `VER-EXC-005-001` | `EXC-005` | operation `EXISTS`; raise `InvalidArtifactKeyError` | invoke store boundary once | `FAILED` | null | `INVALID_KEY` | `NONE` | NONE |
| `VER-EXC-006-001` | `EXC-006` | operation `EXISTS`; raise `PermissionError` | invoke store boundary once | `FAILED` | null | `ACCESS_DENIED` | `PRIOR` | NONE |
| `VER-EXC-007-001` | `EXC-007` | operation `EXISTS`; raise `FileNotFoundError` | invoke store boundary once | `COMPLETED` with exists false | false | null | `NONE` | NONE |
| `VER-EXC-008-001` | `EXC-008` | operation `EXISTS`; raise `StoreReadIOError` | invoke store boundary once | `FAILED` | null | `READ_FAILED` | `PRIOR` | NONE |
| `VER-EXC-009-001` | `EXC-009` | operation `CREATE`; raise `InvalidArtifactKeyError` | invoke store boundary once | `FAILED` | null | `INVALID_KEY` | `NONE` | NONE |
| `VER-EXC-010-001` | `EXC-010` | operation `CREATE`; raise `PermissionError` | invoke store boundary once | `FAILED` | null | `ACCESS_DENIED` | `NONE` | NONE |
| `VER-EXC-011-001` | `EXC-011` | operation `CREATE`; raise `FileExistsError` | invoke store boundary once | `FAILED` | null | `ALREADY_EXISTS` | `PRIOR` | NONE |
| `VER-EXC-012-001` | `EXC-012` | operation `CREATE`; raise `StoreWriteError` | invoke store boundary once | `FAILED` | null | `WRITE_FAILED` | `NONE` | NONE |
| `VER-EXC-013-001` | `EXC-013` | operation `CREATE`; raise `StoreFlushError` | invoke store boundary once | `FAILED` | null | `FLUSH_FAILED` | `NONE` | NONE |
| `VER-EXC-014-001` | `EXC-014` | operation `CREATE`; raise `StoreAtomicPublicationError` | invoke store boundary once | `FAILED` | null | `ATOMIC_PUBLICATION_FAILED` | `NONE` | NONE |
| `VER-EXC-015-001` | `EXC-015` | operation `CREATE`; raise `StoreDurabilityError` | invoke store boundary once | `FAILED` | null | `DURABILITY_FAILED` | `NEW` | NONE |
| `VER-EXC-016-001` | `EXC-016` | operation `REPLACE`; raise `InvalidArtifactKeyError` | invoke store boundary once | `FAILED` | null | `INVALID_KEY` | `NONE` | NONE |
| `VER-EXC-017-001` | `EXC-017` | operation `REPLACE`; raise `PermissionError` | invoke store boundary once | `FAILED` | null | `ACCESS_DENIED` | `PRIOR` | NONE |
| `VER-EXC-018-001` | `EXC-018` | operation `REPLACE`; raise `FileNotFoundError` | invoke store boundary once | `FAILED` | null | `NOT_FOUND` | `NONE` | NONE |
| `VER-EXC-019-001` | `EXC-019` | operation `REPLACE`; raise `StoreWriteError` | invoke store boundary once | `FAILED` | null | `WRITE_FAILED` | `PRIOR` | NONE |
| `VER-EXC-020-001` | `EXC-020` | operation `REPLACE`; raise `StoreFlushError` | invoke store boundary once | `FAILED` | null | `FLUSH_FAILED` | `PRIOR` | NONE |
| `VER-EXC-021-001` | `EXC-021` | operation `REPLACE`; raise `StoreAtomicPublicationError` | invoke store boundary once | `FAILED` | null | `ATOMIC_PUBLICATION_FAILED` | `PRIOR` | NONE |
| `VER-EXC-022-001` | `EXC-022` | operation `REPLACE`; raise `StoreDurabilityError` | invoke store boundary once | `FAILED` | null | `DURABILITY_FAILED` | `NEW` | NONE |
| `VER-EXC-023-001` | `EXC-023` | operation `DELETE`; raise `InvalidArtifactKeyError` | invoke store boundary once | `FAILED` | null | `INVALID_KEY` | `NONE` | NONE |
| `VER-EXC-024-001` | `EXC-024` | operation `DELETE`; raise `PermissionError` | invoke store boundary once | `FAILED` | null | `ACCESS_DENIED` | `PRIOR` | NONE |
| `VER-EXC-025-001` | `EXC-025` | operation `DELETE`; raise `FileNotFoundError` | invoke store boundary once | `NOT_FOUND` | null | null | `NONE` | NONE |
| `VER-EXC-026-001` | `EXC-026` | operation `DELETE`; raise `StoreIdentityMismatchError` | invoke store boundary once | `FAILED` | null | `IDENTITY_MISMATCH` | `PRIOR` | NONE |
| `VER-EXC-027-001` | `EXC-027` | operation `DELETE`; raise `StoreDeleteError` | invoke store boundary once | `FAILED` | null | `DELETE_FAILED` | `PRIOR` | NONE |
| `VER-EXC-028-001` | `EXC-028` | operation `QUARANTINE`; raise `InvalidArtifactKeyError` | invoke store boundary once | `FAILED` | null | `INVALID_KEY` | `NONE` | NONE |
| `VER-EXC-029-001` | `EXC-029` | operation `QUARANTINE`; raise `PermissionError` | invoke store boundary once | `FAILED` | null | `ACCESS_DENIED` | `PRIOR` | NONE |
| `VER-EXC-030-001` | `EXC-030` | operation `QUARANTINE`; raise `FileNotFoundError` | invoke store boundary once | `NOT_FOUND` | null | null | `NONE` | NONE |
| `VER-EXC-031-001` | `EXC-031` | operation `QUARANTINE`; raise `FileExistsError` | invoke store boundary once | `FAILED` | null | `ALREADY_EXISTS` | `PRIOR` | NONE |
| `VER-EXC-032-001` | `EXC-032` | operation `QUARANTINE`; raise `StoreAtomicPublicationError` | invoke store boundary once | `FAILED` | null | `ATOMIC_PUBLICATION_FAILED` | `PRIOR` | NONE |
| `VER-EXC-033-001` | `EXC-033` | operation `QUARANTINE`; raise `StoreDurabilityError` | invoke store boundary once | `FAILED` | null | `DURABILITY_FAILED` | `NEW` | NONE |
| `VER-EXC-034-001` | `EXC-034` | operation `QUARANTINE`; raise `StoreQuarantineError` | invoke store boundary once | `FAILED` | null | `QUARANTINE_FAILED` | `PRIOR` | NONE |
| `VER-EXC-035-001` | `EXC-035` | READ raises `KeyboardInterrupt` | invoke store boundary once | unconverted | null | n/a | unchanged by propagation | NONE |
| `VER-EXC-036-001` | `EXC-036` | READ raises unexpected `RuntimeError` | invoke store boundary once | unconverted | null | n/a | unchanged by propagation | NONE |
| `VER-EXC-037-001` | `EXC-037` | implementation has no generic exception conversion branch | inspect catch boundary once | COMPLETED | no generic catch | null | NONE | NONE |
| `VER-RSF-001-001` | `RSF-001` | valid `StoreReadResultV1` containing field `status` | construct through public constructor | COMPLETED | field type=`PersistentStoreStatusV1`; nullable=no | null | PRIOR | NONE |
| `VER-RSF-002-001` | `RSF-002` | valid `StoreReadResultV1` containing field `payload` | construct through public constructor | COMPLETED | field type=`Nullable<CanonicalBytesV1>`; nullable=yes | null | PRIOR | NONE |
| `VER-RSF-003-001` | `RSF-003` | valid `StoreReadResultV1` containing field `failure` | construct through public constructor | COMPLETED | field type=`Nullable<PersistentStoreFailureCodeV1>`; nullable=yes | null | PRIOR | NONE |
| `VER-RSF-004-001` | `RSF-004` | valid `StoreReadResultV1` containing field `authority` | construct through public constructor | COMPLETED | field type=`PersistentStoreAuthorityV1`; nullable=no | null | PRIOR | NONE |
| `VER-RSF-005-001` | `RSF-005` | valid `StoreExistsResultV1` containing field `status` | construct through public constructor | COMPLETED | field type=`PersistentStoreStatusV1`; nullable=no | null | PRIOR | NONE |
| `VER-RSF-006-001` | `RSF-006` | valid `StoreExistsResultV1` containing field `exists` | construct through public constructor | COMPLETED | field type=`Nullable<StrictBoolean>`; nullable=yes | null | PRIOR | NONE |
| `VER-RSF-007-001` | `RSF-007` | valid `StoreExistsResultV1` containing field `failure` | construct through public constructor | COMPLETED | field type=`Nullable<PersistentStoreFailureCodeV1>`; nullable=yes | null | PRIOR | NONE |
| `VER-RSF-008-001` | `RSF-008` | valid `StoreExistsResultV1` containing field `authority` | construct through public constructor | COMPLETED | field type=`PersistentStoreAuthorityV1`; nullable=no | null | PRIOR | NONE |
| `VER-RSF-009-001` | `RSF-009` | valid `StoreMutationResultV1` containing field `status` | construct through public constructor | COMPLETED | field type=`PersistentStoreStatusV1`; nullable=no | null | PRIOR | NONE |
| `VER-RSF-010-001` | `RSF-010` | valid `StoreMutationResultV1` containing field `failure` | construct through public constructor | COMPLETED | field type=`Nullable<PersistentStoreFailureCodeV1>`; nullable=yes | null | PRIOR | NONE |
| `VER-RSF-011-001` | `RSF-011` | valid `StoreMutationResultV1` containing field `authority` | construct through public constructor | COMPLETED | field type=`PersistentStoreAuthorityV1`; nullable=no | null | PRIOR | NONE |
| `VER-RSF-012-001` | `RSF-012` | valid `StoreDeleteResultV1` containing field `status` | construct through public constructor | COMPLETED | field type=`PersistentStoreStatusV1`; nullable=no | null | PRIOR | NONE |
| `VER-RSF-013-001` | `RSF-013` | valid `StoreDeleteResultV1` containing field `failure` | construct through public constructor | COMPLETED | field type=`Nullable<PersistentStoreFailureCodeV1>`; nullable=yes | null | PRIOR | NONE |
| `VER-RSF-014-001` | `RSF-014` | valid `StoreDeleteResultV1` containing field `authority` | construct through public constructor | COMPLETED | field type=`PersistentStoreAuthorityV1`; nullable=no | null | PRIOR | NONE |
| `VER-RSF-015-001` | `RSF-015` | valid `StoreQuarantineResultV1` containing field `status` | construct through public constructor | COMPLETED | field type=`PersistentStoreStatusV1`; nullable=no | null | PRIOR | NONE |
| `VER-RSF-016-001` | `RSF-016` | valid `StoreQuarantineResultV1` containing field `failure` | construct through public constructor | COMPLETED | field type=`Nullable<PersistentStoreFailureCodeV1>`; nullable=yes | null | PRIOR | NONE |
| `VER-RSF-017-001` | `RSF-017` | valid `StoreQuarantineResultV1` containing field `authority` | construct through public constructor | COMPLETED | field type=`PersistentStoreAuthorityV1`; nullable=no | null | PRIOR | NONE |
| `VER-RSF-018-001` | `RSF-018` | valid `StoreReadResultV1` containing field `operation` | construct through public constructor | COMPLETED | field type=`PersistentStoreOperationV1`; nullable=no | null | PRIOR | NONE |
| `VER-RSF-019-001` | `RSF-019` | valid `StoreExistsResultV1` containing field `operation` | construct through public constructor | COMPLETED | field type=`PersistentStoreOperationV1`; nullable=no | null | PRIOR | NONE |
| `VER-RSF-020-001` | `RSF-020` | valid `StoreMutationResultV1` containing field `operation` | construct through public constructor | COMPLETED | field type=`PersistentStoreOperationV1`; nullable=no | null | PRIOR | NONE |
| `VER-RSF-021-001` | `RSF-021` | valid `StoreDeleteResultV1` containing field `operation` | construct through public constructor | COMPLETED | field type=`PersistentStoreOperationV1`; nullable=no | null | PRIOR | NONE |
| `VER-RSF-022-001` | `RSF-022` | valid `StoreQuarantineResultV1` containing field `operation` | construct through public constructor | COMPLETED | field type=`PersistentStoreOperationV1`; nullable=no | null | PRIOR | NONE |
| `VER-RVR-001-001` | `RVR-001` | `StoreReadResultV1`; operation=`READ`; status=`COMPLETED`; payload=nonempty immutable bytes; failure=null; authority=`PRIOR` | construct StoreReadResultV1 | COMPLETED | nonempty immutable bytes | null | `PRIOR` | NONE |
| `VER-RVR-002-001` | `RVR-002` | `StoreReadResultV1`; operation=`READ`; status=`NOT_FOUND`; payload=null; failure=null; authority=`NONE` | construct StoreReadResultV1 | COMPLETED | null | null | `NONE` | NONE |
| `VER-RVR-003-001` | `RVR-003` | `StoreReadResultV1`; operation=`READ`; status=`FAILED`; payload=null; failure=`ACCESS_DENIED`; authority=`PRIOR` | construct StoreReadResultV1 | COMPLETED | null | `ACCESS_DENIED` | `PRIOR` | NONE |
| `VER-RVR-004-001` | `RVR-004` | `StoreReadResultV1`; operation=`READ`; status=`FAILED`; payload=null; failure=`INVALID_KEY`; authority=`NONE` | construct StoreReadResultV1 | COMPLETED | null | `INVALID_KEY` | `NONE` | NONE |
| `VER-RVR-005-001` | `RVR-005` | `StoreReadResultV1`; operation=`READ`; status=`FAILED`; payload=null; failure=`READ_FAILED`; authority=`PRIOR` | construct StoreReadResultV1 | COMPLETED | null | `READ_FAILED` | `PRIOR` | NONE |
| `VER-RVR-006-001` | `RVR-006` | operation=CREATE; status=COMPLETED; payload=bytes(01); failure=null; authority=PRIOR | construct StoreReadResultV1 | REJECTED | null | CONTRACT_INVALID_RESULT | NONE | NONE |
| `VER-RVR-007-001` | `RVR-007` | operation=READ; status=COMPLETED; payload=null; failure=null; authority=PRIOR | construct StoreReadResultV1 | REJECTED | null | CONTRACT_INVALID_RESULT | NONE | NONE |
| `VER-EVR-001-001` | `EVR-001` | `StoreExistsResultV1`; operation=`EXISTS`; status=`COMPLETED`; exists=Boolean true; failure=null; authority=`PRIOR` | construct StoreExistsResultV1 | COMPLETED | Boolean true | null | `PRIOR` | NONE |
| `VER-EVR-002-001` | `EVR-002` | `StoreExistsResultV1`; operation=`EXISTS`; status=`COMPLETED`; exists=Boolean false; failure=null; authority=`NONE` | construct StoreExistsResultV1 | COMPLETED | Boolean false | null | `NONE` | NONE |
| `VER-EVR-003-001` | `EVR-003` | `StoreExistsResultV1`; operation=`EXISTS`; status=`FAILED`; exists=null; failure=`ACCESS_DENIED`; authority=`PRIOR` | construct StoreExistsResultV1 | COMPLETED | null | `ACCESS_DENIED` | `PRIOR` | NONE |
| `VER-EVR-004-001` | `EVR-004` | `StoreExistsResultV1`; operation=`EXISTS`; status=`FAILED`; exists=null; failure=`INVALID_KEY`; authority=`NONE` | construct StoreExistsResultV1 | COMPLETED | null | `INVALID_KEY` | `NONE` | NONE |
| `VER-EVR-005-001` | `EVR-005` | `StoreExistsResultV1`; operation=`EXISTS`; status=`FAILED`; exists=null; failure=`READ_FAILED`; authority=`PRIOR` | construct StoreExistsResultV1 | COMPLETED | null | `READ_FAILED` | `PRIOR` | NONE |
| `VER-EVR-006-001` | `EVR-006` | operation=READ; status=COMPLETED; exists=true; failure=null; authority=PRIOR | construct StoreExistsResultV1 | REJECTED | null | CONTRACT_INVALID_RESULT | NONE | NONE |
| `VER-EVR-007-001` | `EVR-007` | operation=EXISTS; status=NOT_FOUND; exists=null; failure=null; authority=NONE | construct StoreExistsResultV1 | REJECTED | null | CONTRACT_INVALID_RESULT | NONE | NONE |
| `VER-MVR-001-001` | `MVR-001` | operation=`CREATE`; status=`COMPLETED`; failure=null; authority=`NEW` | construct StoreMutationResultV1 | COMPLETED | null | null | `NEW` | NONE |
| `VER-MVR-002-001` | `MVR-002` | operation=`CREATE`; status=`FAILED`; failure=`ACCESS_DENIED`; authority=`NONE` | construct StoreMutationResultV1 | COMPLETED | null | `ACCESS_DENIED` | `NONE` | NONE |
| `VER-MVR-003-001` | `MVR-003` | operation=`CREATE`; status=`FAILED`; failure=`ALREADY_EXISTS`; authority=`PRIOR` | construct StoreMutationResultV1 | COMPLETED | null | `ALREADY_EXISTS` | `PRIOR` | NONE |
| `VER-MVR-004-001` | `MVR-004` | operation=`CREATE`; status=`FAILED`; failure=`INVALID_KEY`; authority=`NONE` | construct StoreMutationResultV1 | COMPLETED | null | `INVALID_KEY` | `NONE` | NONE |
| `VER-MVR-005-001` | `MVR-005` | operation=`CREATE`; status=`FAILED`; failure=`WRITE_FAILED`; authority=`NONE` | construct StoreMutationResultV1 | COMPLETED | null | `WRITE_FAILED` | `NONE` | NONE |
| `VER-MVR-006-001` | `MVR-006` | operation=`CREATE`; status=`FAILED`; failure=`FLUSH_FAILED`; authority=`NONE` | construct StoreMutationResultV1 | COMPLETED | null | `FLUSH_FAILED` | `NONE` | NONE |
| `VER-MVR-007-001` | `MVR-007` | operation=`CREATE`; status=`FAILED`; failure=`ATOMIC_PUBLICATION_FAILED`; authority=`NONE` | construct StoreMutationResultV1 | COMPLETED | null | `ATOMIC_PUBLICATION_FAILED` | `NONE` | NONE |
| `VER-MVR-008-001` | `MVR-008` | operation=`CREATE`; status=`FAILED`; failure=`DURABILITY_FAILED`; authority=`NEW` | construct StoreMutationResultV1 | COMPLETED | null | `DURABILITY_FAILED` | `NEW` | NONE |
| `VER-MVR-009-001` | `MVR-009` | operation=`REPLACE`; status=`COMPLETED`; failure=null; authority=`NEW` | construct StoreMutationResultV1 | COMPLETED | null | null | `NEW` | NONE |
| `VER-MVR-010-001` | `MVR-010` | operation=`REPLACE`; status=`FAILED`; failure=`ACCESS_DENIED`; authority=`PRIOR` | construct StoreMutationResultV1 | COMPLETED | null | `ACCESS_DENIED` | `PRIOR` | NONE |
| `VER-MVR-011-001` | `MVR-011` | operation=`REPLACE`; status=`FAILED`; failure=`NOT_FOUND`; authority=`NONE` | construct StoreMutationResultV1 | COMPLETED | null | `NOT_FOUND` | `NONE` | NONE |
| `VER-MVR-012-001` | `MVR-012` | operation=`REPLACE`; status=`FAILED`; failure=`INVALID_KEY`; authority=`NONE` | construct StoreMutationResultV1 | COMPLETED | null | `INVALID_KEY` | `NONE` | NONE |
| `VER-MVR-013-001` | `MVR-013` | operation=`REPLACE`; status=`FAILED`; failure=`WRITE_FAILED`; authority=`PRIOR` | construct StoreMutationResultV1 | COMPLETED | null | `WRITE_FAILED` | `PRIOR` | NONE |
| `VER-MVR-014-001` | `MVR-014` | operation=`REPLACE`; status=`FAILED`; failure=`FLUSH_FAILED`; authority=`PRIOR` | construct StoreMutationResultV1 | COMPLETED | null | `FLUSH_FAILED` | `PRIOR` | NONE |
| `VER-MVR-015-001` | `MVR-015` | operation=`REPLACE`; status=`FAILED`; failure=`ATOMIC_PUBLICATION_FAILED`; authority=`PRIOR` | construct StoreMutationResultV1 | COMPLETED | null | `ATOMIC_PUBLICATION_FAILED` | `PRIOR` | NONE |
| `VER-MVR-016-001` | `MVR-016` | operation=`REPLACE`; status=`FAILED`; failure=`DURABILITY_FAILED`; authority=`NEW` | construct StoreMutationResultV1 | COMPLETED | null | `DURABILITY_FAILED` | `NEW` | NONE |
| `VER-MVR-017-001` | `MVR-017` | operation=DELETE; status=COMPLETED; failure=null; authority=NEW | construct StoreMutationResultV1 | REJECTED | null | CONTRACT_INVALID_RESULT | NONE | NONE |
| `VER-MVR-018-001` | `MVR-018` | operation=CREATE; status=FAILED; failure=DELETE_FAILED; authority=PRIOR | construct StoreMutationResultV1 | REJECTED | null | CONTRACT_INVALID_RESULT | NONE | NONE |
| `VER-DVR-001-001` | `DVR-001` | operation=DELETE; status=`COMPLETED`; failure=null; authority=`NONE` | construct StoreDeleteResultV1 | COMPLETED | null | null | `NONE` | NONE |
| `VER-DVR-002-001` | `DVR-002` | operation=DELETE; status=`NOT_FOUND`; failure=null; authority=`NONE` | construct StoreDeleteResultV1 | COMPLETED | null | null | `NONE` | NONE |
| `VER-DVR-003-001` | `DVR-003` | operation=DELETE; status=`FAILED`; failure=`ACCESS_DENIED`; authority=`PRIOR` | construct StoreDeleteResultV1 | COMPLETED | null | `ACCESS_DENIED` | `PRIOR` | NONE |
| `VER-DVR-004-001` | `DVR-004` | operation=DELETE; status=`FAILED`; failure=`INVALID_KEY`; authority=`NONE` | construct StoreDeleteResultV1 | COMPLETED | null | `INVALID_KEY` | `NONE` | NONE |
| `VER-DVR-005-001` | `DVR-005` | operation=DELETE; status=`FAILED`; failure=`DELETE_FAILED`; authority=`PRIOR` | construct StoreDeleteResultV1 | COMPLETED | null | `DELETE_FAILED` | `PRIOR` | NONE |
| `VER-DVR-006-001` | `DVR-006` | operation=DELETE; status=`FAILED`; failure=`IDENTITY_MISMATCH`; authority=`PRIOR` | construct StoreDeleteResultV1 | COMPLETED | null | `IDENTITY_MISMATCH` | `PRIOR` | NONE |
| `VER-DVR-007-001` | `DVR-007` | operation=READ; status=COMPLETED; failure=null; authority=NONE | construct StoreDeleteResultV1 | REJECTED | null | CONTRACT_INVALID_RESULT | NONE | NONE |
| `VER-DVR-008-001` | `DVR-008` | operation=DELETE; status=FAILED; failure=READ_FAILED; authority=PRIOR | construct StoreDeleteResultV1 | REJECTED | null | CONTRACT_INVALID_RESULT | NONE | NONE |
| `VER-QVR-001-001` | `QVR-001` | operation=QUARANTINE; status=`COMPLETED`; failure=null; authority=`NEW` | construct StoreQuarantineResultV1 | COMPLETED | null | null | `NEW` | NONE |
| `VER-QVR-002-001` | `QVR-002` | operation=QUARANTINE; status=`NOT_FOUND`; failure=null; authority=`NONE` | construct StoreQuarantineResultV1 | COMPLETED | null | null | `NONE` | NONE |
| `VER-QVR-003-001` | `QVR-003` | operation=QUARANTINE; status=`FAILED`; failure=`ACCESS_DENIED`; authority=`PRIOR` | construct StoreQuarantineResultV1 | COMPLETED | null | `ACCESS_DENIED` | `PRIOR` | NONE |
| `VER-QVR-004-001` | `QVR-004` | operation=QUARANTINE; status=`FAILED`; failure=`ALREADY_EXISTS`; authority=`PRIOR` | construct StoreQuarantineResultV1 | COMPLETED | null | `ALREADY_EXISTS` | `PRIOR` | NONE |
| `VER-QVR-005-001` | `QVR-005` | operation=QUARANTINE; status=`FAILED`; failure=`INVALID_KEY`; authority=`NONE` | construct StoreQuarantineResultV1 | COMPLETED | null | `INVALID_KEY` | `NONE` | NONE |
| `VER-QVR-006-001` | `QVR-006` | operation=QUARANTINE; status=`FAILED`; failure=`ATOMIC_PUBLICATION_FAILED`; authority=`PRIOR` | construct StoreQuarantineResultV1 | COMPLETED | null | `ATOMIC_PUBLICATION_FAILED` | `PRIOR` | NONE |
| `VER-QVR-007-001` | `QVR-007` | operation=QUARANTINE; status=`FAILED`; failure=`DURABILITY_FAILED`; authority=`NEW` | construct StoreQuarantineResultV1 | COMPLETED | null | `DURABILITY_FAILED` | `NEW` | NONE |
| `VER-QVR-008-001` | `QVR-008` | operation=QUARANTINE; status=`FAILED`; failure=`QUARANTINE_FAILED`; authority=`PRIOR` | construct StoreQuarantineResultV1 | COMPLETED | null | `QUARANTINE_FAILED` | `PRIOR` | NONE |
| `VER-QVR-009-001` | `QVR-009` | operation=READ; status=COMPLETED; failure=null; authority=NEW | construct StoreQuarantineResultV1 | REJECTED | null | CONTRACT_INVALID_RESULT | NONE | NONE |
| `VER-QVR-010-001` | `QVR-010` | operation=QUARANTINE; status=FAILED; failure=READ_FAILED; authority=PRIOR | construct StoreQuarantineResultV1 | REJECTED | null | CONTRACT_INVALID_RESULT | NONE | NONE |
| `VER-OBJ-001-001` | `OBJ-001` | StoreReadResultV1(READ,COMPLETED,bytes(01),null,PRIOR) | perform construction | COMPLETED | equal immutable result; repr omits bytes | null | PRIOR | NONE |
| `VER-OBJ-002-001` | `OBJ-002` | StoreReadResultV1(READ,COMPLETED,bytes(01),null,PRIOR) | perform copy and equality | COMPLETED | equal immutable result; repr omits bytes | null | PRIOR | NONE |
| `VER-OBJ-003-001` | `OBJ-003` | StoreReadResultV1(READ,COMPLETED,bytes(01),null,PRIOR) | perform representation | COMPLETED | equal immutable result; repr omits bytes | null | PRIOR | NONE |
| `VER-OBJ-004-001` | `OBJ-004` | StoreReadResultV1(READ,COMPLETED,bytes(01),null,PRIOR) | perform pickle and subclass | COMPLETED | equal immutable result; repr omits bytes | null | PRIOR | NONE |
| `VER-OBJ-005-001` | `OBJ-005` | StoreReadResultV1(READ,COMPLETED,bytes(01),null,PRIOR) | perform passivity | COMPLETED | equal immutable result; repr omits bytes | null | PRIOR | NONE |
| `VER-OBJ-006-001` | `OBJ-006` | same structurally valid lower result in one APP-legal and one APP-illegal protocol context | validate lower structure then dispatch through APP | COMPLETED then REJECTED | same lower result shape | null | unchanged lower authority | NONE |
| `VER-PST-001-001` | `PST-001` | complete canonical UpdateStateFileV1 model | prepare canonical bytes; assert zero store and zero Protocol dispatch | COMPLETED | exact canonical bytes | null | NONE | NONE |
| `VER-PST-002-001` | `PST-002` | fixture for `create(key, canonical_bytes)` satisfying valid key; destination expected absent | invoke create once; assert dispatch `APP-137` and referenced `COMP-017` | COMPLETED | StoreMutationResultV1(COMPLETED,null,NEW) | null | Protocol reference `COMP-017` | Protocol reference `COMP-017` |
| `VER-PST-003-001` | `PST-003` | fixture for `replace(key, canonical_bytes)` satisfying valid key; destination expected present | invoke replace once; assert dispatch `APP-141` and referenced `COMP-021` | COMPLETED | StoreMutationResultV1(COMPLETED,null,NEW) | null | Protocol reference `COMP-021` | Protocol reference `COMP-021` |
| `VER-PST-004-001` | `PST-004` | successful update-state replace result COMPLETED/NEW | project immutable result; assert dispatch `APP-141` and referenced `COMP-021` | COMPLETED | one immutable projection | null | Protocol reference `COMP-021` | Protocol reference `COMP-021` |
| `VER-PST-005-001` | `PST-005` | fixture for quarantine malformed bytes satisfying earliest validation error already selected | invoke quarantine once; assert dispatch `APP-146` and referenced `COMP-026` | COMPLETED | StoreQuarantineResultV1(COMPLETED,null,NEW) | null | Protocol reference `COMP-026` | Protocol reference `COMP-026` |
| `VER-PST-006-001` | `PST-006` | retained reference durably absent with storage identity volume-42 | invoke identity-checked delete once; assert dispatch `APP-156` and referenced `COMP-036` | COMPLETED | StoreDeleteResultV1(COMPLETED,null,NONE) | null | Protocol reference `COMP-036` | Protocol reference `COMP-036` |
| `VER-PFC-000-001` | `PFC-000` | foreign failure member UNKNOWN_FAILURE | construct PersistentStoreFailureCodeV1 | REJECTED | null | null | NONE | NONE |
| `VER-PFC-001-001` | `PFC-001` | member `ACCESS_DENIED` | construct and serialize PersistentStoreFailureCodeV1 | COMPLETED | `ACCESS_DENIED` | null | NONE | NONE |
| `VER-PFC-002-001` | `PFC-002` | member `ALREADY_EXISTS` | construct and serialize PersistentStoreFailureCodeV1 | COMPLETED | `ALREADY_EXISTS` | null | NONE | NONE |
| `VER-PFC-003-001` | `PFC-003` | member `NOT_FOUND` | construct and serialize PersistentStoreFailureCodeV1 | COMPLETED | `NOT_FOUND` | null | NONE | NONE |
| `VER-PFC-004-001` | `PFC-004` | member `INVALID_KEY` | construct and serialize PersistentStoreFailureCodeV1 | COMPLETED | `INVALID_KEY` | null | NONE | NONE |
| `VER-PFC-005-001` | `PFC-005` | member `READ_FAILED` | construct and serialize PersistentStoreFailureCodeV1 | COMPLETED | `READ_FAILED` | null | NONE | NONE |
| `VER-PFC-006-001` | `PFC-006` | member `WRITE_FAILED` | construct and serialize PersistentStoreFailureCodeV1 | COMPLETED | `WRITE_FAILED` | null | NONE | NONE |
| `VER-PFC-007-001` | `PFC-007` | member `FLUSH_FAILED` | construct and serialize PersistentStoreFailureCodeV1 | COMPLETED | `FLUSH_FAILED` | null | NONE | NONE |
| `VER-PFC-008-001` | `PFC-008` | member `ATOMIC_PUBLICATION_FAILED` | construct and serialize PersistentStoreFailureCodeV1 | COMPLETED | `ATOMIC_PUBLICATION_FAILED` | null | NONE | NONE |
| `VER-PFC-009-001` | `PFC-009` | member `DURABILITY_FAILED` | construct and serialize PersistentStoreFailureCodeV1 | COMPLETED | `DURABILITY_FAILED` | null | NONE | NONE |
| `VER-PFC-010-001` | `PFC-010` | member `DELETE_FAILED` | construct and serialize PersistentStoreFailureCodeV1 | COMPLETED | `DELETE_FAILED` | null | NONE | NONE |
| `VER-PFC-011-001` | `PFC-011` | member `QUARANTINE_FAILED` | construct and serialize PersistentStoreFailureCodeV1 | COMPLETED | `QUARANTINE_FAILED` | null | NONE | NONE |
| `VER-PFC-012-001` | `PFC-012` | member `IDENTITY_MISMATCH` | construct and serialize PersistentStoreFailureCodeV1 | COMPLETED | `IDENTITY_MISMATCH` | null | NONE | NONE |
| `VER-FAM-001-001` | `FAM-001` | operation=`READ`; failure=`ACCESS_DENIED` | construct failed store result | `FAILED` | null | `ACCESS_DENIED` | `PRIOR` | Protocol-owned; not selected by FAM |
| `VER-FAM-002-001` | `FAM-002` | operation=`READ`; failure=`INVALID_KEY` | construct failed store result | `FAILED` | null | `INVALID_KEY` | `NONE` | Protocol-owned; not selected by FAM |
| `VER-FAM-003-001` | `FAM-003` | operation=`READ`; failure=`READ_FAILED` | construct failed store result | `FAILED` | null | `READ_FAILED` | `PRIOR` | Protocol-owned; not selected by FAM |
| `VER-FAM-004-001` | `FAM-004` | operation=`EXISTS`; failure=`ACCESS_DENIED` | construct failed store result | `FAILED` | null | `ACCESS_DENIED` | `PRIOR` | Protocol-owned; not selected by FAM |
| `VER-FAM-005-001` | `FAM-005` | operation=`EXISTS`; failure=`INVALID_KEY` | construct failed store result | `FAILED` | null | `INVALID_KEY` | `NONE` | Protocol-owned; not selected by FAM |
| `VER-FAM-006-001` | `FAM-006` | operation=`EXISTS`; failure=`READ_FAILED` | construct failed store result | `FAILED` | null | `READ_FAILED` | `PRIOR` | Protocol-owned; not selected by FAM |
| `VER-FAM-007-001` | `FAM-007` | operation=`CREATE`; failure=`ACCESS_DENIED` | construct failed store result | `FAILED` | null | `ACCESS_DENIED` | `NONE` | Protocol-owned; not selected by FAM |
| `VER-FAM-008-001` | `FAM-008` | operation=`CREATE`; failure=`ALREADY_EXISTS` | construct failed store result | `FAILED` | null | `ALREADY_EXISTS` | `PRIOR` | Protocol-owned; not selected by FAM |
| `VER-FAM-009-001` | `FAM-009` | operation=`CREATE`; failure=`INVALID_KEY` | construct failed store result | `FAILED` | null | `INVALID_KEY` | `NONE` | Protocol-owned; not selected by FAM |
| `VER-FAM-010-001` | `FAM-010` | operation=`CREATE`; failure=`WRITE_FAILED` | construct failed store result | `FAILED` | null | `WRITE_FAILED` | `NONE` | Protocol-owned; not selected by FAM |
| `VER-FAM-011-001` | `FAM-011` | operation=`CREATE`; failure=`FLUSH_FAILED` | construct failed store result | `FAILED` | null | `FLUSH_FAILED` | `NONE` | Protocol-owned; not selected by FAM |
| `VER-FAM-012-001` | `FAM-012` | operation=`CREATE`; failure=`ATOMIC_PUBLICATION_FAILED` | construct failed store result | `FAILED` | null | `ATOMIC_PUBLICATION_FAILED` | `NONE` | Protocol-owned; not selected by FAM |
| `VER-FAM-013-001` | `FAM-013` | operation=`CREATE`; failure=`DURABILITY_FAILED` | construct failed store result | `FAILED` | null | `DURABILITY_FAILED` | `NEW` | Protocol-owned; not selected by FAM |
| `VER-FAM-014-001` | `FAM-014` | operation=`REPLACE`; failure=`ACCESS_DENIED` | construct failed store result | `FAILED` | null | `ACCESS_DENIED` | `PRIOR` | Protocol-owned; not selected by FAM |
| `VER-FAM-015-001` | `FAM-015` | operation=`REPLACE`; failure=`NOT_FOUND` | construct failed store result | `FAILED` | null | `NOT_FOUND` | `NONE` | Protocol-owned; not selected by FAM |
| `VER-FAM-016-001` | `FAM-016` | operation=`REPLACE`; failure=`INVALID_KEY` | construct failed store result | `FAILED` | null | `INVALID_KEY` | `NONE` | Protocol-owned; not selected by FAM |
| `VER-FAM-017-001` | `FAM-017` | operation=`REPLACE`; failure=`WRITE_FAILED` | construct failed store result | `FAILED` | null | `WRITE_FAILED` | `PRIOR` | Protocol-owned; not selected by FAM |
| `VER-FAM-018-001` | `FAM-018` | operation=`REPLACE`; failure=`FLUSH_FAILED` | construct failed store result | `FAILED` | null | `FLUSH_FAILED` | `PRIOR` | Protocol-owned; not selected by FAM |
| `VER-FAM-019-001` | `FAM-019` | operation=`REPLACE`; failure=`ATOMIC_PUBLICATION_FAILED` | construct failed store result | `FAILED` | null | `ATOMIC_PUBLICATION_FAILED` | `PRIOR` | Protocol-owned; not selected by FAM |
| `VER-FAM-020-001` | `FAM-020` | operation=`REPLACE`; failure=`DURABILITY_FAILED` | construct failed store result | `FAILED` | null | `DURABILITY_FAILED` | `NEW` | Protocol-owned; not selected by FAM |
| `VER-FAM-021-001` | `FAM-021` | operation=`DELETE`; failure=`ACCESS_DENIED` | construct failed store result | `FAILED` | null | `ACCESS_DENIED` | `PRIOR` | Protocol-owned; not selected by FAM |
| `VER-FAM-022-001` | `FAM-022` | operation=`DELETE`; failure=`INVALID_KEY` | construct failed store result | `FAILED` | null | `INVALID_KEY` | `NONE` | Protocol-owned; not selected by FAM |
| `VER-FAM-023-001` | `FAM-023` | operation=`DELETE`; failure=`DELETE_FAILED` | construct failed store result | `FAILED` | null | `DELETE_FAILED` | `PRIOR` | Protocol-owned; not selected by FAM |
| `VER-FAM-024-001` | `FAM-024` | operation=`DELETE`; failure=`IDENTITY_MISMATCH` | construct failed store result | `FAILED` | null | `IDENTITY_MISMATCH` | `PRIOR` | Protocol-owned; not selected by FAM |
| `VER-FAM-025-001` | `FAM-025` | operation=`QUARANTINE`; failure=`ACCESS_DENIED` | construct failed store result | `FAILED` | null | `ACCESS_DENIED` | `PRIOR` | Protocol-owned; not selected by FAM |
| `VER-FAM-026-001` | `FAM-026` | operation=`QUARANTINE`; failure=`ALREADY_EXISTS` | construct failed store result | `FAILED` | null | `ALREADY_EXISTS` | `PRIOR` | Protocol-owned; not selected by FAM |
| `VER-FAM-027-001` | `FAM-027` | operation=`QUARANTINE`; failure=`INVALID_KEY` | construct failed store result | `FAILED` | null | `INVALID_KEY` | `NONE` | Protocol-owned; not selected by FAM |
| `VER-FAM-028-001` | `FAM-028` | operation=`QUARANTINE`; failure=`ATOMIC_PUBLICATION_FAILED` | construct failed store result | `FAILED` | null | `ATOMIC_PUBLICATION_FAILED` | `PRIOR` | Protocol-owned; not selected by FAM |
| `VER-FAM-029-001` | `FAM-029` | operation=`QUARANTINE`; failure=`DURABILITY_FAILED` | construct failed store result | `FAILED` | null | `DURABILITY_FAILED` | `NEW` | Protocol-owned; not selected by FAM |
| `VER-FAM-030-001` | `FAM-030` | operation=`QUARANTINE`; failure=`QUARANTINE_FAILED` | construct failed store result | `FAILED` | null | `QUARANTINE_FAILED` | `PRIOR` | Protocol-owned; not selected by FAM |
| `VER-VAL-001-001` | `VAL-001` | UPDATE_STATE read returns NOT_FOUND/null/NONE | validate lower NOT_FOUND fact; assert dispatch `APP-122` and referenced `COMP-002` | NOT_FOUND | null | null | Protocol reference `COMP-002` | Protocol reference `COMP-002` |
| `VER-VAL-002-001` | `VAL-002` | UPDATE_STATE payload is zero bytes | reject at this earliest wire stage; assert dispatch `SAP-003` and zero local semantic result | REJECTED | null | Protocol reference `SEM-003` | Protocol reference `SEM-003` | Protocol reference `SEM-003` |
| `VER-VAL-003-001` | `VAL-003` | UPDATE_STATE payload contains byte 0xFF | reject at this earliest wire stage; assert dispatch `SAP-003` and zero local semantic result | REJECTED | null | Protocol reference `SEM-003` | Protocol reference `SEM-003` | Protocol reference `SEM-003` |
| `VER-VAL-004-001` | `VAL-004` | UPDATE_STATE payload is {}{} | reject at this earliest wire stage; assert dispatch `SAP-003` and zero local semantic result | REJECTED | null | Protocol reference `SEM-003` | Protocol reference `SEM-003` | Protocol reference `SEM-003` |
| `VER-VAL-005-001` | `VAL-005` | UPDATE_STATE object contains duplicate schema keys | reject at this earliest wire stage; assert dispatch `SAP-003` and zero local semantic result | REJECTED | null | Protocol reference `SEM-003` | Protocol reference `SEM-003` | Protocol reference `SEM-003` |
| `VER-VAL-006-001` | `VAL-006` | UPDATE_STATE payload contains insignificant ASCII space | reject at this earliest wire stage; assert dispatch `SAP-003` and zero local semantic result | REJECTED | null | Protocol reference `SEM-003` | Protocol reference `SEM-003` | Protocol reference `SEM-003` |
| `VER-VAL-007-001` | `VAL-007` | UPDATE_STATE root is an empty array | reject at this earliest wire stage; assert dispatch `SAP-003` and zero local semantic result | REJECTED | null | Protocol reference `SEM-003` | Protocol reference `SEM-003` | Protocol reference `SEM-003` |
| `VER-VAL-008-001` | `VAL-008` | UPDATE_STATE schema is windows-update-unknown | reject at this earliest wire stage; assert dispatch `SAP-003` and zero local semantic result | REJECTED | null | Protocol reference `SEM-003` | Protocol reference `SEM-003` | Protocol reference `SEM-003` |
| `VER-VAL-009-001` | `VAL-009` | UPDATE_STATE schema_version is integer 2 | reject at this earliest wire stage; assert dispatch `SAP-003` and zero local semantic result | REJECTED | null | Protocol reference `SEM-003` | Protocol reference `SEM-003` | Protocol reference `SEM-003` |
| `VER-VAL-010-001` | `VAL-010` | UPDATE_STATE object contains field unexpected | reject at this earliest wire stage; assert dispatch `SAP-003` and zero local semantic result | REJECTED | null | Protocol reference `SEM-003` | Protocol reference `SEM-003` | Protocol reference `SEM-003` |
| `VER-VAL-011-001` | `VAL-011` | UPDATE_STATE current_version is integer 1 | reject at this earliest wire stage; assert dispatch `SAP-003` and zero local semantic result | REJECTED | null | Protocol reference `SEM-003` | Protocol reference `SEM-003` | Protocol reference `SEM-003` |
| `VER-VAL-012-001` | `VAL-012` | UPDATE_STATE active_manifest_sha256 contains 64 uppercase A characters | reject at this earliest wire stage; assert dispatch `SAP-003` and zero local semantic result | REJECTED | null | Protocol reference `SEM-003` | Protocol reference `SEM-003` | Protocol reference `SEM-003` |
| `VER-VAL-013-001` | `VAL-013` | UPDATE_STATE active_manifest_sequence is 1 while active_manifest_sha256 is null | reject at this earliest wire stage; assert dispatch `SAP-003` and zero local semantic result | REJECTED | null | Protocol reference `SEM-003` | Protocol reference `SEM-003` | Protocol reference `SEM-003` |
| `VER-VAL-014-001` | `VAL-014` | canonical UpdateStateFileV1 bytes | accept canonical bytes; assert dispatch `APP-121` and referenced `COMP-001` | COMPLETED | immutable `UpdateStateFileV1` | null | Protocol reference `COMP-001` | Protocol reference `COMP-001` |
| `VER-VAL-002-002` | `VAL-002` | update-state bytes exceed 1048576 bytes and begin with invalid UTF-8 | validate once | REJECTED at `VAL-002`; `VAL-003` not evaluated | null | Protocol reference `SEM-003` through `SAP-003` | Protocol reference `SEM-003` | Protocol reference `SEM-003` |
| `VER-VAL-003-002` | `VAL-003` | bounded update-state bytes begin with invalid UTF-8 and would be malformed JSON | validate once | REJECTED at `VAL-003`; `VAL-004` not evaluated | null | Protocol reference `SEM-003` through `SAP-003` | Protocol reference `SEM-003` | Protocol reference `SEM-003` |
| `VER-VAL-004-002` | `VAL-004` | bounded valid UTF-8 begins with a malformed JSON object prefix whose completed form would contain a duplicate key | validate once | REJECTED at `VAL-004`; duplicate-key inspection at `VAL-005` not evaluated | null | Protocol reference `SEM-003` through `SAP-003` | Protocol reference `SEM-003` | Protocol reference `SEM-003` |
| `VER-VAL-005-002` | `VAL-005` | valid JSON object contains a duplicate key and noncanonical whitespace | validate once | REJECTED at `VAL-005`; `VAL-006` not evaluated | null | Protocol reference `SEM-003` through `SAP-003` | Protocol reference `SEM-003` | Protocol reference `SEM-003` |
| `VER-VAL-008-002` | `VAL-008` | canonical object has wrong schema and invalid field type | validate once | REJECTED at `VAL-008`; `VAL-011` not evaluated | null | Protocol reference `SEM-003` through `SAP-003` | Protocol reference `SEM-003` | Protocol reference `SEM-003` |
| `VER-VAL-008-003` | `VAL-008` | canonical object has wrong schema and an unknown field | validate once | REJECTED at `VAL-008`; unknown-field inspection at `VAL-010` not evaluated | null | Protocol reference `SEM-003` through `SAP-003` | Protocol reference `SEM-003` | Protocol reference `SEM-003` |
| `VER-VAL-010-002` | `VAL-010` | canonical update-state object has unknown field and cross-field invariant failure | validate once | REJECTED at `VAL-010`; `VAL-013` not evaluated | null | Protocol reference `SEM-003` through `SAP-003` | Protocol reference `SEM-003` | Protocol reference `SEM-003` |
| `VER-VAL-011-002` | `VAL-011` | canonical update-state object has a wrong field type and would violate a cross-field invariant | validate once | REJECTED at `VAL-011`; invariant inspection at `VAL-013` not evaluated | null | Protocol reference `SEM-003` through `SAP-003` | Protocol reference `SEM-003` | Protocol reference `SEM-003` |
| `VER-ERR-000-001` | `ERR-000` | foreign format error UNKNOWN_FORMAT_ERROR | construct PersistenceFormatErrorCodeV1 | REJECTED | null | null | NONE | NONE |
| `VER-ERR-001-001` | `ERR-001` | protocol error `UPDATE_STATE_MALFORMED` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `UPDATE_STATE_MALFORMED` | null | NONE | NONE |
| `VER-ERR-002-001` | `ERR-002` | protocol error `UPDATE_STATE_QUARANTINED` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `UPDATE_STATE_QUARANTINED` | null | NONE | NONE |
| `VER-ERR-003-001` | `ERR-003` | protocol error `UPDATE_STATE_PERSISTENCE_FAILED` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `UPDATE_STATE_PERSISTENCE_FAILED` | null | NONE | NONE |
| `VER-ERR-004-001` | `ERR-004` | protocol error `OBSERVATION_PUBLICATION_FAILED` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `OBSERVATION_PUBLICATION_FAILED` | null | NONE | NONE |
| `VER-ERR-005-001` | `ERR-005` | protocol error `UPDATE_OPERATION_INTERRUPTED` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `UPDATE_OPERATION_INTERRUPTED` | null | NONE | NONE |
| `VER-ERR-006-001` | `ERR-006` | protocol error `UPDATE_CHECK_FAILED` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `UPDATE_CHECK_FAILED` | null | NONE | NONE |
| `VER-ERR-007-001` | `ERR-007` | protocol error `UPDATE_METADATA_RECHECK_REQUIRED` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `UPDATE_METADATA_RECHECK_REQUIRED` | null | NONE | NONE |
| `VER-ERR-008-001` | `ERR-008` | protocol error `UPDATE_DOWNLOAD_INTERRUPTED` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `UPDATE_DOWNLOAD_INTERRUPTED` | null | NONE | NONE |
| `VER-ERR-009-001` | `ERR-009` | protocol error `UPDATE_DOWNLOAD_FAILED` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `UPDATE_DOWNLOAD_FAILED` | null | NONE | NONE |
| `VER-ERR-010-001` | `ERR-010` | protocol error `UPDATE_MANIFEST_INCOMPATIBLE` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `UPDATE_MANIFEST_INCOMPATIBLE` | null | NONE | NONE |
| `VER-ERR-011-001` | `ERR-011` | protocol error `RETAINED_INSTALLER_MISSING` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `RETAINED_INSTALLER_MISSING` | null | NONE | NONE |
| `VER-ERR-012-001` | `ERR-012` | protocol error `RETAINED_INSTALLER_INVALID` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `RETAINED_INSTALLER_INVALID` | null | NONE | NONE |
| `VER-ERR-013-001` | `ERR-013` | protocol error `RETAINED_INSTALLER_HASH_MISMATCH` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `RETAINED_INSTALLER_HASH_MISMATCH` | null | NONE | NONE |
| `VER-ERR-014-001` | `ERR-014` | protocol error `RETAINED_INSTALLER_REVALIDATION_FAILED` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `RETAINED_INSTALLER_REVALIDATION_FAILED` | null | NONE | NONE |
| `VER-ERR-015-001` | `ERR-015` | protocol error `HANDOFF_RECEIPT_MISSING` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `HANDOFF_RECEIPT_MISSING` | null | NONE | NONE |
| `VER-ERR-016-001` | `ERR-016` | protocol error `HANDOFF_RECEIPT_MALFORMED` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `HANDOFF_RECEIPT_MALFORMED` | null | NONE | NONE |
| `VER-ERR-017-001` | `ERR-017` | protocol error `HANDOFF_RECEIPT_PERSISTENCE_FAILED` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `HANDOFF_RECEIPT_PERSISTENCE_FAILED` | null | NONE | NONE |
| `VER-ERR-018-001` | `ERR-018` | protocol error `HANDOFF_RECEIPT_STALE` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `HANDOFF_RECEIPT_STALE` | null | NONE | NONE |
| `VER-ERR-019-001` | `ERR-019` | protocol error `HANDOFF_LINEAGE_MISMATCH` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `HANDOFF_LINEAGE_MISMATCH` | null | NONE | NONE |
| `VER-ERR-020-001` | `ERR-020` | protocol error `HANDOFF_PROCESS_IDENTITY_MISMATCH` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `HANDOFF_PROCESS_IDENTITY_MISMATCH` | null | NONE | NONE |
| `VER-ERR-021-001` | `ERR-021` | protocol error `HANDOFF_PROCESS_IDENTITY_UNAVAILABLE` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `HANDOFF_PROCESS_IDENTITY_UNAVAILABLE` | null | NONE | NONE |
| `VER-ERR-022-001` | `ERR-022` | protocol error `HANDOFF_PROCESS_NOT_OBSERVED` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `HANDOFF_PROCESS_NOT_OBSERVED` | null | NONE | NONE |
| `VER-ERR-023-001` | `ERR-023` | protocol error `INSTALLER_HANDOFF_CANCELLED` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `INSTALLER_HANDOFF_CANCELLED` | null | NONE | NONE |
| `VER-ERR-024-001` | `ERR-024` | protocol error `INSTALLER_PRELAUNCH_VERIFICATION_FAILED` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `INSTALLER_PRELAUNCH_VERIFICATION_FAILED` | null | NONE | NONE |
| `VER-ERR-025-001` | `ERR-025` | protocol error `INSTALLER_PROCESS_START_FAILED` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `INSTALLER_PROCESS_START_FAILED` | null | NONE | NONE |
| `VER-ERR-026-001` | `ERR-026` | protocol error `INSTALLER_RECEIPT_TIMEOUT` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `INSTALLER_RECEIPT_TIMEOUT` | null | NONE | NONE |
| `VER-ERR-027-001` | `ERR-027` | protocol error `INSTALLER_MUTEX_TIMEOUT` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `INSTALLER_MUTEX_TIMEOUT` | null | NONE | NONE |
| `VER-ERR-028-001` | `ERR-028` | protocol error `HEALTH_RECEIPT_MALFORMED` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `HEALTH_RECEIPT_MALFORMED` | null | NONE | NONE |
| `VER-ERR-029-001` | `ERR-029` | protocol error `HEALTH_RECEIPT_PERSISTENCE_FAILED` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `HEALTH_RECEIPT_PERSISTENCE_FAILED` | null | NONE | NONE |
| `VER-ERR-030-001` | `ERR-030` | protocol error `HEALTH_INITIALIZATION_LINEAGE_MISSING` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `HEALTH_INITIALIZATION_LINEAGE_MISSING` | null | NONE | NONE |
| `VER-ERR-031-001` | `ERR-031` | protocol error `HEALTH_INITIALIZATION_LINEAGE_MISMATCH` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `HEALTH_INITIALIZATION_LINEAGE_MISMATCH` | null | NONE | NONE |
| `VER-ERR-032-001` | `ERR-032` | protocol error `HEALTH_VALIDATION_TIMEOUT` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `HEALTH_VALIDATION_TIMEOUT` | null | NONE | NONE |
| `VER-ERR-033-001` | `ERR-033` | protocol error `HEALTH_VALIDATION_INTERRUPTED` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `HEALTH_VALIDATION_INTERRUPTED` | null | NONE | NONE |
| `VER-ERR-034-001` | `ERR-034` | protocol error `HEALTH_VALIDATION_FAILED` | construct and serialize ProtocolErrorCodeV1 | COMPLETED | `HEALTH_VALIDATION_FAILED` | null | NONE | NONE |
| `VER-RID-001-001` | `RID-001` | runtime requirement registry entry `SCP-*` | resolve identifier to one implementation test | COMPLETED | `SCP-*` | null | NONE | NONE |
| `VER-RID-002-001` | `RID-002` | runtime requirement registry entry `TRM-*` | resolve identifier to one implementation test | COMPLETED | `TRM-*` | null | NONE | NONE |
| `VER-RID-003-001` | `RID-003` | runtime requirement registry entry `SCL-*` | resolve identifier to one implementation test | COMPLETED | `SCL-*` | null | NONE | NONE |
| `VER-RID-004-001` | `RID-004` | runtime requirement registry entry `CLS-*`, `TYP-*`, `PAK-*`, `PSO-*`, `OLS-*`, `PSS-*`, `PSA-*`, `AKY-*` | resolve identifier to one implementation test | COMPLETED | `CLS-*`, `TYP-*`, `PAK-*`, `PSO-*`, `OLS-*`, `PSS-*`, `PSA-*`, `AKY-*` | null | NONE | NONE |
| `VER-RID-005-001` | `RID-005` | runtime requirement registry entry `ART-*`, `KEY-*` | resolve identifier to one implementation test | COMPLETED | `ART-*`, `KEY-*` | null | NONE | NONE |
| `VER-RID-006-001` | `RID-006` | runtime requirement registry entry `OWN-*` | resolve identifier to one implementation test | COMPLETED | `OWN-*` | null | NONE | NONE |
| `VER-RID-007-001` | `RID-007` | runtime requirement registry entry `SCH-<schema>-*` | resolve identifier to one implementation test | COMPLETED | `SCH-<schema>-*` | null | NONE | NONE |
| `VER-RID-008-001` | `RID-008` | runtime requirement registry entry `SER-*` | resolve identifier to one implementation test | COMPLETED | `SER-*` | null | NONE | NONE |
| `VER-RID-009-001` | `RID-009` | runtime requirement registry entry `STR-*`, `EXC-*`, `RSF-*`, `RVR-*`, `EVR-*`, `MVR-*`, `DVR-*`, `QVR-*`, `OBJ-*`, `PST-*` | resolve identifier to one implementation test | COMPLETED | `STR-*`, `EXC-*`, `RSF-*`, `RVR-*`, `EVR-*`, `MVR-*`, `DVR-*`, `QVR-*`, `OBJ-*`, `PST-*` | null | NONE | NONE |
| `VER-RID-010-001` | `RID-010` | runtime requirement registry entry `PFC-*`, `FAM-*`, `VAL-*`, `CON-*` | resolve identifier to one implementation test | COMPLETED | `PFC-*`, `FAM-*`, `VAL-*`, `CON-*` | null | NONE | NONE |
| `VER-RID-011-001` | `RID-011` | runtime requirement registry entry `ERR-*` | resolve identifier to one implementation test | COMPLETED | `ERR-*` | null | NONE | NONE |
| `VER-RID-012-001` | `RID-012` | runtime requirement registry entry `PSC-*` | resolve identifier to one implementation test | COMPLETED | `PSC-*` | null | NONE | NONE |
| `VER-RID-013-001` | `RID-013` | runtime requirement registry entry `VER-*` | resolve identifier to one implementation test | COMPLETED | `VER-*` | null | NONE | NONE |
| `VER-SCL-014-002` | `SCL-014` | version string `v1.2.3` | construct StableVersionV1 and round-trip JSON | COMPLETED | v1.2.3 | null | NONE | NONE |
| `VER-SCL-014-003` | `SCL-014` | version string `1.2.3-alpha` | construct StableVersionV1 and round-trip JSON | COMPLETED | 1.2.3-alpha | null | NONE | NONE |
| `VER-SCL-014-004` | `SCL-014` | version string `1.2.3+build` | construct StableVersionV1 and round-trip JSON | COMPLETED | 1.2.3+build | null | NONE | NONE |
| `VER-SCL-014-005` | `SCL-014` | version string `release-2026.08` | construct StableVersionV1 and round-trip JSON | COMPLETED | release-2026.08 | null | NONE | NONE |
| `VER-AKY-003-002` | `AKY-003` | UTF-8 artifact key of exactly 1 byte | validate once | COMPLETED | same key | null | NONE | NONE |
| `VER-AKY-003-003` | `AKY-003` | UTF-8 artifact key of exactly 1024 bytes | validate once | COMPLETED | same key | null | NONE | NONE |
| `VER-AKY-003-004` | `AKY-003` | empty artifact key | validate once | REJECTED | null | INVALID_KEY | NONE | NONE |
| `VER-AKY-003-005` | `AKY-003` | UTF-8 artifact key of 1025 bytes | validate once | REJECTED | null | INVALID_KEY | NONE | NONE |
| `VER-RVR-007-002` | `RVR-007` | operation=`READ`; status=`COMPLETED`; payload=null; authority=`NONE` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-RVR-007-003` | `RVR-007` | operation=`READ`; status=`NOT_FOUND`; payload=non-null bytes; authority=`NONE` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-RVR-007-004` | `RVR-007` | operation=`CREATE`; status=`COMPLETED`; payload=non-null bytes; authority=`NEW` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-RVR-007-005` | `RVR-007` | operation=`REPLACE`; status=`COMPLETED`; payload=non-null bytes; authority=`NEW` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-RVR-007-006` | `RVR-007` | operation=`DELETE`; status=`COMPLETED`; payload=non-null bytes; authority=`NONE` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-RVR-007-007` | `RVR-007` | operation=`QUARANTINE`; status=`COMPLETED`; payload=non-null bytes; authority=`NEW` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-RVR-007-008` | `RVR-007` | operation=`IDENTITY_CHECK`; status=`COMPLETED`; payload=non-null bytes; authority=`PRIOR` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-RVR-007-009` | `RVR-007` | operation=`READ`; status=`FAILED`; payload=non-null bytes; authority=`PRIOR` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-EVR-007-002` | `EVR-007` | operation=`EXISTS`; status=`COMPLETED`; payload=null; authority=`NONE` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-EVR-007-003` | `EVR-007` | operation=`EXISTS`; status=`NOT_FOUND`; payload=true; authority=`NONE` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-EVR-007-004` | `EVR-007` | operation=`EXISTS`; status=`FAILED`; payload=true; authority=`PRIOR` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-EVR-007-005` | `EVR-007` | operation=`READ`; status=`COMPLETED`; payload=true; authority=`PRIOR` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-EVR-007-006` | `EVR-007` | operation=`EXISTS`; status=`COMPLETED`; payload=true; authority=`NEW` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-EVR-007-007` | `EVR-007` | operation=`EXISTS`; status=`FAILED`; payload=null; authority=`UNKNOWN` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-MVR-018-002` | `MVR-018` | operation=`CREATE`; status=`COMPLETED`; payload=null; authority=`NEW` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-MVR-018-003` | `MVR-018` | operation=`REPLACE`; status=`COMPLETED`; payload=null; authority=`NEW` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-MVR-018-004` | `MVR-018` | operation=`CREATE`; status=`FAILED`; payload=non-null metadata; authority=`PRIOR` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-MVR-018-005` | `MVR-018` | operation=`DELETE`; status=`COMPLETED`; payload=non-null metadata; authority=`NONE` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-MVR-018-006` | `MVR-018` | operation=`CREATE`; status=`COMPLETED`; payload=non-null metadata; authority=`PRIOR` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-DVR-008-002` | `DVR-008` | operation=`DELETE`; status=`COMPLETED`; payload=non-null flag; authority=`NONE` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-DVR-008-003` | `DVR-008` | operation=`DELETE`; status=`NOT_FOUND`; payload=non-null flag; authority=`NONE` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-DVR-008-004` | `DVR-008` | operation=`DELETE`; status=`FAILED`; payload=non-null flag; authority=`PRIOR` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-DVR-008-005` | `DVR-008` | operation=`READ`; status=`COMPLETED`; payload=null; authority=`PRIOR` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-DVR-008-006` | `DVR-008` | operation=`DELETE`; status=`COMPLETED`; payload=null; authority=`NEW` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-QVR-010-002` | `QVR-010` | operation=`QUARANTINE`; status=`COMPLETED`; payload=null; authority=`NEW` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-QVR-010-003` | `QVR-010` | operation=`QUARANTINE`; status=`NOT_FOUND`; payload=non-null key; authority=`NONE` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-QVR-010-004` | `QVR-010` | operation=`QUARANTINE`; status=`FAILED`; payload=non-null key; authority=`PRIOR` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-QVR-010-005` | `QVR-010` | operation=`READ`; status=`COMPLETED`; payload=non-null key; authority=`PRIOR` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-QVR-010-006` | `QVR-010` | operation=`QUARANTINE`; status=`COMPLETED`; payload=non-null key; authority=`PRIOR` | construct result once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-RVR-007-010` | `RVR-007` | operation=READ; status=FOREIGN; payload=null; failure=null; authority=NONE | construct once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-RVR-007-011` | `RVR-007` | operation=READ; status=FAILED; payload=null; failure=null; authority=PRIOR | construct once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-RVR-007-012` | `RVR-007` | operation=READ; status=COMPLETED; payload=bytes(01); failure=READ_FAILED; authority=PRIOR | construct once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-RVR-007-013` | `RVR-007` | operation=READ; status=FAILED; payload=null; failure=READ_FAILED; authority=NONE | construct once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-EVR-007-008` | `EVR-007` | operation=EXISTS; status=FOREIGN; exists=null; failure=null; authority=NONE | construct once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-EVR-007-009` | `EVR-007` | operation=EXISTS; status=FAILED; exists=null; failure=null; authority=PRIOR | construct once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-EVR-007-010` | `EVR-007` | operation=EXISTS; status=COMPLETED; exists=true; failure=READ_FAILED; authority=PRIOR | construct once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-EVR-007-011` | `EVR-007` | operation=EXISTS; status=FAILED; exists=null; failure=READ_FAILED; authority=NONE | construct once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-MVR-018-007` | `MVR-018` | operation=CREATE; status=FOREIGN; failure=null; authority=NONE | construct once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-MVR-018-008` | `MVR-018` | operation=CREATE; status=FAILED; failure=null; authority=NONE | construct once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-MVR-018-009` | `MVR-018` | operation=CREATE; status=COMPLETED; failure=WRITE_FAILED; authority=NEW | construct once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-MVR-018-010` | `MVR-018` | operation=CREATE; status=FAILED; failure=WRITE_FAILED; authority=PRIOR | construct once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-DVR-008-007` | `DVR-008` | operation=DELETE; status=FOREIGN; failure=null; authority=NONE | construct once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-DVR-008-008` | `DVR-008` | operation=DELETE; status=FAILED; failure=null; authority=PRIOR | construct once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-DVR-008-009` | `DVR-008` | operation=DELETE; status=COMPLETED; failure=DELETE_FAILED; authority=NONE | construct once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-DVR-008-010` | `DVR-008` | operation=DELETE; status=FAILED; failure=DELETE_FAILED; authority=NONE | construct once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-QVR-010-007` | `QVR-010` | operation=QUARANTINE; status=FOREIGN; failure=null; authority=NONE | construct once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-QVR-010-008` | `QVR-010` | operation=QUARANTINE; status=FAILED; failure=null; authority=PRIOR | construct once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-QVR-010-009` | `QVR-010` | operation=QUARANTINE; status=COMPLETED; failure=QUARANTINE_FAILED; authority=NEW | construct once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-QVR-010-010` | `QVR-010` | operation=QUARANTINE; status=FAILED; failure=QUARANTINE_FAILED; authority=NONE | construct once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-OBJ-001-002` | `OBJ-001` | valid StoreReadResultV1 copied then internal authority replaced with NONE | reconstruct copied state through public constructor | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-OBJ-004-002` | `OBJ-004` | subclass of StoreReadResultV1 with otherwise valid fields | construct once | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-OBJ-004-003` | `OBJ-004` | pickle payload reconstructing copied-invalid StoreReadResultV1 state | unpickle through authoritative reconstruction | REJECTED | null | INVALID_RESULT | NONE | NONE |
| `VER-EXC-035-002` | `EXC-035` | READ raises `SystemExit` | invoke store boundary once | unconverted | null | n/a | unchanged by propagation | NONE |
| `VER-EXC-035-003` | `EXC-035` | READ raises `GeneratorExit` | invoke store boundary once | unconverted | null | n/a | unchanged by propagation | NONE |
| `VER-EXC-036-002` | `EXC-036` | EXISTS raises unexpected `RuntimeError` | invoke store boundary once | unconverted | null | n/a | unchanged by propagation | NONE |
| `VER-EXC-036-003` | `EXC-036` | CREATE raises unexpected `RuntimeError` | invoke store boundary once | unconverted | null | n/a | unchanged by propagation | NONE |
| `VER-EXC-036-004` | `EXC-036` | REPLACE raises unexpected `RuntimeError` | invoke store boundary once | unconverted | null | n/a | unchanged by propagation | NONE |
| `VER-EXC-036-005` | `EXC-036` | DELETE raises unexpected `RuntimeError` | invoke store boundary once | unconverted | null | n/a | unchanged by propagation | NONE |
| `VER-EXC-036-006` | `EXC-036` | QUARANTINE raises unexpected `RuntimeError` | invoke store boundary once | unconverted | null | n/a | unchanged by propagation | NONE |
| `VER-EXC-037-002` | `EXC-037` | implementation source contains no generic exception conversion branch | perform static catch-boundary inspection | COMPLETED | no generic catch | null | NONE | NONE |
| `VER-SCP-005-001` | `SCP-005` | legal frozen APP success, APP failure, and SAP non-store fixtures | verify three frozen dispatch chains and zero local semantic table | COMPLETED | `APP-137 -> COMP-017`; `APP-037 -> RED-037`; `SAP-003 -> SEM-003` | null | NONE | NONE |
| `VER-CON-001-001` | `CON-001` | injected frozen `ProtocolApplicabilityMatrixV1` authority | enumerate its public records without reading specification text | COMPLETED | 160 keys; 152 LEGAL; 8 ILLEGAL; sources only COMP, RED, NONE | null | NONE | NONE |
| `VER-CON-002-001` | `CON-002` | injected frozen APP and COMP authority records | verify exact APP-to-COMP bijection without reading specification text | COMPLETED | 39 APP source references equal `COMP-001..039` exactly once | null | NONE | NONE |
| `VER-CON-003-001` | `CON-003` | injected frozen APP and RED authority records | verify exact APP-to-RED bijection without reading specification text | COMPLETED | 113 APP source references equal `RED-001..113` exactly once | null | NONE | NONE |
| `VER-CON-004-001` | `CON-004` | injected frozen SAP and SEM authority records | verify exact SAP-to-SEM bijection without reading specification text | COMPLETED | 34 legal SAP keys reference same-numbered `SEM-001..034` exactly once | null | NONE | NONE |
| `VER-CON-005-001` | `CON-005` | one valid and one free-floating six-field result fixture | construct exact `RED-037` result, then change only retryability to NOT_RETRYABLE | COMPLETED then REJECTED | unchanged `RED-037` accepted; mutated tuple rejected by `RES-002` | null | Protocol reference `RED-037` | Protocol reference `RED-037` |
| `VER-CON-006-001` | `CON-006` | simultaneous primary and higher-precedence public-error conditions | apply Section 11.1 priorities 1 and 12 to a `RED-037`-backed result plus retained-installer absence | FAILED | public error selected from `SEM-001`; remaining fields retained from `RED-037` | Protocol references `SEM-001` and `RED-037` | Protocol reference `RED-037` | Protocol reference `RED-037` |
| `VER-CON-007-001` | `CON-007` | all 30 FAM rows and their exact APP/RED consumers | compare 30 unique FAM operation/failure pairs with all APP/RED lower-pair references | COMPLETED | 30 unique FAM pairs; every RED lower pair exists in FAM; no runtime field read from FAM | null | NONE | NONE |
| `VER-PSC-001-001` | `PSC-001` | injected frozen APP authority records | enumerate records without reading specification text | COMPLETED | 160 total; 152 LEGAL; 8 retained-installer REPLACE keys ILLEGAL | null | NONE | NONE |
| `VER-PSC-002-001` | `PSC-002` | injected frozen COMP authority records | enumerate records and verify APP backlinks without reading specification text | COMPLETED | 39 unique COMP rows; each referenced by one LEGAL/COMP APP key | null | NONE | NONE |
| `VER-PSC-003-001` | `PSC-003` | injected frozen RED authority records | enumerate records and verify APP backlinks without reading specification text | COMPLETED | 113 unique RED rows; each referenced by one LEGAL/RED APP key | null | NONE | NONE |
| `VER-PSC-004-001` | `PSC-004` | injected frozen SAP and SEM authority records | enumerate records without reading specification text | COMPLETED | 34 unique same-numbered legal pairs with no missing or extra ID | null | NONE | NONE |
| `VER-PSC-005-001` | `PSC-005` | valid six-field result and one invalid value per field | construct `RED-037`, then independently corrupt status, error, authority, retryability, cleanup, and diagnostics | one COMPLETED then six REJECTED | only exact `RED-037` tuple accepted under `RES-002`; each one-field corruption rejected | null | Protocol reference `RED-037` | Protocol reference `RED-037` |
| `VER-PSC-006-001` | `PSC-006` | two simultaneously observed public errors with one projection | apply Section 11.1 priorities 1 and 12 to a `RED-037`-backed result plus retained-installer absence | FAILED | public error from `SEM-001`; status remains from `RED-037` | Protocol references `SEM-001` and `RED-037` | Protocol reference `RED-037` | Protocol reference `RED-037` |
| `VER-PSC-007-001` | `PSC-007` | valid runtime diagnostic plus serialization attempt | attach exact `DIA-001..005` diagnostic to `RED-037`, then attempt persisted serialization | COMPLETED then REJECTED | validated runtime diagnostic; zero persisted bytes | Protocol reference `RED-037` | Protocol reference `RED-037` | Protocol reference `RED-037` |
| `VER-PSC-008-001` | `PSC-008` | one RETRY_OWNED_CLEANUP projection | exercise exact `CLY-003..006` entry, one retry, terminal duplicate, and abandonment fixtures | COMPLETED | attempt count never exceeds 2; terminal duplicate performs zero store calls | null | NONE | Protocol references `CLY-003..006` |
| `VER-PSC-009-001` | `PSC-009` | result authority NONE, PRIOR, NEW, then foreign UNKNOWN | construct `COMP-002`/NONE, `COMP-001`/PRIOR, `COMP-017`/NEW, then replace authority with foreign UNKNOWN | three COMPLETED then REJECTED | three exact COMP tuples accepted; foreign authority constructs no result | null | Protocol references `COMP-002`, `COMP-001`, `COMP-017` | Protocol references the same COMP rows |
| `VER-PSC-010-001` | `PSC-010` | canonical artifact and serialized error fixtures before and after alignment | compare all schema rows and 34 ERR serialized values before and after alignment | COMPLETED | byte-identical schemas, field metadata, JSON values, and public-error strings | null | NONE | NONE |
| `VER-PSC-011-001` | `PSC-011` | injected frozen ALN authority records | enumerate records without reading specification text and compare their referenced authority ranges with this document's conformance references | COMPLETED | exactly `ALN-001..013`; no missing, extra, or locally copied semantic row | null | NONE | NONE |

| Materiality metric | Result |
| --- | ---: |
| Normative requirement count | 404 |
| Verification row count | 499 |
| Requirements without verification | 0 |
| Verification rows without requirements | 0 |
| Duplicate requirement IDs | 0 |
| Duplicate verification IDs | 0 |
| Grouped verification rows | 0 |
| Placeholder setup cells | 0 |
| Placeholder action cells | 0 |
| Placeholder result cells | 0 |
| Placeholder error cells | 0 |
| Placeholder authority cells | 0 |
| Rows inspecting specification text | 0 |
| Normative prose without requirement ID | 0 |
