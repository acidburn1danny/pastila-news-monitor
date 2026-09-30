# VNext Active Integration Candidate Closure & Atomic Activation Semantics Repair v1

## Verdict

PASS + 0 BLOCKERS.

The inactive candidate is complete, self-contained, exhaustively inventoried, restorable, startup-capable, and able to execute the integrated core E2E from its materialized SQLite state. The active product root and active product lock were not modified.

## Identities

- Result identity: `3dec31b7632497eb0855922b975396f6a0ca7446fa908c3481eaabe359283e27`
- Candidate product lock identity: `68fb2c347367ff3aa725cfb44de11be07921ad2e39fcbe98b01b389eee46c19b`
- Candidate product lock SHA-256: `0ff93c4d9f550c8458d2223ae91627903bf02dc24973c59d3069fa94ada1100e`
- Active dependency graph: `f393b101ae5bf1dcab73775d463307765bf9a24568c8d045d4284aebac4d415e`
- Platform semantics authority: `b36072106b26922166662fdafcf06afa54022f8d1e289c7490ab4cb0822a548d`
- Frozen platform authority: `ef5318bfa36af16350ec96d16ef84eb8b55c527894c3c5045f08d4b9ba1bc498`
- Stable platform content: `93a314b96a2e687ed76c298f440d426681c49d446bec5edfe0cb175fa9dd82fd`
- R2 dependency lock: `53fafbc03f70c8c32357645a6a428260f1bdfbd104edbe1c4aa825e95c83a10f`
- Runtime source commit: `c211a07551284627a8e23c6e84d7dbf7e1125681`
- Assembly boundary commit: `a65095dc0b362fcbba6439d64cc5af4ae9d294ff`

## Closure

- Candidate files: 24846
- Candidate bytes: 33317267323
- Application inventory: 24 files
- Deterministic rebuild: 2/2 byte-exact
- Clean-room restore: PASS
- Startup: PASS_STARTUP_READY
- Integrated E2E: PASS, terminal state EXPORTED
- Full-root atomic fault windows: BEFORE_BACKUP, AFTER_BACKUP, AFTER_ACTIVATE PASS
- Rollback: exhaustive full-tree byte-exact
- Extra byte rejection: PASS
- Host platform dependency verification: PASS
- LEGACY_DEPENDENCY_COUNT: 0

## CAR

1. Canonicalized bootstrap and runtime state ownership under `vnext-product-runtime-v1`.
2. Separated immutable application bytes from mutable SQLite runtime state while retaining a content-addressed bootstrap and pristine-staging gate.

3. Replaced lock-only rollback evidence with exhaustive tree identities over files, directories and symlinks for both roots.

Every affected result was invalidated and reproduced fresh after repair.

## Product invariants

- `/root/pastila-vnext/v1` remained unchanged.
- Active product-lock SHA-256 remained `2ddc484171f3b58f0f10ce4c4c73c1db51323d5c545320c578dc17ebb3edb4e6`.
- `/root/pastila-vnext/v2` remained absent.
- Active integration was not executed.
- Product-lock replacement was not executed.
- No model load or inference occurred.
