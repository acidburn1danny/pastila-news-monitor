# VNext Orchestrator Retry-Evidence Integrity & Structural-Failure Factual Routing Repair v1

## Closed findings

EditorDraft rehydration now validates the exact EDITOR_PENDING to EDITOR_DRAFT_READY transition. When its input is a retry receipt rather than the invocation receipt, the immutable retry receipt is mandatory and is validated for content identity, workflow, SourcePacket, invocation, and authorization binding.

StructuralFailure is now a first-class factual-review input in the orchestrator. It can produce only an explicit source fallback or abstention; ACCEPT_DRAFT remains forbidden. Structural failures and their factual results are rehydratable from persistent ownership evidence.

## Fault evidence

Dedicated tests remove, alter, and cross-bind retry receipts and require fail-closed behavior. Additional tests cover structural fallback, abstention, restart rehydration, and rejection of draft acceptance.

## Boundaries

No SQLite table, workflow state, product root, or product lock changed. Active integration remains false.
