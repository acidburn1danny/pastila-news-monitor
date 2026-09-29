# VNext Product Orchestrator & Integrated Core E2E Closure v1

## Decision

The product orchestrator is a thin coordinator over the published VNext component boundaries. It owns ordering and fail-closed state routing. It does not own SCOUT selection, factual review, policy approval, EDITOR output, or FINAL eligibility.

## Integrated path

SCOUT capture and grouping -> explicit event selection -> SourcePacket -> R2 EditorDraft -> explicit factual review authority -> AcceptedSetup or source fallback -> explicit policy authority -> deterministic FINAL -> immutable export receipt.

## Authority

Factual review and policy approval remain explicit typed instructions carrying actor, allowed outcome, authorization identity, and reason. The orchestrator cannot synthesize either authority. Event selection remains an explicit event identity.

## Recovery

Each component persists through its existing SQLite and immutable artifact boundary. The orchestrator adds no database table, workflow state, artifact owner, or alternate eligibility path. Existing component replay and recovery semantics remain authoritative.

## Isolation

This successor is tested in temporary roots. Active integration and product-lock replacement remain false. The persistent product root is not written by this closure.
