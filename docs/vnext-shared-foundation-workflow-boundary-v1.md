# VNext Shared Foundation & Canonical Workflow Boundary v1

Status: **isolated implementation boundary; not active**.

This boundary implements the minimum shared primitives authorized by commit `4bd80d1aebede3737292cf97640e5d63ca07786e`. It has no dependency on the active VNext product root, SCOUT, SourcePacket, R2, candidate models, SQLite product state, evaluation/archive tooling, network access, or inference.

## Modules

- `vnext_foundation_v1`: canonical JSON, SHA-256 identities, schema/version checks, atomic storage, immutable receipt publication, path containment, dependency-lock validation, preflight, tree identities, recovery, and path-aware legacy scanning.
- `vnext_workflow_v1`: canonical states and transitions, minimal operational receipts, fail-closed transitions, idempotent replay, conflicting replay rejection, and atomic fixture-state storage.

The separation is intentional: byte/storage/dependency primitives do not know workflow semantics, while workflow authority consumes only the shared foundation.

## Identity and receipt contract

Canonical objects are UTF-8 JSON with sorted keys, no insignificant whitespace, no NaN, and SHA-256 identity. Operational receipt identity covers semantic audit fields. Optional observation time and provenance remain stored metadata but do not change semantic identity. Full stored bytes may independently receive a content identity.

Receipts contain identities, states, actor, outcome, and attempt data. They never contain source or model payloads. Immutable standalone receipt publication refuses overwrite.

## Atomicity and recovery

Writes use a same-directory exclusive temporary file, flush, file `fsync`, atomic replace, and directory `fsync` where supported. Temporary writes are ineligible. Recovery removes only recognized unpublished temporary files and never synthesizes state from their presence.

## Dependency and legacy contract

Locks declare every node, identity, relative path, roots, and transitive edges. Undeclared, unreachable, cyclic, mismatched, escaping, legacy-bound, or external symlink/hardlink dependencies fail closed. Legacy scanning recognizes concrete path/import bindings; benign prose such as `legacy reporting` is ignored.

## Workflow contract

Every transition names the expected previous state and resulting state. Illegal state, wrong workflow, conflicting replay, and corrupt state identity fail closed. A repeated request with the same idempotency identity and semantic fingerprint returns the original receipt without another state change.

`EditorDraft` and factual product behavior are not implemented here. This boundary provides state authority only. VOICE remains `DISABLED_UNTIL_PROMOTION`; `STOP_ALL_CANDIDATES` remains active.

## Integration boundary

The code is repository-local and fixture-tested. It is not referenced by the active product lock and is not materialized under `/root/pastila-vnext/v1`. Integration, migration, and product-lock replacement require separate authorization.
