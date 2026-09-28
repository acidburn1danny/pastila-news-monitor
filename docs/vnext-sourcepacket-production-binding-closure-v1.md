# VNext SourcePacket Production Binding Closure v1

Status: **ISOLATED_NOT_ACTIVE**  
Verdict: **PASS**

## Decision

SCOUT Production Closure emits an internally valid `vnext-source-packet`. The frozen downstream contract expects `editor-vnext-source-packet`. This closure preserves both published authorities and adds one pure, fail-closed binding at their boundary. It does not change capture, grouping, selection, persistence, R2, or factual acceptance.

The two completeness labels are compatible in this bounded context. SCOUT deterministically retains one selected capture for every unique source in the grouped event. The frozen handoff calls the same source coverage `ALL_CAPTURED_UNIQUE_SOURCES`. The binding does not add, remove, select, rank, or rewrite sources.

## Binding

- `event_identity` becomes `event_id`.
- `source_identity` becomes `source_id`.
- `capture_identity` becomes the frozen contract's `capture_sha256` provenance field.
- `text_sha256` becomes `sha256`.
- Source text bytes, byte boundaries, URLs, titles, timestamps, names, positions, and content scope remain unchanged.
- The packet identity is recomputed over the frozen target representation.

Input packet identity, source uniqueness, canonical ordering, byte boundaries, text hashes, capture identities, provenance fields, selection authority, completeness claim, and content scope are verified before binding. The target is independently verified after binding. Any mismatch fails closed.

## Self-containment

The bound packet contains the source text bytes and provenance required by the published SourcePacket contract. Validation requires no database, repository lookup, product root, network, historical receipt, EvidencePacket, selector, or factual ledger. Runtime dependencies are the Python standard library and the published shared foundation only.

## Frozen order and exclusions

This closure performs no historical SCOUT database migration, product-data migration, active integration, product-root or product-lock modification, R2/EDITOR rebuild, factual acceptance, VOICE work, or cleanup. The consolidated SQLite boundary is exercised only through a temporary fixture database to prove that the actual SCOUT production output binds successfully.

`STOP_ALL_CANDIDATES` remains active, `VOICE = DISABLED_UNTIL_PROMOTION`, and `LEGACY_DEPENDENCY_COUNT = 0`.

## Acceptance evidence

The dedicated suite covers deterministic binding, frozen-contract compatibility, byte and provenance preservation, real SCOUT fixture output, independent target validation, and adversarial identity/text/boundary/source/content-scope/authority/completeness mutations. The auditor reproduces the closure, fixture, and bound packet identities and checks the exact dependency allowlist.

