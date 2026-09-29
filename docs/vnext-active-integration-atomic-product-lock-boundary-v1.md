# VNext Active Integration & Atomic Product-Lock Replacement Boundary v1

## Verdict

PASS + 0 BLOCKERS. Candidatul este pregătit și verificat, dar nu este activat.

## Boundary

Sursa este commitul publicat `c211a07551284627a8e23c6e84d7dbf7e1125681`. Closure-ul candidatului conține numai graful activ: foundation/workflow/SQLite, SCOUT, SourcePacket, R2/EDITOR, factual acceptance, policy, deterministic FINAL, orchestrator, configurația surselor, authorities active, R2 și platforma Python ML.

VOICE candidates, frozen evaluation evidence, review receipts și runtime-urile legacy sunt excluse.

## Evidence

- Candidate product-lock identity: `e96b9d34256b4dc24621f1c76531c849cb08c95ee54c35a2b686e65717c2d48b`
- Boundary identity: `5acd4c7052c105e1333709b88a6522ea52fe56b6457efe581943caf312c883ca`
- R2 lock identity: `53fafbc03f70c8c32357645a6a428260f1bdfbd104edbe1c4aa825e95c83a10f`
- Materialized closure: 24,593 files, 33,313,379,068 bytes
- Deterministic rebuild: PASS (2/2 identical locks)
- Dependency preflight: PASS
- Clean-room restore with source candidate unavailable: PASS
- Integrated deterministic E2E through EXPORTED: PASS
- Acceptance identity: `9a1aaedf88f90d639bb431645d3f3f2c7b7805d842342088df074631fa27d79b`
- Atomic swap and byte-exact rollback simulation: PASS
- LEGACY_DEPENDENCY_COUNT: 0
- Model load / inference: false / false

## CAR

1. Cross-filesystem reflink was unsupported. Replaced it with an independent physical copy and restarted evidence.
2. The historical platform tree identity included mutable Python caches. The candidate lock now hashes stable platform content while excluding only `__pycache__` and `.pyc`; all executable dependency bytes remain materialized.
3. The legacy scan initially matched its own marker literals. Markers are constructed without embedding the forbidden complete paths, then the audit was restarted.
4. The deterministic acceptance backend used the wrong prompt parser and then the wrong FINAL identity key. Both were corrected and all affected evidence was rebuilt fresh.

## Activation gate

The active product root `/root/pastila-vnext/v1` and its product lock remain unchanged. Actual root mutation and product-lock replacement require separate owner authorization. The candidate and restore roots are temporary validation workspaces.
