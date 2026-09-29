# VNext SCOUT Workflow Event Ownership & Grouping Lineage Integrity Repair v1

Status: **SUCCESSOR_ISOLATED_NOT_ACTIVE**
Verdict: **PASS**

## Repair

Global content-addressed events remain reusable. SQLite schema v7 adds only the workflow-to-event authority relation, with canonical grouping position and grouping identity. Selection now proves that the selected event belongs uniquely to the current workflow before the GROUPED to SELECTED transition.

Recovery reproduces the ordered grouping output identity and validates the exact CAPTURED to GROUPED transition and operational receipt. Missing, duplicate, altered, or cross-workflow membership and transition lineage fails closed, including terminal factual-result rehydration.

## Consolidation

The active graph retains one canonical SourcePacket contract. No event payload is duplicated per workflow. The new relation separates global content identity from workflow ownership without adding another runtime component.

## Validation

- VNext self-contained suite: **324/324 PASS**
- Dedicated migration and adversarial tests: **14/14 PASS**
- SQLite schema: **v7**, monotonic migration from v6
- Active integration: **not performed**
- Product-lock replacement: **not performed**
- LEGACY_DEPENDENCY_COUNT = 0
- Audit streak: **0/2**
