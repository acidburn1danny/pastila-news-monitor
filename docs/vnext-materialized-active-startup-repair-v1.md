# VNext Materialized ACTIVE Startup & Preflight Compatibility Repair v1

## Verdict

PASS + 0 BLOCKERS.

The materialized ACTIVE product now has one canonical path: `product.py -> ACTIVE preflight`. Integrated acceptance invokes the same startup before exercising the workflow and reaching `EXPORTED`. The standalone auditor executes both boundaries and rejects bypass.

## Identities

- Product lock: `63c547f5d5bb794a9a6d5b7aea3c71fd10dc418063494267ea3fbd03e8399646`
- Product-lock SHA-256: `ed053323071bca256fb76d59c459c4da83076cbc0b29d6d1791e9996792297ef`
- Active graph: `dcac0c59b8ebacc492e8c053e00894b03dd654d569617b325e78073e67a8239f`
- Standalone audit: `b03686ae1ffed07dee9fe4a6473722ea5536e77f9c86f1e6b0f5f46d923f7c74`

## Validation

Startup passed with explicit platform dependencies. Repository-unavailable standalone audit passed, E2E reached `EXPORTED` through canonical startup, and all nine fault probes failed closed. Repository and legacy dependency counts are zero. Active and rollback roots were not modified.