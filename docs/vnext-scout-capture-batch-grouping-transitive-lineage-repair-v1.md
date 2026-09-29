# VNext SCOUT Capture Batch & Capture-to-Grouping Transitive Lineage Integrity Repair v1

Status: **SUCCESSOR_ISOLATED_NOT_ACTIVE**
Verdict: **PASS**

## Repair

Recovery now binds the exact SCOUT transition receipts to canonical workflow history and validates the content-addressed capture batch named by the exact DISCOVERED to CAPTURED transition. The CAPTURED to GROUPED input must equal that batch identity.

The complete capture batch is reconciled against capture rows, immutable capture payloads, event-source membership, and workflow-event membership. The grouping must consume every authorized capture exactly once and no other capture.

Operational transition receipts are bound to their attempt and idempotency rows. Missing, duplicate, altered, and cross-workflow lineage fails closed during immediate, downstream, and terminal recovery.

## Minimality

SQLite remains schema v7. Existing transition rows, capture batches, capture rows, immutable blobs, event membership, and workflow history already express the required authority. No new table or runtime component was introduced.

## Validation

- VNext self-contained suite: **340/340 PASS**
- Dedicated adversarial tests: **16/16 PASS**
- Self-contained successor auditor: **PASS**
- SQLite schema migration: **none**
- Active integration: **not performed**
- Product-lock replacement: **not performed**
- LEGACY_DEPENDENCY_COUNT = 0
- Audit streak: **0/2**
