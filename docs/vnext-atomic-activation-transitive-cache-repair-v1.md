# VNext Atomic Activation Transitive Executable-Cache Suppression Repair v1

## Verdict

PASS + 0 BLOCKERS.

The activation controller now sets PYTHONDONTWRITEBYTECODE=1 for every staged preflight, post-swap preflight, and live auditor/E2E subprocess. Child processes inherit the same environment, while the canonical candidate policy continues to reject every pyc and __pycache__ entry.

## Demonstrated root cause

The prior controller passed -B only to the direct Python process. A child process invoked during staged validation did not inherit that command-line option and created executable cache inside the candidate platform tree.

## Bounded repair

- one execution environment function injects PYTHONDONTWRITEBYTECODE=1;
- all three activation subprocess boundaries consume that exact environment;
- no candidate file or identity changes;
- post-run surface verification still rejects executable cache and every unauthorized byte;
- no waiting or soak gate exists.

## Exact scope

1. scripts/vnext_atomic_activation_managed_mutable_v1.py
2. scripts/audit_vnext_atomic_activation_transitive_cache_v1.py
3. docs/artifacts/vnext-atomic-activation-transitive-cache-repair-result-v1.json
4. docs/vnext-atomic-activation-transitive-cache-repair-v1.md
5. tests/test_vnext_atomic_activation_transitive_cache_v1.py

## Fresh evidence

- unprotected nested child: PYC_GENERATED;
- protected nested child: NO_EXECUTABLE_CACHE;
- environment binding: PASS;
- candidate commit remains 929972ebc89e54c7d7d94b87346b2faf50823608;
- LEGACY_DEPENDENCY_COUNT = 0;
- result identity: d18d8457d68a23fb61b0329af29c0ee4a651409b21ad2d9bf6fa2f3cfe2e0af3.

## Product invariants

The active product root, active product-lock, protected rollback root, and candidate identities were not modified. No activation, VOICE, GUI, or time-based gate was executed.

## Next gate

Publish this exact checkpoint and perform fresh post-push closure. Any activation retry remains separately authorized.
