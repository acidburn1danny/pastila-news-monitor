# VNext Product Orchestrator State-Aware Recovery & Terminal Routing Repair v1

## Closed findings

The orchestrator now resumes EDITOR from a persisted SourcePacket, requires an explicit authorization identity before retrying an EDITOR_PENDING inference, persists it in an immutable receipt bound as the transition input, and permits an explicit structural-failure disposition without implicit retry.

Policy routing resumes from persisted APPROVED_FOR_FINAL, FINAL_READY, and EXPORTED states by loading and validating the consumed policy authority. REJECT and REVISE produce typed terminal results. Factual ABSTAIN is persisted, rehydratable, and cannot enter policy.

## Boundaries

No workflow state, SQLite table, artifact authority, product root, or product lock was added or replaced. Active integration remains false. Recovery uses existing immutable artifacts, decisions, receipts, and transition ownership.

## Fault evidence

Dedicated tests inject failures after SourcePacket persistence, during EDITOR_PENDING, after policy decision persistence, and between FINAL_READY and EXPORTED. They also cover terminal REJECTED, REVISION_REQUIRED, and ABSTAINED routing.
