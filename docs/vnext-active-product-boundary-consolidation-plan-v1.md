# VNext Active Product Boundary & Consolidation Plan v1

Status: **DESIGN AUTHORITY ONLY**  
Verdict: **C — REFACTOR / CONSOLIDATE BEFORE CONTINUING**  
Target: **MODULAR MONOLITH**  
Persistent product root: `/root/pastila-vnext/v1`

## Purpose

This checkpoint defines the bounded authority for a later consolidation. It does not implement, migrate, move, archive, integrate, promote, or delete anything. The active product lock and physical VNext root remain unchanged.

## Target architecture

The target is one modular monolith with logical modules for shared foundation, SCOUT, SourcePacket, EDITOR, factual acceptance, workflow policy, deterministic FINAL, and a product CLI. SQLite remains the operational state store. R2 remains the EDITOR reference realizer. VOICE is a disabled boundary until a separate mechanism passes promotion. The minimal CHIEF EDITOR responsibility is workflow, policy, and approval inside the orchestrator; it is not a separate model. GUI work is deferred until the core workflow is stable.

Canonical flow:

`SCOUT capture → grouping → user selection → SourcePacket → R2 EDITOR → EditorDraft → structural validation → factual acceptance → ACCEPT / SOURCE_FALLBACK / ABSTAIN → AcceptedSetup → VOICE boundary → workflow/policy approval → deterministic FINAL → export`

`EditorDraft` is never eligible as `AcceptedSetup`.

## Product boundaries

### Active product

- product CLI and integrated workflow;
- SCOUT production capture, grouping, selection, and provenance;
- self-contained SourcePacket;
- R2 plus its exact model, adapter, tokenizer, decoding, and platform closure;
- structural validation;
- explicit factual acceptance with safe fallback and abstention;
- workflow/policy approval;
- deterministic FINAL assembly/export;
- SQLite operational state;
- shared identity, storage, lock, preflight, recovery, and observability foundation.

### Development and evaluation

Evaluation tooling is not imported by the product. It owns fixtures, bake-offs, blind review, scoring, unseal, taxonomy, shadow calibration, promotion evaluation, and experimental authorities. Every experiment begins with a pilot and permits a maximum 100 observations before a mandatory `STOP / REVISE / CONTINUE` checkpoint. Work beyond 100 requires explicit evidence. Intermediates are ephemeral; only protocol, input closure, terminal result, and minimum justified evidence persist.

### Frozen evidence archive

Frozen protocols, terminal results, minimum receipts, reports, and candidate closure indexes remain immutable and independently verifiable. They are never startup dependencies. `STOP_ALL_CANDIDATES` remains active. Qwen3 and Qwen2.5 candidate bytes, bake-off runs, review tooling, 216 receipts, scoring/unseal/taxonomy tooling, historical authorities, failed runs, and experimental adapters are excluded from the active graph.

### Ephemeral workspace

Clean-room restores, caches, candidates, tokenized data, partial outputs, temporary receipts, and experimental intermediates are ephemeral by default. They are excluded from product locks and cannot become hidden dependencies.

## Shared foundation

One implementation will eventually own canonical UTF-8 JSON, stable key ordering, SHA-256 identities, tree identities, atomic `temp/fsync/replace`, immutable receipts, schema/version validation, dependency lock resolution, path containment, state transitions, preflight, direct/transitive legacy scanning, and clean-room acceptance. This checkpoint authorizes only its design.

## State, storage, and recovery

The target uses `state/product.sqlite3` with foreign keys, WAL, bounded busy timeout, transactional monotonic migrations, SQLite backup API, WAL checkpoint before snapshots, and restore integrity checks. Large immutable payloads may remain content-addressed with database references. Writes have a single owner, every operation has an idempotency key, partial outputs are ineligible, and recovery creates an explicit new attempt.

## SCOUT

The existing SourcePacket contract and source definitions are preserved where valid. Current capture/grouping is a development baseline requiring production closure: adapter contracts, HTTP failure behavior, encodings, duplicate capture, canonical URLs, source health, deterministic recapture, grouping auditability, migrations, and realistic acceptance. Historical database migration is not required unless product behavior demonstrates a need.

## EDITOR and factual acceptance

R2 produces `EditorDraft`, not accepted product output. Structural validation precedes factual acceptance. Until a verifier earns separate promotion, factual acceptance is explicit human authority; otherwise the workflow uses source-preserving fallback or abstains. The shadow verifier remains optional, non-authoritative, and unable to alter output, routing, requests, or startup.

## VOICE, policy, FINAL, and GUI

This plan does not design a VOICE mechanism. A future mechanism may enter the graph only after factual safety, commentary quality, repetition, stability, pilot, terminal decision, and explicit promotion gates. R2 cannot serve as VOICE. Policy/approval remains an orchestrator responsibility. FINAL is deterministic. GUI follows stable CLI/state/E2E and contains no independent factual logic.

## Migration order

1. Freeze inventory and active dependency graph.
2. Establish shared foundation contracts.
3. Establish canonical workflow/state contracts.
4. Prepare the replacement product lock without activating it.
5. Consolidate SQLite schema and migrations.
6. Production-close SCOUT.
7. Preserve and bind SourcePacket.
8. Preserve R2 byte-identically.
9. Rebuild EDITOR around `EditorDraft`.
10. Add explicit factual acceptance, fallback, and abstention.
11. Add workflow/policy orchestration.
12. Add deterministic FINAL.
13. Pass integrated clean-room E2E.
14. Separate evaluation imports and archive indexes.
15. Remove rejected candidates and evidence from the active graph.
16. Pass deployment/restore acceptance.
17. Only then begin a separately authorized VOICE mechanism pilot.
18. Build GUI after workflow stabilization.
19. Reach `GLOBAL_VNEXT_MIGRATION_PASS`.
20. Consider cleanup only under separate authorization.

## Startup boundary and observability

Startup verifies root containment, product and platform locks, forbidden paths, host platform, R2 bytes, configuration, schemas, database migrations, writable atomic storage, recovery state, adapters, editor smoke, and `LEGACY_DEPENDENCY_COUNT = 0`. Minimum structured observability records workflow/operation IDs, transitions, component outcome, duration, source health, model latency/memory, fallback/abstention counts, acceptance decisions, database health, and backup age without logging full sensitive payloads by default.

## Cleanup eligibility

Nothing is cleaned by this plan. An artifact becomes eligible only after global migration pass, zero direct/transitive references, independent evidence closure, successful restore/E2E without it, documented retention, and separate owner authorization.

## Consolidation exit

Consolidation ends only after the active graph is minimal and explicit, product imports exclude evaluation/archive, SCOUT is production-closed, SourcePacket is self-contained, factual acceptance cannot be bypassed, fallback/abstention operate, SQLite backup/restore passes, FINAL is deterministic, clean-room startup/E2E passes with legacy unavailable, and `LEGACY_DEPENDENCY_COUNT = 0`.

## Authorized next phase

After this checkpoint is published and verified, the next separately authorized action is implementation of the shared foundation and canonical workflow/state boundary only. Physical migration, product-lock replacement, archival, cleanup, VOICE design, and GUI remain unauthorized.
