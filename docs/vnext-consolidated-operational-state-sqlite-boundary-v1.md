# VNext Consolidated Operational State & SQLite Boundary v1

Status: **isolated, fixture-only, not active**.

This boundary persists the canonical state and receipts defined by `VNext Shared Foundation & Canonical Workflow Boundary v1`. SQLite does not define legal transitions. Every transition is validated by the published Python workflow authority before the transaction is committed.

## Minimal data model

The schema keeps dedicated relational tables for source capture and workflow linkage. Three structurally identical generated-output concepts share `workflow_artifacts`, distinguished by `EDITOR_DRAFT`, `VOICE_DRAFT`, or `FINAL_OUTPUT`. Factual decisions and approvals share `decisions`, distinguished by `FACTUAL` or `APPROVAL`. This avoids empty symmetric tables while retaining unambiguous workflow gates.

Operational transition persistence uses `workflows`, `state_transitions`, `idempotency`, and `attempts`. `schema_migrations` locks monotonic schema history. `writer_owner` binds a database permanently to one writer authority identity; reads remain concurrent.

## Transaction contract

Writes use `BEGIN IMMEDIATE`. State document update, transition receipt, idempotency fingerprint, and attempt record commit together. Any exception before commit rolls all of them back. If commit succeeds but caller acknowledgement fails, replay finds the stored idempotency fingerprint and returns the original receipt without another transition. A different request under the same key fails closed.

## SQLite policy

- `journal_mode=WAL`;
- `foreign_keys=ON` on every connection;
- explicit `busy_timeout`, default 5000 ms;
- `synchronous=FULL` for writers;
- short-lived connections owned by each operation;
- one persisted writer identity;
- full WAL checkpoint before backup;
- `PRAGMA integrity_check`, `foreign_key_check`, migration history, and canonical workflow validation.

Correctness and restart recovery take precedence over throughput. There are no distributed locks, queues, services, ORM, migration framework, network dependency, or server database.

## Backup and restore

Backup uses the SQLite backup API into a temporary database, validates it, fsyncs it, and publishes it atomically to a new path. Restore verifies content identity, restores into another new temporary database, verifies integrity/schema/canonical state, and publishes to a new non-active path. Restore never overwrites an existing database and does not activate the result.

## Payload policy

SQLite stores operational metadata and content-addressed references. Large source/model payloads remain outside this boundary and are represented only by identity, contained reference, kind, and schema identity.

## Isolation

All tests use temporary fixture databases. The active product database, SCOUT database, `/root/pastila-vnext/v1`, model closures, network, inference, frozen evidence, and receipts are not accessed. Product migration and active integration remain unauthorized.
