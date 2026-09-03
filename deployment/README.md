# Deployment boundary

The YAML files in this directory are intentionally outside `.github/workflows`
and contain unresolved tokens. They cannot trigger or acquire metadata.

The capture-orchestration core, production HTTPS adapter, cryptographic
initiation binding, and immutable action/container pins are frozen but inert.
Milestone 9 now separates offline request/response verification, one-shot
RFC-3161 transport, and attestation-only activation. See
`docs/architecture/milestone-9-proof-boundary.md`. Milestone 10 owns any later
publisher or registry metadata capability.
