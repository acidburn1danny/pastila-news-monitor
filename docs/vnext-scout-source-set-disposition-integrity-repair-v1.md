# VNext SCOUT Source-Set Authority & Per-Source Capture Disposition Integrity Repair v1

Status: **SUCCESSOR_ISOLATED_NOT_ACTIVE**
Verdict: **PASS**

## Repair

Capture accepts one validated typed SourceSet containing the canonical document, its content identity, and the exact enabled SourceDefinitions. The former split authority API is removed. The immutable SourceSet is published under the workflow root, and the capture batch plus the DISCOVERED to CAPTURED transition are bound to its identity.

Every enabled source has exactly one deterministic disposition: CAPTURED with article count, CAPTURE_FAILED with failure class, or NO_ELIGIBLE_ENTRIES. Captured payload provenance is reconciled against the exact source id, name, feed URL, and categories in the bound SourceDefinition.

Recovery validates the SourceSet, capture batch, dispositions, capture payloads, transition receipts, workflow event membership, and downstream lineage. Missing, duplicate, altered, subset, extra-source, false-identity, modified-definition, and cross-workflow evidence fails closed through downstream and terminal recovery.

## Persistence adjudication

SQLite remains schema v7. The existing sources table is a current non-authoritative registry and may safely reflect the latest observed revision. Historical authority is the immutable content-addressed SourceSet referenced by each capture batch and transition. A schema migration would duplicate authority without improving recovery correctness.

## Minimality

No new runtime service, table, model, or product dependency was introduced. One value type and one immutable artifact class replace independently supplied identity and definitions.

## Validation

- VNext self-contained suite: **357/357 PASS**
- Dedicated adversarial tests: **17/17 PASS**
- Self-contained successor auditor: **PASS**
- SQLite schema migration: **none**
- Active integration: **not performed**
- Product-lock replacement: **not performed**
- LEGACY_DEPENDENCY_COUNT = 0
- Audit streak: **0/2**
