# VNext Active Preflight Product-Lock v5 Attestation Compatibility Repair v1

## Verdict

PASS + 0 BLOCKERS after bounded CARs and fresh audit restart.

## Root cause and repair

The active v8 preflight accepted only product-lock schema v4. The published attestation successor is schema v5, and the v10 active auditor also interpreted only the predecessor attestation shape. The repair adds semantic v5 validation to the canonical preflight and makes the active auditor validate either the frozen v4 predecessor or the current v5 receipt/authority chain. Identity checks remain fail-closed.

## Managed installation closure

The successor product-lock keeps the 30-path managed inventory and changes exactly four managed bytes before product-lock commit:

1. `app/cli/preflight.py`;
2. `app/cli/audit.py`;
3. `manifest/activation/vnext-activation-receipt-v1.json`;
4. `manifest/authorities/vnext-active-product-lock-successor-v1.json`.

The receipt and Active-State Authority retain their published identities. The preflight and auditor are now inventory-bound by the successor lock.

## Identities

- Activation Receipt: `1c5b0c103ba609408780f93b59ac98fec31d29151601ed20e5299cd8c8ce587f`;
- Active-State Authority: `1d53b5402e30251abf412aa649e3a3f231b59bddfd4628c2e5ee9141b532d7a8`;
- Product-lock successor: `b9609a71c07803ff58cd3e8980b8c8bb31cd717b538be68bdd76fa6b6914ecba`;
- Product-lock successor SHA-256: `233488e0ed2e0e1f273ced35bcaccd52e012d49544d86a9a45402f4fc7e5d12d`;
- Result identity: `51681aba791a8c3e1f58454ea9e39d61f0b9444d044a4efac779f4181e8bfee2`.

## Fresh validation

- dedicated tests: 4/4 PASS;
- active VNext suite: 482 PASS / 1 PRE_ACTIVATION_COMMIT_ONLY deselected;
- isolated overlay materialization: PASS;
- canonical preflight: PASS_PREFLIGHT;
- real startup: PASS_STARTUP_READY;
- live self-contained auditor: PASS;
- integrated E2E: EXPORTED;
- SQLite, R2, platform and canonical protected rollback closure: PASS;
- repository dependency count: 0;
- LEGACY_DEPENDENCY_COUNT: 0.

## CARs

1. The dedicated test initially imported the materialized preflight outside its runtime layout. The unnecessary import was removed and all affected validation restarted fresh.
2. A direct `python -I preflight.py` harness probe removed the script directory from `sys.path`. It was replaced with the canonical `product.py` startup path and validation restarted fresh.
3. The live-audit harness initially supplied the current rollback root while the canonical rollback manifest authorizes the protected historical root. The probe was corrected to the exact manifest binding and validation restarted fresh.
4. The repository-wide test invocation was replaced by the active VNext suite selector. The single frozen pre-activation node remains deselected and unmodified.

## Invariants

The active product, active product-lock, both rollback roots and published predecessor evidence remain unchanged. No waiting period was used. No installation was attempted.
