# Controlled Experiment Manifest Contract

## Purpose and scope

The controlled-experiment manifest is the canonical machine-readable summary of one
Scout revision-quality experiment. It records identity, lineage, frozen variables,
execution counts, integrity gates, aggregate results, decision, promotion state, and
the inventory of supporting evidence. Detailed scenario evidence remains in its
specialized artifact and is referenced by repository-relative path and SHA-256 hash.

The current contract is `scout_revision_quality_experiment_manifest` schema `1.0.0`,
contract version `1`. Unsupported schema or contract versions fail closed. A future
major version requires an explicit reader upgrade; additive evolution within a
supported version must remain compatible with the typed model.

## Canonical fields and lifecycle

The manifest is authoritative for experiment and run identity, lifecycle, baseline,
treatment, independent variable, hypothesis, prompt delta budget, provider and
benchmark fingerprints, planned and actual execution, integrity gates, aggregate
technical/reference/editorial/operational results, candidate decision, root
conclusion, promotion status, and artifact inventory. `COMPLETE` describes a valid
finished experiment; it does not imply that its candidate was effective or promoted.

Part 7H.2 is therefore an experiment-valid `PROMPT_EXPERIMENT` whose candidate is
`REJECT`, effectiveness is `FAIL`, and promotion is `NOT_PROMOTED`.

## Fingerprinting

Supporting artifact fingerprints are SHA-256 over raw file bytes. The validator
rejects missing required artifacts, unsafe/non-repository paths, unsupported hash
algorithms, and hash mismatches.

The manifest fingerprint is SHA-256 over canonical JSON with sorted keys and compact
separators. It excludes `manifest_fingerprint`, generation time, validation results,
and artifact hash/status values. Artifact identities, types, paths, and required flags
remain inside the boundary. This deliberate boundary resolves the circular linkage in
which benchmark history stores the manifest fingerprint while the manifest validates
the current benchmark-history byte hash.

## Validation and decision semantics

JSON Schema validates structure. The immutable Pydantic contracts and runtime
validator additionally enforce cross-field semantics: scenario totals, request and
response counts, zero retries/fallbacks/replays, technical and editorial totals,
reference totals, prompt-budget consistency, distinct control/treatment prompts,
decision-gate consistency, and promotion rules.

`ADOPT` requires passing technical, reference, and editorial gates. `REJECT` can never
promote. A targeted metric can move in its expected direction without overriding the
overall decision. Validation returns structured errors and warnings; unavailable
provider revision/API metadata is a warning, never a substituted value.

## Security

Manifests contain no credentials, API keys, bearer tokens, authorization headers,
environment values, raw provider secrets, or absolute user paths. Artifact paths are
POSIX-style repository-relative paths, and no artifact is executed or remotely
fetched during validation.

## Future experiment workflow

1. Complete the controlled experiment and freeze its supporting evidence.
2. Build a manifest using the reusable typed builder.
3. Link its stable manifest fingerprint into append-only benchmark metadata.
4. Rebuild artifact hashes, serialize canonical UTF-8 JSON, and emit JSON Schema.
5. Run runtime consistency and artifact validation before declaring completion.

Legacy Part 7C.2 and Part 7H evidence is complete enough for future backfill and is
classified `BACKFILL_READY`; this milestone creates only the required Part 7H.2
manifest. Validation failures are reported without repairing or reinterpreting the
historical experiment.

The canonical Part 7H.2 instance is
`docs/artifacts/experiments/part-7h-2/experiment-manifest.json`; its structural schema
is `docs/schemas/experiment-manifest.schema.json`.
