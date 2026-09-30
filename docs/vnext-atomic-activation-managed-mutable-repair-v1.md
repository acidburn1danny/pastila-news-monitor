# VNext Atomic Activation Managed-vs-Mutable Post-Swap Verification Repair v1

## Verdict

PASS + 0 BLOCKERS.

The activation controller now verifies immutable authority bytes separately from declared mutable runtime state and regenerable cache after the atomic swap. The validated candidate remains unchanged.

## Root cause and CAR

The previous controller compared the full live tree to the staged tree after startup and Integrated E2E. SQLite legitimately created state/product.sqlite3-wal and state/product.sqlite3-shm, so a byte-exact full-tree comparison incorrectly rejected a healthy activation.

The bounded repair:

- snapshots managed authority bytes, entry types, ownership, modes, sizes, and hashes before activation;
- treats state/product.sqlite3 as mutable state while preserving its required path, type, owner, and mode;
- permits only cache paths classified by the candidate canonical runtime-byte policy;
- rejects managed drift, missing managed bytes, unauthorized extra bytes, and invalid mutable/cache entry types;
- preserves byte-exact rollback verification for the prior product root and product lock;
- performs no waiting or soak gate.

## Scope

1. scripts/vnext_atomic_activation_managed_mutable_v1.py
2. scripts/audit_vnext_atomic_activation_managed_mutable_v1.py
3. docs/artifacts/vnext-atomic-activation-managed-mutable-repair-result-v1.json
4. docs/vnext-atomic-activation-managed-mutable-repair-v1.md
5. tests/test_vnext_atomic_activation_managed_mutable_v1.py

## Validation

The self-contained audit demonstrates:

- declared mutable SQLite content may change;
- declared WAL/SHM cache may appear;
- managed-byte drift fails closed;
- unauthorized extra bytes fail closed;
- injected post-swap failure restores the previous root byte-exactly;
- no candidate byte is modified;
- LEGACY_DEPENDENCY_COUNT = 0.

Frozen result identity: d7de4a334ddb3fa88934aa30afb6ec6a31f1f19704c61a803648c6d7b50d20e1.

## Product invariants

- active root /root/pastila-vnext/v1 was not modified;
- active product-lock SHA-256 remains 0ff93c4d9f550c8458d2223ae91627903bf02dc24973c59d3069fa94ada1100e;
- protected rollback root was not modified or deleted;
- protected rollback product-lock SHA-256 remains 2ddc484171f3b58f0f10ce4c4c73c1db51323d5c545320c578dc17ebb3edb4e6;
- no activation, VOICE, GUI, or time-based gate was executed.

## Next gate

Publish the exact checkpoint commit, run fresh post-push reproduction, then request separate authorization before any activation retry.
