# VNext Canonical Rollback Authority Consolidation & Historical Root Retirement Boundary v1

## Verdict

PASS + 0 BLOCKERS. The immediate predecessor root is the sole canonical rollback target in the successor authority. The older protected root is classified historical and retirement remains a separate, unexecuted owner gate.

## Design

- The actual activation receipt remains immutable and continues to bind the product lock that was activated.
- The successor product lock separately records its direct predecessor and the original activation candidate.
- The canonical rollback manifest v2 binds `/root/pastila-vnext/.rollback-pre-exchange-5e31722e`, its product-lock identity, SHA-256, graph, and managed inventory.
- The active-state authority v2 binds the current active lock, immutable activation receipt, and canonical immediate-predecessor rollback manifest.
- Historical root `/root/pastila-vnext/.rollback-pre-68fb2c347367` is non-canonical and retained pending separately authorized retirement.

## Validation

- Content-addressed identities reproduced fresh.
- Isolated OverlayFS prospective installation passed canonical preflight and real startup.
- Integrated E2E reached `EXPORTED` through the canonical startup boundary.
- The standalone auditor validated rollback integrity against the immediate predecessor.
- Active root and both rollback-root product-lock SHA-256 values remained unchanged.
- `LEGACY_DEPENDENCY_COUNT = 0`.

## Boundaries

No successor installation, active product-lock replacement, rollback-root deletion, VOICE work, or GUI work was executed.


## CAR-01 — Canonical target semantic pinning

An independent adversarial audit showed that internal content-address consistency alone did not pin the authorized rollback root. The successor preflight now requires the exact immediate-predecessor root, product-lock identity and SHA-256, the exact historical-root classification, and the separate retirement gate. A fully coherent and recontent-addressed rewrite to an unauthorized root is rejected fail-closed. All dependent evidence was rebuilt and the complete boundary audit restarted fresh.


## CAR-02 — Publication reconstruction mode normalization

Fresh upstream reconstruction exposed umask-dependent executable source modes (`0775`) propagated by `copy2` into the simulated product. The product preflight correctly rejected group-writable bytes. The boundary auditor now copies content while preserving each canonical target mode, making publication closure independent of archive extraction umask without changing the candidate or any authority identity.
