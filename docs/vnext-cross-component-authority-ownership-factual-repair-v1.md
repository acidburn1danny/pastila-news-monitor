# VNext Cross-Component Authority, Artifact Ownership & Factual Acceptance Repair v1

Status: **ISOLATED_NOT_ACTIVE**. Base: `70b5b04ae06f1f4c469413e7365a6812079f8614`.

This successor replaces local unpublished checkpoint `97cbadd04b6eb0150e3c28d6d3e4ee6b474f6f36`.

## Repairs

- Workflow authority v3 is generated from and exhaustively equal to executable states and transitions.
- Structural failure routes through `FACTUAL_REVIEW_PENDING`; it cannot directly create eligible fallback.
- SQLite migration v3 changes workflow artifact ownership to the composite key `(workflow_identity, artifact_identity)` and adds noneligible `STRUCTURAL_FAILURE`.
- Authoritative Editor and factual rows use strict inserts. Conflicts fail closed.
- Factual decisions, outputs, and receipts bind the workflow and trusted review-session identity.
- Draft and structural-failure inputs share one explicit factual gate. Structural failure permits only approved source fallback or abstention.
- SQLite workflow association and state are the sole eligibility authority. An unassociated blob is never eligible.
- A successor UTF-8 fixture covers Romanian diacritics without altering frozen historical evidence.

No verifier is promoted. No product root, product lock, R2 bytes, SourcePacket semantics, active integration, Orchestrator, FINAL, VOICE, or GUI is changed.
