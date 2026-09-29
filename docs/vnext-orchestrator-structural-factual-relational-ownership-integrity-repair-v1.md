# VNext Orchestrator Structural & Factual Relational Ownership Integrity Repair v1

Status: PASS + 0 BLOCKERS

This bounded successor closes two demonstrated rehydration defects without changing the SQLite schema or widening the active architecture.

- StructuralFailure rehydration requires its exact workflow-owned EDITOR_PENDING -> STRUCTURAL_FAIL -> FACTUAL_REVIEW_PENDING lineage.
- Factual rehydration binds the complete decision row, immutable payload and receipt, factual artifact row, exact adjudication transition, and decision-receipt provenance.
- Missing, duplicate, altered, and cross-workflow lineage fails closed for both EditorDraft and StructuralFailure paths.
- Active integration and product-lock replacement remain false.
- Audit streak remains 0/2.
