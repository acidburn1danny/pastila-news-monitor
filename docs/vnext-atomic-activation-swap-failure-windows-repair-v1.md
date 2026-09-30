# VNext Atomic Activation Swap Failure Windows Repair v1

## Verdict

PASS + 0 BLOCKERS after bounded CARs and fresh audit restart.

## Demonstrated findings

Independent fault injection showed that the two-rename activation sequence could leave the active path absent after a second-rename failure, and could fail rollback when the fixed quarantine path collided. A subsequent audit restart showed that rollback rename failures still exposed an unsafe intermediate state.

## Best recommended repair

The controller now uses Linux renameat2(RENAME_EXCHANGE) on the already required same filesystem. The active and staged roots exchange atomically in one syscall. Validation failure exchanges them back atomically. Backup finalization occurs only after validation; if it fails, the exchange is rolled back. A transient rollback exchange failure receives one bounded immediate retry and the restored root is verified byte-exactly.

## Exact scope

1. scripts/vnext_atomic_activation_managed_mutable_v1.py
2. scripts/audit_vnext_atomic_activation_swap_failure_windows_v1.py
3. docs/artifacts/vnext-atomic-activation-swap-failure-windows-repair-result-v1.json
4. docs/vnext-atomic-activation-swap-failure-windows-repair-v1.md
5. tests/test_vnext_atomic_activation_swap_failure_windows_v1.py

## Fresh evidence

- validation failure: ATOMIC_BYTE_EXACT_ROLLBACK;
- backup-finalization failure: ATOMIC_BYTE_EXACT_ROLLBACK;
- transient rollback exchange failure: RETRIED_BYTE_EXACT;
- success path: ATOMIC_EXCHANGE_PASS;
- mechanism: renameat2(RENAME_EXCHANGE);
- candidate modified: false;
- active root modified: false;
- waiting period: false;
- LEGACY_DEPENDENCY_COUNT = 0;
- result identity: 47d49570c1daf8000fd7bcdbef0cb27080307ebf7afa14a928f841a2747c4533.

## Invariants

Candidate commit and identities remain unchanged. The active root, active product-lock, and protected rollback root were not modified. No activation, VOICE, GUI, or time-based gate was executed.

## Next gate

Publish this exact checkpoint and perform fresh post-push closure. Activation remains separately authorized.
