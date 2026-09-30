# VNext Active-State Authority Attestation & Rollback Proof Repair v1

## Verdict

PASS + 0 BLOCKERS. This bounded successor repairs the two demonstrated authority gaps without changing either protected product root.

## Scope

- semantic `ACTIVATED` product-lock successor;
- content-addressed post-activation receipt;
- canonical rollback manifest;
- deterministic builder;
- self-contained auditor;
- dedicated reproduction and fault-injection tests;
- content-addressed terminal result.

## Authority semantics

The installed candidate remains immutable and is identified by product-lock identity `68fb2c347367ff3aa725cfb44de11be07921ad2e39fcbe98b01b389eee46c19b` and SHA-256 `0ff93c4d9f550c8458d2223ae91627903bf02dc24973c59d3069fa94ada1100e`. The successor records that immutable installed candidate while declaring the prospective active authority state as `ACTIVATED`.

The activation receipt is explicitly a post-activation attestation. It does not claim to have existed at swap time.

## Canonical rollback

Required rollback authority consists of the old product lock plus R2, Python/ML platform, EDITOR V0 runtime, SCOUT runtime and SCOUT state. `__pycache__`, `.pyc`, SQLite sidecars and journals are regenerable runtime bytes. VOICE candidates, reviews and bake-off runs are excluded because the old product lock does not declare them as active dependencies.

The earlier raw full-tree claim remains preserved as `UNRECONCILED_NON_AUTHORITATIVE`; it is not rewritten or fabricated. Every required managed component is freshly hashed in place.

## Validation

- active managed bytes and installed candidate lock: PASS;
- successor/receipt/rollback cross-binding: PASS;
- R2 byte closure: PASS;
- platform full-tree closure using the frozen algorithm: PASS;
- SQLite integrity: PASS;
- startup: `PASS_STARTUP_READY`;
- isolated E2E: `EXPORTED`;
- three atomic fault windows: PASS byte-exact recovery;
- isolated restore and controlled return: PASS;
- active and rollback roots unchanged: PASS;
- `LEGACY_DEPENDENCY_COUNT = 0`.

## Activation boundary

These artifacts are publication-safe design and evidence. They do not replace the active lock and do not mutate the active root. A later owner-authorized atomic successor activation is required before the semantic successor becomes active authority.
