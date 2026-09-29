# VNext FINAL Atomic Publication, Recovery & Authority Semantics Repair v1

## Verdict

PASS + 0 BLOCKERS, isolated and not active.

## Atomic publication

The internal FINAL blob may exist before FINAL_READY, but no export or export
receipt is created until the FINAL_READY transition commits. Export eligibility
requires all of:

- workflow state EXPORTED;
- workflow-owned FINAL artifact;
- immutable export receipt;
- matching content-addressed FINAL and export bytes.

A crash after export creation but before EXPORTED leaves the workflow at
FINAL_READY. The loader rejects it until deterministic recovery completes the
EXPORTED transition.

## Authority semantics

The manifest distinguishes the implemented merged post-acceptance Policy+FINAL
slice from the product orchestrator, which remains unimplemented. Active
integration and product-lock replacement remain false.

## Validation

Fault injection covers failure before FINAL_READY, failure before EXPORTED, and
post-export tampering. Audit streak remains 0/2.
