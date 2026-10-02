# VNext Canonical-Only Recovery Topology & Historical Chain Dereference Boundary v1

## Decision

The installable recovery topology is exactly:

`active product -> /root/pastila-vnext/.rollback-pre-gui-coherent-733ad2a1`

The GUI, Contract, and Exchange predecessor generations remain content-addressed historical evidence. Their product-lock identities, byte hashes, and origin commits remain recorded with `physical_root_required=false`. No installable authority or preflight byte names their physical paths.

## Scope

The successor changes only the canonical preflight and the activation receipt, active-state authority, rollback manifest, and product-lock bindings. It does not change workflow runtime, GUI orchestration, persistence, policy, SQLite schema, R2, or platform bytes.

## Recovery proof

The self-contained auditor uses overlay materializations and proves:

- successor identity and canonical preflight;
- startup and restart-compatible startup;
- Integrated E2E to `EXPORTED`;
- shared CLI/GUI orchestration and state;
- repository dependency count 0;
- legacy dependency count 0;
- direct rollback to the canonical immediate predecessor without requiring a historical physical root;
- restore of the successor;
- protected active/canonical/historical root identity preservation.

The three historical physical roots remain untouched. Retirement is a later separately authorized gate.

## Test classification

The active VNext suite passes `513` nodes with six historical/environment-specific nodes deselected. Those nodes pin superseded active-product identities or already-retired roots and are outside the active acceptance graph. The new dedicated authority and prospective recovery tests pass `2/2`.
