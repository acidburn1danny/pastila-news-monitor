# VNext Active Integration Candidate Closure & Atomic Activation Semantics Repair v1

## Verdict

PASS + 0 BLOCKERS.

The inactive candidate is complete, self-contained, exhaustively inventoried, restorable, startup-capable, and able to execute the integrated core E2E from its materialized SQLite state. The active product root and active product lock were not modified.

## Identities

- Result identity: `f56dd9edd429ed265b97f89b4508a1efe7c951b546ed55c1c57893a403a3bee1`
- Candidate product lock identity: `28e930dc7725f71fc9ae8b8256cbec860ef409ec7034cf35c19da60a9055f9ca`
- Candidate product lock SHA-256: `d33118308cc38c728dfc0a9c59a8d35ff54bc2f8d3b8671ccbe11f2aa2e3c522`
- Active dependency graph: `f393b101ae5bf1dcab73775d463307765bf9a24568c8d045d4284aebac4d415e`
- Platform semantics authority: `b36072106b26922166662fdafcf06afa54022f8d1e289c7490ab4cb0822a548d`
- Frozen platform authority: `ef5318bfa36af16350ec96d16ef84eb8b55c527894c3c5045f08d4b9ba1bc498`
- Stable platform content: `93a314b96a2e687ed76c298f440d426681c49d446bec5edfe0cb175fa9dd82fd`
- R2 dependency lock: `53fafbc03f70c8c32357645a6a428260f1bdfbd104edbe1c4aa825e95c83a10f`
- Runtime source commit: `c211a07551284627a8e23c6e84d7dbf7e1125681`
- Assembly boundary commit: `f84a9c6b493e7f54de3ea47f7fd97441af3d3db2`

## Closure

- Candidate files: 24846
- Candidate bytes: 33317267323
- Application inventory: 24 files
- Deterministic rebuild: 2/2 byte-exact
- Clean-room restore: PASS
- Startup: PASS_STARTUP_READY
- Integrated E2E: PASS, terminal state EXPORTED
- Full-root atomic fault windows: BEFORE_BACKUP, AFTER_BACKUP, AFTER_ACTIVATE PASS
- Rollback: byte-exact
- Extra byte rejection: PASS
- Host platform dependency verification: PASS
- LEGACY_DEPENDENCY_COUNT: 0

## CAR

1. Canonicalized bootstrap and runtime state ownership under `vnext-product-runtime-v1`.
2. Separated immutable application bytes from mutable SQLite runtime state while retaining a content-addressed bootstrap and pristine-staging gate.

Every affected result was invalidated and reproduced fresh after repair.

## Product invariants

- `/root/pastila-vnext/v1` remained unchanged.
- Active product-lock SHA-256 remained `2ddc484171f3b58f0f10ce4c4c73c1db51323d5c545320c578dc17ebb3edb4e6`.
- `/root/pastila-vnext/v2` remained absent.
- Active integration was not executed.
- Product-lock replacement was not executed.
- No model load or inference occurred.
