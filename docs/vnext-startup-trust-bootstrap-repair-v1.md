# VNext Canonical Startup Trust Bootstrap & Executable Cache Exclusion Repair v1

Status: PASS + 0 BLOCKERS

Base: 12a3d3f49d366d6601266d9284652d3010b7d180

## Repair

- Canonical product entrypoint removes its directory from sys.path before non-builtin imports.
- Bootstrap verifies the complete managed inventory before importing product modules.
- Executable caches and sourceless bytecode are forbidden product bytes.
- Canonical preflight, startup, builder, and standalone auditor consume the same byte policy.
- Standalone auditor independently enforces exact component directories and exhaustive R2 inventory.
- Startup and E2E use isolated -I -B interpreter boundaries.

## Evidence

- Product lock: ec9c4f082c573e5815f8fd183e6191b037710ea0ebe96864e17177375c0cdb57
- Product lock SHA-256: e1b0b9b8750912db0da2f44950952282d29e369d54c8d24794c0ff55a25ff41c
- Active graph: 6e4310e4baf15a22adc4e5731115905e8ba421e6b6b7f3b761ac37a7053d0f9d
- Standalone audit: 65ae8fe54a28047051b2e0579999c75dbdb4b4b31fa0c78ece75154ca001c24d
- Adversarial matrix: 8/8
- Startup: PASS_STARTUP_READY
- Integrated E2E: EXPORTED
- Repository dependency count: 0
- Legacy dependency count: 0

The active product and protected rollback root were not modified. Audit streak remains 0/2.
