# Deployment boundary

The YAML file in this directory is intentionally outside `.github/workflows`
and contains unresolved tokens. It cannot trigger or acquire metadata.

Materialization is fail-closed until a later authorization supplies a frozen
capture executable, immutable action/container pins, the single scheduled UTC
event, its RFC-3161 precommit, and the final V2.3.7 deployment manifest.
