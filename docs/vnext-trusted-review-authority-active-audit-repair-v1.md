# VNext Trusted Review Authority & Active Audit Consolidation Repair v1

Status: `ISOLATED_NOT_ACTIVE`

This successor closes two demonstrated cross-component blockers over
`214e41fc1d4f6ba42dbafbb60b3467167e74a250` without changing the active product
root or product lock.

## Trusted review authority

Factual decisions now require a persisted SQLite review session bound to the
workflow, source packet, exact review input, actor, and one allowed outcome.
The SQLite writer creates the grant only while the workflow is in
`FACTUAL_REVIEW_PENDING`. The factual decision consumes the `OPEN` session in
the same transaction that persists the decision, output association, and state
transition. A fabricated, mismatched, or replayed session fails closed.

## Active audit authority

`vnext-active-authority-audit-manifest-v1.json` is the single current authority
index. It identifies the current workflow and SQLite contracts, runtime module
set, current auditor, historical commit-only auditors, and active-graph
exclusions.

Historical auditors and evidence remain immutable. They reproduce their bound
commits and are not current-head audit entry points. The obsolete SourcePacket
compatibility adapter is excluded from the active graph because the canonical
`vnext-source-packet` now flows directly from SCOUT to EDITOR.

## Boundaries

No active integration, product-lock replacement, Orchestrator/Policy, FINAL,
cleanup, model activity, or next-phase work is part of this repair. Audit
streak remains `0/2`; the next gate is a new full fresh cross-component audit.
